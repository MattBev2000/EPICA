from LangmuirProbe import LangmuirProbeAnalysis
from EPICA import EPICAFolderReader
from pathlib import Path


BASE_PATH = Path(__file__).resolve().parent
PLOT_PATH = BASE_PATH / "plots"
LOG_PATH = BASE_PATH / "logs"


if __name__ == "__main__":
    # try:
    #     now = "2026_05_14"

    #     DATA_PATH = BASE_PATH / f"data_{now}" / "SL1IPB"

    #     SLP = [1, 10]
    #     MODULE = "70"
    #     CHANNEL = "CHA"

    #     for i in SLP:
    #         dataset_name = f"{now}_SLP_ACQ{i}"

    #         reader = EPICAFolderReader(root_dir=DATA_PATH)
    #         tA, vA, iA = reader.get_data(acq_n=i, module_id=MODULE, channel=CHANNEL)
    #         probe = LangmuirProbeAnalysis(voltage=vA, current=iA, time=tA, dataset_name=dataset_name, plot_dir=PLOT_PATH, log_dir=LOG_PATH)

    #         if i == 1:
    #             probe.plot_time_series(show=True)
    #         else:
    #             results = probe.analyze(probe_area_m2=2.01e-6, voltage_range=(-100, -20), probe_conf="single", ion_mass_amu="Helium")
    #             probe.plot_fits(show=True)

    # except Exception as e:
    #     print(f"Error processing SLP data: {e}")


    try:
        now = "2026_06_10"

        DATA_PATH = BASE_PATH / f"data_{now}" / "SL1IPB"

        SLP = [19]
        MODULE = "60"
        CHANNEL = "CHA"

        for i in SLP:
            dataset_name = f"{now}_SLP_ACQ{i}"

            reader = EPICAFolderReader(root_dir=DATA_PATH)
            tA, vA, iA = reader.get_data(acq_n=i, module_id=MODULE, channel=CHANNEL)

            probe = LangmuirProbeAnalysis(voltage=vA, current=iA, time=tA, dataset_name=dataset_name, plot_dir=PLOT_PATH, log_dir=LOG_PATH)
            results = probe.analyze(probe_area_m2=2.01e-6, voltage_range=(-100, -20), probe_conf="single", ion_mass_amu="Helium")
            probe.plot_time_series(show=True, statistics=False)
            probe.plot_i_vs_v(show=True)

    except Exception as e:
        print(f"Error processing SLP data: {e}")

    
    # try:
    #     now = "2026_06_12"

    #     DATA_PATH = BASE_PATH / f"data_{now}" / "SL1IPB"

    #     DLP = [2]
    #     MODULE = "70"
    #     CHANNEL = "CHA"

    #     for i in DLP:
    #         dataset_name = f"{now}_DLP_ACQ{i}"

    #         reader = EPICAFolderReader(root_dir=DATA_PATH)
    #         tA, vA, iA = reader.get_data(acq_n=i, module_id=MODULE, channel=CHANNEL)

    #         probe = LangmuirProbeAnalysis(voltage=vA, current=iA, time=tA, dataset_name=dataset_name, plot_dir=PLOT_PATH, log_dir=LOG_PATH)
    #         probe.plot_i_vs_v(show=True)

    # except Exception as e:
    #     print(f"Error processing DLP data: {e}")
