from __future__ import annotations

from datetime import datetime
from math import floor, log10
from pathlib import Path
from typing import Iterable, Optional, Tuple
import re

import numpy as np


E_CHARGE = 1.6022e-19
ELECTRON_MASS = 9.1e-31
PROTON_MASS = 1.67e-27

Range = Optional[Tuple[float, float]]

ATOMIC_MASS_AMU = {
    "Hydrogen": 1.0,
    "Helium": 4.0,
    "Nitrogen": 14.0,
    "Argon": 39.9,
    "Xenon": 131.3,
    "Neon": 20.18,
}


class LangmuirProbeAnalysis:
    """Standalone single Langmuir probe analysis from voltage/current arrays.

    The class is intentionally small and file-format independent: pass the
    measured voltage and current sequences directly to ``__init__`` and run the
    analysis with ``analyze()``.

    The numerical procedure is the same four-parameter SLP fit used in
    ``anlang_yokogawa_file_singolo_2.py``:

        I(V) = Is * (1 + R * (V - Vf)) * (exp((V - Vf) / Te) - 1)

    followed by the same plasma-parameter estimates using the supplied exposed
    probe area:

        area = probe_area_m2
        alpha = 0.5 * (log(mi / (2 * pi * me)) + 1)
        cs = sqrt(e * Te / mi)
        n = 2 * Is / (e * cs * area)
        Vp = Vf + alpha * Te

    Public use is intentionally compact: initialize the class, call
    ``analyze()``, and optionally call ``plot_fits()`` to inspect the latest
    fit.
    """

    def __init__(self, 
                 voltage: Iterable[float], 
                 current: Iterable[float], 
                 time: Iterable[float] | None = None, 
                 dataset_name: str = "single_langmuir_dataset", 
                 output_dir: str | Path = ".", 
                 plot_dir: str | Path | None = None, 
                 log_dir: str | Path | None = None) -> None:
        self.dataset_name = str(dataset_name).strip() or "single_langmuir_dataset"
        self.output_dir = Path(output_dir)
        self.plot_dir = Path(plot_dir) if plot_dir is not None else self.output_dir / "plots"
        self.log_dir = Path(log_dir) if log_dir is not None else self.output_dir / "logs"

        voltage_array = np.asarray(voltage, dtype=float)
        current_array = np.asarray(current, dtype=float)
        time_array = None if time is None else np.asarray(time, dtype=float)

        if voltage_array.shape != current_array.shape:
            raise ValueError("voltage and current must have the same shape.")
        if voltage_array.ndim != 1:
            raise ValueError("voltage and current must be one-dimensional arrays.")
        if time_array is not None and time_array.shape != voltage_array.shape:
            raise ValueError("time, voltage and current must have the same shape.")

        mask = np.isfinite(voltage_array) & np.isfinite(current_array)
        if time_array is not None:
            mask &= np.isfinite(time_array)
        if int(mask.sum()) < 6:
            raise ValueError("At least 6 finite samples are required.")

        self.time = None if time_array is None else time_array[mask]
        self.time_voltage = voltage_array[mask]
        self.time_current = current_array[mask]

        order = np.argsort(voltage_array[mask])
        self.voltage = voltage_array[mask][order]
        self.current = current_array[mask][order]

        self._last_results: dict[str, object] | None = None


    def analyze(self,
                probe_area_m2: float,
                ion_mass_amu: float | str = ATOMIC_MASS_AMU["Argon"],
                probe_conf: str = "single",
                voltage_range: Range = None,
                current_range: Range = None,
                initial_te_ev: float = 2.0,
                initial_r: float = 0.0,
                write_log: bool = True,
                log_path: str | Path | None = None,
                append_parameters_table: bool = False,
                parameters_table_path: str | Path = "parametri_plasma.txt",
                probe_name: str = "") -> dict[str, object]:
        """Run the SLP or DLP analysis depending on probe_conf.

        Parameters
        ----------
        probe_area_m2:
            Exposed probe collection area in square metres.
        ion_mass_amu:
            Ion mass in atomic mass units, or one of the keys in
            ``ATOMIC_MASS_AMU`` such as ``"Argon"``.
        probe_conf:
            Probe configuration: ``"single"`` for a single Langmuir probe
            (four-parameter fit) or ``"double"`` for a double Langmuir probe
            (three-parameter tanh fit).  Raises ``ValueError`` for any other
            value.
        voltage_range:
            Fit voltage interval ``(Vmin, Vmax)``. If omitted, all voltages are
            used.
        current_range:
            Optional fit current interval ``(Imin, Imax)``.
        initial_te_ev, initial_r:
            Initial guesses for the fit.  For the double probe, ``initial_r``
            is used as the initial conductance G [A/V].
        write_log:
            If true, write a text report to disk.
        append_parameters_table:
            If true, append the compact legacy parameter table.

        Returns
        -------
        dict[str, object]
            Scalar plasma parameters, fit arrays, covariance, and a text report.
        """

        if probe_conf not in ("single", "double"):
            raise ValueError(
                f"probe_conf must be 'single' or 'double', got {probe_conf!r}."
            )

        xfit, yfit = self._select_fit_region(voltage_range, current_range)
        ion_mass_value = self._normalize_ion_mass(ion_mass_amu)
        ion_mass_kg = PROTON_MASS * ion_mass_value
        area_m2 = self._validate_probe_area_m2(probe_area_m2)
        area_mm2 = area_m2 * 1e6

        # ---- single probe: 4-parameter fit --------------------------------
        if probe_conf == "single":
            vf_guess = self._floating_potential_guess()
            p0 = np.array([initial_te_ev, yfit[0], vf_guess, initial_r], dtype=float)
            popt, pcov = self._curve_fit(xfit, yfit, p0, probe_conf="single")
            fitted = self._langmuir_characteristic_4par(xfit, *popt)

            te, isat, vf, r_corr = [float(v) for v in popt]
            alpha = 0.5 * (np.log(ion_mass_kg / (2.0 * np.pi * ELECTRON_MASS)) + 1.0)
            try:
                sound_speed = float(np.sqrt(E_CHARGE * te / ion_mass_kg))
                density = float(2.0 * isat / (E_CHARGE * sound_speed * area_m2))
            except Exception:
                sound_speed = float("nan")
                density = 0.0
            plasma_potential = float(vf + alpha * te)
            r_squared = self._r_squared(yfit, fitted)

            results: dict[str, object] = {
                "probe_configuration": "single",
                "electron_temperature_ev": te,
                "electron_density_m-3": density,
                "ion_saturation_current_a": isat,
                "floating_potential_v": vf,
                "plasma_potential_v": plasma_potential,
                "slope_correction_r": r_corr,
                "sound_speed_m_s-1": sound_speed,
                "probe_area_m2": float(area_m2),
                "probe_area_mm2": float(area_mm2),
                "ion_mass_amu": float(ion_mass_value),
                "ion_mass_kg": float(ion_mass_kg),
                "alpha": float(alpha),
                "fit_r2": float(r_squared),
                "fit_parameters": {
                    "Te_eV": te,
                    "Is_A": isat,
                    "Vf_V": vf,
                    "R": r_corr,
                },
                "fit_covariance": np.asarray(pcov, dtype=float),
                "fit_voltage_v": np.asarray(xfit, dtype=float),
                "fit_current_a": np.asarray(yfit, dtype=float),
                "fitted_current_a": np.asarray(fitted, dtype=float),
                "voltage_range": voltage_range,
                "current_range": current_range,
            }

        # ---- double probe: 3-parameter tanh fit ---------------------------
        else:
            isat_guess = float(np.max(np.abs(yfit)) / 2.0)
            p0 = np.array([initial_te_ev, isat_guess, initial_r], dtype=float)
            popt, pcov = self._curve_fit(xfit, yfit, p0, probe_conf="double")
            fitted = self._langmuir_characteristic_double(xfit, *popt)

            te, isat, g_corr = [float(v) for v in popt]
            try:
                sound_speed = float(np.sqrt(E_CHARGE * te / ion_mass_kg))
                density = float(2.0 * isat / (E_CHARGE * sound_speed * area_m2))
            except Exception:
                sound_speed = float("nan")
                density = 0.0
            r_squared = self._r_squared(yfit, fitted)

            results = {
                "probe_configuration": "double",
                "electron_temperature_ev": te,
                "electron_density_m-3": density,
                "ion_saturation_current_a": isat,
                "conductance_correction_g": g_corr,
                "sound_speed_m_s-1": sound_speed,
                "probe_area_m2": float(area_m2),
                "probe_area_mm2": float(area_mm2),
                "ion_mass_amu": float(ion_mass_value),
                "ion_mass_kg": float(ion_mass_kg),
                "fit_r2": float(r_squared),
                "fit_parameters": {
                    "Te_eV": te,
                    "Is_A": isat,
                    "G": g_corr,
                },
                "fit_covariance": np.asarray(pcov, dtype=float),
                "fit_voltage_v": np.asarray(xfit, dtype=float),
                "fit_current_a": np.asarray(yfit, dtype=float),
                "fitted_current_a": np.asarray(fitted, dtype=float),
                "voltage_range": voltage_range,
                "current_range": current_range,
            }

        report = self._format_report(results)
        results["report"] = report
        self._last_results = results

        if write_log:
            written_log_path = self._save_log(report, log_path)
            results["log_path"] = str(written_log_path)

        if append_parameters_table:
            table_path = self._append_parameters_table(
                results,
                parameters_table_path,
                probe_name,
            )
            results["parameters_table_path"] = str(table_path)

        return results


    def plot_fits(self, save_path: str | Path | None = None,
                  show: bool = True):
        """Plot the measured I-V curve and the latest fit (single or double probe)."""

        if self._last_results is None:
            raise ValueError("No fit available. Run analyze() first.")

        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ImportError(
                "plot_fits requires matplotlib. Install it or call analyze() only."
            ) from exc

        results = self._last_results
        probe_conf = str(results["probe_configuration"])
        fit_voltage = np.asarray(results["fit_voltage_v"], dtype=float)
        fit_current = np.asarray(results["fitted_current_a"], dtype=float)
        selected_current = np.asarray(results["fit_current_a"], dtype=float)

        plot_path = Path(save_path) if save_path is not None else self._default_output_path(
            "fits",
            ".png",
            self.plot_dir,
        )
        plot_path.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(
            self.voltage,
            self.current,
            ".",
            color="0.35",
            markersize=4,
            label="Measured Points",
        )
        ax.plot(
            fit_voltage,
            selected_current,
            ".",
            color="#1f77b4",
            markersize=5,
            label="Fitted Data Points",
        )

        te = float(results["electron_temperature_ev"])
        ne = float(results["electron_density_m-3"])

        ax.plot(
            fit_voltage,
            fit_current,
            "r-",
            linewidth=2.2,
        )
        ax.axhline(0.0, color="green", linestyle="--", linewidth=1.2)

        if probe_conf == "single":
            ax.axvline(
                float(results["floating_potential_v"]),
                color="#9467bd",
                linestyle="--",
                linewidth=1.2,
                label=f"Vf",
            )
            ax.axvline(
                float(results["plasma_potential_v"]),
                color="#ff7f0e",
                linestyle="--",
                linewidth=1.2,
                label=f"Vp",
            )

        conf_label = "Single probe" if probe_conf == "single" else "Double probe"
        ax.set_title(f"Langmuir characteristic ({conf_label}) - {self.dataset_name}", fontsize=18)
        ax.set_xlabel("Voltage [V]", fontsize=16)
        ax.set_ylabel("Current [A]", fontsize=16)
        ax.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2))
        ax.tick_params(axis="both", labelsize=16)
        ax.grid(True, color="0.88")
        ax.legend(frameon=True, fontsize=16)
        fig.savefig(plot_path, dpi=220, bbox_inches="tight")

        if show:
            plt.show()
        return fig, ax


    def plot_i_vs_v(self, save_path: str | Path | None = None,
                    show: bool = True):
        """Plot the measured current as a function of voltage."""

        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ImportError(
                "plot_i_vs_v requires matplotlib. Install it or call analyze() only."
            ) from exc

        plot_path = Path(save_path) if save_path is not None else self._default_output_path(
            "i-v",
            ".png",
            self.plot_dir,
        )
        plot_path.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(
            self.voltage,
            self.current,
            ".",
            color="0.35",
            markersize=4,
            label="Measured I-V",
        )
        ax.axhline(0.0, color="green", linestyle="--", linewidth=1.2)

        ax.set_title(f"I-V characteristic - {self.dataset_name}", fontsize=18)
        ax.set_xlabel("Voltage [V]", fontsize=16)
        ax.set_ylabel("Current [A]", fontsize=16)
        ax.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2))
        ax.tick_params(axis="both", labelsize=16)
        ax.grid(True, color="0.88")
        ax.legend(frameon=True, fontsize=16)
        fig.savefig(plot_path, dpi=220, bbox_inches="tight")

        if show:
            plt.show()
        return fig, ax


    def plot_time_series(self, save_dir: str | Path | None = None,
                         show: bool = True,
                         statistics: bool = True) -> dict[str, dict[str, object]]:
        """Plot V(t) and I(t), optionally adding mean and noise statistics."""

        if self.time is None:
            raise ValueError(
                "No time array available. Pass time=... when creating the probe."
            )

        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ImportError(
                "plot_time_series requires matplotlib. Install it or call analyze() only."
            ) from exc

        output_dir = Path(save_dir) if save_dir is not None else self.plot_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        plot_specs = {
            "voltage": {
                "suffix": "voltage_time",
                "values": self.time_voltage,
                "quantity_label": "Voltage",
                "ylabel": "Voltage [V]",
                "unit": "V",
            },
            "current": {
                "suffix": "current_time",
                "values": self.time_current,
                "quantity_label": "Current",
                "ylabel": "Current [A]",
                "unit": "A",
            },
        }

        outputs: dict[str, dict[str, object]] = {}
        for quantity, spec in plot_specs.items():
            values = np.asarray(spec["values"], dtype=float)
            mean_value = float(np.mean(values))
            noise_values = values - mean_value
            noise_value = float(np.sqrt(np.mean(noise_values ** 2)))
            plot_path = self._default_output_path(
                str(spec["suffix"]),
                ".png",
                output_dir,
            )

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(
                self.time,
                values,
                ".",
                color="0.35",
                markersize=4,
                label=f"Measured {spec['quantity_label']}",
            )
            if statistics:
                ax.axhline(
                    mean_value,
                    color="r",
                    linestyle="-",
                    linewidth=2.2,
                    label=(
                        f"Mean {spec['quantity_label']}"
                    ),
                )

            ax.set_title(f"{spec['quantity_label']} vs time - {self.dataset_name}", fontsize=18)
            ax.set_xlabel("Time [s]", fontsize=16)
            ax.set_ylabel(str(spec["ylabel"]), fontsize=16)
            ax.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2))
            ax.tick_params(axis="both", labelsize=16)
            ax.grid(True, color="0.88")
            if statistics:
                ax.legend(frameon=True, fontsize=16)
            fig.savefig(plot_path, dpi=220, bbox_inches="tight")

            outputs[quantity] = {
                "fig": fig,
                "ax": ax,
                "path": plot_path,
                "mean": mean_value,
                "noise": noise_value,
            }

        if show:
            plt.show()
        return outputs




    @staticmethod
    def _langmuir_characteristic_4par(voltage: Iterable[float] | np.ndarray, 
                                      electron_temperature_ev: float,
                                      saturation_current_a: float,
                                      floating_potential_v: float, 
                                      slope_correction: float) -> np.ndarray:
        voltage = np.asarray(voltage, dtype=float)
        with np.errstate(over="ignore", invalid="ignore"):
            return saturation_current_a * (
                1.0 + slope_correction * (voltage - floating_potential_v)
            ) * (np.exp((voltage - floating_potential_v) / electron_temperature_ev) - 1.0)


    @staticmethod
    def _langmuir_characteristic_double(voltage: Iterable[float] | np.ndarray,
                                        electron_temperature_ev: float,
                                        saturation_current_a: float,
                                        slope_correction: float) -> np.ndarray:
        """Three-parameter double probe I-V model.

        I(V) = Is * tanh(V / (2 * Te)) + G * V

        Parameters
        ----------
        voltage:
            Differential voltage between the two probes [V].
        electron_temperature_ev:
            Electron temperature [eV].
        saturation_current_a:
            Ion saturation current [A].
        slope_correction:
            Conductance G accounting for finite slope in saturation [A/V].
        """
        voltage = np.asarray(voltage, dtype=float)
        with np.errstate(over="ignore", invalid="ignore"):
            return saturation_current_a * np.tanh(
                voltage / (2.0 * electron_temperature_ev)
            ) + slope_correction * voltage


    def _curve_fit(self,
                   voltage: np.ndarray,
                   current: np.ndarray,
                   initial_parameters: np.ndarray,
                   probe_conf: str = "single") -> tuple[np.ndarray, np.ndarray]:
        try:
            from scipy.optimize import curve_fit
        except ImportError as exc:
            raise ImportError(
                "LangmuirProbeAnalysis requires scipy.optimize.curve_fit for the "
                "four-parameter SLP fit."
            ) from exc

        model = (
            self._langmuir_characteristic_4par
            if probe_conf == "single"
            else self._langmuir_characteristic_double
        )
        return curve_fit(
            model,
            voltage,
            current,
            p0=initial_parameters,
            method="lm",
            maxfev=10000,
        )


    @staticmethod
    def _resolve_voltage_range(voltage_range: Range, 
                               voltage_window: Range) -> Range:
        if voltage_range is not None and voltage_window is not None:
            if tuple(voltage_range) != tuple(voltage_window):
                raise ValueError("Use either voltage_range or voltage_window, not both.")
        return voltage_range if voltage_range is not None else voltage_window


    def _select_fit_region(self, 
                           voltage_range: Range, 
                           current_range: Range) -> tuple[np.ndarray, np.ndarray]:
        mask = np.ones_like(self.voltage, dtype=bool)
        if voltage_range is not None:
            lo, hi = sorted(voltage_range)
            mask &= (self.voltage > lo) & (self.voltage < hi)
        if current_range is not None:
            lo, hi = sorted(current_range)
            mask &= (self.current > lo) & (self.current < hi)

        xfit = self.voltage[mask]
        yfit = self.current[mask]
        if xfit.size < 4:
            raise ValueError("The selected fit region must contain at least 4 points.")
        return xfit, yfit

    def _floating_potential_guess(self) -> float:
        try:
            vf1 = self.voltage[np.where(self.current >= 0.0)][0]
            vf2 = self.voltage[np.where(self.current <= 0.0)][-1]
            return float((vf1 + vf2) / 2.0)
        except Exception:
            return 0.0


    @staticmethod
    def _validate_probe_area_m2(probe_area_m2: float) -> float:
        area_m2 = float(probe_area_m2)
        if area_m2 <= 0 or not np.isfinite(area_m2):
            raise ValueError("Probe area must be positive and finite.")
        return area_m2


    @staticmethod
    def _normalize_ion_mass(ion_mass_amu: float | str) -> float:
        if isinstance(ion_mass_amu, str):
            stripped = ion_mass_amu.strip()
            if stripped in ATOMIC_MASS_AMU:
                return float(ATOMIC_MASS_AMU[stripped])
            return float(stripped)
        return float(ion_mass_amu)


    @staticmethod
    def _r_squared(values: np.ndarray, fitted: np.ndarray) -> float:
        ss_res = float(np.sum((values - fitted) ** 2))
        ss_tot = float(np.sum((values - np.mean(values)) ** 2))
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0


    def _format_report(self, results: dict[str, object]) -> str:
        probe_conf = str(results["probe_configuration"])
        te = float(results["electron_temperature_ev"])
        ne = float(results["electron_density_m-3"])
        isat = float(results["ion_saturation_current_a"])

        if probe_conf == "single":
            title = f"Single Langmuir probe analysis: {self.dataset_name}"
            model_line = "  I = Is * (1 + R * (V - Vf)) * (exp((V - Vf) / Te) - 1)"
            extra_params = [
                f"  Floating potential Vf:   {float(results['floating_potential_v']):.6g} V",
                f"  Plasma potential Vp:     {float(results['plasma_potential_v']):.6g} V",
                f"  R correction:            {float(results['slope_correction_r']):.6g}",
            ]
            extra_derived = [
                f"  Alpha:                   {float(results['alpha']):.6g}",
            ]
        else:
            title = f"Double Langmuir probe analysis: {self.dataset_name}"
            model_line = "  I = Is * tanh(V / (2 * Te)) + G * V"
            extra_params = [
                f"  Conductance correction G:{float(results['conductance_correction_g']):.6g} A/V",
            ]
            extra_derived = []

        lines = [
            title,
            "=" * (len(title)),
            f"Samples available:         {self.voltage.size:d}",
            f"Samples fitted:            {len(results['fit_voltage_v']):d}",
            f"Voltage range:             {self.voltage[0]:.4g} to {self.voltage[-1]:.4g} V",
            f"Current range:             {np.min(self.current):.4e} to {np.max(self.current):.4e} A",
            "",
            "Fit model",
            model_line,
            "",
            "Plasma parameters",
            f"  Electron temperature Te: {te:.6g} eV",
            f"  Electron density n:      {ne:.6e} m^-3",
            f"  Ion saturation Is:       {isat:.6e} A",
            *extra_params,
            "",
            "Derived quantities",
            f"  Probe area:              {float(results['probe_area_m2']):.6e} m^2",
            f"  Ion mass:                {float(results['ion_mass_amu']):.6g} amu",
            f"  Sound speed:             {float(results['sound_speed_m_s-1']):.6e} m/s",
            *extra_derived,
            "",
            "Fit quality",
            f"  R-squared:               {float(results['fit_r2']):.6f}",
            "",
            "Fit data",
            "  voltage_V, current_A, fitted_current_A",
        ]

        for voltage, current, fitted in zip(
            np.asarray(results["fit_voltage_v"], dtype=float),
            np.asarray(results["fit_current_a"], dtype=float),
            np.asarray(results["fitted_current_a"], dtype=float),
        ):
            lines.append(f"  {voltage:.8g}, {current:.8g}, {fitted:.8g}")
        return "\n".join(lines)


    def _save_log(self, report: str, path: str | Path | None) -> Path:
        log_path = Path(path) if path is not None else self._default_output_path(
            "log",
            ".log",
            self.log_dir,
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        probe_conf = str(self._last_results["probe_configuration"]) if self._last_results else "unknown"
        fit_procedure = (
            "Four-parameter SLP fit" if probe_conf == "single"
            else "Three-parameter DLP tanh fit"
        )
        text = "\n".join(
            [
                report,
                "",
                "Analysis metadata",
                f"  Created at:              {datetime.now().isoformat(timespec='seconds')}",
                f"  Probe configuration:     {probe_conf}",
                f"  Fit procedure:           {fit_procedure}",
                "",
            ]
        )
        log_path.write_text(text, encoding="utf-8")
        return log_path


    def _append_parameters_table(
        self,
        results: dict[str, object],
        path: str | Path,
        probe_name: str,
    ) -> Path:
        table_path = Path(path)
        if table_path.parent != Path("."):
            table_path.parent.mkdir(parents=True, exist_ok=True)

        probe_conf = str(results["probe_configuration"])

        if probe_conf == "single":
            header = "\t".join([
                "filename", "sonda", "Te [eV]", "ne [m-3]",
                "Is [A]", "Vf [V]", "Vp [V]", "R",
            ])
            row = "\t".join([
                self.dataset_name,
                probe_name,
                str(self._round_sig(float(results["electron_temperature_ev"]))),
                str(self._round_sig(float(results["electron_density_m-3"]))),
                str(self._round_sig(float(results["ion_saturation_current_a"]))),
                str(self._round_sig(float(results["floating_potential_v"]))),
                str(self._round_sig(float(results["plasma_potential_v"]))),
                str(self._round_sig(float(results["slope_correction_r"]))),
            ])
        else:
            header = "\t".join([
                "filename", "sonda", "Te [eV]", "ne [m-3]",
                "Is [A]", "G [A/V]",
            ])
            row = "\t".join([
                self.dataset_name,
                probe_name,
                str(self._round_sig(float(results["electron_temperature_ev"]))),
                str(self._round_sig(float(results["electron_density_m-3"]))),
                str(self._round_sig(float(results["ion_saturation_current_a"]))),
                str(self._round_sig(float(results["conductance_correction_g"]))),
            ])

        needs_header = not table_path.exists() or table_path.stat().st_size == 0
        with table_path.open("a", encoding="utf-8") as file_object:
            if needs_header:
                file_object.write(header)
            file_object.write("\n")
            file_object.write(row)
        return table_path


    def _default_output_path(self, suffix: str, extension: str, directory: str | Path) -> Path:
        safe_name = self._safe_filename(self.dataset_name)
        return Path(directory) / f"{safe_name}_{suffix}{extension}"


    @staticmethod
    def _safe_filename(name: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
        return safe.strip("._") or "single_langmuir_dataset"


    @staticmethod
    def _round_sig(x: float, sig: int = 4) -> float:
        if x == 0 or not np.isfinite(x):
            return float(x)
        return round(x, sig - int(floor(log10(abs(x)))) - 1)
