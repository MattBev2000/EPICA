from EPICA import EPICAFolderReader
from pathlib import Path

import csv
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime



ADC_BITS = 16
REFERENCE_ENOB = 14.2  # Reference value for the 78.125 kHz configuration.


# ----------------------------------------------------------------------------------------
# Path confguration 
# ----------------------------------------------------------------------------------------
BASE_PATH = Path(__file__).resolve().parent
PLOT_PATH = BASE_PATH / "plots"
LOGS_PATH = BASE_PATH / "logs"


# ----------------------------------------------------------------------------------------
# Noise analysis methods
# ----------------------------------------------------------------------------------------
def _to_numeric_array(sequence):
    data = np.asarray(sequence, dtype=float)
    if data.size == 0:
        raise ValueError("La sequenza non puo essere vuota.")
    if not np.all(np.isfinite(data)):
        raise ValueError("La sequenza deve contenere solo valori numerici finiti.")
    return data


def calculate_signal_vrms(sequence):
    data = _to_numeric_array(sequence)
    return np.sqrt(np.mean(data**2))


def calculate_vrms(sequence):
    return calculate_signal_vrms(sequence)


def calculate_noise_vrms(sequence):
    data = _to_numeric_array(sequence)
    centered_data = data - np.mean(data)
    return np.sqrt(np.mean(centered_data**2))


def calculate_std(sequence):
    data = _to_numeric_array(sequence)
    return np.std(data)


def calculate_mean(sequence):
    data = _to_numeric_array(sequence)
    return np.mean(data)


def calculate_lsb(sequence):
    data = _to_numeric_array(sequence)
    levels = np.unique(data)
    if levels.size < 2:
        return np.nan

    steps = np.diff(levels)
    steps = steps[steps > 0]
    if steps.size == 0:
        return np.nan

    return np.median(steps)


def calculate_resolution(sequence):
    return calculate_effective_resolution(sequence)


def calculate_fsr(sequence, full_scale_range=None):
    if full_scale_range is not None:
        return float(full_scale_range)

    lsb = calculate_lsb(sequence)
    if not np.isfinite(lsb):
        return np.nan
    return lsb * (2**ADC_BITS)


def calculate_ideal_quantization_noise(sequence, full_scale_range=None):
    if full_scale_range is not None:
        return float(full_scale_range) / (2**ADC_BITS) / np.sqrt(12)

    lsb = calculate_lsb(sequence)
    if not np.isfinite(lsb):
        return np.nan
    return lsb / np.sqrt(12)


def calculate_reference_noise(sequence, full_scale_range=None):
    fsr = calculate_fsr(sequence, full_scale_range)
    if not np.isfinite(fsr):
        return np.nan
    return fsr / ((2**REFERENCE_ENOB) * np.sqrt(12))


def calculate_enob_from_noise(sequence, full_scale_range=None):
    noise_vrms = calculate_noise_vrms(sequence)
    fsr = calculate_fsr(sequence, full_scale_range)
    if noise_vrms <= 0 or not np.isfinite(fsr):
        return np.nan
    return np.log2(fsr / (noise_vrms * np.sqrt(12)))


def calculate_effective_resolution(sequence, enob=None, full_scale_range=None):
    data = _to_numeric_array(sequence)
    fsr = calculate_fsr(data, full_scale_range)
    if enob is None:
        enob = calculate_enob_from_noise(data, full_scale_range)

    if not np.isfinite(fsr) or not np.isfinite(enob):
        return np.nan

    return fsr / (2**enob)


def calculate_noise_recap(sequence, full_scale_range=None):
    data = _to_numeric_array(sequence)
    noise_vrms = calculate_noise_vrms(data)
    measured_lsb = calculate_lsb(data)
    fsr = calculate_fsr(data, full_scale_range)
    quantization_lsb = fsr / (2**ADC_BITS) if np.isfinite(fsr) else np.nan
    reference_noise = calculate_reference_noise(data, full_scale_range)
    enob_from_noise = calculate_enob_from_noise(data, full_scale_range)
    effective_resolution = calculate_effective_resolution(data, enob_from_noise, full_scale_range)
    reference_effective_resolution = calculate_effective_resolution(data, REFERENCE_ENOB, full_scale_range)

    return {
        "samples": data.size,
        "mean": calculate_mean(data),
        "signal_vrms": calculate_signal_vrms(data),
        "noise_vrms": noise_vrms,
        "std": calculate_std(data),
        "lsb": measured_lsb,
        "quantization_lsb": quantization_lsb,
        "fsr": fsr,
        "ideal_quantization_noise": calculate_ideal_quantization_noise(data, full_scale_range),
        "reference_enob": REFERENCE_ENOB,
        "reference_noise": reference_noise,
        "enob_from_noise": enob_from_noise,
        "enob_delta": enob_from_noise - REFERENCE_ENOB,
        "effective_resolution": effective_resolution,
        "reference_effective_resolution": reference_effective_resolution,
        "noise_to_reference_ratio": noise_vrms / reference_noise,
        "levels": np.unique(data).size,
        "min": np.min(data),
        "max": np.max(data),
        "peak_to_peak": np.ptp(data),
    }


def write_noise_recap(sequence, log_path=None, label=None, quantity_label="Voltage [V]", current_fsr=None):
    recap = calculate_noise_recap(sequence)
    display_scale, display_quantity_label, display_unit = _display_scale_from_label(quantity_label, current_fsr)
    value_unit = display_unit or _extract_unit(display_quantity_label) or ""
    rms_unit = f"{value_unit}rms" if value_unit else "rms"
    fsr_scale, fsr_unit = _fsr_pm_display_scale_unit(quantity_label, current_fsr, display_scale, value_unit)
    fsr_pm = recap["fsr"] * fsr_scale / 2.0
    fsr_pm_label = _format_pm_value(fsr_pm, fsr_unit)

    if log_path is None:
        LOGS_PATH.mkdir(parents=True, exist_ok=True)
        log_path = LOGS_PATH / f"{filename}_noise_recap.log"
    else:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "NOISE ANALYSIS RECAP",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if label is not None:
        lines.append(f"Label: {label}")
    lines.append(f"Quantity: {display_quantity_label}")
    if current_fsr is not None:
        lines.append(f"Current FSR: {current_fsr}")
        lines.append(f"Current FSR range [{fsr_unit}]: {fsr_pm_label}")

    lines.extend(
        [
            "",
            f"Samples: {recap['samples']}",
            f"Mean [{value_unit}]: {recap['mean'] * display_scale:.10g}",
            f"Signal RMS [{rms_unit}]: {recap['signal_vrms'] * display_scale:.10g}",
            f"Noise RMS / std [{rms_unit}]: {recap['noise_vrms'] * display_scale:.10g}",
            f"Measured data step [{value_unit}]: {recap['lsb'] * display_scale:.10g}",
            f"Quantization LSB used [{value_unit}]: {recap['quantization_lsb'] * display_scale:.10g}",
            f"Full-scale range [{value_unit}]: {recap['fsr'] * display_scale:.10g}",
            f"Full-scale range as pm half-range [{fsr_unit}]: {fsr_pm_label}",
            f"Ideal 16-bit quantization noise [{rms_unit}]: {recap['ideal_quantization_noise'] * display_scale:.10g}",
            f"Reference ENOB: {recap['reference_enob']:.10g}",
            f"Reference noise RMS [{rms_unit}]: {recap['reference_noise'] * display_scale:.10g}",
            f"Estimated ENOB from noise: {recap['enob_from_noise']:.10g}",
            f"ENOB delta vs reference: {recap['enob_delta']:.10g}",
            f"Effective resolution from estimated ENOB [{value_unit}]: {recap['effective_resolution'] * display_scale:.10g}",
            f"Effective resolution from reference ENOB [{value_unit}]: {recap['reference_effective_resolution'] * display_scale:.10g}",
            f"Noise / reference noise: {recap['noise_to_reference_ratio']:.10g}",
            f"Levels: {recap['levels']}",
            f"Min [{value_unit}]: {recap['min'] * display_scale:.10g}",
            f"Max [{value_unit}]: {recap['max'] * display_scale:.10g}",
            f"Peak-to-peak [{value_unit}]: {recap['peak_to_peak'] * display_scale:.10g}",
            "",
        ]
    )

    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write("\n".join(lines))

    return log_path


def make_noise_comparison_row(sequence, acq_id, fs_khz, channel, quantity_label="Voltage [V]", current_fsr=None):
    recap = calculate_noise_recap(sequence)
    display_scale, display_quantity_label, display_unit = _display_scale_from_label(quantity_label, current_fsr)
    value_unit = display_unit or _extract_unit(display_quantity_label) or ""
    rms_unit = f"{value_unit}rms" if value_unit else "rms"
    fsr = recap["fsr"] * display_scale
    fsr_scale, fsr_unit = _fsr_pm_display_scale_unit(quantity_label, current_fsr, display_scale, value_unit)
    fsr_pm = recap["fsr"] * fsr_scale / 2.0

    return {
        "acq": acq_id,
        "fs_khz": fs_khz,
        "channel": channel,
        "quantity": display_quantity_label,
        "unit": value_unit,
        "rms_unit": rms_unit,
        "current_fsr": current_fsr or "",
        "samples": recap["samples"],
        "mean": recap["mean"] * display_scale,
        "signal_rms": recap["signal_vrms"] * display_scale,
        "noise_rms": recap["noise_vrms"] * display_scale,
        "measured_data_step": recap["lsb"] * display_scale,
        "quantization_lsb": recap["quantization_lsb"] * display_scale,
        "fsr": fsr,
        "fsr_pm": fsr_pm,
        "fsr_pm_unit": fsr_unit,
        "fsr_pm_label": _format_pm_value(fsr_pm, fsr_unit),
        "ideal_16bit_q_noise": recap["ideal_quantization_noise"] * display_scale,
        "reference_enob": recap["reference_enob"],
        "reference_noise": recap["reference_noise"] * display_scale,
        "estimated_enob": recap["enob_from_noise"],
        "enob_delta": recap["enob_delta"],
        "effective_resolution": recap["effective_resolution"] * display_scale,
        "reference_effective_resolution": recap["reference_effective_resolution"] * display_scale,
        "noise_to_reference": recap["noise_to_reference_ratio"],
        "levels": recap["levels"],
        "peak_to_peak": recap["peak_to_peak"] * display_scale,
    }


def write_noise_comparison(rows, csv_path=None):
    if csv_path is None:
        LOGS_PATH.mkdir(parents=True, exist_ok=True)
        csv_path = LOGS_PATH / f"{filename}_noise_comparison.csv"
    else:
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "acq",
        "fs_khz",
        "channel",
        "quantity",
        "unit",
        "rms_unit",
        "current_fsr",
        "samples",
        "mean",
        "signal_rms",
        "noise_rms",
        "measured_data_step",
        "quantization_lsb",
        "fsr",
        "fsr_pm",
        "fsr_pm_unit",
        "fsr_pm_label",
        "ideal_16bit_q_noise",
        "reference_enob",
        "reference_noise",
        "estimated_enob",
        "enob_delta",
        "effective_resolution",
        "reference_effective_resolution",
        "noise_to_reference",
        "levels",
        "peak_to_peak",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


def _apply_paper_style(ax, xlabel, ylabel, title=None):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title is not None:
        ax.set_title(title)
    ax.minorticks_on()
    ax.grid(True, which="major", alpha=0.25, linewidth=0.8)
    ax.grid(True, which="minor", alpha=0.12, linewidth=0.5)
    ax.tick_params(direction="in", which="both", top=True, right=True)
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)


def _save_figure(fig, save_path, dpi):
    if save_path is not None:
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")


def _extract_unit(label):
    start = label.rfind("[")
    end = label.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    return label[start + 1:end].strip()


def _replace_unit(label, unit):
    start = label.rfind("[")
    end = label.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return f"{label} [{unit}]"
    return f"{label[:start + 1]}{unit}{label[end:]}"


def _normalize_current_fsr(current_fsr):
    if current_fsr is None:
        return ""

    return (
        str(current_fsr)
        .replace("+-", "")
        .replace("\u00b1", "")
        .replace("\u00c2\u00b1", "")
        .lower()
        .replace("pm", "")
        .strip()
    )


def _current_display_unit(current_fsr=None):
    if current_fsr is None:
        return "mA"

    fsr = _normalize_current_fsr(current_fsr)
    if fsr == "1ma":
        return "uA"
    if fsr in {"10ma", "100ma"}:
        return "mA"
    if fsr == "1a":
        return "A"
    return "mA"


def _unit_scale(unit):
    return {
        "uA": 1e6,
        "mA": 1e3,
        "A": 1.0,
        "mV": 1e3,
        "V": 1.0,
    }.get(unit, 1.0)


def _display_scale_from_label(label, current_fsr=None):
    unit = _extract_unit(label)
    if unit == "A":
        display_unit = _current_display_unit(current_fsr)
        return _unit_scale(display_unit), _replace_unit(label, display_unit), display_unit
    return 1.0, label, unit


def _format_pm_value(value, unit, latex=False):
    value = np.trunc(float(value) * 100.0) / 100.0
    if latex:
        unit_suffix = rf"\,\mathrm{{{unit}}}" if unit else ""
        return rf"\pm {value:.2f}{unit_suffix}"

    unit_suffix = f" {unit}" if unit else ""
    return f"pm{value:.2f}{unit_suffix}"


def _format_scientific_value(value):
    if not np.isfinite(value):
        return "nan"
    mantissa, exponent = f"{float(value):.3e}".split("e")
    return f"{mantissa}e{int(exponent)}"


def _fsr_pm_display_scale_unit(quantity_label, current_fsr, default_scale, default_unit):
    unit = _extract_unit(quantity_label)
    if unit == "A" and current_fsr is not None:
        fsr = _normalize_current_fsr(current_fsr)
        if fsr == "1a":
            return 1.0, "A"
        if fsr in {"1ma", "10ma", "100ma"}:
            return 1e3, "mA"
    return default_scale, default_unit


def _sampling_khz_from_info(reader, acq_id):
    return reader.get_info(acq_id)["fs"] / 1000.0


def _rotate_histogram_x_ticks(ax):
    ax.tick_params(axis="x", labelrotation=45)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")


def _plot_noise_histogram_on_ax(
    ax,
    sequence,
    bins,
    xlabel,
    ylabel,
    title=None,
    hist_mode="probability",
    current_fsr=None,
):
    data = _to_numeric_array(sequence)
    display_scale, display_xlabel, display_unit = _display_scale_from_label(xlabel, current_fsr)
    display_data = data * display_scale
    recap = calculate_noise_recap(data)
    bin_edges = np.histogram_bin_edges(display_data, bins=bins)
    base_unit = _extract_unit(xlabel) or display_unit or ""
    fsr_scale, fsr_unit = _fsr_pm_display_scale_unit(xlabel, current_fsr, display_scale, display_unit or "")
    fsr_pm_label = _format_pm_value(recap["fsr"] * fsr_scale / 2.0, fsr_unit, latex=True)

    if hist_mode == "probability":
        hist_weights = np.ones_like(display_data) / display_data.size
    elif hist_mode == "counts":
        hist_weights = None
    elif hist_mode == "density":
        hist_weights = None
    else:
        raise ValueError("hist_mode deve essere 'probability', 'counts' oppure 'density'.")

    ax.hist(
        display_data,
        bins=bin_edges,
        weights=hist_weights,
        density=(hist_mode == "density"),
        color="0.70",
        edgecolor="0.20",
        linewidth=0.7,
        alpha=0.85,
        label="Data",
    )
    ax.axvline(recap["mean"] * display_scale, color="0.15", linestyle="--", linewidth=1.0, label="Mean")

    xmin = np.min(display_data)
    xmax = np.max(display_data)
    if xmin == xmax:
        half_width = max(abs(xmin) * 0.05, 0.5)
        ax.set_xlim(xmin - half_width, xmax + half_width)
    else:
        ax.set_xlim(xmin, xmax)

    ax.text(
        0.03,
        0.97,
            (
            f"$\\mu$={_format_scientific_value(recap['mean'])} {base_unit}\n"
            f"$\\sigma_\\mathrm{{rms}}$={_format_scientific_value(recap['noise_vrms'])} {base_unit}\n"
            f"$\\mathrm{{FSR}}={fsr_pm_label}$\n"
            f"$\\mathrm{{ENOB}}$={recap['enob_from_noise']:.3g}\n"
            f"$\\mathrm{{LSB}}_{{eff}}$={_format_scientific_value(recap['effective_resolution'])} {base_unit}"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        linespacing=0.95,
        bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "0.75", "alpha": 0.9},
    )
    _apply_paper_style(ax, display_xlabel, ylabel, title)
    _rotate_histogram_x_ticks(ax)
    ax.legend(frameon=False, loc="upper right")


def plot_noise_histogram(
    sequence,
    bins="auto",
    xlabel="Voltage [V]",
    ylabel="Probability",
    title=None,
    save_path=None,
    dpi=300,
    hist_mode="probability",
    current_fsr=None,
):
    with plt.rc_context(
        {
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 12,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.dpi": 120,
            "savefig.dpi": dpi,
        }
    ):
        fig, ax = plt.subplots(figsize=(5.2, 3.6))
        _plot_noise_histogram_on_ax(ax, sequence, bins, xlabel, ylabel, title, hist_mode, current_fsr)
        fig.tight_layout()
        _save_figure(fig, save_path, dpi)

    return fig, ax


def plot_noise_histogram_subplots(
    sequence_a,
    sequence_b,
    bins="auto",
    xlabel="Voltage [V]",
    ylabel="Probability",
    titles=("Channel A", "Channel B"),
    suptitle=None,
    save_path=None,
    dpi=300,
    hist_mode="probability",
    current_fsr_a=None,
    current_fsr_b=None,
):
    with plt.rc_context(
        {
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 12,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.dpi": 120,
            "savefig.dpi": dpi,
        }
    ):
        fig, axs = plt.subplots(1, 2, figsize=(9.62, 4.55), sharey=True)
        _plot_noise_histogram_on_ax(axs[0], sequence_a, bins, xlabel, ylabel, titles[0], hist_mode, current_fsr_a)
        _plot_noise_histogram_on_ax(axs[1], sequence_b, bins, xlabel, ylabel, titles[1], hist_mode, current_fsr_b)
        if suptitle is not None:
            fig.suptitle(suptitle)
        fig.tight_layout()
        _save_figure(fig, save_path, dpi)

    return fig, axs


def plot_noise_time_subplots(
    time_a,
    sequence_a,
    time_b,
    sequence_b,
    time_xlabel="Time [s]",
    signal_ylabel="Voltage [V]",
    titles=("Channel A", "Channel B"),
    suptitle=None,
    save_path=None,
    dpi=300,
    current_fsr_a=None,
    current_fsr_b=None,
):
    t_a = _to_numeric_array(time_a)
    data_a = _to_numeric_array(sequence_a)
    t_b = _to_numeric_array(time_b)
    data_b = _to_numeric_array(sequence_b)

    if t_a.shape != data_a.shape:
        raise ValueError("time_a e sequence_a devono avere la stessa lunghezza.")
    if t_b.shape != data_b.shape:
        raise ValueError("time_b e sequence_b devono avere la stessa lunghezza.")

    signal_scale_a, display_signal_ylabel_a, _ = _display_scale_from_label(signal_ylabel, current_fsr_a)
    signal_scale_b, display_signal_ylabel_b, _ = _display_scale_from_label(signal_ylabel, current_fsr_b)
    display_data_a = data_a * signal_scale_a
    display_data_b = data_b * signal_scale_b
    display_signal_ylabel = display_signal_ylabel_a
    if display_signal_ylabel_a != display_signal_ylabel_b:
        display_signal_ylabel = f"{display_signal_ylabel_a} / {display_signal_ylabel_b}"

    with plt.rc_context(
        {
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 12,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.dpi": 120,
            "savefig.dpi": dpi,
        }
    ):
        fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.5), sharey=True)

        axs[0].plot(t_a, display_data_a, marker=".", linestyle="None", color="tab:blue", markersize=3.0)
        _apply_paper_style(axs[0], time_xlabel, display_signal_ylabel, f"{titles[0]} - Time evolution")

        axs[1].plot(t_b, display_data_b, marker=".", linestyle="None", color="tab:orange", markersize=3.0)
        _apply_paper_style(axs[1], time_xlabel, display_signal_ylabel, f"{titles[1]} - Time evolution")

        if suptitle is not None:
            fig.suptitle(suptitle)
        fig.tight_layout()
        _save_figure(fig, save_path, dpi)

    return fig, axs


def plot_noise_time_histogram_subplots(
    time_a,
    sequence_a,
    time_b,
    sequence_b,
    bins="auto",
    time_xlabel="Time [s]",
    signal_ylabel="Voltage [V]",
    hist_xlabel="Voltage [V]",
    hist_ylabel="Probability",
    titles=("Channel A", "Channel B"),
    suptitle=None,
    save_path=None,
    dpi=300,
    hist_mode="probability",
    current_fsr_a=None,
    current_fsr_b=None,
):
    t_a = _to_numeric_array(time_a)
    data_a = _to_numeric_array(sequence_a)
    t_b = _to_numeric_array(time_b)
    data_b = _to_numeric_array(sequence_b)

    if t_a.shape != data_a.shape:
        raise ValueError("time_a e sequence_a devono avere la stessa lunghezza.")
    if t_b.shape != data_b.shape:
        raise ValueError("time_b e sequence_b devono avere la stessa lunghezza.")

    signal_scale_a, display_signal_ylabel_a, _ = _display_scale_from_label(signal_ylabel, current_fsr_a)
    signal_scale_b, display_signal_ylabel_b, _ = _display_scale_from_label(signal_ylabel, current_fsr_b)
    display_data_a = data_a * signal_scale_a
    display_data_b = data_b * signal_scale_b
    display_signal_ylabel = display_signal_ylabel_a
    if display_signal_ylabel_a != display_signal_ylabel_b:
        display_signal_ylabel = f"{display_signal_ylabel_a} / {display_signal_ylabel_b}"
    effective_hist_xlabel = hist_xlabel
    if hist_xlabel == "Voltage [V]" and _extract_unit(signal_ylabel) != "V":
        effective_hist_xlabel = signal_ylabel

    with plt.rc_context(
        {
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 12,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.dpi": 120,
            "savefig.dpi": dpi,
        }
    ):
        fig, axs = plt.subplots(2, 2, figsize=(10.5, 7.0))

        axs[0, 0].plot(t_a, display_data_a, marker=".", linestyle="None", color="tab:blue", markersize=3.0)
        _apply_paper_style(axs[0, 0], time_xlabel, display_signal_ylabel, f"{titles[0]} - Time evolution")

        axs[0, 1].plot(t_b, display_data_b, marker=".", linestyle="None", color="tab:orange", markersize=3.0)
        _apply_paper_style(axs[0, 1], time_xlabel, display_signal_ylabel, f"{titles[1]} - Time evolution")

        _plot_noise_histogram_on_ax(
            axs[1, 0],
            data_a,
            bins,
            effective_hist_xlabel,
            hist_ylabel,
            f"{titles[0]} - Histogram",
            hist_mode,
            current_fsr_a,
        )
        _plot_noise_histogram_on_ax(
            axs[1, 1],
            data_b,
            bins,
            effective_hist_xlabel,
            hist_ylabel,
            f"{titles[1]} - Histogram",
            hist_mode,
            current_fsr_b,
        )

        if suptitle is not None:
            fig.suptitle(suptitle)
        fig.tight_layout()
        _save_figure(fig, save_path, dpi)

    return fig, axs


def _fft_window(n_samples, window):
    if window is None or str(window).lower() in {"none", "rect", "rectangular", "boxcar"}:
        return np.ones(n_samples)
    if str(window).lower() in {"hann", "hanning"}:
        return np.hanning(n_samples)
    if str(window).lower() == "blackman":
        return np.blackman(n_samples)
    raise ValueError("window deve essere 'hann', 'blackman' oppure 'rect'.")


def _mark_bin_band(mask, center_index, half_width):
    start = max(1, int(center_index) - int(half_width))
    stop = min(mask.size, int(center_index) + int(half_width) + 1)
    mask[start:stop] = True


def _safe_db_ratio(numerator, denominator):
    if numerator <= 0 or denominator <= 0:
        return np.nan
    return 10.0 * np.log10(numerator / denominator)


def calculate_fft_sinad_snr(
    sequence,
    fs_hz,
    signal_frequency_hz=None,
    signal_bins=2,
    harmonic_bins=2,
    max_harmonics=5,
    window="hann",
):
    """Calcola spettro FFT, SNR e SINAD usando una fondamentale manuale oppure autodetect."""
    data = _to_numeric_array(sequence)
    if data.size < 8:
        raise ValueError("Servono almeno 8 campioni per calcolare FFT, SNR e SINAD.")
    if fs_hz <= 0:
        raise ValueError("fs_hz deve essere positivo.")
    if signal_frequency_hz is not None:
        signal_frequency_hz = float(signal_frequency_hz)
        if signal_frequency_hz <= 0 or signal_frequency_hz >= fs_hz / 2.0:
            raise ValueError("signal_frequency_hz deve essere maggiore di 0 e minore di fs_hz/2.")

    centered_data = data - np.mean(data)
    n_samples = centered_data.size
    fft_window = _fft_window(n_samples, window)
    coherent_gain = np.sum(fft_window) / n_samples
    if coherent_gain == 0:
        raise ValueError("La finestra FFT ha coherent gain nullo.")

    spectrum = np.fft.rfft(centered_data * fft_window)
    frequencies = np.fft.rfftfreq(n_samples, d=1.0 / fs_hz)
    amplitude = np.abs(spectrum) / (n_samples * coherent_gain)
    if amplitude.size > 2:
        amplitude[1:-1] *= 2.0

    power = np.abs(spectrum) ** 2
    power[0] = 0.0
    if power.size < 2 or np.max(power[1:]) <= 0:
        return {
            "frequencies": frequencies,
            "amplitude": amplitude,
            "magnitude_db": np.full_like(amplitude, np.nan, dtype=float),
            "fundamental_frequency": np.nan,
            "fundamental_index": None,
            "requested_signal_frequency": signal_frequency_hz,
            "fundamental_source": "manual" if signal_frequency_hz is not None else "auto",
            "signal_power": np.nan,
            "noise_power": np.nan,
            "distortion_power": np.nan,
            "sinad_db": np.nan,
            "snr_db": np.nan,
            "thd_db": np.nan,
            "enob_from_sinad": np.nan,
            "samples": n_samples,
            "fs_hz": fs_hz,
        }

    if signal_frequency_hz is None:
        fundamental_index = int(np.argmax(power[1:]) + 1)
        fundamental_source = "auto"
    else:
        fundamental_index = int(np.argmin(np.abs(frequencies - signal_frequency_hz)))
        fundamental_index = max(1, fundamental_index)
        fundamental_source = "manual"

    signal_mask = np.zeros(power.size, dtype=bool)
    harmonic_mask = np.zeros(power.size, dtype=bool)

    _mark_bin_band(signal_mask, fundamental_index, signal_bins)
    for harmonic in range(2, int(max_harmonics) + 1):
        harmonic_index = fundamental_index * harmonic
        if harmonic_index >= power.size:
            break
        _mark_bin_band(harmonic_mask, harmonic_index, harmonic_bins)

    harmonic_mask &= ~signal_mask
    valid_mask = np.ones(power.size, dtype=bool)
    valid_mask[0] = False

    signal_power = np.sum(power[signal_mask])
    distortion_power = np.sum(power[harmonic_mask])
    noise_mask = valid_mask & ~signal_mask & ~harmonic_mask
    noise_power = np.sum(power[noise_mask])
    noise_distortion_power = np.sum(power[valid_mask & ~signal_mask])

    eps = np.finfo(float).tiny
    magnitude_db = 20.0 * np.log10(np.maximum(amplitude, eps))
    sinad_db = _safe_db_ratio(signal_power, noise_distortion_power)
    snr_db = _safe_db_ratio(signal_power, noise_power)
    thd_db = _safe_db_ratio(distortion_power, signal_power)
    enob_from_sinad = (sinad_db - 1.76) / 6.02 if np.isfinite(sinad_db) else np.nan

    return {
        "frequencies": frequencies,
        "amplitude": amplitude,
        "magnitude_db": magnitude_db,
        "fundamental_frequency": frequencies[fundamental_index],
        "fundamental_index": fundamental_index,
        "requested_signal_frequency": signal_frequency_hz,
        "fundamental_source": fundamental_source,
        "signal_power": signal_power,
        "noise_power": noise_power,
        "distortion_power": distortion_power,
        "sinad_db": sinad_db,
        "snr_db": snr_db,
        "thd_db": thd_db,
        "enob_from_sinad": enob_from_sinad,
        "samples": n_samples,
        "fs_hz": fs_hz,
    }


def _subplot_grid(n_items, max_cols=3):
    if n_items <= 0:
        raise ValueError("La lista acquisizioni non puo essere vuota.")
    cols = min(max_cols, int(np.ceil(np.sqrt(n_items))))
    rows = int(np.ceil(n_items / cols))
    return rows, cols


def _format_db(value):
    return "nan" if not np.isfinite(value) else f"{value:.2f}"


def _format_frequency_khz(value_hz):
    return "nan" if not np.isfinite(value_hz) else f"{value_hz / 1000.0:.4g}"


def _resolve_signal_frequency_hz(signal_frequency_hz, acq_id, channel):
    def _coerce_frequency_value(value):
        if value is None:
            return None
        if isinstance(value, dict):
            for channel_key in (channel, channel.lower()):
                if channel_key in value:
                    return _coerce_frequency_value(value[channel_key])
            return None
        return float(value)

    if signal_frequency_hz is None:
        return None
    if np.isscalar(signal_frequency_hz):
        return float(signal_frequency_hz)
    if isinstance(signal_frequency_hz, dict):
        channel = channel.upper()
        candidates = [
            (acq_id, channel),
            (str(acq_id), channel),
            acq_id,
            str(acq_id),
            channel,
            channel.lower(),
        ]
        for key in candidates:
            if key in signal_frequency_hz:
                return _coerce_frequency_value(signal_frequency_hz[key])
        return None
    raise TypeError("signal_frequency_hz deve essere None, un numero oppure un dizionario.")


def _plot_fft_sinad_snr_on_ax(ax, fft_recap, title, display_unit):
    frequencies_khz = fft_recap["frequencies"] / 1000.0
    ax.plot(
        frequencies_khz,
        fft_recap["magnitude_db"],
        color="tab:blue",
        linewidth=0.9,
    )
    if np.isfinite(fft_recap["fundamental_frequency"]):
        ax.axvline(
            fft_recap["fundamental_frequency"] / 1000.0,
            color="0.15",
            linestyle="--",
            linewidth=1.0,
        )

    finite_magnitude = fft_recap["magnitude_db"][np.isfinite(fft_recap["magnitude_db"])]
    if finite_magnitude.size:
        ymax = np.max(finite_magnitude)
        ax.set_ylim(ymax - 120.0, ymax + 6.0)
    if frequencies_khz.size:
        ax.set_xlim(0.0, np.max(frequencies_khz))

    unit_suffix = display_unit or "unit"
    source = fft_recap.get("fundamental_source", "auto")
    annotation = (
        f"$f_0$={_format_frequency_khz(fft_recap['fundamental_frequency'])} kHz ({source})\n"
        f"$\\mathrm{{SNR}}$={_format_db(fft_recap['snr_db'])} dB\n"
        f"$\\mathrm{{SINAD}}$={_format_db(fft_recap['sinad_db'])} dB\n"
        f"$\\mathrm{{ENOB}}_{{SINAD}}$={_format_db(fft_recap['enob_from_sinad'])}"
    )
    ax.text(
        0.03,
        0.97,
        annotation,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        linespacing=0.95,
        bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "0.75", "alpha": 0.9},
    )
    _apply_paper_style(ax, "Frequency [kHz]", f"Amplitude [dB re 1 {unit_suffix}]", title)


def plot_fft_sinad_snr_acquisitions(
    acquisitions,
    reader=None,
    module_id="70",
    quantity="voltage",
    signal_frequency_hz=None,
    save_dir=PLOT_PATH,
    filename_prefix=None,
    max_cols=3,
    dpi=300,
    signal_bins=2,
    harmonic_bins=2,
    max_harmonics=5,
    window="hann",
):
    """Crea due figure NxM, una per CHA e una per CHB, a partire da una lista acquisizioni."""
    acq_ids = list(acquisitions)
    rows, cols = _subplot_grid(len(acq_ids), max_cols=max_cols)
    if reader is None:
        reader = EPICAFolderReader(root_dir=DATA_PATH)

    quantity_key = str(quantity).lower()
    if quantity_key not in {"voltage", "current"}:
        raise ValueError("quantity deve essere 'voltage' oppure 'current'.")

    results = {"CHA": [], "CHB": []}
    with plt.rc_context(
        {
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 12,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.dpi": 120,
            "savefig.dpi": dpi,
        }
    ):
        fig_a, axs_a = plt.subplots(rows, cols, figsize=(cols * 5.2, rows * 3.6), squeeze=False)
        fig_b, axs_b = plt.subplots(rows, cols, figsize=(cols * 5.2, rows * 3.6), squeeze=False)

        for index, acq_id in enumerate(acq_ids):
            fs_hz = reader.get_info(acq_id)["fs"]
            t_a, v_a, i_a = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHA")
            t_b, v_b, i_b = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHB")

            if quantity_key == "current":
                shunt_a = reader.get_channel_shunt(acq_n=acq_id, channel="CHA")
                shunt_b = reader.get_channel_shunt(acq_n=acq_id, channel="CHB")
                sequence_a = i_a
                sequence_b = i_b
                quantity_label = "Current [A]"
                current_fsr_a = shunt_a
                current_fsr_b = shunt_b
            else:
                sequence_a = v_a
                sequence_b = v_b
                quantity_label = "Voltage [V]"
                current_fsr_a = None
                current_fsr_b = None

            display_scale_a, _, display_unit_a = _display_scale_from_label(quantity_label, current_fsr_a)
            display_scale_b, _, display_unit_b = _display_scale_from_label(quantity_label, current_fsr_b)
            signal_frequency_a = _resolve_signal_frequency_hz(signal_frequency_hz, acq_id, "CHA")
            signal_frequency_b = _resolve_signal_frequency_hz(signal_frequency_hz, acq_id, "CHB")
            fft_a = calculate_fft_sinad_snr(
                sequence_a * display_scale_a,
                fs_hz,
                signal_frequency_hz=signal_frequency_a,
                signal_bins=signal_bins,
                harmonic_bins=harmonic_bins,
                max_harmonics=max_harmonics,
                window=window,
            )
            fft_b = calculate_fft_sinad_snr(
                sequence_b * display_scale_b,
                fs_hz,
                signal_frequency_hz=signal_frequency_b,
                signal_bins=signal_bins,
                harmonic_bins=harmonic_bins,
                max_harmonics=max_harmonics,
                window=window,
            )

            fft_a.update({"acq": acq_id, "channel": "CHA", "quantity": quantity_key, "unit": display_unit_a})
            fft_b.update({"acq": acq_id, "channel": "CHB", "quantity": quantity_key, "unit": display_unit_b})
            results["CHA"].append(fft_a)
            results["CHB"].append(fft_b)

            title = f"ACQ {acq_id} - {fs_hz / 1000.0:.4g} kHz"
            _plot_fft_sinad_snr_on_ax(axs_a.flat[index], fft_a, title, display_unit_a)
            _plot_fft_sinad_snr_on_ax(axs_b.flat[index], fft_b, title, display_unit_b)

        for index in range(len(acq_ids), rows * cols):
            axs_a.flat[index].axis("off")
            axs_b.flat[index].axis("off")

        fig_a.suptitle(f"CHA - FFT, SNR, SINAD ({quantity_key})")
        fig_b.suptitle(f"CHB - FFT, SNR, SINAD ({quantity_key})")
        fig_a.tight_layout(rect=[0, 0, 1, 0.96])
        fig_b.tight_layout(rect=[0, 0, 1, 0.96])

        if save_dir is not None:
            save_dir = Path(save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
            prefix = filename_prefix or f"{now}_{quantity_key.upper()}_FFT_SNR_SINAD"
            _save_figure(fig_a, save_dir / f"{prefix}_CHA.png", dpi)
            _save_figure(fig_b, save_dir / f"{prefix}_CHB.png", dpi)

    return fig_a, fig_b, results


def plot_gaussian(*args, **kwargs):
    return plot_noise_histogram(*args, **kwargs)


def plot_gaussian_subplots(*args, **kwargs):
    return plot_noise_histogram_subplots(*args, **kwargs)


def plot_xy(
    x_sequence,
    y_sequence,
    xlabel="x",
    ylabel="y",
    title=None,
    label=None,
    save_path=None,
    dpi=300,
    marker="o",
    linestyle="-",
):
    x = _to_numeric_array(x_sequence)
    y = _to_numeric_array(y_sequence)

    if x.shape != y.shape:
        raise ValueError("Le sequenze x e y devono avere la stessa lunghezza.")

    with plt.rc_context(
        {
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 12,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.dpi": 120,
            "savefig.dpi": dpi,
        }
    ):
        fig, ax = plt.subplots(figsize=(5.2, 3.6))
        ax.plot(
            x,
            y,
            marker=marker,
            linestyle=linestyle,
            color="tab:blue",
            linewidth=1.5,
            markersize=4.0,
            markeredgewidth=0.7,
            markeredgecolor="0.15",
            label=label,
        )
        _apply_paper_style(ax, xlabel, ylabel, title)
        if label is not None:
            ax.legend(frameon=False, loc="best")
        fig.tight_layout()
        _save_figure(fig, save_path, dpi)

    return fig, ax


# ----------------------------------------------------------------------------------------
# Main program 
# ----------------------------------------------------------------------------------------
if __name__ == "__main__":

    # try:
    #     now = "2026_06_05"
    #     DATA_PATH = BASE_PATH / f"data_{now}" / f"SL1IPB"
    #     acq_v = [1, 2, 3, 4]  # 156.250kHz, 78.125kHz, 39.0625kHz, 19.53125kHz
    #     module_id = "70"

    #     name = "VOLTAGE"
    #     filename = f"{now}_{name}"
    #     dataset_name = f"{filename}_NOISE_ANALYSIS"

    #     reader = EPICAFolderReader(root_dir=DATA_PATH)

    #     for acq_n in range(len(acq_v)):
    #         acq_id = acq_v[acq_n]
    #         fs_khz = _sampling_khz_from_info(reader, acq_id)

    #         tA, vA, iA = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHA")
    #         tB, vB, iB = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHB")

    #         write_noise_recap(vA, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHA_noise.log", label=f"CHA acq {acq_id}", quantity_label="Voltage [V]")
    #         write_noise_recap(vB, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHB_noise.log", label=f"CHB acq {acq_id}", quantity_label="Voltage [V]",)
            
    #         fig_time, axs_time = plot_noise_time_subplots(
    #             tA,
    #             vA,
    #             tB,
    #             vB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Voltage [V]",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_CHB_time.png",
    #         )
    #         fig_hist, axs_hist = plot_noise_histogram_subplots(
    #             vA,
    #             vB,
    #             xlabel="Voltage [V]",
    #             ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_CHB_histogram.png",
    #         )
    #         fig, axs = plot_noise_time_histogram_subplots(
    #             tA,
    #             vA,
    #             tB,
    #             vB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Voltage [V]",
    #             hist_xlabel="Voltage [V]",
    #             hist_ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_CHB_time_histogram.png",
    #         )
    #         plt.show()

    # except Exception as e:
    #     print(f"Errore durante l'analisi: {e}, passo alla prossima acquisizione.")



    # try:
    #     now = "2026_06_08"
    #     DATA_PATH = BASE_PATH / f"data_{now}" / f"SL1IPB"
    #     acq_v = [2, 5, 8]
    #     module_id = "60"

    #     name = "Voltage"
    #     filename = f"{now}_{name}"
    #     dataset_name = f"{filename}_NOISE_ANALYSIS"

    #     reader = EPICAFolderReader(root_dir=DATA_PATH)

    #     for acq_n in range(len(acq_v)):
    #         acq_id = acq_v[acq_n]
    #         fs_khz = _sampling_khz_from_info(reader, acq_id)

    #         tA, vA, iA = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHA")
    #         tB, vB, iB = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHB")

    #         write_noise_recap(iA, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHA_noise.log", label=f"CHA acq {acq_id}", quantity_label="Voltage [V]")
    #         write_noise_recap(iB, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHB_noise.log", label=f"CHB acq {acq_id}", quantity_label="Voltage [V]",)
            
    #         fig_time, axs_time = plot_noise_time_subplots(
    #             tA,
    #             iA,
    #             tB,
    #             iB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Voltage [V]",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_CHB_time.png",
    #         )
    #         fig_hist, axs_hist = plot_noise_histogram_subplots(
    #             iA,
    #             iB,
    #             xlabel="Voltage [V]",
    #             ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_CHB_histogram.png",
    #         )
    #         fig, axs = plot_noise_time_histogram_subplots(
    #             tA,
    #             iA,
    #             tB,
    #             iB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Voltage [V]",
    #             hist_xlabel="Voltage [V]",
    #             hist_ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_CHB_time_histogram.png",
    #         )
    #         plt.show()

    # except Exception as e:
    #     print(f"Errore durante l'analisi: {e}, passo alla prossima acquisizione.")



    # try:
    #     now = "2026_06_08"
    #     DATA_PATH = BASE_PATH / f"data_{now}" / f"SL1IPB"
    #     acq_i = [2, 5, 8]  # 2=1mA, 5=10mA, 8=100mA, 
    #     acq_i1A = [12, 14] # 12=1A chB, 14=1A chA
    #     module_id = "60"

    #     reader = EPICAFolderReader(root_dir=DATA_PATH)

    #     name = "CURRENT"
    #     filename = f"{now}_{name}"
    #     dataset_name = f"{filename}_NOISE_ANALYSIS"

    #     for acq_n in range(len(acq_i)):
    #         acq_id = acq_i[acq_n]
    #         fs_khz = _sampling_khz_from_info(reader, acq_id)

    #         tA, vA, iA = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHA")
    #         tB, vB, iB = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHB")
    #         shunt_a = reader.get_channel_shunt(acq_n=acq_id, channel="CHA")
    #         shunt_b = reader.get_channel_shunt(acq_n=acq_id, channel="CHB")

    #         write_noise_recap(iA, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHA_{shunt_a}_noise.log", label=f"CHA acq {acq_id}", quantity_label="Current [A]", current_fsr=shunt_a)
    #         write_noise_recap(iB, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHB_{shunt_b}_noise.log", label=f"CHB acq {acq_id}", quantity_label="Current [A]", current_fsr=shunt_b)
            
    #         fig_time, axs_time = plot_noise_time_subplots(
    #             tA,
    #             iA,
    #             tB,
    #             iB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Current [A]",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_{shunt_a}_CHB_{shunt_b}_time.png",
    #             current_fsr_a=shunt_a,
    #             current_fsr_b=shunt_b,
    #         )
    #         fig_hist, axs_hist = plot_noise_histogram_subplots(
    #             iA,
    #             iB,
    #             xlabel="Current [A]",
    #             ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_{shunt_a}_CHB_{shunt_b}_histogram.png",
    #             current_fsr_a=shunt_a,
    #             current_fsr_b=shunt_b,
    #         )
    #         fig, axs = plot_noise_time_histogram_subplots(
    #             tA,
    #             iA,
    #             tB,
    #             iB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Current [A]",
    #             hist_xlabel="Current [A]",
    #             hist_ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_{shunt_a}_CHB_{shunt_b}_time_histogram.png",
    #             current_fsr_a=shunt_a,
    #             current_fsr_b=shunt_b,
    #         )
    #         plt.show()


    #         name = "CURRENT"
    #         filename = f"{now}_{name}"
    #         dataset_name = f"{filename}_NOISE_ANALYSIS"

    #         fs_khz = _sampling_khz_from_info(reader, acq_i1A[0])

    #         tA, vA, iA = reader.get_data(acq_n=acq_i1A[0], module_id=module_id, channel="CHA")
    #         tB, vB, iB = reader.get_data(acq_n=acq_i1A[1], module_id=module_id, channel="CHB")
    #         shunt_a = reader.get_channel_shunt(acq_n=acq_i1A[0], channel="CHA")
    #         shunt_b = reader.get_channel_shunt(acq_n=acq_i1A[1], channel="CHB")

    #         write_noise_recap(
    #             iA,
    #             log_path=LOGS_PATH / f"{dataset_name}_acq{acq_i1A[0]}_fs{fs_khz}_CHA_{shunt_a}_noise.log",
    #             label=f"CHA acq {acq_i1A[0]}",
    #             quantity_label="Current [A]",
    #             current_fsr=shunt_a,
    #         )

    #         write_noise_recap(
    #             iB,
    #             log_path=LOGS_PATH / f"{dataset_name}_acq{acq_i1A[1]}_fs{fs_khz}_CHB_{shunt_b}_noise.log",
    #             label=f"CHB acq {acq_i1A[1]}",
    #             quantity_label="Current [A]",
    #             current_fsr=shunt_b,
    #         )
            
    #         fig_time, axs_time = plot_noise_time_subplots(
    #             tA,
    #             iA,
    #             tB,
    #             iB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Current [A]",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_i1A[0]} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_i1A[0]}_Fs{fs_khz}_CHA_{shunt_a}_CHB_{shunt_b}_time.png",
    #             current_fsr_a=shunt_a,
    #             current_fsr_b=shunt_b,
    #         )
    #         fig_hist, axs_hist = plot_noise_histogram_subplots(
    #             iA,
    #             iB,
    #             xlabel="Current [A]",
    #             ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_i1A[0]} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_i1A[0]}_Fs{fs_khz}_CHA_{shunt_a}_CHB_{shunt_b}_histogram.png",
    #             current_fsr_a=shunt_a,
    #             current_fsr_b=shunt_b,
    #         )
    #         fig, axs = plot_noise_time_histogram_subplots(
    #             tA,
    #             iA,
    #             tB,
    #             iB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Current [A]",
    #             hist_xlabel="Current [A]",
    #             hist_ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_i1A[0]} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_i1A[0]}_Fs{fs_khz}_CHA_{shunt_a}_CHB_{shunt_b}_time_histogram.png",
    #             current_fsr_a=shunt_a,
    #             current_fsr_b=shunt_b,
    #         )
    #         plt.show()

    # except Exception as e:
    #     print(f"Errore durante l'analisi: {e}, passo alla prossima acquisizione.")



    # try:
    #     now = "2026_06_12"
    #     DATA_PATH = BASE_PATH / f"data_{now}" / f"SL1IPB"
    #     acq_v = [2, 4, 6, 8]
    #     module_id = "70"

    #     name = "Voltage"
    #     filename = f"{now}_{name}"
    #     dataset_name = f"{filename}_NOISE_ANALYSIS"

    #     reader = EPICAFolderReader(root_dir=DATA_PATH)

    #     for acq_n in range(len(acq_v)):
    #         acq_id = acq_v[acq_n]
    #         fs_khz = _sampling_khz_from_info(reader, acq_id)

    #         tA, vA, iA = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHA")
    #         tB, vB, iB = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHB")

    #         write_noise_recap(vA, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHA_noise.log", label=f"CHA acq {acq_id}", quantity_label="Voltage [V]")
    #         write_noise_recap(vB, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHB_noise.log", label=f"CHB acq {acq_id}", quantity_label="Voltage [V]",)
            
    #         fig_time, axs_time = plot_noise_time_subplots(
    #             tA,
    #             vA,
    #             tB,
    #             vB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Voltage [V]",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_CHB_time.png",
    #         )
    #         fig_hist, axs_hist = plot_noise_histogram_subplots(
    #             vA,
    #             vB,
    #             xlabel="Voltage [V]",
    #             ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_CHB_histogram.png",
    #         )
    #         fig, axs = plot_noise_time_histogram_subplots(
    #             tA,
    #             vA,
    #             tB,
    #             vB,
    #             time_xlabel="Time [s]",
    #             signal_ylabel="Voltage [V]",
    #             hist_xlabel="Voltage [V]",
    #             hist_ylabel="Probability",
    #             titles=("Channel A", "Channel B"),
    #             suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
    #             save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_CHB_time_histogram.png",
    #         )
    #         plt.show()

    # except Exception as e:
    #     print(f"Errore durante l'analisi: {e}, passo alla prossima acquisizione.")



    try:
        now = "2026_06_12"
        DATA_PATH = BASE_PATH / f"data_{now}" / f"SL1IPB"
        acq_i = [10, 12, 14, 16]
        module_id = "70"

        reader = EPICAFolderReader(root_dir=DATA_PATH)

        name = "CURRENT"
        filename = f"{now}_{name}"
        dataset_name = f"{filename}_NOISE_ANALYSIS"

        for acq_n in range(len(acq_i)):
            acq_id = acq_i[acq_n]
            fs_khz = _sampling_khz_from_info(reader, acq_id)

            tA, vA, iA = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHA")
            tB, vB, iB = reader.get_data(acq_n=acq_id, module_id=module_id, channel="CHB")
            shunt_a = reader.get_channel_shunt(acq_n=acq_id, channel="CHA")
            shunt_b = reader.get_channel_shunt(acq_n=acq_id, channel="CHB")

            write_noise_recap(iA, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHA_{shunt_a}_noise.log", label=f"CHA acq {acq_id}", quantity_label="Current [A]", current_fsr=shunt_a)
            write_noise_recap(iB, log_path=LOGS_PATH / f"{dataset_name}_acq{acq_id}_fs{fs_khz}_CHB_{shunt_b}_noise.log", label=f"CHB acq {acq_id}", quantity_label="Current [A]", current_fsr=shunt_b)
            
            fig_time, axs_time = plot_noise_time_subplots(
                tA,
                iA,
                tB,
                iB,
                time_xlabel="Time [s]",
                signal_ylabel="Current [A]",
                titles=("Channel A", "Channel B"),
                suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
                save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_{shunt_a}_CHB_{shunt_b}_time.png",
                current_fsr_a=shunt_a,
                current_fsr_b=shunt_b,
            )
            fig_hist, axs_hist = plot_noise_histogram_subplots(
                iA,
                iB,
                xlabel="Current [A]",
                ylabel="Probability",
                titles=("Channel A", "Channel B"),
                suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
                save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_{shunt_a}_CHB_{shunt_b}_histogram.png",
                current_fsr_a=shunt_a,
                current_fsr_b=shunt_b,
            )
            fig, axs = plot_noise_time_histogram_subplots(
                tA,
                iA,
                tB,
                iB,
                time_xlabel="Time [s]",
                signal_ylabel="Current [A]",
                hist_xlabel="Current [A]",
                hist_ylabel="Probability",
                titles=("Channel A", "Channel B"),
                suptitle=f"Acquisition {acq_id} - {fs_khz} kHz",
                save_path=PLOT_PATH / f"{dataset_name}_ACQ{acq_id}_Fs{fs_khz}_CHA_{shunt_a}_CHB_{shunt_b}_time_histogram.png",
                current_fsr_a=shunt_a,
                current_fsr_b=shunt_b,
            )
            plt.show()

    except Exception as e:
        print(f"Errore durante l'analisi: {e}, passo alla prossima acquisizione.")
    