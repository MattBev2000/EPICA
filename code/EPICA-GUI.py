import contextlib
import os
import paramiko
import queue
import shlex
import shutil
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


# ----------------------------------------------------------------------------------------
# Date and time of acquisition 
# ----------------------------------------------------------------------------------------
now = date.today().strftime("%Y-%m-%d").replace("-", "_")


# ----------------------------------------------------------------------------------------
# Acquisition parameters
# ----------------------------------------------------------------------------------------
SAMPLING = {
    "156.250kHz": 2,
    "78.125kHz": 3,
    "39.0625kHz": 4,
    "19.53125kHz": 5,
}

FSR = {
    "1mA": 0,
    "10mA": 1,
    "100mA": 2,
    "1A": 3,
}

CONF = {
    "All open": 0,
    "A floating & B floating": 1,
    "A SLP & B floating": 2,
    "A floating & B SLP": 3,
    "A & B SLP": 4,
    "DLP": 5,
}

MODULES = {f"Module n. {index}": f"{(index - 1) * 10:02d}" for index in range(1, 9)}
MODULE_CHOICES = ["All", *MODULES.keys(), "None"]
REMOTE_DELETE_DIR = "/SwDMA/testDMA/SL1IPB"


# ----------------------------------------------------------------------------------------
# Path confguration 
# ----------------------------------------------------------------------------------------
BASE_PATH = Path(__file__).resolve().parent

DATA_PATH = BASE_PATH / f"data_{now}" / f"SL1IPB"
PLOT_PATH = BASE_PATH / "plots"
LOGS_PATH = BASE_PATH / "logs"
CSV_PATH = BASE_PATH / "csv_setup"

# for folder in [DATA_PATH, PLOT_PATH, LOGS_PATH, CSV_PATH]:
#     folder.mkdir(parents=True, exist_ok=True)

BASE_PATH = str(BASE_PATH)
DATA_PATH = str(DATA_PATH)
PLOT_PATH = str(PLOT_PATH)
LOGS_PATH = str(LOGS_PATH)
CSV_PATH = str(CSV_PATH)


def resolve_storage_paths(base_path, serial, today):
    base = Path(base_path).expanduser()
    serial_folder = serial.strip() or "SL1IPB"
    return {
        "base_path": str(base),
        "data_path": str(base / f"data_{today}" / serial_folder),
        "plot_path": str(base / "plots"),
        "logs_path": str(base / "logs"),
        "csv_path": str(base / "csv_setup"),
    }


def ensure_storage_paths(paths):
    for key in ["data_path", "plot_path", "logs_path", "csv_path"]:
        Path(paths[key]).mkdir(parents=True, exist_ok=True)


def run_ssh_cmd(ssh_target, command, timeout=None):
    stdin, stdout, stderr = ssh_target.exec_command(command, get_pty=True)
    channel = stdout.channel
    out_chunks = []
    err_chunks = []
    sudo_password_sent = False
    started_at = time.monotonic()

    while True:
        if channel.recv_ready():
            text = channel.recv(4096).decode(errors="ignore")
            out_chunks.append(text)
            if "sudo" in command and not sudo_password_sent and "password" in text.lower():
                stdin.write("eladit\n")
                stdin.flush()
                sudo_password_sent = True

        if channel.recv_stderr_ready():
            err_chunks.append(channel.recv_stderr(4096).decode(errors="ignore"))

        if channel.exit_status_ready():
            while channel.recv_ready():
                out_chunks.append(channel.recv(4096).decode(errors="ignore"))
            while channel.recv_stderr_ready():
                err_chunks.append(channel.recv_stderr(4096).decode(errors="ignore"))
            break

        if timeout is not None and time.monotonic() - started_at > timeout:
            channel.close()
            raise TimeoutError(f"SSH command timed out after {timeout} seconds: {command}")

        time.sleep(0.02)

    out = "".join(out_chunks)
    err = "".join(err_chunks)
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


class EpicaDaq:
    def __init__(
        self,
        ip_ek26="192.168.54.119",
        sn_ek26="SL1IPB",
        remote_dir="/home/petalinux/SwDMA/testDMA",
        local_dir=".",
        data_dir="data",
        csv_dir="csv_setup",
        online=True,
        verbose=True,
        create_data_dir=True,
    ):
        self.ip_ek26 = ip_ek26
        self.sn_ek26 = sn_ek26
        self.remote_dir = remote_dir
        self.local_dir = local_dir
        self.verbose = verbose
        self.online = online
        self.local_csv_dir = csv_dir
        self.local_data_dir = data_dir
        if create_data_dir:
            os.makedirs(self.local_data_dir, exist_ok=True)
        self.remote_csv_dir = self.remote_dir
        self.remote_data_dir = self.remote_dir + "/" + self.sn_ek26

    def configure_frontend(self, cfg_str="-d 3 -c 4 -sa 3 -sb 3"):
        ssh_ek26 = paramiko.SSHClient()
        ssh_ek26.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_ek26.connect(self.ip_ek26, username="petalinux", password="eladit", timeout=1)
        except Exception as exc:
            raise ConnectionError(f"Impossibile connettersi a {self.ip_ek26}: {exc}") from exc

        try:
            config_command = f"sudo ./testDMA {cfg_str}"
            cmd = f"cd {self.remote_dir} && {config_command}"
            print(f"\nEseguo configurazione front-end: {cmd}")
            ret, out, err = run_ssh_cmd(ssh_ek26, cmd)
            if ret:
                if err:
                    print(f"\nErrori:\n{err}")
                raise RuntimeError(f"Configurazione front-end fallita - exit code {ret}")
            print("\nConfigurazione front-end inviata")
            return out
        finally:
            ssh_ek26.close()

    def delete_remote_acquisition_files(self, target_dirs=None):
        ssh_ek26 = paramiko.SSHClient()
        ssh_ek26.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_ek26.connect(self.ip_ek26, username="petalinux", password="eladit", timeout=1)
        except Exception as exc:
            raise ConnectionError(f"Impossibile connettersi a {self.ip_ek26}: {exc}") from exc

        try:
            target_dirs = target_dirs or [REMOTE_DELETE_DIR, self.remote_data_dir]
            unique_dirs = []
            for target_dir in target_dirs:
                target_dir = str(target_dir).strip().rstrip("/")
                if target_dir and target_dir not in unique_dirs:
                    unique_dirs.append(target_dir)
            quoted_dirs = " ".join(shlex.quote(target_dir) for target_dir in unique_dirs)
            listed_dirs = "\\n".join(f"  - {target_dir}" for target_dir in unique_dirs)
            cmd = (
                "target_dir=''; "
                f"for candidate in {quoted_dirs}; do "
                "if [ -d \"$candidate\" ]; then target_dir=\"$candidate\"; break; fi; "
                "done; "
                "if [ -z \"$target_dir\" ]; then "
                f"printf 'No delete target directory found. Tried:\\n{listed_dirs}\\n'; "
                "exit 1; "
                "fi; "
                "cd \"$target_dir\" && "
                "printf 'Using delete target: %s\\n' \"$target_dir\" && "
                "rm -rf -- *.info *.dak"
            )
            print(f"\nEseguo cancellazione file remoti: {cmd}")
            ret, out, err = run_ssh_cmd(ssh_ek26, cmd, timeout=20)
            if ret:
                if err:
                    print(f"\nErrori:\n{err}")
                raise RuntimeError(f"Cancellazione file remoti fallita - exit code {ret}")
            print("\nFile .info e .dak cancellati")
            return out
        finally:
            ssh_ek26.close()

    def connect_and_acquire(
        self,
        waveform_file_name="seq_rc001.csv",
        cfg_str="-d 3 -c 4 -sa 3 -sb 3",
        run_acquisition=True,
    ):
        ssh_ek26 = paramiko.SSHClient()
        ssh_ek26.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_ek26.connect(self.ip_ek26, username="petalinux", password="eladit", timeout=1)
        except Exception as exc:
            raise ConnectionError(f"Impossibile connettersi a {self.ip_ek26}: {exc}") from exc

        try:
            sftp_ek26 = ssh_ek26.open_sftp()
            local_csv_fpath = os.path.join(self.local_csv_dir, waveform_file_name)
            remote_csv_fpath = os.path.join(self.remote_csv_dir, waveform_file_name).replace("\\", "/")
            print(f"Carico il file CSV: {local_csv_fpath} -> {remote_csv_fpath}")
            sftp_ek26.put(local_csv_fpath, remote_csv_fpath)
            print("Upload CSV completato")
            print("-" * 60)
        except Exception as exc:
            ssh_ek26.close()
            raise RuntimeError(f"Errore durante upload CSV: {exc}") from exc

        acq_command = f'sudo ./testDMA -v {cfg_str} -f "{waveform_file_name}"'

        if run_acquisition:
            cmd = f"cd {self.remote_dir} && {acq_command}"
            print(f"\nEseguo comando: {cmd}")
            _ret, out, err = run_ssh_cmd(ssh_ek26, cmd)

            last_line = out.strip().splitlines()[-1] if out.strip() else ""
            if last_line.startswith("*** TEST OK"):
                print(f"\nAcquisizione completata: {last_line}")
            else:
                print("\nATTENZIONE: acquisizione non completata correttamente!")
                print(f"\nOutput completo:\n{out}")
                if err:
                    print(f"\nErrori:\n{err}")
                sftp_ek26.close()
                ssh_ek26.close()
                raise RuntimeError("Acquisizione fallita - output inatteso")
            print("_" * 60)

        time.sleep(0.5)

        items = sftp_ek26.listdir_attr(self.remote_data_dir)
        print("Copio le acquisizioni in locale")
        print(f"Totale file trovati: {len(items)}")

        fnames = [item.filename for item in items]
        info_code = [filename[0:5] for filename in fnames if filename.endswith(".info")]
        info_code.sort()
        print(info_code)
        if not info_code:
            sftp_ek26.close()
            ssh_ek26.close()
            raise RuntimeError(f"Nessun file .info trovato in {self.remote_data_dir}")
        acq_code = info_code[-1]

        print(f"Scarico acquisizione: {acq_code}")
        fnames = [filename for filename in fnames if filename.startswith(acq_code)]

        for filename in fnames:
            print(filename)
            remote_item_fpath = self.remote_data_dir + "/" + filename
            local_item_fpath = os.path.join(self.local_data_dir, filename)
            sftp_ek26.get(remote_item_fpath, local_item_fpath)

        sftp_ek26.close()
        ssh_ek26.close()
        print("\nCopia eseguita")
        return acq_code


class DmaAcquisition:
    def __init__(self, plot_dir="plots", data_dir="data"):
        self.data_dir = data_dir
        self.plot_dir = plot_dir
        self.IB_SHUNT_MAP = {
            "1mA": 4.027e-08,
            "10mA": 3.986e-07,
            "100mA": 3.906e-06,
            "1A": 3.910e-05,
        }
        self.VB_NOMINAL = 6.455e-03

    def _dak_reader(self, filepath, ib_factor):
        raw = np.fromfile(filepath, dtype="<u4")
        voltage = (raw & 0xFFFF).astype(np.int16) * self.VB_NOMINAL
        current = ((raw >> 16) & 0xFFFF).astype(np.int16) * ib_factor
        return voltage, current

    def _parse_info(self, filepath):
        with open(filepath, "r") as info_file:
            lines = info_file.readlines()

        info = {"boards_sn": {}}
        for line in lines:
            text = line.strip()
            if text.startswith("Freq Campionamento"):
                info["fs"] = float(text.split(":")[-1])
            elif text.startswith("Shunt A,B"):
                parts = text.split(":")[-1].strip().split()
                info["shunt_a"], info["shunt_b"] = parts[0], parts[1]
        return info

    def _resolve_acq_code(self, acq_n, all_files):
        if isinstance(acq_n, str) and acq_n.lower() == "last":
            acq_codes = [
                int(filename[:5])
                for filename in all_files
                if len(filename) >= 5 and filename[:5].isdigit() and filename.endswith(".info")
            ]
            if not acq_codes:
                raise FileNotFoundError(f"No acquisition .info files found in {self.data_dir}")
            return f"{max(acq_codes):05d}"
        return f"{int(acq_n):05d}"

    def plot(self, acq_n, target_modules=None, name=None, show=True):
        figures = self.create_figures(acq_n, target_modules=target_modules, name=name)
        if show:
            plt.show()
        return figures

    def create_figures(self, acq_n, target_modules=None, name=None):
        if target_modules is None:
            target_modules = ["70"]
        if not target_modules:
            return []

        all_files = os.listdir(self.data_dir)
        acq_code = self._resolve_acq_code(acq_n, all_files)
        dak_files = [filename for filename in all_files if filename.startswith(acq_code) and filename.endswith(".dak")]
        info_file = next(
            (filename for filename in all_files if filename.startswith(acq_code) and filename.endswith(".info")),
            None,
        )
        if not info_file:
            raise FileNotFoundError(f"No .info file found for acquisition {acq_code}")

        info = self._parse_info(os.path.join(self.data_dir, info_file))
        figures = []
        use_module_suffix = len(target_modules) > 1
        for mod_id in target_modules:
            mod_chans = {
                "CHA": next((filename for filename in dak_files if f"_M{mod_id}_CHA" in filename), None),
                "CHB": next((filename for filename in dak_files if f"_M{mod_id}_CHB" in filename), None),
            }
            if any(mod_chans.values()):
                plot_name = f"{name}_M{mod_id}" if name and use_module_suffix else name
                figures.extend(self._render_module_plots(mod_id, mod_chans, info, name=plot_name))
        return figures

    def _render_module_plots(self, mod, chans, info, name=None):
        fig_td, axs_td = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
        fig_td.suptitle(f"Module M{mod} - Time Domain", fontsize=14)
        axs_td[1, 0].set_xlabel("Time [s]")
        axs_td[1, 1].set_xlabel("Time [s]")

        fig_iv, axs_iv = plt.subplots(2, 1, figsize=(10, 8))
        fig_iv.suptitle(f"Module M{mod} - I-V Characteristic", fontsize=14)

        for index, ch_name in enumerate(["CHA", "CHB"]):
            if chans[ch_name]:
                shunt_key = info["shunt_a"] if ch_name == "CHA" else info["shunt_b"]
                voltage, current = self._dak_reader(
                    os.path.join(self.data_dir, chans[ch_name]),
                    self.IB_SHUNT_MAP[shunt_key],
                )
                time_axis = np.arange(len(voltage)) / info["fs"]

                axs_td[0, index].plot(time_axis, voltage)
                axs_td[0, index].set_title(f"{ch_name} - Voltage [V]")
                axs_td[0, index].grid(True)

                axs_td[1, index].plot(time_axis, current)
                axs_td[1, index].set_title(f"{ch_name} - Current [A]")
                axs_td[1, index].grid(True)

                axs_iv[index].plot(voltage, current, ".", markersize=1)
                axs_iv[index].set_title(f"{ch_name} - I(V)")
                axs_iv[index].set_xlabel("Voltage [V]")
                axs_iv[index].set_ylabel("Current [A]")
                axs_iv[index].grid(True)

        fig_td.tight_layout(rect=[0, 0.03, 1, 0.95])
        fig_iv.tight_layout(rect=[0, 0.03, 1, 0.95])
        if name:
            fig_td.savefig(os.path.join(self.plot_dir, f"{name}_time_domain.png"), bbox_inches="tight")
            fig_iv.savefig(os.path.join(self.plot_dir, f"{name}_i-v.png"), bbox_inches="tight")
        return [fig_td, fig_iv]


class QueueWriter:
    def __init__(self, output_queue):
        self.output_queue = output_queue

    def write(self, text):
        if text:
            self.output_queue.put(("message", text))

    def flush(self):
        pass


class SpiderPlotWindow(tk.Toplevel):
    def __init__(self, master, figures):
        super().__init__(master)
        self.title("SPIDER - Acquisition plots")
        self.geometry(self._window_geometry(width_ratio=0.82, height_ratio=0.82, max_width=1120, max_height=740))
        self.minsize(820, 540)
        self.configure(bg="#0f131a")
        self.figures = figures
        self.canvases = []

        header = ttk.Frame(self, style="Surface.TFrame", padding=(14, 10))
        header.pack(fill="x")
        ttk.Label(header, text="SPIDER Plot View", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text=f"{len(figures)} figures",
            style="Muted.TLabel",
        ).pack(side="right")

        notebook = ttk.Notebook(self, style="Dark.TNotebook")
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for index, figure in enumerate(figures, start=1):
            figure.patch.set_facecolor("#111722")
            for axis in figure.axes:
                axis.set_facecolor("#141b27")
                axis.tick_params(colors="#c7d0dd")
                axis.xaxis.label.set_color("#d8dee9")
                axis.yaxis.label.set_color("#d8dee9")
                axis.title.set_color("#f2f5f8")
                for spine in axis.spines.values():
                    spine.set_color("#384252")
                axis.grid(True, color="#2a3341", alpha=0.75)
            if figure._suptitle:
                figure._suptitle.set_color("#f2f5f8")

            tab = ttk.Frame(notebook, style="Panel.TFrame")
            notebook.add(tab, text=f"Plot {index}")
            canvas = FigureCanvasTkAgg(figure, master=tab)
            canvas.draw()
            toolbar = NavigationToolbar2Tk(canvas, tab, pack_toolbar=False)
            toolbar.update()
            toolbar.pack(fill="x", padx=8, pady=(8, 0))
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
            self.canvases.append(canvas)

    def _window_geometry(self, width_ratio, height_ratio, max_width, max_height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(max_width, max(820, int(screen_width * width_ratio)))
        height = min(max_height, max(540, int(screen_height * height_ratio)))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        return f"{width}x{height}+{x}+{y}"


class SshTerminalPanel(ttk.Frame):
    SHIFT_MASK = 0x0001
    CONTROL_MASK = 0x0004
    ALT_MASKS = (0x0008, 0x0080, 0x20000)

    SPECIAL_KEY_SEQUENCES = {
        "Return": "\r",
        "KP_Enter": "\r",
        "BackSpace": "\x7f",
        "Delete": "\x1b[3~",
        "KP_Delete": "\x1b[3~",
        "Tab": "\t",
        "Escape": "\x1b",
        "Up": "\x1b[A",
        "KP_Up": "\x1b[A",
        "Down": "\x1b[B",
        "KP_Down": "\x1b[B",
        "Right": "\x1b[C",
        "KP_Right": "\x1b[C",
        "Left": "\x1b[D",
        "KP_Left": "\x1b[D",
        "Home": "\x1b[H",
        "KP_Home": "\x1b[H",
        "End": "\x1b[F",
        "KP_End": "\x1b[F",
        "Prior": "\x1b[5~",
        "KP_Prior": "\x1b[5~",
        "Next": "\x1b[6~",
        "KP_Next": "\x1b[6~",
        "Insert": "\x1b[2~",
        "KP_Insert": "\x1b[2~",
    }

    MODIFIED_CSI_KEYS = {
        "Up": ("1", "A"),
        "KP_Up": ("1", "A"),
        "Down": ("1", "B"),
        "KP_Down": ("1", "B"),
        "Right": ("1", "C"),
        "KP_Right": ("1", "C"),
        "Left": ("1", "D"),
        "KP_Left": ("1", "D"),
        "Home": ("1", "H"),
        "KP_Home": ("1", "H"),
        "End": ("1", "F"),
        "KP_End": ("1", "F"),
        "Insert": ("2", "~"),
        "KP_Insert": ("2", "~"),
        "Delete": ("3", "~"),
        "KP_Delete": ("3", "~"),
        "Prior": ("5", "~"),
        "KP_Prior": ("5", "~"),
        "Next": ("6", "~"),
        "KP_Next": ("6", "~"),
    }

    def __init__(self, master, ip_var, username="petalinux", password="eladit"):
        super().__init__(master, style="Panel.TFrame")

        self.ip_var = ip_var
        self.username = username
        self.password = password
        self.client = None
        self.channel = None
        self.connected = False
        self.output_queue = queue.Queue()
        self.terminal_font = None
        self.command_var = tk.StringVar()

        self._build_layout()
        self._write_local("SSH terminal ready. Use Connect to start an interactive shell.\n", "muted")
        self.after(40, self._drain_output_queue)

    def _build_layout(self):
        top = ttk.Frame(self, style="Surface.TFrame", padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="SSH Terminal", style="Section.TLabel").pack(side="left")
        self.target_label = ttk.Label(top, text=self._target_text(), style="Muted.TLabel")
        self.target_label.pack(side="left", padx=(10, 0))
        ttk.Button(top, text="Connect", command=self._reconnect, takefocus=False).pack(side="right")
        ttk.Button(top, text="Disconnect", command=self._disconnect, takefocus=False).pack(side="right", padx=(0, 8))

        self.terminal = tk.Text(
            self,
            bg="#05070b",
            fg="#d8dee9",
            insertbackground="#ffffff",
            selectbackground="#2f7dd1",
            relief="flat",
            borderwidth=0,
            font=("Consolas", 10),
            wrap="char",
            undo=False,
            height=12,
        )
        self.terminal_font = tkfont.Font(font=self.terminal["font"])
        self.terminal.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.terminal.tag_configure("error", foreground="#ff8a8a")
        self.terminal.tag_configure("muted", foreground="#8f9aaa")
        self.terminal.focus_set()
        self.terminal.bind("<Key>", self._send_key)
        self.terminal.bind("<Control-v>", self._paste)
        self.terminal.bind("<<Paste>>", self._paste)
        self.terminal.bind("<<Copy>>", self._copy_selection)
        self.terminal.bind("<Button-2>", self._paste)
        self.terminal.bind("<Configure>", self._resize_pty)
        self.terminal.bind("<Button-1>", lambda _event: self.terminal.focus_set())

        command_row = ttk.Frame(self, style="Panel.TFrame")
        command_row.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(command_row, text="$", style="PanelMuted.TLabel").pack(side="left", padx=(0, 6))
        self.command_entry = ttk.Entry(command_row, textvariable=self.command_var)
        self.command_entry.pack(side="left", fill="x", expand=True)
        self.command_entry.bind("<Return>", self._send_command_line)
        ttk.Button(command_row, text="Send", command=self._send_command_line, takefocus=False).pack(side="left", padx=(8, 0))

    def _target_text(self):
        ip = self.ip_var.get().strip() or "<missing-ip>"
        return f"{self.username}@{ip}"

    def _connect_worker(self):
        try:
            ip = self.ip_var.get().strip()
            if not ip:
                raise ValueError("Insert EK26 IP before connecting the terminal.")
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(ip, username=self.username, password=self.password, timeout=5)
            cols, rows = self._terminal_size_chars()
            self.channel = self.client.invoke_shell(term="xterm-256color", width=cols, height=rows)
            self.channel.settimeout(0.2)
            self.connected = True
            self.output_queue.put(("local", "Connected. Interactive shell ready.\n", "muted"))
            self.output_queue.put(("focus", "", None))
            threading.Thread(target=self._reader_worker, daemon=True).start()
        except Exception as exc:
            self.output_queue.put(("local", f"SSH connection failed: {exc}\n", "error"))

    def _reader_worker(self):
        while self.connected and self.channel:
            try:
                if self.channel.recv_ready():
                    data = self.channel.recv(4096).decode(errors="ignore")
                    self.output_queue.put(("remote", data, None))
                else:
                    time.sleep(0.02)
            except Exception as exc:
                if self.connected:
                    self.output_queue.put(("local", f"\nSSH read error: {exc}\n", "error"))
                break

    def _send_key(self, event):
        if event.keysym in {"Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R"}:
            return "break"

        is_control, is_shift, is_alt = self._key_modifiers(event)
        key = event.keysym.lower()

        if is_control and key == "v":
            return self._paste()
        if is_shift and key == "insert":
            return self._paste()
        if is_control and key in {"c", "insert"}:
            if self._has_selection():
                return self._copy_selection()
            return self._send_payload("\x03")

        payload = self._payload_for_key(event, is_control, is_shift, is_alt)
        if payload is None:
            return "break"

        self._send_payload(payload)
        return "break"

    def _key_modifiers(self, event):
        state = getattr(event, "state", 0)
        is_control = bool(state & self.CONTROL_MASK)
        is_shift = bool(state & self.SHIFT_MASK)
        is_alt = any(state & mask for mask in self.ALT_MASKS)
        return is_control, is_shift, is_alt

    def _payload_for_key(self, event, is_control, is_shift, is_alt):
        modifiers = self._xterm_modifier_code(is_shift, is_alt, is_control)
        if modifiers and event.keysym in self.MODIFIED_CSI_KEYS:
            prefix, suffix = self.MODIFIED_CSI_KEYS[event.keysym]
            return f"\x1b[{prefix};{modifiers}{suffix}"

        if is_control:
            if event.char and ord(event.char) < 32:
                return event.char
            payload = self._control_payload(event.keysym)
            if payload is not None:
                return payload

        payload = self.SPECIAL_KEY_SEQUENCES.get(event.keysym)
        if payload is not None:
            return payload

        if event.char:
            return f"\x1b{event.char}" if is_alt else event.char
        return None

    def _control_payload(self, keysym):
        key = keysym.lower()
        if len(key) == 1 and "a" <= key <= "z":
            return chr(ord(key) - ord("a") + 1)
        return {
            "space": "\x00",
            "at": "\x00",
            "bracketleft": "\x1b",
            "backslash": "\x1c",
            "bracketright": "\x1d",
            "asciicircum": "\x1e",
            "underscore": "\x1f",
            "minus": "\x1f",
            "question": "\x7f",
        }.get(key)

    def _xterm_modifier_code(self, is_shift, is_alt, is_control):
        code = 1
        if is_shift:
            code += 1
        if is_alt:
            code += 2
        if is_control:
            code += 4
        return code if code > 1 else None

    def _send_payload(self, payload):
        if not self.connected or not self.channel:
            return "break"
        try:
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            while payload:
                sent = self.channel.send(payload)
                if sent <= 0:
                    raise RuntimeError("SSH channel closed while sending input")
                payload = payload[sent:]
        except Exception as exc:
            self._write_local(f"\nSSH send error: {exc}\n", "error")
        return "break"

    def _terminal_size_chars(self):
        if not self.terminal_font:
            return 120, 36
        char_width = max(1, self.terminal_font.measure("M"))
        char_height = max(1, self.terminal_font.metrics("linespace"))
        width = max(20, self.terminal.winfo_width() // char_width)
        height = max(5, self.terminal.winfo_height() // char_height)
        return width, height

    def _resize_pty(self, _event=None):
        if not self.connected or not self.channel:
            return
        try:
            cols, rows = self._terminal_size_chars()
            self.channel.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    def _has_selection(self):
        return bool(self.terminal.tag_ranges(tk.SEL))

    def _copy_selection(self, _event=None):
        if not self._has_selection():
            return "break"
        try:
            text = self.terminal.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(text)
        except Exception as exc:
            self._write_local(f"\nCopy failed: {exc}\n", "error")
        return "break"

    def _paste(self, _event=None):
        try:
            text = self._clipboard_text()
            self._send_payload(text.replace("\n", "\r"))
        except Exception as exc:
            self._write_local(f"\nPaste failed: {exc}\n", "error")
        return "break"

    def _clipboard_text(self):
        try:
            return self.clipboard_get()
        except tk.TclError:
            return self.selection_get(selection="PRIMARY")

    def _drain_output_queue(self):
        try:
            while True:
                kind, payload, tag = self.output_queue.get_nowait()
                if kind in {"remote", "local"}:
                    self._write_local(payload, tag)
                elif kind == "focus":
                    self.after(10, self.command_entry.focus_set)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(40, self._drain_output_queue)

    def _write_local(self, text, tag=None):
        self.terminal.configure(state="normal")
        self.terminal.insert(tk.END, text, tag)
        self.terminal.see(tk.END)

    def _send_command_line(self, _event=None):
        command = self.command_var.get()
        if not self.connected or not self.channel:
            self._write_local("\nSSH terminal is not connected.\n", "error")
            return "break"
        self._send_payload(command + "\r")
        self.command_var.set("")
        self.command_entry.focus_set()
        return "break"

    def _disconnect(self):
        self.connected = False
        if self.channel:
            self.channel.close()
            self.channel = None
        if self.client:
            self.client.close()
            self.client = None
        self._write_local("\nDisconnected.\n", "muted")

    def _reconnect(self):
        self._disconnect()
        self.target_label.configure(text=self._target_text())
        self._write_local(f"Connecting to {self._target_text()}...\n", "muted")
        threading.Thread(target=self._connect_worker, daemon=True).start()
        self.after(10, self.command_entry.focus_set)

    def _close(self):
        self.connected = False
        if self.channel:
            self.channel.close()
        if self.client:
            self.client.close()


class EPCIAAcquisition(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EPCIA Acquisition")
        self.geometry(self._window_geometry(width_ratio=0.88, height_ratio=0.86, max_width=1060, max_height=720))
        self.minsize(900, 580)
        self.configure(bg="#0b0f14")

        self.output_queue = queue.Queue()
        self.worker = None
        self.configure_worker = None
        self.delete_worker = None
        self.plot_window = None
        self.ssh_terminal = None
        self.frontend_config_signature = None

        self._init_style()
        self._init_vars()
        self._build_layout()
        self._update_path_footer()
        self.after(80, self._drain_output_queue)

    def _window_geometry(self, width_ratio, height_ratio, max_width, max_height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(max_width, max(900, int(screen_width * width_ratio)))
        height = min(max_height, max(580, int(screen_height * height_ratio)))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _init_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure(".", background="#0b0f14", foreground="#d8dee9", fieldbackground="#151b24")
        self.style.configure("Root.TFrame", background="#0b0f14")
        self.style.configure("Surface.TFrame", background="#101720")
        self.style.configure("Panel.TFrame", background="#111722")
        self.style.configure("TLabel", background="#0b0f14", foreground="#d8dee9")
        self.style.configure("Title.TLabel", background="#101720", foreground="#f5f7fb", font=("Segoe UI", 14, "bold"))
        self.style.configure("Section.TLabel", background="#111722", foreground="#f5f7fb", font=("Segoe UI", 10, "bold"))
        self.style.configure("Muted.TLabel", background="#101720", foreground="#8f9aaa")
        self.style.configure("PanelMuted.TLabel", background="#111722", foreground="#8f9aaa")
        self.style.configure("TButton", background="#263244", foreground="#f5f7fb", borderwidth=0, padding=(10, 6))
        self.style.map("TButton", background=[("active", "#33435a"), ("disabled", "#1a202b")])
        self.style.configure("Accent.TButton", background="#2f7dd1", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        self.style.map("Accent.TButton", background=[("active", "#3d8fe8"), ("disabled", "#243145")])
        self.style.configure("Danger.TButton", background="#d12f2f", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        self.style.map("Danger.TButton", background=[("active", "#f04a4a"), ("disabled", "#4a2528")])
        self.style.configure("TEntry", fieldbackground="#151b24", foreground="#f5f7fb", bordercolor="#2a3341", padding=5)
        self.style.configure("TCombobox", fieldbackground="#151b24", foreground="#f5f7fb", bordercolor="#2a3341", padding=5)
        self.style.map("TCombobox", fieldbackground=[("readonly", "#151b24")], foreground=[("readonly", "#f5f7fb")])
        self.style.configure("TCheckbutton", background="#111722", foreground="#d8dee9")
        self.style.configure("Dark.TNotebook", background="#0f131a", borderwidth=0)
        self.style.configure("Dark.TNotebook.Tab", background="#17202c", foreground="#d8dee9", padding=(12, 8))
        self.style.map("Dark.TNotebook.Tab", background=[("selected", "#243145")], foreground=[("selected", "#ffffff")])

    def _init_vars(self):
        self.today = date.today().strftime("%Y-%m-%d").replace("-", "_")
        self.fs_var = tk.StringVar(value="78.125kHz")
        self.fsr_var = tk.StringVar(value="10mA")
        self.conf_var = tk.StringVar(value="A & B SLP")
        self.acq_var = tk.StringVar(value="last")
        self.module_var = tk.StringVar(value="Module n. 8")
        self.csv_var = tk.StringVar()
        self.file_name_var = tk.StringVar()
        self.base_path_var = tk.StringVar()
        self.ip_var = tk.StringVar(value="192.168.54.119")
        self.serial_var = tk.StringVar(value="SL1IPB")
        self.remote_dir_var = tk.StringVar(value="/home/petalinux/SwDMA/testDMA")
        self.run_acquisition_var = tk.BooleanVar(value=True)
        self.auto_name_var = tk.BooleanVar(value=True)
        self.base_path_var.trace_add("write", lambda *_args: self._update_path_footer())
        self.serial_var.trace_add("write", lambda *_args: self._update_path_footer())
        for var in [self.fs_var, self.fsr_var, self.conf_var, self.module_var, self.ip_var, self.remote_dir_var]:
            var.trace_add("write", self._mark_frontend_configuration_dirty)

    def _build_layout(self):
        root = ttk.Frame(self, style="Root.TFrame", padding=10)
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root, style="Surface.TFrame", padding=(14, 10))
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="EPCIA Acquisition", style="Title.TLabel").pack(side="left")
        self.status_label = ttk.Label(top, text="Ready", style="Muted.TLabel")
        self.status_label.pack(side="right")

        body = ttk.Frame(root, style="Root.TFrame")
        body.pack(fill="both", expand=True)
        left_outer = ttk.Frame(body, style="Panel.TFrame")
        left_outer.pack(side="left", fill="y", padx=(0, 8))
        right = ttk.Frame(body, style="Panel.TFrame", padding=12)
        right.pack(side="left", fill="both", expand=True)

        left = self._scrollable_panel(left_outer, width=300)
        self._build_controls(left)
        self._build_terminal(right)
        self._build_messages(right)

    def _build_terminal(self, parent):
        self.ssh_terminal = SshTerminalPanel(parent, ip_var=self.ip_var)
        self.ssh_terminal.pack(fill="x", expand=False, pady=(0, 10))

    def _scrollable_panel(self, parent, width):
        canvas = tk.Canvas(parent, width=width, bg="#111722", highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas, style="Panel.TFrame", padding=12)
        content_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def configure_scrollregion(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def configure_content(event):
            canvas.itemconfigure(content_id, width=event.width)

        def scroll_with_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        content.bind("<Configure>", configure_scrollregion)
        canvas.bind("<Configure>", configure_content)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", scroll_with_wheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="y", expand=False)
        scrollbar.pack(side="right", fill="y")
        return content

    def _build_controls(self, parent):
        ttk.Label(parent, text="Acquisition setup", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self._combo(parent, "Sampling", self.fs_var, list(SAMPLING.keys()))
        self._combo(parent, "Full-scale range", self.fsr_var, list(FSR.keys()))
        self._combo(parent, "Configuration", self.conf_var, list(CONF.keys()), width=30)
        self._entry(parent, "Acquisition", self.acq_var)
        self._combo(parent, "Module", self.module_var, MODULE_CHOICES, width=30)

        ttk.Separator(parent).pack(fill="x", pady=10)
        ttk.Label(parent, text="Storage", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self._path_entry(parent, "Base save path", self.base_path_var, self._browse_base_path)

        ttk.Separator(parent).pack(fill="x", pady=10)
        ttk.Label(parent, text="CSV import", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self._path_entry(parent, "CSV file", self.csv_var, self._browse_csv)

        ttk.Separator(parent).pack(fill="x", pady=10)
        ttk.Label(parent, text="Target", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self._entry(parent, "EK26 IP", self.ip_var)
        self._entry(parent, "Serial", self.serial_var)
        self._entry(parent, "Remote dir", self.remote_dir_var, width=34)

        ttk.Separator(parent).pack(fill="x", pady=10)
        self._entry(parent, "Output name", self.file_name_var, width=30)
        ttk.Checkbutton(parent, text="Automatic output name", variable=self.auto_name_var).pack(anchor="w", pady=(2, 6))
        ttk.Checkbutton(parent, text="Run remote acquisition", variable=self.run_acquisition_var).pack(anchor="w", pady=(0, 12))

        self.configure_button = ttk.Button(parent, text="Configure front-end", command=self._configure_frontend)
        self.configure_button.pack(fill="x", pady=(0, 8))
        self.run_button = ttk.Button(parent, text="Run acquisition + plot", style="Accent.TButton", command=self._run)
        self.run_button.pack(fill="x")
        self.delete_button = ttk.Button(parent, text="Delete Files", style="Danger.TButton", command=self._delete_remote_files)
        self.delete_button.pack(fill="x", pady=(8, 0))
        ttk.Button(parent, text="Clear messages", command=self._clear_messages).pack(fill="x", pady=(8, 0))

    def _build_messages(self, parent):
        header = ttk.Frame(parent, style="Panel.TFrame")
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="Messages", style="Section.TLabel").pack(side="left")
        ttk.Label(header, text="Live stdout/stderr handling", style="PanelMuted.TLabel").pack(side="right")

        self.messages = scrolledtext.ScrolledText(
            parent,
            bg="#070a0f",
            fg="#d8dee9",
            insertbackground="#ffffff",
            selectbackground="#2f7dd1",
            relief="flat",
            borderwidth=0,
            font=("Consolas", 9),
            wrap="word",
        )
        self.messages.pack(fill="both", expand=True)
        self.messages.tag_configure("error", foreground="#ff8a8a")
        self.messages.tag_configure("ok", foreground="#77d18d")
        self.messages.tag_configure("muted", foreground="#8f9aaa")

        footer = ttk.Frame(parent, style="Panel.TFrame")
        footer.pack(fill="x", pady=(10, 0))
        self.data_path_label = ttk.Label(footer, style="PanelMuted.TLabel")
        self.data_path_label.pack(anchor="w")
        self.plot_path_label = ttk.Label(footer, style="PanelMuted.TLabel")
        self.plot_path_label.pack(anchor="w")
        self.logs_path_label = ttk.Label(footer, style="PanelMuted.TLabel")
        self.logs_path_label.pack(anchor="w")
        self._update_path_footer()

    def _combo(self, parent, label, var, values, width=22):
        ttk.Label(parent, text=label, style="PanelMuted.TLabel").pack(anchor="w", pady=(6, 2))
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=width)
        combo.pack(fill="x")
        combo.bind("<MouseWheel>", self._ignore_combo_mousewheel)
        combo.bind("<Button-4>", self._ignore_combo_mousewheel)
        combo.bind("<Button-5>", self._ignore_combo_mousewheel)
        return combo

    def _ignore_combo_mousewheel(self, _event=None):
        return "break"

    def _entry(self, parent, label, var, width=22):
        ttk.Label(parent, text=label, style="PanelMuted.TLabel").pack(anchor="w", pady=(6, 2))
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.pack(fill="x")
        return entry

    def _path_entry(self, parent, label, var, command):
        ttk.Label(parent, text=label, style="PanelMuted.TLabel").pack(anchor="w", pady=(6, 2))
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x")
        entry = ttk.Entry(row, textvariable=var, width=22)
        entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse", command=command).pack(side="left", padx=(8, 0))
        return entry

    def _current_paths(self):
        base_path = self.base_path_var.get().strip()
        if not base_path:
            return {
                "base_path": "",
                "data_path": "",
                "plot_path": "",
                "logs_path": "",
                "csv_path": "",
            }
        return resolve_storage_paths(base_path, self.serial_var.get(), self.today)

    def _update_path_footer(self):
        if not hasattr(self, "data_path_label"):
            return
        paths = self._current_paths()
        self.data_path_label.configure(text=f"Data: {paths['data_path']}")
        self.plot_path_label.configure(text=f"Plots: {paths['plot_path']}")
        self.logs_path_label.configure(text=f"Logs: {paths['logs_path']}")

    def _browse_base_path(self):
        selected = filedialog.askdirectory(
            title="Select base folder for EPICA data",
            initialdir=self.base_path_var.get().strip() or BASE_PATH,
        )
        if selected:
            self.base_path_var.set(selected)
            self._ensure_current_storage_paths()
            self._update_path_footer()
            self._write_message(f"Storage folders ready in: {selected}\n", "ok")

    def _browse_csv(self):
        selected = filedialog.askopenfilename(
            title="Select CSV setup file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self.csv_var.set(selected)

    def _clear_messages(self):
        self.messages.configure(state="normal")
        self.messages.delete("1.0", tk.END)
        self.messages.configure(state="normal")

    def _write_message(self, text, tag=None):
        self.messages.insert(tk.END, text, tag)
        self.messages.see(tk.END)

    def _set_running(self, running):
        self.run_button.configure(state="disabled" if running else "normal")
        if hasattr(self, "configure_button"):
            self.configure_button.configure(state="disabled" if running else "normal")
        if hasattr(self, "delete_button"):
            self.delete_button.configure(state="disabled" if running else "normal")
        self.status_label.configure(text="Running..." if running else "Ready")

    def _set_configuring(self, configuring):
        self.configure_button.configure(state="disabled" if configuring else "normal")
        self.run_button.configure(state="disabled" if configuring else "normal")
        if hasattr(self, "delete_button"):
            self.delete_button.configure(state="disabled" if configuring else "normal")
        self.status_label.configure(text="Configuring front-end..." if configuring else "Ready")

    def _set_deleting(self, deleting):
        self.configure_button.configure(state="disabled" if deleting else "normal")
        self.run_button.configure(state="disabled" if deleting else "normal")
        self.delete_button.configure(state="disabled" if deleting else "normal")
        self.status_label.configure(text="Deleting files..." if deleting else "Ready")

    def _ensure_current_storage_paths(self):
        ensure_storage_paths(self._current_paths())

    def _mark_frontend_configuration_dirty(self, *_args):
        self.frontend_config_signature = None

    def _build_cfg_string(self, settings):
        return f"-d {SAMPLING[settings['fs']]} -c {CONF[settings['conf']]} -sa {FSR[settings['fsr']]} -sb {FSR[settings['fsr']]}"

    def _configuration_signature(self, settings):
        return (
            settings["ip"],
            settings["remote_dir"],
            tuple(settings["modules"]),
            self._build_cfg_string(settings),
        )

    def _frontend_configuration_is_current(self, settings):
        return self.frontend_config_signature == self._configuration_signature(settings)

    def _run(self):
        if self.worker and self.worker.is_alive():
            return
        settings = self._collect_settings()
        if settings["run_acquisition"] and not self._frontend_configuration_is_current(settings):
            message = "Configure the front-end first."
            self._write_message(f"\nERROR: {message}\n", "error")
            messagebox.showerror("noise_acq", message)
            return
        self.file_name_var.set(settings["name"])
        self._set_running(True)
        self._write_message("\n" + "=" * 72 + "\nStarting run\n", "ok")
        self.worker = threading.Thread(target=self._run_worker, args=(settings,), daemon=True)
        self.worker.start()

    def _configure_frontend(self):
        if self.configure_worker and self.configure_worker.is_alive():
            return
        if self.worker and self.worker.is_alive():
            return
        settings = self._collect_settings()
        signature = self._configuration_signature(settings)
        self._set_configuring(True)
        self._write_message("\n" + "=" * 72 + "\nConfiguring front-end\n", "ok")
        self.configure_worker = threading.Thread(
            target=self._configure_frontend_worker,
            args=(settings, signature),
            daemon=True,
        )
        self.configure_worker.start()

    def _delete_remote_files(self):
        if self.delete_worker and self.delete_worker.is_alive():
            return
        if self.worker and self.worker.is_alive():
            return
        if self.configure_worker and self.configure_worker.is_alive():
            return
        settings = self._collect_settings()
        if not settings["ip"]:
            message = "Insert EK26 IP before deleting files."
            self._write_message(f"\nERROR: {message}\n", "error")
            messagebox.showerror("Delete Files", message)
            return
        self._set_deleting(True)
        self._write_message("\n" + "=" * 72 + "\nDeleting remote files\n", "ok")
        self.delete_worker = threading.Thread(target=self._delete_remote_files_worker, args=(settings,), daemon=True)
        self.delete_worker.start()

    def _collect_settings(self):
        fs = self.fs_var.get()
        fsr = self.fsr_var.get()
        acq = self.acq_var.get().strip() or "last"
        module_label = self.module_var.get().strip()
        if module_label == "All":
            modules = list(MODULES.values())
        elif module_label == "None":
            modules = []
        else:
            module_code = MODULES.get(module_label)
            modules = [module_code] if module_code else []
        name = self.file_name_var.get().strip()
        if self.auto_name_var.get() or not name:
            if module_label == "All":
                module_slug = "all"
            elif module_label == "None":
                module_slug = "none"
            else:
                module_slug = "-".join(modules) if modules else "module"
            name = f"{self.today}_acq{acq}_M{module_slug}_{fs}_{fsr}".replace("/", "-")
        paths = self._current_paths()
        return {
            "fs": fs,
            "fsr": fsr,
            "conf": self.conf_var.get(),
            "acq": acq,
            "modules": modules,
            "module_label": module_label,
            "csv": self.csv_var.get().strip(),
            "name": name,
            "paths": paths,
            "ip": self.ip_var.get().strip(),
            "serial": self.serial_var.get().strip(),
            "remote_dir": self.remote_dir_var.get().strip(),
            "run_acquisition": self.run_acquisition_var.get(),
        }

    def _delete_remote_files_worker(self, settings):
        writer = QueueWriter(self.output_queue)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                self._execute_remote_delete(settings)
            self.output_queue.put(("delete_done_message", "Remote .info and .dak files deleted\n"))
        except Exception as exc:
            self.output_queue.put(("error", f"\nERROR: {exc}\n"))
        finally:
            self.output_queue.put(("delete_done", ""))

    def _execute_remote_delete(self, settings):
        serial = settings["serial"] or "SL1IPB"
        remote_data_dir = f"{settings['remote_dir'].rstrip('/')}/{serial}" if settings["remote_dir"] else ""
        target_dirs = [REMOTE_DELETE_DIR, remote_data_dir]
        target_dirs = [target_dir for index, target_dir in enumerate(target_dirs) if target_dir and target_dir not in target_dirs[:index]]

        print("Target paths:")
        for target_dir in target_dirs:
            print(f"  {target_dir}")
        print("Commands:")
        print("  cd <first existing target path>")
        print("  rm -rf -- *.info *.dak")
        print("-" * 72)
        daq = EpicaDaq(
            ip_ek26=settings["ip"],
            sn_ek26=settings["serial"],
            remote_dir=settings["remote_dir"],
            local_dir=settings["paths"]["base_path"] or ".",
            data_dir=settings["paths"]["data_path"] or "data",
            csv_dir=settings["paths"]["csv_path"] or "csv_setup",
            create_data_dir=False,
        )
        daq.delete_remote_acquisition_files(target_dirs=target_dirs)

    def _configure_frontend_worker(self, settings, signature):
        writer = QueueWriter(self.output_queue)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                self._execute_frontend_configuration(settings)
            self.output_queue.put(("configured", signature))
        except Exception as exc:
            self.output_queue.put(("error", f"\nERROR: {exc}\n"))
        finally:
            self.output_queue.put(("config_done", ""))

    def _execute_frontend_configuration(self, settings):
        fs = settings["fs"]
        fsr = settings["fsr"]
        conf = settings["conf"]
        modules = settings["modules"]
        if not settings["ip"]:
            raise ValueError("Insert EK26 IP before configuring the front-end")
        if not settings["remote_dir"]:
            raise ValueError("Insert remote dir before configuring the front-end")

        cfg = self._build_cfg_string(settings)
        module_codes = ", ".join(modules) if modules else "none"
        print(f"Module:               {settings['module_label']} ({module_codes})")
        print(f"Sampling:             {fs}")
        print(f"Full-scale range:     {fsr}")
        print(f"Configuration:        {conf}")
        print(f"Command string:       {cfg}")
        print("-" * 72)

        daq = EpicaDaq(
            ip_ek26=settings["ip"],
            sn_ek26=settings["serial"],
            remote_dir=settings["remote_dir"],
            local_dir=settings["paths"]["base_path"] or ".",
            data_dir=settings["paths"]["data_path"] or "data",
            csv_dir=settings["paths"]["csv_path"] or "csv_setup",
            create_data_dir=False,
        )
        daq.configure_frontend(cfg_str=cfg)

    def _run_worker(self, settings):
        writer = QueueWriter(self.output_queue)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                figures = self._execute_pipeline(settings)
            if figures:
                self.output_queue.put(("plots", figures))
            self.output_queue.put(("done", "Run completed\n"))
        except Exception as exc:
            self.output_queue.put(("error", f"\nERROR: {exc}\n"))
            self.output_queue.put(("done", "Run failed\n"))

    def _execute_pipeline(self, settings):
        fs = settings["fs"]
        fsr = settings["fsr"]
        conf = settings["conf"]
        acq = settings["acq"]
        modules = settings["modules"]

        paths = settings["paths"]
        if not paths["base_path"]:
            raise ValueError("Select a base save path before running")
        csv_name = self._prepare_csv_file(settings["csv"], paths["csv_path"])
        cfg = self._build_cfg_string(settings)
        name = settings["name"]

        print(f"Date:                 {self.today}")
        print(f"Acquisition:          {acq}")
        module_codes = ", ".join(modules) if modules else "none"
        print(f"Module:               {settings['module_label']} ({module_codes})")
        print(f"Sampling:             {fs}")
        print(f"Full-scale range:     {fsr}")
        print(f"Configuration:        {conf}")
        print(f"CSV file:             {csv_name}")
        print(f"Base path:            {paths['base_path']}")
        print(f"Data path:            {paths['data_path']}")
        print(f"Plot path:            {paths['plot_path']}")
        print(f"Command string:       {cfg}")
        print("-" * 72)

        daq = EpicaDaq(
            ip_ek26=settings["ip"],
            sn_ek26=settings["serial"],
            remote_dir=settings["remote_dir"],
            local_dir=paths["base_path"],
            data_dir=paths["data_path"],
            csv_dir=paths["csv_path"],
        )
        if settings["run_acquisition"]:
            acq_code = daq.connect_and_acquire(waveform_file_name=csv_name, cfg_str=cfg)
            acq_for_plot = acq_code
        else:
            print("Remote acquisition skipped. Plotting selected local acquisition.")
            acq_for_plot = acq

        if not modules:
            print("Module selection is None. Plot generation and image saving skipped.")
            return []

        dma = DmaAcquisition(plot_dir=paths["plot_path"], data_dir=paths["data_path"])
        figures = dma.plot(acq_n=acq_for_plot, target_modules=modules, name=name, show=False)
        if not figures:
            raise RuntimeError("No plot was generated for the selected module(s)")
        print(f"Generated {len(figures)} plot figure(s)")
        return figures

    def _prepare_csv_file(self, csv_value, csv_path):
        if not csv_value:
            raise ValueError("Select or import a CSV setup file")

        source = Path(csv_value)
        csv_dir = Path(csv_path)
        if source.is_absolute():
            if not source.exists():
                raise FileNotFoundError(f"CSV file not found: {source}")
            destination = csv_dir / source.name
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
                print(f"Imported CSV: {source} -> {destination}")
            return destination.name

        candidate = csv_dir / csv_value
        if not candidate.exists():
            raise FileNotFoundError(f"CSV file not found in {csv_path}: {csv_value}")
        return candidate.name

    def _drain_output_queue(self):
        try:
            while True:
                kind, payload = self.output_queue.get_nowait()
                if kind == "message":
                    self._write_message(payload)
                elif kind == "error":
                    self._write_message(payload, "error")
                    messagebox.showerror("noise_acq", payload.strip())
                elif kind == "plots":
                    self._open_plots(payload)
                elif kind == "configured":
                    self.frontend_config_signature = payload
                    self._write_message("Front-end configured.\n", "ok")
                elif kind == "config_done":
                    self._set_configuring(False)
                elif kind == "delete_done_message":
                    self._write_message(payload, "ok")
                elif kind == "delete_done":
                    self._set_deleting(False)
                elif kind == "done":
                    tag = "ok" if "completed" in payload else "error"
                    self._write_message(payload, tag)
                    self._set_running(False)
        except queue.Empty:
            pass
        self.after(80, self._drain_output_queue)

    def _open_plots(self, figures):
        if self.plot_window and self.plot_window.winfo_exists():
            self.plot_window.destroy()
        self.plot_window = SpiderPlotWindow(self, figures)
        self.plot_window.focus()


if __name__ == "__main__":
    app = EPCIAAcquisition()
    app.mainloop()
