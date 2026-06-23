# pip install matplotlib

"""
Waveform Editor

Desktop application for creating and editing four synchronized waveforms
sharing the same X axis, with real-time PWL/CSV preview.
Compatible with Python 3.8+.
"""

import csv
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

class WaveformEditor(tk.Tk):
    """Main editor window."""

    DEFAULT_X_MAX = 10.0
    DEFAULT_Y1_MAX = 255.5
    DEFAULT_Y2_MAX = 255.5
    DEFAULT_Y3_MAX = 1.2
    DEFAULT_Y4_MAX = 1.2
    DEFAULT_X_UNIT = "ms"
    X_UNITS = ("us", "ms", "s")
    DEFAULT_NUM_STEPS = 100
    DEFAULT_INTRINSIC_DELAY_US = 62
    POINT_PICK_RADIUS_PX = 18

    def __init__(self):
        super().__init__()

        self.title("EPICA Waveform Editor")
        self.minsize(1400, 950)

        # Every point shares the same X across all four plots.
        self.points = []
        self.x_max = self.DEFAULT_X_MAX
        self.y1_max = self.DEFAULT_Y1_MAX
        self.y2_max = self.DEFAULT_Y2_MAX
        self.y3_max = self.DEFAULT_Y3_MAX
        self.y4_max = self.DEFAULT_Y4_MAX
        self.x_unit = self.DEFAULT_X_UNIT
        self.num_steps = self.DEFAULT_NUM_STEPS
        self.intrinsic_delay_us = self.DEFAULT_INTRINSIC_DELAY_US

        self._syncing = False
        self._drag_index = None
        self._drag_axis = None
        self._cell_editor = None
        self._cell_editor_data = None
        self.dark_mode = True

        self._setup_style()
        self._build_ui()
        self._connect_plot_events()
        self._center_window(1500, 1000)
        self._refresh_all()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            style.theme_use("alt")

        if self.dark_mode:
            bg_main       = "#1e1e1e"
            bg_panel      = "#2d2d2d"
            bg_bottom     = "#252525"
            fg_label      = "#e0e0e0"
            fg_panel_title = "#ffffff"
            tree_bg       = "#2d2d2d"
            tree_fg       = "#e0e0e0"
            tree_sel_bg   = "#3a5a8a"
            tree_sel_fg   = "#ffffff"
            tree_head_bg  = "#3a3a3a"
            tree_head_fg  = "#d0d0d0"
            entry_bg      = "#3a3a3a"
            entry_fg      = "#e0e0e0"
            btn_bg        = "#3a3a3a"
            btn_fg        = "#e0e0e0"
            combo_bg      = "#3a3a3a"
            combo_fg      = "#e0e0e0"
            check_bg      = "#252525"
            check_fg      = "#e0e0e0"
        else:
            bg_main       = "#f4f6f8"
            bg_panel      = "#ffffff"
            bg_bottom     = "#e8edf3"
            fg_label      = "#243040"
            fg_panel_title = "#243040"
            tree_bg       = "#ffffff"
            tree_fg       = "#243040"
            tree_sel_bg   = "#2563eb"
            tree_sel_fg   = "#ffffff"
            tree_head_bg  = "#e8edf3"
            tree_head_fg  = "#243040"
            entry_bg      = "#ffffff"
            entry_fg      = "#243040"
            btn_bg        = "#e8edf3"
            btn_fg        = "#243040"
            combo_bg      = "#ffffff"
            combo_fg      = "#243040"
            check_bg      = "#e8edf3"
            check_fg      = "#243040"

        # Store colors for use in plot drawing and cell editor
        self._colors = dict(
            bg_main=bg_main, bg_panel=bg_panel, bg_bottom=bg_bottom,
            fg_label=fg_label, tree_bg=tree_bg, tree_fg=tree_fg,
            entry_bg=entry_bg, entry_fg=entry_fg,
        )

        style.configure("TFrame", background=bg_main)
        style.configure("Panel.TFrame", background=bg_panel)
        style.configure("Bottom.TFrame", background=bg_bottom)
        style.configure("TLabel", background=bg_bottom, foreground=fg_label)
        style.configure("PanelTitle.TLabel", background=bg_panel, foreground=fg_panel_title, font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=(14, 7), font=("Segoe UI", 9, "bold"),
                        background=btn_bg, foreground=btn_fg)
        style.map("TButton",
                  background=[("active", tree_sel_bg)],
                  foreground=[("active", tree_sel_fg)])
        style.configure("TEntry", padding=(6, 5),
                        fieldbackground=entry_bg, foreground=entry_fg,
                        insertcolor=entry_fg)
        style.configure("TCombobox", fieldbackground=combo_bg, foreground=combo_fg,
                        background=combo_bg, selectbackground=tree_sel_bg,
                        selectforeground=tree_sel_fg)
        style.map("TCombobox",
                  fieldbackground=[("readonly", combo_bg)],
                  foreground=[("readonly", combo_fg)])
        style.configure("TCheckbutton", background=check_bg, foreground=check_fg)
        style.map("TCheckbutton", background=[("active", check_bg)])

        # Treeview full dark/light theming
        style.configure("Treeview",
                        rowheight=28, font=("Segoe UI", 10),
                        background=tree_bg, foreground=tree_fg,
                        fieldbackground=tree_bg)
        style.map("Treeview",
                  background=[("selected", tree_sel_bg)],
                  foreground=[("selected", tree_sel_fg)])
        style.configure("Treeview.Heading",
                        font=("Segoe UI", 10, "bold"),
                        background=tree_head_bg, foreground=tree_head_fg,
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[("active", tree_sel_bg)],
                  foreground=[("active", tree_sel_fg)])

    def _build_ui(self):
        bg_color = "#1e1e1e" if self.dark_mode else "#f4f6f8"
        self.configure(background=bg_color)

        main = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 8))

        left_panel = ttk.Frame(main, style="Panel.TFrame")
        right_panel = ttk.Frame(main, style="Panel.TFrame")
        main.add(left_panel, weight=3)
        main.add(right_panel, weight=1)

        self._build_plot_panel(left_panel)
        self._build_table_panel(right_panel)

    def _build_plot_panel(self, parent):
        ttk.Label(parent, text="Plots", style="PanelTitle.TLabel").pack(anchor=tk.W, padx=12, pady=(10, 0))

        fig_bg = "#1e1e1e" if self.dark_mode else "#ffffff"
        self.figure = Figure(figsize=(5, 10), dpi=100, facecolor=fig_bg)
        self.ax1 = self.figure.add_subplot(411)
        self.ax2 = self.figure.add_subplot(412, sharex=self.ax1)
        self.ax3 = self.figure.add_subplot(413, sharex=self.ax1)
        self.ax4 = self.figure.add_subplot(414, sharex=self.ax1)
        self.figure.subplots_adjust(left=0.12, right=0.96, top=0.96, bottom=0.06, hspace=0.72)

        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.configure(background=fig_bg, highlightthickness=0)
        canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _build_table_panel(self, parent):
        # Configure parent: left column for tables, right column for controls
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=0)
        
        # Table container (left column)
        tables_container = ttk.Frame(parent, style="Panel.TFrame")
        tables_container.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        tables_container.rowconfigure(0, weight=0)
        tables_container.rowconfigure(1, weight=1)
        tables_container.rowconfigure(2, weight=0)
        tables_container.rowconfigure(3, weight=1)
        tables_container.columnconfigure(0, weight=1)

        # --- Table 1: editable control points ---
        tables_container.rowconfigure(1, weight=1)
        tables_container.rowconfigure(3, weight=1)
        tables_container.rowconfigure(5, weight=1)

        ttk.Label(tables_container, text="Control Points", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        control_frame = ttk.Frame(tables_container, style="Panel.TFrame")
        control_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        control_frame.rowconfigure(0, weight=1)
        control_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(control_frame, columns=("x", "y3", "y4", "y1", "y2", "dt"), show="headings", selectmode="browse")
        for column, title in (("x", self._x_heading()), ("y3", "Polarity"), ("y4", "Load"), ("y1", "Preregulator"), ("y2", "PWM"), ("dt", self._dt_heading())):
            self.tree.heading(column, text=title)
            self.tree.column(column, anchor=tk.CENTER, stretch=True, width=75)

        control_scroll = ttk.Scrollbar(control_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=control_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        control_scroll.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self._start_cell_edit)
        self.tree.bind("<Button-1>", self._cancel_cell_edit_if_click_outside, add="+")

        # --- Table 2: PWL preview (sparse control points, same as .pwl file) ---
        ttk.Label(tables_container, text="PWL Preview", style="PanelTitle.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 6))
        pwl_prev_frame = ttk.Frame(tables_container, style="Panel.TFrame")
        pwl_prev_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        pwl_prev_frame.rowconfigure(0, weight=1)
        pwl_prev_frame.columnconfigure(0, weight=1)

        self.pwl_tree = ttk.Treeview(pwl_prev_frame, columns=("x", "y3", "y4", "y1", "y2"), show="headings", selectmode="browse")
        for column, title in (("x", self._x_heading()), ("y3", "Polarity"), ("y4", "Load"), ("y1", "Preregulator"), ("y2", "PWM")):
            self.pwl_tree.heading(column, text=title)
            self.pwl_tree.column(column, anchor=tk.CENTER, stretch=True, width=80)

        pwl_prev_scroll = ttk.Scrollbar(pwl_prev_frame, orient=tk.VERTICAL, command=self.pwl_tree.yview)
        self.pwl_tree.configure(yscrollcommand=pwl_prev_scroll.set)
        self.pwl_tree.grid(row=0, column=0, sticky="nsew")
        pwl_prev_scroll.grid(row=0, column=1, sticky="ns")

        # --- Table 3: CSV preview (interpolated samples) ---
        ttk.Label(tables_container, text="CSV Preview", style="PanelTitle.TLabel").grid(row=4, column=0, sticky="w", pady=(0, 6))
        csv_frame = ttk.Frame(tables_container, style="Panel.TFrame")
        csv_frame.grid(row=5, column=0, sticky="nsew")
        csv_frame.rowconfigure(0, weight=1)
        csv_frame.columnconfigure(0, weight=1)

        self.csv_tree = ttk.Treeview(csv_frame, columns=("y3", "y4", "y1", "y2", "dt"), show="headings", selectmode="browse")
        for column, title in (("y3", "Polarity"), ("y4", "Load"), ("y1", "Preregulator"), ("y2", "PWM"), ("dt", "dt (us)")):
            self.csv_tree.heading(column, text=title)
            self.csv_tree.column(column, anchor=tk.CENTER, stretch=True, width=80)

        csv_scroll = ttk.Scrollbar(csv_frame, orient=tk.VERTICAL, command=self.csv_tree.yview)
        self.csv_tree.configure(yscrollcommand=csv_scroll.set)
        self.csv_tree.grid(row=0, column=0, sticky="nsew")
        csv_scroll.grid(row=0, column=1, sticky="ns")
        
        # Build vertical control bar on the right side
        self._build_vertical_control_bar(parent)

    def _build_vertical_control_bar(self, parent):
        controls = ttk.Frame(parent, style="Panel.TFrame")
        controls.grid(row=0, column=1, sticky="ns", padx=(5, 10), pady=10)
        controls.columnconfigure(0, weight=1)

        # X max control
        ttk.Label(controls, text="X max:", style="PanelTitle.TLabel").pack(fill=tk.X, pady=(0, 2))
        self.x_max_var = tk.StringVar(value=self._format_number(self.DEFAULT_X_MAX))
        self.x_max_entry = ttk.Entry(controls, textvariable=self.x_max_var, width=10)
        self.x_max_entry.pack(fill=tk.X, padx=2, pady=(0, 8))

        # X unit control
        ttk.Label(controls, text="X unit:", style="PanelTitle.TLabel").pack(fill=tk.X, pady=(0, 2))
        self.x_unit_var = tk.StringVar(value=self.DEFAULT_X_UNIT)
        self.x_unit_combo = ttk.Combobox(controls, textvariable=self.x_unit_var, values=self.X_UNITS, state="readonly", width=8)
        self.x_unit_combo.pack(fill=tk.X, padx=2, pady=(0, 8))

        # Num steps control
        self.num_steps_label = ttk.Label(controls, text=self._num_steps_label_text(), style="PanelTitle.TLabel")
        self.num_steps_label.pack(fill=tk.X, pady=(0, 2))
        self.num_steps_var = tk.StringVar(value=str(self.DEFAULT_NUM_STEPS))
        self.num_steps_entry = ttk.Entry(controls, textvariable=self.num_steps_var, width=10)
        self.num_steps_entry.pack(fill=tk.X, padx=2, pady=(0, 8))

        # Intrinsic delay control
        ttk.Label(controls, text="Intrinsic delay (µs):", style="PanelTitle.TLabel").pack(fill=tk.X, pady=(0, 2))
        self.intrinsic_delay_var = tk.StringVar(value=str(self.DEFAULT_INTRINSIC_DELAY_US))
        self.intrinsic_delay_entry = ttk.Entry(controls, textvariable=self.intrinsic_delay_var, width=10)
        self.intrinsic_delay_entry.pack(fill=tk.X, padx=2, pady=(0, 8))

        # Theme toggle
        self.theme_var = tk.BooleanVar(value=self.dark_mode)
        ttk.Checkbutton(controls, text="Dark Theme", variable=self.theme_var, command=self._toggle_theme).pack(fill=tk.X, padx=2, pady=(0, 8))

        # Separator
        ttk.Separator(controls, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        # Buttons
        ttk.Button(controls, text="RESET", command=self._reset).pack(fill=tk.X, padx=2, pady=(0, 4))
        ttk.Button(controls, text="EXPORT CSV", command=self._export_csv).pack(fill=tk.X, padx=2, pady=(0, 4))
        ttk.Button(controls, text="IMPORT PWL", command=self._import_pwl).pack(fill=tk.X, padx=2)

        # Bind entry events
        self.x_max_entry.bind("<Return>", self._apply_x_limits)
        self.x_max_entry.bind("<Tab>", self._apply_x_limits)
        self.x_max_entry.bind("<FocusOut>", self._apply_x_limits)

        self.num_steps_entry.bind("<Return>", self._apply_num_steps)
        self.num_steps_entry.bind("<Tab>", self._apply_num_steps)
        self.num_steps_entry.bind("<FocusOut>", self._apply_num_steps)
        self.x_unit_combo.bind("<<ComboboxSelected>>", self._apply_x_unit)

        self.intrinsic_delay_entry.bind("<Return>", self._apply_intrinsic_delay)
        self.intrinsic_delay_entry.bind("<Tab>", self._apply_intrinsic_delay)
        self.intrinsic_delay_entry.bind("<FocusOut>", self._apply_intrinsic_delay)

    def _build_bottom_bar_in_panel(self, parent):
        bottom = ttk.Frame(parent, style="Bottom.TFrame", padding=(10, 8))
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(10, 0))

        ttk.Label(bottom, text="X max:").pack(side=tk.LEFT, padx=(0, 4))
        self.x_max_var = tk.StringVar(value=self._format_number(self.DEFAULT_X_MAX))
        self.x_max_entry = ttk.Entry(bottom, textvariable=self.x_max_var, width=7)
        self.x_max_entry.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(bottom, text="X unit:").pack(side=tk.LEFT, padx=(0, 4))
        self.x_unit_var = tk.StringVar(value=self.DEFAULT_X_UNIT)
        self.x_unit_combo = ttk.Combobox(bottom, textvariable=self.x_unit_var, values=self.X_UNITS, width=4, state="readonly")
        self.x_unit_combo.pack(side=tk.LEFT, padx=(0, 8))

        self.num_steps_label = ttk.Label(bottom, text=self._num_steps_label_text())
        self.num_steps_label.pack(side=tk.LEFT, padx=(0, 4))
        self.num_steps_var = tk.StringVar(value=str(self.DEFAULT_NUM_STEPS))
        self.num_steps_entry = ttk.Entry(bottom, textvariable=self.num_steps_var, width=6)
        self.num_steps_entry.pack(side=tk.LEFT, padx=(0, 8))

        self.x_max_entry.bind("<Return>", self._apply_x_limits)
        self.x_max_entry.bind("<Tab>", self._apply_x_limits)
        self.x_max_entry.bind("<FocusOut>", self._apply_x_limits)

        self.num_steps_entry.bind("<Return>", self._apply_num_steps)
        self.num_steps_entry.bind("<Tab>", self._apply_num_steps)
        self.num_steps_entry.bind("<FocusOut>", self._apply_num_steps)
        self.x_unit_combo.bind("<<ComboboxSelected>>", self._apply_x_unit)

        self.theme_var = tk.BooleanVar(value=self.dark_mode)
        ttk.Checkbutton(bottom, text="Dark Theme", variable=self.theme_var, command=self._toggle_theme).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(bottom, text="RESET", command=self._reset).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bottom, text="EXPORT CSV", command=self._export_csv).pack(side=tk.LEFT)

    def _build_bottom_bar(self):
        bottom = ttk.Frame(self, style="Bottom.TFrame", padding=(12, 10))
        bottom.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Label(bottom, text="X max:").pack(side=tk.LEFT, padx=(0, 6))
        self.x_max_var = tk.StringVar(value=self._format_number(self.DEFAULT_X_MAX))
        self.x_max_entry = ttk.Entry(bottom, textvariable=self.x_max_var, width=8)
        self.x_max_entry.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(bottom, text="X unit:").pack(side=tk.LEFT, padx=(0, 6))
        self.x_unit_var = tk.StringVar(value=self.DEFAULT_X_UNIT)
        self.x_unit_combo = ttk.Combobox(bottom, textvariable=self.x_unit_var, values=self.X_UNITS, width=5, state="readonly")
        self.x_unit_combo.pack(side=tk.LEFT, padx=(0, 12))

        self.num_steps_label = ttk.Label(bottom, text=self._num_steps_label_text())
        self.num_steps_label.pack(side=tk.LEFT, padx=(0, 6))
        self.num_steps_var = tk.StringVar(value=str(self.DEFAULT_NUM_STEPS))
        self.num_steps_entry = ttk.Entry(bottom, textvariable=self.num_steps_var, width=8)
        self.num_steps_entry.pack(side=tk.LEFT, padx=(0, 12))

        self.x_max_entry.bind("<Return>", self._apply_x_limits)
        self.x_max_entry.bind("<Tab>", self._apply_x_limits)
        self.x_max_entry.bind("<FocusOut>", self._apply_x_limits)

        self.num_steps_entry.bind("<Return>", self._apply_num_steps)
        self.num_steps_entry.bind("<Tab>", self._apply_num_steps)
        self.num_steps_entry.bind("<FocusOut>", self._apply_num_steps)
        self.x_unit_combo.bind("<<ComboboxSelected>>", self._apply_x_unit)

        self.theme_var = tk.BooleanVar(value=self.dark_mode)
        ttk.Checkbutton(bottom, text="Dark Theme", variable=self.theme_var, command=self._toggle_theme).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(bottom, text="RESET", command=self._reset).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(bottom, text="EXPORT CSV", command=self._export_csv).pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # Eventi matplotlib
    # ------------------------------------------------------------------
    def _connect_plot_events(self):
        self.canvas.mpl_connect("button_press_event", self._on_plot_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_plot_motion)
        self.canvas.mpl_connect("button_release_event", self._on_plot_release)

    def _on_plot_press(self, event):
        axis_name = self._axis_name(event.inaxes)
        if axis_name is None or event.xdata is None or event.ydata is None:
            return

        if event.xdata < 0 or event.ydata < 0:
            return

        if event.button == 3:
            self._add_point(axis_name, event.xdata, event.ydata)
        elif event.button == 1 and self.points:
            self._drag_index = self._nearest_point_index(event, axis_name)
            self._drag_axis = axis_name

    def _on_plot_motion(self, event):
        axis_name = self._axis_name(event.inaxes)
        if self._drag_index is None or axis_name != self._drag_axis:
            return
        if event.xdata is None or event.ydata is None:
            return

        x = min(max(event.xdata, 0.0), self.x_max)
        y = self._clamp_y(axis_name, event.ydata)

        point = self.points[self._drag_index]
        point["x"] = x
        point[axis_name] = y
        self._sort_points()
        self._drag_index = self._nearest_data_index(x)
        self._refresh_all()

    def _on_plot_release(self, _event):
        self._drag_index = None
        self._drag_axis = None

    def _axis_name(self, axes):
        if axes is self.ax1:
            return "y1"
        if axes is self.ax2:
            return "y2"
        if axes is self.ax3:
            return "y3"
        if axes is self.ax4:
            return "y4"
        return None

    def _nearest_point_index(self, event, axis_name):
        """Returns the index of the point closest to the cursor in pixels."""
        axes = {"y1": self.ax1, "y2": self.ax2, "y3": self.ax3, "y4": self.ax4}[axis_name]
        cursor = (event.x, event.y)
        best_index = None
        best_distance = None

        for index, point in enumerate(self.points):
            px, py = axes.transData.transform((point["x"], point[axis_name]))
            distance = math.hypot(px - cursor[0], py - cursor[1])
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = index

        if best_distance is not None and best_distance <= self.POINT_PICK_RADIUS_PX:
            return best_index
        return best_index

    def _nearest_data_index(self, x_value):
        if not self.points:
            return None
        return min(range(len(self.points)), key=lambda index: abs(self.points[index]["x"] - x_value))

    # ------------------------------------------------------------------
    # State, plots and tables synchronization
    # ------------------------------------------------------------------
    def _add_point(self, axis_name, x, y):
        x = min(max(x, 0.0), self.x_max)
        y = self._clamp_y(axis_name, y)
        
        # Determine which other axes to interpolate
        other_axes = [a for a in ["y1", "y2", "y3", "y4"] if a != axis_name]

        point = {"x": x, axis_name: y}
        for other_axis in other_axes:
            point[other_axis] = self._interpolate_control_value(other_axis, x)
        
        self.points.append(point)
        self._sort_points()
        self._refresh_all()

    def _sort_points(self):
        self.points.sort(key=lambda point: point["x"])

    def _refresh_all(self):
        if self._syncing:
            return

        self._syncing = True
        try:
            self._draw_plots()
            self._refresh_tables()
        finally:
            self._syncing = False

    def _draw_plots(self):
        self._draw_single_plot(self.ax1, "y1", "Preregulator", self.y1_max, "#2563eb")
        self._draw_single_plot(self.ax2, "y2", "PWM", self.y2_max, "#7c3aed")
        self._draw_single_plot(self.ax3, "y3", "Polarity", self.y3_max, "#059669")
        self._draw_single_plot(self.ax4, "y4", "Load", self.y4_max, "#dc2626")
        self.canvas.draw_idle()

    def _draw_single_plot(self, axes, axis_name, title, y_max, line_color):
        if self.dark_mode:
            ax_bg        = "#252525"
            grid_color   = "#404040"
            text_color   = "#d0d0d0"
            annot_fc     = "#2d2d2d"
            annot_ec     = "#555555"
            annot_color  = "#e0e0e0"
            scatter_edge = "#1e1e1e"
            spine_color  = "#505050"
        else:
            ax_bg        = "#fbfcfe"
            grid_color   = "#d6dde6"
            text_color   = "#1f2937"
            annot_fc     = "#ffffff"
            annot_ec     = "#cbd5e1"
            annot_color  = "#1f2937"
            scatter_edge = "#ffffff"
            spine_color  = "#d6dde6"

        axes.clear()
        axes.set_facecolor(ax_bg)
        axes.set_title(title, fontsize=12, pad=6, color=text_color)
        # Only show x-label on the bottom subplot; the others share the x-axis
        if axes is self.ax4:
            axes.set_xlabel(self._x_heading(), color=text_color, labelpad=4)
        else:
            axes.set_xlabel("", color=text_color)
            axes.tick_params(labelbottom=False)
        axes.set_ylabel(axis_name.upper(), color=text_color)
        axes.tick_params(colors=text_color, which="both")
        for spine in axes.spines.values():
            spine.set_edgecolor(spine_color)
        axes.set_xlim(0, self.x_max)
        axes.set_ylim(0, y_max)
        axes.grid(True, color=grid_color, linewidth=0.8, alpha=0.75)

        if not self.points:
            return

        xs = [point["x"] for point in self.points]
        ys = [point[axis_name] for point in self.points]

        # Use step plot for digital signals (y3, y4), regular plot for analog signals
        if axis_name in ("y3", "y4"):
            axes.step(xs, ys, where="post", color=line_color, linewidth=2.0, zorder=2)
        else:
            axes.plot(xs, ys, color=line_color, linewidth=2.0, zorder=2)

        axes.scatter(xs, ys, s=54, color="#f97316", edgecolors=scatter_edge, linewidths=1.4, zorder=3)

        for x, y in zip(xs, ys):
            label = f"({self._format_number(x)}, {self._format_number(y)})"
            axes.annotate(
                label,
                (x, y),
                xytext=(7, 7),
                textcoords="offset points",
                fontsize=8,
                color=annot_color,
                bbox={"boxstyle": "round,pad=0.25", "fc": annot_fc, "ec": annot_ec, "alpha": 0.9},
                zorder=4,
            )

    def _refresh_tables(self):
        self._destroy_cell_editor()
        self.tree.heading("x", text=self._x_heading())
        self.tree.heading("dt", text=self._dt_heading())
        self.pwl_tree.heading("x", text=self._x_heading())

        # --- Table 1: editable control points ---
        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, point in enumerate(self.points):
            dt = self._control_dt(index)
            self.tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    self._format_number(point["x"]),
                    self._format_number(point["y3"]),
                    self._format_number(point["y4"]),
                    self._format_number(point["y1"]),
                    self._format_number(point["y2"]),
                    self._format_number(dt),
                ),
            )

        # --- Table 2: PWL preview (sparse control points, mirrors .pwl file) ---
        for item in self.pwl_tree.get_children():
            self.pwl_tree.delete(item)

        for index, (x, y3, y4, y1, y2) in enumerate(self._build_pwl_rows()):
            self.pwl_tree.insert("", tk.END, iid=f"pwl-{index}", values=(
                self._format_number(x), y3, y4, y1, y2))

        # --- Table 3: CSV preview (interpolated samples) ---
        for item in self.csv_tree.get_children():
            self.csv_tree.delete(item)

        for index, (y3, y4, y1, y2, dt) in enumerate(self._build_csv_export_rows()):
            self.csv_tree.insert("", tk.END, iid=f"csv-{index}", values=(y3, y4, y1, y2, dt))

    # ------------------------------------------------------------------
    # Inline PWL table editing
    # ------------------------------------------------------------------
    def _start_cell_edit(self, event):
        if self._syncing:
            return

        if self.tree.identify("region", event.x, event.y) != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        column_map = {"#1": "x", "#2": "y3", "#3": "y4", "#4": "y1", "#5": "y2", "#6": "dt"}
        if not item_id or column_id not in column_map:
            return

        bbox = self.tree.bbox(item_id, column_id)
        if not bbox:
            return

        self._destroy_cell_editor()

        x, y, width, height = bbox
        column_name = column_map[column_id]
        current_value = self.tree.set(item_id, column_name)

        editor = tk.Entry(
            self.tree,
            borderwidth=1,
            relief=tk.SOLID,
            highlightthickness=1,
            highlightbackground="#94a3b8" if not self.dark_mode else "#555555",
            highlightcolor="#2563eb" if not self.dark_mode else "#3a8fd8",
            font=("Segoe UI", 10),
            justify=tk.CENTER,
            background=self._colors.get("entry_bg", "#ffffff"),
            foreground=self._colors.get("entry_fg", "#243040"),
            insertbackground=self._colors.get("entry_fg", "#243040"),
        )
        editor.insert(0, current_value)
        editor.select_range(0, tk.END)
        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()

        self._cell_editor = editor
        self._cell_editor_data = (item_id, column_name)

        editor.bind("<Return>", self._commit_cell_edit)
        editor.bind("<Tab>", self._commit_cell_edit)
        editor.bind("<Escape>", lambda _event: self._destroy_cell_editor())
        editor.bind("<FocusOut>", self._commit_cell_edit)

    def _commit_cell_edit(self, event=None):
        if self._cell_editor is None or self._cell_editor_data is None:
            return

        item_id, column_name = self._cell_editor_data
        raw_value = self._cell_editor.get().strip().replace(",", ".")
        parsed_value = self._parse_non_negative_number(raw_value)

        if parsed_value is None:
            self._mark_editor_invalid()
            if event is not None and getattr(event, "keysym", "") == "Tab":
                return "break"
            return

        point_index = int(item_id)
        if 0 <= point_index < len(self.points):
            if column_name == "x":
                self.points[point_index]["x"] = min(parsed_value, self.x_max)
            elif column_name in ("y1", "y2", "y3", "y4"):
                self.points[point_index][column_name] = self._clamp_y(column_name, parsed_value)
            elif point_index > 0:
                previous_x = self.points[point_index - 1]["x"]
                self.points[point_index]["x"] = min(previous_x + parsed_value, self.x_max)
            self._sort_points()

        self._destroy_cell_editor()
        self._refresh_all()

        if event is not None and getattr(event, "keysym", "") == "Tab":
            return "break"
        return None

    def _mark_editor_invalid(self):
        if self._cell_editor is not None:
            self._cell_editor.configure(highlightbackground="#dc2626", highlightcolor="#dc2626",
                                        background="#4a1a1a" if self.dark_mode else "#fff0f0")
            self._cell_editor.focus_set()

    def _destroy_cell_editor(self):
        if self._cell_editor is not None:
            self._cell_editor.destroy()
        self._cell_editor = None
        self._cell_editor_data = None

    def _cancel_cell_edit_if_click_outside(self, event):
        if self._cell_editor is None:
            return
        widget_under_pointer = self.winfo_containing(event.x_root, event.y_root)
        if widget_under_pointer is not self._cell_editor:
            self._commit_cell_edit()

    # ------------------------------------------------------------------
    # Global controls
    # ------------------------------------------------------------------
    def _apply_x_limits(self, event=None):
        x_value = self._parse_positive_number(self.x_max_var.get().strip().replace(",", "."))

        if x_value is None:
            self.x_max_var.set(self._format_number(self.x_max))
        else:
            self.x_max = x_value
            self.x_max_var.set(self._format_number(self.x_max))

        for point in self.points:
            point["x"] = min(max(point["x"], 0.0), self.x_max)

        self._sort_points()
        self._refresh_all()
        return "break" if event is not None and getattr(event, "keysym", "") == "Tab" else None

    def _apply_num_steps(self, event=None):
        value = self._parse_positive_integer(self.num_steps_var.get().strip())
        if value is None:
            self.num_steps_var.set(str(self.num_steps))
        else:
            self.num_steps = value
            self.num_steps_var.set(str(self.num_steps))
            self._refresh_all()

        return "break" if event is not None and getattr(event, "keysym", "") == "Tab" else None

    def _apply_intrinsic_delay(self, event=None):
        value = self._parse_non_negative_number(self.intrinsic_delay_var.get().strip().replace(",", "."))
        if value is None:
            self.intrinsic_delay_var.set(str(self.intrinsic_delay_us))
        else:
            self.intrinsic_delay_us = value
            self.intrinsic_delay_var.set(self._format_number(self.intrinsic_delay_us))
            self._refresh_all()
        return "break" if event is not None and getattr(event, "keysym", "") == "Tab" else None

    def _apply_x_unit(self, _event=None):
        selected_unit = self.x_unit_var.get()
        if selected_unit not in self.X_UNITS:
            self.x_unit_var.set(self.x_unit)
            return
        self.x_unit = selected_unit
        self.num_steps_label.configure(text=self._num_steps_label_text())
        self._refresh_all()

    def _toggle_theme(self):
        self.dark_mode = self.theme_var.get()
        self._setup_style()
        # Rebuild UI: destroy all children and rebuild
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()
        self._connect_plot_events()
        self._refresh_all()

    def _reset(self):
        self.points.clear()
        self.x_max = self.DEFAULT_X_MAX
        self.y1_max = self.DEFAULT_Y1_MAX
        self.y2_max = self.DEFAULT_Y2_MAX
        self.y3_max = self.DEFAULT_Y3_MAX
        self.y4_max = self.DEFAULT_Y4_MAX
        self.x_unit = self.DEFAULT_X_UNIT
        self.num_steps = self.DEFAULT_NUM_STEPS
        self.intrinsic_delay_us = self.DEFAULT_INTRINSIC_DELAY_US
        self.x_max_var.set(self._format_number(self.DEFAULT_X_MAX))
        self.x_unit_var.set(self.DEFAULT_X_UNIT)
        self.num_steps_var.set(str(self.DEFAULT_NUM_STEPS))
        self.intrinsic_delay_var.set(str(self.DEFAULT_INTRINSIC_DELAY_US))
        self.num_steps_label.configure(text=self._num_steps_label_text())
        self._refresh_all()

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Export CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return

        import os
        base, _ = os.path.splitext(path)
        pwl_path = base + ".pwl"

        # CSV = interpolated samples
        csv_rows = self._build_csv_export_rows()
        try:
            with open(path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerows(csv_rows)
        except OSError as exc:
            messagebox.showerror("CSV Export Error", f"Cannot save CSV file:\n{exc}")
            return

        # PWL = settings header + sparse control points
        pwl_rows = self._build_pwl_rows()
        try:
            with open(pwl_path, "w", newline="", encoding="utf-8") as pwl_file:
                # Settings header — prefixed with '#' so they are ignored by
                # older parsers that skip comment lines
                pwl_file.write(f"# x_unit={self.x_unit}\n")
                pwl_file.write(f"# x_max={self._format_number(self.x_max)}\n")
                pwl_file.write(f"# num_steps={self.num_steps}\n")
                pwl_file.write(f"# intrinsic_delay_us={self._format_number(self.intrinsic_delay_us)}\n")
                # Data rows: x  y3  y4  y1  y2
                for x, y3, y4, y1, y2 in pwl_rows:
                    pwl_file.write(f"{self._format_number(x)}\t{y3}\t{y4}\t{y1}\t{y2}\n")
        except OSError as exc:
            messagebox.showerror("PWL Export Error", f"Cannot save PWL file:\n{exc}")
            return

        messagebox.showinfo(
            "Export Complete",
            f"Files saved:\n  {path}\n  {pwl_path}",
        )

    # ------------------------------------------------------------------
    # PWL import
    # ------------------------------------------------------------------
    def _import_pwl(self):
        """Import a .pwl file with sparse control points.

        Expected format:
          Optional settings header lines starting with '#':
            # x_unit=ms
            # x_max=10
            # num_steps=100
            # intrinsic_delay_us=62
          Followed by data rows, one per point, tab-separated:
            x  y3  y4  y1  y2
          where x is in the unit specified by x_unit (or the current unit
          if the header is absent).
        Points are loaded directly as control points and plotted.
        The CSV preview is automatically recomputed by interpolation.
        """
        path = filedialog.askopenfilename(
            title="Import PWL",
            filetypes=(("PWL files", "*.pwl"), ("All files", "*.*")),
        )
        if not path:
            return

        new_points = []
        settings = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # Parse settings header lines
                    if line.startswith("#"):
                        content = line[1:].strip()
                        if "=" in content:
                            key, _, value = content.partition("=")
                            settings[key.strip()] = value.strip()
                        continue

                    parts = line.replace(",", ".").split()
                    if len(parts) != 5:
                        messagebox.showerror(
                            "PWL Import Error",
                            f"Line {line_no}: expected 5 values (x y3 y4 y1 y2), found {len(parts)}.\n{line}",
                        )
                        return
                    try:
                        x, y3, y4, y1, y2 = [float(p) for p in parts]
                    except ValueError:
                        messagebox.showerror(
                            "PWL Import Error",
                            f"Line {line_no}: non-numeric value.\n{line}",
                        )
                        return
                    new_points.append({
                        "x":  x,
                        "y1": y1,
                        "y2": y2,
                        "y3": y3,
                        "y4": y4,
                    })
        except OSError as exc:
            messagebox.showerror("PWL Import Error", f"Cannot open file:\n{exc}")
            return

        if not new_points:
            messagebox.showerror("PWL Import Error", "The file is empty.")
            return

        # Restore settings from header (if present)
        if "x_unit" in settings and settings["x_unit"] in self.X_UNITS:
            self.x_unit = settings["x_unit"]
            self.x_unit_var.set(self.x_unit)

        if "x_max" in settings:
            parsed = self._parse_positive_number(settings["x_max"])
            if parsed is not None:
                self.x_max = parsed
                self.x_max_var.set(self._format_number(self.x_max))

        if "num_steps" in settings:
            parsed = self._parse_positive_integer(settings["num_steps"])
            if parsed is not None:
                self.num_steps = parsed
                self.num_steps_var.set(str(self.num_steps))

        if "intrinsic_delay_us" in settings:
            parsed = self._parse_non_negative_number(settings["intrinsic_delay_us"])
            if parsed is not None:
                self.intrinsic_delay_us = parsed
                self.intrinsic_delay_var.set(self._format_number(self.intrinsic_delay_us))

        # Update state
        self.points = new_points
        self._sort_points()

        # If no x_max header was found, adapt to the furthest point
        if "x_max" not in settings:
            max_x = max(p["x"] for p in self.points)
            if max_x > 0:
                self.x_max = max_x
                self.x_max_var.set(self._format_number(self.x_max))

        self.num_steps_label.configure(text=self._num_steps_label_text())
        self._refresh_all()

    # ------------------------------------------------------------------
    # PWL / CSV generation
    # ------------------------------------------------------------------
    def _build_pwl_rows(self):
        """PWL file rows: sparse control points clicked on the plots.

        Format: (x, y3, y4, y1, y2) where x is in the current X unit.
        No interpolation: these are exactly the points in self.points.
        """
        rows = []
        for pt in self.points:
            rows.append((
                pt["x"],
                self._to_int(pt["y3"]),
                self._to_int(pt["y4"]),
                self._to_int(pt["y1"]),
                self._to_int(pt["y2"]),
            ))
        return rows

    def _build_csv_export_rows(self):
        """CSV file rows: samples interpolated between control points.

        self.num_steps is the total number of steps across the entire waveform.
        Steps are distributed proportionally between segments based on their
        relative duration with respect to the total duration.
        The dt of each row is always expressed in µs (integer, min 1),
        regardless of the current X unit.
        The first row always has dt=0 (starting sample).
        The hardware intrinsic delay (self.intrinsic_delay_us) is subtracted
        from each dt so that the total execution time matches the configured
        waveform duration.
        """
        if not self.points:
            return []
        if len(self.points) == 1:
            pt = self.points[0]
            return [(self._to_int(pt["y3"]), self._to_int(pt["y4"]),
                     self._to_int(pt["y1"]), self._to_int(pt["y2"]), 0)]

        total_num_steps = max(1, self.num_steps)

        # Compute duration of each segment (ignore zero-duration segments)
        segments = list(zip(self.points, self.points[1:]))
        durations = [max(0.0, p1["x"] - p0["x"]) for p0, p1 in segments]
        total_duration = sum(durations)

        # Distribute steps proportionally; each segment gets at least 1 step
        if total_duration > 0:
            raw = [total_num_steps * d / total_duration for d in durations]
        else:
            raw = [0.0] * len(segments)

        # Integer rounding that preserves the total sum (Largest Remainder method)
        floors = [int(r) for r in raw]
        remainders = [(raw[i] - floors[i], i) for i in range(len(raw))]
        deficit = total_num_steps - sum(floors)
        for _, i in sorted(remainders, reverse=True)[:deficit]:
            floors[i] += 1
        # Ensure at least 1 step for segments with duration > 0
        steps_per_segment = [
            max(1, s) if durations[i] > 0 else 0
            for i, s in enumerate(floors)
        ]

        # Conversion factor from current X unit to µs
        _to_us = {"us": 1, "ms": 1_000, "s": 1_000_000}.get(self.x_unit, 1)

        rows = []
        for segment_index, ((p0, p1), seg_steps, duration) in enumerate(
            zip(segments, steps_per_segment, durations)
        ):
            # First row: initial sample of the first segment
            if segment_index == 0:
                rows.append((
                    self._to_int(p0["y3"]),
                    self._to_int(p0["y4"]),
                    self._to_int(p0["y1"]),
                    self._to_int(p0["y2"]),
                    0,
                ))

            if duration == 0:
                # Overlapping point: replace the last sample
                if rows:
                    old = rows[-1]
                    rows[-1] = (
                        self._to_int(p1["y3"]),
                        self._to_int(p1["y4"]),
                        self._to_int(p1["y1"]),
                        self._to_int(p1["y2"]),
                        old[4],
                    )
                continue

            # dt in µs = (segment duration in µs / assigned steps) - hardware intrinsic delay
            # This ensures the total execution time matches the configured waveform duration.
            step_dt = max(1, int(round(duration * _to_us / seg_steps - self.intrinsic_delay_us)))

            for step in range(1, seg_steps + 1):
                ratio = step / seg_steps
                y1 = p0["y1"] + (p1["y1"] - p0["y1"]) * ratio
                y2 = p0["y2"] + (p1["y2"] - p0["y2"]) * ratio
                # Digital signals: step function — change only at the last step of the segment
                if step == seg_steps:
                    y3 = p1["y3"]
                    y4 = p1["y4"]
                else:
                    y3 = p0["y3"]
                    y4 = p0["y4"]
                rows.append((
                    self._to_int(y3),
                    self._to_int(y4),
                    self._to_int(y1),
                    self._to_int(y2),
                    step_dt,
                ))

        return rows

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _control_dt(self, index):
        if index <= 0 or index >= len(self.points):
            return 0
        return max(0, self.points[index]["x"] - self.points[index - 1]["x"])

    def _interpolate_control_value(self, axis_name, x_value):
        if not self.points:
            return 0.0

        points = sorted(self.points, key=lambda point: point["x"])
        if x_value <= points[0]["x"]:
            return points[0][axis_name]
        if x_value >= points[-1]["x"]:
            return points[-1][axis_name]

        for p0, p1 in zip(points, points[1:]):
            if p0["x"] <= x_value <= p1["x"]:
                if p1["x"] == p0["x"]:
                    return p1[axis_name]
                # For digital signals (y3, y4), use step function (return first point's value)
                if axis_name in ("y3", "y4"):
                    return p0[axis_name]
                # For analog signals (y1, y2), interpolate
                ratio = (x_value - p0["x"]) / (p1["x"] - p0["x"])
                return p0[axis_name] + (p1[axis_name] - p0[axis_name]) * ratio

        return 0.0

    def _clamp_y(self, axis_name, value):
        if axis_name == "y1":
            y_max = self.y1_max
        elif axis_name == "y2":
            y_max = self.y2_max
        elif axis_name == "y3":
            y_max = self.y3_max
        else:  # y4
            y_max = self.y4_max
        return min(max(value, 0.0), y_max)

    @staticmethod
    def _parse_non_negative_number(value):
        try:
            number = float(value)
        except ValueError:
            return None
        if not math.isfinite(number) or number < 0:
            return None
        return number

    @classmethod
    def _parse_positive_number(cls, value):
        number = cls._parse_non_negative_number(value)
        if number is None or number <= 0:
            return None
        return number

    @staticmethod
    def _parse_positive_integer(value):
        try:
            number = int(value)
        except ValueError:
            return None
        if number <= 0:
            return None
        return number

    @staticmethod
    def _format_number(value):
        return f"{value:.4f}".rstrip("0").rstrip(".")

    @staticmethod
    def _to_int(value):
        return int(round(value))

    def _x_heading(self):
        return f"X ({self.x_unit})"

    def _dt_heading(self):
        return f"dt ({self.x_unit})"

    def _num_steps_label_text(self):
        return "Total steps:"

    def _center_window(self, width, height):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")


if __name__ == "__main__":
    app = WaveformEditor()
    app.mainloop()