import os
import paramiko
import time
from datetime import date


# ---- helper function -----
def run_ssh_cmd( ssh_target, command ):
    stdin, stdout, stderr = ssh_target.exec_command(command, get_pty=True)
    first_output = stdout.channel.recv(1024).decode(errors="ignore")
    if "sudo" in command and "password" in first_output.lower():
        time.sleep(0.5)
        stdin.write("eladit" + "\n")
        time.sleep(0.5)
        stdin.flush()
    out = stdout.read().decode(errors='ignore')
    err = stderr.read().decode(errors='ignore')
    ret = stdout.channel.recv_exit_status()
    stdin.close()
    stdout.close()
    stderr.close()
    if err:
        print("\n--- ERRORI ---")
        print(err)
    if ret:
        print(f"\nExit code: {ret}")
    print(out)
    return ret, out, err


class epica_daq:
    def __init__(
        self,
        ip_ek26="192.168.54.119",
        sn_ek26="SL1IPB",
        remote_dir="/home/petalinux/SwDMA/testDMA",
        local_dir=r"C:\Users\maglab\Mattia\EPICA\mk_III_rc",
        data_dir=r"C:\Users\maglab\Mattia\EPICA\mk_III_rc\data",
        csv_dir=r"C:\Users\maglab\Mattia\EPICA\mk_III_rc\csv_setup",
        online=True,
        verbose=True,
    ):
        # Assign basic parameters
        self.ip_ek26 = ip_ek26
        self.sn_ek26 = sn_ek26
        self.remote_dir = remote_dir
        self.local_dir  = local_dir
        self.verbose = verbose
        self.online = online

        # Handle mutable default arguments (lists)
        # self.board = board if board is not None else ["60"]
        # self.what_to_plot = what_to_plot if what_to_plot is not None else [1, 2]

        # Derived variables (calculated from parameters)
        # self.acq_n = f"{self.acq_code:05d}"

        now = date.today().strftime("%Y-%m-%d").replace("-", "_")
        self.local_csv_dir = csv_dir
        self.local_data_dir = data_dir
        os.makedirs( self.local_data_dir, exist_ok = True)

        self.remote_csv_dir = self.remote_dir
        self.remote_data_dir = self.remote_dir + "/" + self.sn_ek26 

    def __repr__(self):
        return f"<ek26_test IP: {self.ip_ek26}, Command: {self.acq_command}>"

    def connect_and_acquire( 
            self, 
            waveform_file_name="seq_rc001.csv",
            cfg_str="-d 3 -c 4 -sa 3 -sb 3",
            run_acquisition=True
            ):
        
        ssh_ek26 = paramiko.SSHClient()
        ssh_ek26.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_ek26.connect( self.ip_ek26, username="petalinux", password="eladit", timeout=1)
        except Exception as e:
            raise ConnectionError(f"Impossibile connettersi a {self.ip_ek26}: {e}")

        # Upload file csv 
        try:
            sftp_ek26 = ssh_ek26.open_sftp()

            local_csv_fpath = os.path.join( self.local_csv_dir, waveform_file_name)
            remote_csv_fpath = os.path.join( self.remote_csv_dir, waveform_file_name)
            remote_csv_fpath = remote_csv_fpath.replace("\\", "/")

            print( f"Carico il file CSV: {local_csv_fpath} → {remote_csv_fpath}" )

            sftp_ek26.put(local_csv_fpath, remote_csv_fpath)
            print("Upload CSV completato")
            print( "-" * 60 )

        except Exception as e:
            raise RuntimeError(f"Errore durante upload CSV: {e}")

        # Command construction & execution

        acq_command = f'sudo ./testDMA -v {cfg_str} -f "{waveform_file_name}"'

        if run_acquisition:
            cmd = f"cd {self.remote_dir} && {acq_command}"
            print(f"\nEseguo comando: {cmd}")
            ret, out, err = run_ssh_cmd( ssh_ek26, cmd )
        
            last_line = out.strip().splitlines()[-1] if out.strip() else ""
            if last_line.startswith("*** TEST OK"):
                print(f"\nAcquisizione completata: {last_line}")
            else:
                print("\nATTENZIONE: acquisizione non completata correttamente!")
                print(f"\nOutput completo:\n{out}")
                if err:
                    print(f"\nErrori:\n{err}")
                raise RuntimeError("Acquisizione fallita - output inatteso")
            print("_" * 60)

        time.sleep( 0.5 )

        # ********** Scarico i file acquisiti ************
        items = sftp_ek26.listdir_attr( self.remote_data_dir )
        print("Copio le acquisizioni in locale")
        print(f"Totale file trovati: {len(items)}")

        # trovo l'ultimo impulso eseguito        
        fnames = [ item.filename for item in items ]
        info_code = [f[0:5] for f in fnames if f.endswith( '.info' ) ]
        info_code.sort()        
        print( info_code )
        # acq_code = f"{acq_n:05d}"
        acq_code = info_code[-1]
        
        print( f"Scarico acquisizione: {acq_code}" )
        fnames = [ filename for filename in fnames if filename.startswith( acq_code )  ]
        
        for filename in fnames:
            print( filename )

            remote_item_fpath = self.remote_data_dir + "/" + filename
            local_item_fpath = os.path.join( self.local_data_dir, filename)
            sftp_ek26.get(remote_item_fpath, local_item_fpath)
            
        sftp_ek26.close()
        ssh_ek26.close()

        print("\nCopia eseguita")
        # print("_" * 60)

        return acq_code
    

import numpy as np
import matplotlib.pyplot as plt

class DmaAcquisition:
    def __init__(self,
        plot_dir=r"C:\Users\maglab\Mattia\EPICA\mk_III_rc\plots",
        data_dir=r"C:\Users\maglab\Mattia\EPICA\mk_III_rc\data"):

        self.data_dir = data_dir
        self.plot_dir = plot_dir

        self.IB_SHUNT_MAP = {
            "1mA": 4.027E-08, "10mA": 3.986E-07, 
            "100mA": 3.906E-06, "1A": 3.910E-05 
        }
        self.VB_NOMINAL = 6.455E-03

    def _dak_reader(self, filepath, ib_factor):
        raw = np.fromfile(filepath, dtype="<u4")
        voltage = (raw & 0xFFFF).astype(np.int16) * self.VB_NOMINAL
        current = ((raw >> 16) & 0xFFFF).astype(np.int16) * ib_factor
        return voltage, current

    def _parse_info(self, filepath):
        with open(filepath, "r") as f:
            lines = f.readlines()
        
        info = {"boards_sn": {}}
        for line in lines:
            s = line.strip()
            if s.startswith("Freq Campionamento"):
                info["fs"] = float(s.split(":")[-1])
            elif s.startswith("Shunt A,B"):
                parts = s.split(":")[-1].strip().split()
                info["shunt_a"], info["shunt_b"] = parts[0], parts[1]
        return info

    def _resolve_acq_code(self, acq_n, all_files):
        """Return the five-digit acquisition code for a number or for 'last'."""
        if isinstance(acq_n, str) and acq_n.lower() == "last":
            acq_codes = [
                int(f[:5])
                for f in all_files
                if len(f) >= 5 and f[:5].isdigit() and f.endswith(".info")
            ]
            if not acq_codes:
                raise FileNotFoundError(f"No acquisition .info files found in {self.data_dir}")
            return f"{max(acq_codes):05d}"

        return f"{int(acq_n):05d}"

    def plot(self, acq_n, target_modules=["70"], name=None):
        all_files = os.listdir(self.data_dir)
        acq_code = self._resolve_acq_code(acq_n, all_files)
        dak_files = [f for f in all_files if f.startswith(acq_code) and f.endswith(".dak")]
        info_file = [f for f in all_files if f.startswith(acq_code) and f.endswith(".info")][0]
        
        info = self._parse_info(os.path.join(self.data_dir, info_file))
        
        # Raggruppamento dati
        for mod_id in target_modules:
            mod_chans = {
                "CHA": next((f for f in dak_files if f"_M{mod_id}_CHA" in f), None),
                "CHB": next((f for f in dak_files if f"_M{mod_id}_CHB" in f), None)
            }
            
            if any(mod_chans.values()):
                self._render_module_plots(mod_id, mod_chans, info, name=name)

    def _render_module_plots(self, mod, chans, info, name=None):
        # --- 1. FIGURA TIME DOMAIN (2x2) ---
        fig_td, axs_td = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
        fig_td.suptitle(f"Module M{mod} - Time Domain", fontsize=14)
        axs_td[1, 0].set_xlabel("Time [s]")
        axs_td[1, 1].set_xlabel("Time [s]")

        # --- 2. FIGURA I-V (2x1) ---
        fig_iv, axs_iv = plt.subplots(2, 1, figsize=(10, 8))
        fig_iv.suptitle(f"Module M{mod} - I-V Characteristic", fontsize=14)

        for i, ch_name in enumerate(["CHA", "CHB"]):
            if chans[ch_name]:
                shunt_key = info["shunt_a"] if ch_name == "CHA" else info["shunt_b"]
                v, cur = self._dak_reader(
                    os.path.join(self.data_dir, chans[ch_name]), 
                    self.IB_SHUNT_MAP[shunt_key]
                )
                t = np.arange(len(v)) / info["fs"]

                # Plot Time Domain (Voltage top, Current bottom)
                axs_td[0, i].plot(t, v)
                axs_td[0, i].set_title(f"{ch_name} - Voltage [V]")
                axs_td[0, i].grid(True)

                axs_td[1, i].plot(t, cur)
                axs_td[1, i].set_title(f"{ch_name} - Current [A]")
                axs_td[1, i].grid(True)

                # Plot I-V
                axs_iv[i].plot(v, cur, ".", markersize=1)
                axs_iv[i].set_title(f"{ch_name} - I(V)")
                axs_iv[i].set_xlabel("Voltage [V]")
                axs_iv[i].set_ylabel("Current [A]")
                axs_iv[i].grid(True)

        fig_td.tight_layout(rect=[0, 0.03, 1, 0.95])
        fig_iv.tight_layout(rect=[0, 0.03, 1, 0.95])
        if name:
            fig_td.savefig(os.path.join(self.plot_dir, f"{name}_time_domain.png"), bbox_inches="tight")
            fig_iv.savefig(os.path.join(self.plot_dir, f"{name}_i-v.png"), bbox_inches="tight")
        plt.show()
        

# ---------------------------------------------------------------------------
# Data Reading Class
# ---------------------------------------------------------------------------
class EPICAFolderReader:
    """
    Reads EPICA data by searching a directory for files matching specific 
    acquisition numbers, module IDs, and channels.
    """

    VB_NOMINAL = 6.455E-03

    IB_SHUNT_MAP = {
        "1mA": 4.027E-08, 
        "10mA": 3.986E-07, 
        "100mA": 3.906E-06, 
        "1A": 3.910E-05 
    }


    def __init__(self, root_dir, bit: int = 16, enob: float = 14.2):
        """
        Initializes the reader with the directory structure.
        
        Args:
            root_dir: The base directory of the project.
            sn_ek26: The serial number/subfolder name (e.g., "SL1IPB").
        """
        self.data_dir = root_dir
        self.enob = enob
        self.bit = bit
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

    def _parse_info(self, filepath):
        """Parses the .info file to extract sampling frequency and shunt types."""
        info = {}
        with open(filepath, "r") as f:
            lines = f.readlines()
        
        for line in lines:
            s = line.strip()
            if s.startswith("Freq Campionamento"): # Sampling Frequency
                info["fs"] = float(s.split(":")[-1])
            elif s.startswith("Shunt A,B"):
                parts = s.split(":")[-1].strip().split()
                info["shunt_a"], info["shunt_b"] = parts[0], parts[1]
        return info

    def get_data(self, acq_n, module_id, channel="CHA"):
        """
        Finds the relevant files and extracts time, voltage, and current vectors.
        
        Args:
            acq_n (int): The acquisition number (e.g., 1).
            module_id (str): The module ID (e.g., "70").
            channel (str): "CHA" or "CHB".
            
        Returns:
            tuple: (time_vector, voltage_vector, current_vector)
        """
        acq_code = f"{acq_n:05d}"
        all_files = os.listdir(self.data_dir)
        
        # 1. Locate the .info file for this acquisition
        info_file = next((f for f in all_files if f.startswith(acq_code) and f.endswith(".info")), None)
        if not info_file:
            raise FileNotFoundError(f"No .info file found for acquisition {acq_code}")
        
        info = self._parse_info(os.path.join(self.data_dir, info_file))
        
        # 2. Locate the specific .dak file for the module and channel
        search_pattern = f"_M{module_id}_{channel.upper()}"
        dak_file = next((f for f in all_files if f.startswith(acq_code) and search_pattern in f and f.endswith(".dak")), None)
        
        if not dak_file:
            raise FileNotFoundError(f"No .dak file found for Module {module_id} {channel} in acquisition {acq_code}")

        # 3. Read and convert data
        shunt_key = info["shunt_a"] if channel.upper() == "CHA" else info["shunt_b"]
        ib_factor = self.IB_SHUNT_MAP[shunt_key]
        
        raw = np.fromfile(os.path.join(self.data_dir, dak_file), dtype="<u4")
        
        # Voltage: Lower 16 bits
        voltage = ((raw & 0xFFFF).astype(np.int16)) * self.VB_NOMINAL
        SFR_V = self.VB_NOMINAL * (2 ** self.bit)
        sigma_V = (SFR_V / (2 ** self.enob)) / np.sqrt(12)  # quantization noise std dev
        
        # Current: Upper 16 bits
        current = (((raw >> 16) & 0xFFFF).astype(np.int16)) * ib_factor
        SFR_I = ib_factor * (2 ** self.bit)
        sigma_I = (SFR_I / (2 ** self.enob)) / np.sqrt(12)  # quantization noise std dev

        # Time
        time = np.arange(len(voltage)) / info["fs"]
        
        return time, voltage, current
