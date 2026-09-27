"""Reproducible analysis used for the functional-verification results in Section VI.

The script deliberately distinguishes measured quantities from model-dependent
plasma estimates. Experimental conditions that were not recorded are marked as
"not available" and are never inferred from the acquired waveforms.
"""

from __future__ import annotations

import json
from pathlib import Path

from EPICA import EPICAFolderReader
from LangmuirProbe2 import LangmuirProbeAnalysis


BASE_PATH = Path(__file__).resolve().parent
PLOT_PATH = BASE_PATH / "plots"
LOG_PATH = BASE_PATH / "logs"

# Dataset identifiers used for the Section VI single-probe example.
ACQUISITION_DATE = "2026_05_14"
DATA_PATH = BASE_PATH / f"data_{ACQUISITION_DATE}" / "SL1IPB"
MODULE = "70"
CHANNEL = "CHA"
FLOATING_POTENTIAL_ACQUISITION = 1
SWEPT_BIAS_ACQUISITION = 10

# Analysis choices reported in Section VI. The interval is selected manually
# and is applied inclusively. Keeping it explicit makes the published fit
# reproducible and directly answers whether range selection is manual or automatic.
FIT_VOLTAGE_RANGE_V = (-100.0, -20.0)
PROBE_AREA_M2 = 2.01e-6
ION_SPECIES = "Helium"
SHOW_PLOTS = False

# Only information supported by the available records is included. Replace an
# entry only if documentary evidence becomes available; do not infer it.
EXPERIMENTAL_METADATA = {
    "facility_or_source": "laboratory plasma test; further source details not available",
    "discharge_method": "not available",
    "working_gas": ION_SPECIES,
    "gas_pressure": "not available",
    "discharge_power_or_current": "not available",
    "probe_location": "not available",
    "probe_geometry": "exposed collection area available; further dimensions not available",
    "probe_area_m2": PROBE_AREA_M2,
    "reference_diagnostic": "not available",
}


def load_acquisition(acquisition_number: int) -> tuple[object, object, object]:
    """Load one EPICA acquisition using the identifiers reported above."""
    reader = EPICAFolderReader(root_dir=DATA_PATH)
    return reader.get_data(
        acq_n=acquisition_number,
        module_id=MODULE,
        channel=CHANNEL,
    )


def main() -> None:
    PLOT_PATH.mkdir(parents=True, exist_ok=True)
    LOG_PATH.mkdir(parents=True, exist_ok=True)

    # Floating-potential acquisition: report directly measured mean and RMS
    # fluctuation; no plasma-model fit is applied to this dataset.
    fp_name = f"{ACQUISITION_DATE}_SLP_ACQ{FLOATING_POTENTIAL_ACQUISITION}"
    fp_time, fp_voltage, fp_current = load_acquisition(
        FLOATING_POTENTIAL_ACQUISITION
    )
    fp_probe = LangmuirProbeAnalysis(
        voltage=fp_voltage,
        current=fp_current,
        time=fp_time,
        dataset_name=fp_name,
        plot_dir=PLOT_PATH,
        log_dir=LOG_PATH,
    )
    fp_outputs = fp_probe.plot_time_series(show=SHOW_PLOTS)

    # Swept-bias acquisition: use the explicitly documented manual interval.
    # The returned plasma quantities are model-dependent estimates and are not
    # presented as independently validated measurements.
    sweep_name = f"{ACQUISITION_DATE}_SLP_ACQ{SWEPT_BIAS_ACQUISITION}"
    sweep_time, sweep_voltage, sweep_current = load_acquisition(
        SWEPT_BIAS_ACQUISITION
    )
    sweep_probe = LangmuirProbeAnalysis(
        voltage=sweep_voltage,
        current=sweep_current,
        time=sweep_time,
        dataset_name=sweep_name,
        plot_dir=PLOT_PATH,
        log_dir=LOG_PATH,
    )
    sweep_results = sweep_probe.analyze(
        probe_area_m2=PROBE_AREA_M2,
        voltage_range=FIT_VOLTAGE_RANGE_V,
        probe_conf="single",
        ion_mass_amu=ION_SPECIES,
        metadata=EXPERIMENTAL_METADATA,
        analysis_scope="functional verification of acquisition and analysis workflow",
        write_log=True,
        write_machine_readable=True,
    )
    sweep_probe.plot_fits(show=SHOW_PLOTS)

    # Compact manifest separating directly measured statistics from fitted
    # estimates and recording the limitations of the available experiment log.
    manifest = {
        "analysis_scope": sweep_results["analysis_scope"],
        "experimental_metadata": EXPERIMENTAL_METADATA,
        "floating_potential_measurement": {
            "dataset": fp_name,
            "mean_voltage_v": fp_outputs["voltage"]["mean"],
            "rms_voltage_fluctuation_v": fp_outputs["voltage"]["noise"],
        },
        "single_probe_fit": {
            "dataset": sweep_name,
            "selection_method": sweep_results["fit_selection_method"],
            "requested_voltage_range_v": list(FIT_VOLTAGE_RANGE_V),
            "actual_voltage_range_v": list(
                sweep_results["actual_fit_voltage_range_v"]
            ),
            "samples_available": sweep_results["samples_available"],
            "samples_fitted": sweep_results["samples_fitted"],
            "fit_parameters": sweep_results["fit_parameters"],
            "parameter_standard_errors": sweep_results[
                "fit_parameter_standard_errors"
            ],
            "fit_diagnostics": sweep_results["fit_diagnostics"],
            "r_squared": sweep_results["fit_r2"],
            "interpretation_note": sweep_results["interpretation_note"],
        },
    }
    manifest_path = LOG_PATH / "section_vi_analysis_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(sweep_results["report"])
    print(f"Section VI manifest: {manifest_path}")


if __name__ == "__main__":
    main()
