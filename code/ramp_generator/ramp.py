"""Tkinter editor and register-word generator for EPICA power-supply ramps.

The public :func:`ramp_generator` function opens the editor and returns the
sample period together with the hexadecimal register-word sequence. See the
README for the complete file format and generation rules.
"""

from __future__ import annotations

import csv
import tkinter as tk
from dataclasses import dataclass, replace
from tkinter import filedialog, messagebox, ttk


TABLE_FIELDS = ("enable", "pol", "load", "pre", "pwm", "pwm4e", "pwm4q", "step", "note")
TABLE_HEADINGS = ("EN", "POL", "LOAD", "PRE", "PWM", "4E", "PWM4Q", "STEP", "NOTE")
TABLE_COLUMN_WIDTHS = (58, 58, 62, 76, 76, 58, 76, 70, 350)
CSV_FILE_TYPES = (("CSV files", "*.csv"), ("All files", "*.*"))
CSV_HEADERS = (TABLE_FIELDS, TABLE_HEADINGS, (*TABLE_HEADINGS[:-1], "NOTA"))

ANALOG_FIELDS = ("pre", "pwm", "pwm4q")
DIGITAL_PLOT_LANES = (
    ("POL", "pol", "#2ca02c"),
    ("EN", "enable", "#ff7f0e"),
    ("4E", "pwm4e", "#8c564b"),
)
DEFAULT_ROW = (1, 0, 0, 0, 0, 0, 0, 1, "")
DEFAULT_SEQUENCE = (
    (1, 1, 0, 0, 0, 0, 0, 0, "start"),
    (1, 1, 0, 0, 0, 0, 0, 1, ""),
    (1, 1, 0, 210, 200, 0, 0, 60, "negative ramp"),
    (1, 1, 0, 0, 0, 0, 0, 60, "return to zero"),
    (1, 1, 0, 0, 0, 0, 0, 4, "zero hold"),
    (1, 0, 0, 0, 0, 0, 0, 1, "polarity change"),
    (1, 0, 0, 210, 200, 0, 0, 60, "positive ramp"),
    (1, 0, 0, 0, 0, 0, 0, 60, "return to zero"),
    (1, 0, 0, 0, 0, 0, 0, 4, "final hold"),
)


@dataclass(frozen=True)
class Step:
    enable: int
    pol: int
    load: int
    pre: int
    pwm: int
    pwm4e: int
    pwm4q: int
    points: int
    note: str


def compute_register(step: Step, decim: int) -> int:
    """Compile the AS20P2 register word for one ramp sample."""
    prereg = step.pwm4q if step.pwm4e else step.pre
    return (
        ((step.pol & 0x1) << 31)
        | ((decim & 0x7) << 28)
        | ((step.load & 0x1) << 27)
        | ((step.pwm4e & 0x1) << 26)
        | ((step.enable & 0x1) << 24)
        | ((prereg & 0xFF) << 16)
        | ((step.pwm & 0xFF) << 8)
    )


def interpolate_int(start: int, stop: int, points: int) -> list[int]:
    """Integer linear interpolation with a guaranteed final point."""
    if points == 1:
        return [start]
    return [
        stop if k == points - 1 else int(start + (stop - start) * k / (points - 1))
        for k in range(points)
    ]


def build_ramp(steps: list[Step], decim: int) -> list[Step]:
    """Create samples with interpolated analog values and destination digital bits."""
    samples: list[Step] = []
    for source, destination in zip(steps, steps[1:]):
        if destination.points <= 0:
            continue
        samples.extend(_build_segment(source, destination))
    if not samples:
        raise ValueError("No valid segment: at least one row after the first must have STEP > 0.")
    return samples


def _build_segment(source: Step, destination: Step) -> list[Step]:
    """Generate one segment while preserving the destination digital fields."""
    interpolated_values = zip(
        *(
            interpolate_int(getattr(source, field), getattr(destination, field), destination.points)
            for field in ANALOG_FIELDS
        )
    )
    return [
        replace(destination, **dict(zip(ANALOG_FIELDS, values)))
        for values in interpolated_values
    ]


def ramp_to_hex_string(samples: list[Step], decim: int) -> str:
    """Convert samples to a ``0xXXXXXXXX, 0xXXXXXXXX, ...`` string."""
    return ", ".join(f"0x{compute_register(sample, decim):08X}" for sample in samples)


def parse_ramp_parameters(dt_value: str, decim_value: str) -> tuple[int, int]:
    """Parse and validate the editor-wide parameters."""
    try:
        dt = int(dt_value)
        decim = int(decim_value)
    except ValueError as exc:
        raise ValueError("dt and decim must be integers.") from exc
    if dt <= 0:
        raise ValueError("dt must be greater than zero.")
    if not 0 <= decim <= 7:
        raise ValueError("decim must be between 0 and 7.")
    return dt, decim


def step_from_table_values(values: tuple[object, ...], row_number: int) -> Step:
    """Convert one table row into a validated ``Step``."""
    try:
        numeric_values = [int(values[index]) for index in range(8)]
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Row {row_number}: the first eight fields must be integers.") from exc

    enable, pol, load, pre, pwm, pwm4e, pwm4q, points = numeric_values
    if any(value not in (0, 1) for value in (enable, pol, load, pwm4e)):
        raise ValueError(f"Row {row_number}: EN, POL, LOAD, and 4E must be 0 or 1.")
    if not all(0 <= value <= 255 for value in (pre, pwm, pwm4q)):
        raise ValueError(f"Row {row_number}: PRE, PWM, and PWM4Q must be between 0 and 255.")
    if points < 0:
        raise ValueError(f"Row {row_number}: STEP cannot be negative.")

    note = str(values[8]).replace("\r", " ").replace("\n", " ")
    return Step(*numeric_values, note)


def read_table_csv(path: str) -> list[tuple[str, ...]]:
    """Read and validate rows from an exported EPICA table CSV file."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as csv_file:
            rows = [tuple(row) for row in csv.reader(csv_file) if any(cell.strip() for cell in row)]
    except (OSError, csv.Error) as exc:
        raise ValueError(f"Unable to read CSV file: {exc}") from exc

    if not rows:
        raise ValueError("The CSV file is empty.")
    if rows[0] not in CSV_HEADERS:
        expected_header = ", ".join(TABLE_FIELDS)
        raise ValueError(f"Invalid CSV header. Expected: {expected_header}.")

    table_rows = rows[1:]
    if len(table_rows) < 2:
        raise ValueError("The CSV file must contain at least two table rows.")
    for row_number, row in enumerate(table_rows, start=1):
        if len(row) != len(TABLE_FIELDS):
            raise ValueError(f"Row {row_number}: expected {len(TABLE_FIELDS)} columns.")
        step_from_table_values(row, row_number)
    return table_rows


def write_table_csv(path: str, rows: list[tuple[str, ...]]) -> None:
    """Write the current editor table in the CSV format accepted by the importer."""
    try:
        with open(path, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(TABLE_FIELDS)
            writer.writerows(rows)
    except (OSError, csv.Error) as exc:
        raise ValueError(f"Unable to write CSV file: {exc}") from exc


class RampGeneratorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("EPICA - Ramp Generator")
        self.geometry("1450x720")
        self.minsize(1100, 560)
        self.dt = tk.StringVar(value="600")
        self.decim = tk.StringVar(value="0")
        self.status = tk.StringVar(value="Edit the sequence, then export it as CSV.")
        self.plot_info = tk.StringVar(value="Ramp preview")
        self._edit_widget: ttk.Entry | None = None
        self._plot_samples: list[Step] = []
        self._plot_dt = 1
        self._plot_refresh_job: str | None = None
        self._result: tuple[int, str] | None = None
        self._build_ui()
        self._add_default_sequence()
        self.after_idle(self.refresh_plot)
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def _build_ui(self) -> None:
        panes = ttk.Panedwindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=8, pady=8)
        editor = ttk.Frame(panes)
        preview = ttk.Frame(panes)
        panes.add(editor, weight=3)
        panes.add(preview, weight=2)

        self._build_editor(editor)
        self._build_preview(preview)
        self.dt.trace_add("write", self._schedule_plot_refresh)
        self.decim.trace_add("write", self._schedule_plot_refresh)
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=6).pack(
            fill="x", side="bottom"
        )

    def _build_editor(self, editor: ttk.Frame) -> None:
        self._build_parameters(editor)
        self._build_table(editor)
        self._build_commands(editor)

    def _build_parameters(self, parent: ttk.Frame) -> None:
        params = ttk.Frame(parent, padding=(2, 2, 2, 4))
        params.pack(fill="x")
        ttk.Label(params, text="dt [µs]").pack(side="left")
        ttk.Entry(params, textvariable=self.dt, width=8).pack(side="left", padx=(5, 18))
        ttk.Label(params, text="decim (0-7)").pack(side="left")
        ttk.Spinbox(params, from_=0, to=7, textvariable=self.decim, width=5).pack(side="left", padx=5)
        ttk.Label(
            params,
            text="POL=0 positive, POL=1 negative | 4E=0 uses PRE, 4E=1 uses PWM4Q",
        ).pack(side="left", padx=20)

    def _build_table(self, parent: ttk.Frame) -> None:
        table_box = ttk.Frame(parent, padding=(2, 4, 2, 4))
        table_box.pack(fill="both", expand=True)
        table_box.rowconfigure(0, weight=1)
        table_box.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(table_box, columns=TABLE_FIELDS, show="headings", selectmode="browse")
        for field, heading, width in zip(TABLE_FIELDS, TABLE_HEADINGS, TABLE_COLUMN_WIDTHS):
            alignment = "w" if field == "note" else "center"
            self.table.heading(field, text=heading)
            self.table.column(field, width=width, minwidth=45, anchor=alignment)
        vertical_scrollbar = ttk.Scrollbar(table_box, orient="vertical", command=self.table.yview)
        horizontal_scrollbar = ttk.Scrollbar(table_box, orient="horizontal", command=self.table.xview)
        self.table.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.table.bind("<Double-1>", self._start_edit)

    def _build_commands(self, parent: ttk.Frame) -> None:
        commands = ttk.Frame(parent, padding=(2, 4))
        commands.pack(fill="x")
        ttk.Button(commands, text="Import CSV", command=self.import_table).pack(side="left")
        ttk.Button(commands, text="Add Row", command=self.add_row).pack(side="left", padx=5)
        ttk.Button(commands, text="Delete Row", command=self.delete_row).pack(side="left", padx=5)
        ttk.Button(commands, text="Move Up", command=lambda: self.move_row(-1)).pack(side="left", padx=5)
        ttk.Button(commands, text="Move Down", command=lambda: self.move_row(1)).pack(side="left", padx=5)
        ttk.Button(commands, text="Clear", command=self.clear_rows).pack(side="left", padx=5)
        ttk.Button(commands, text="Export", command=self.export_sequence).pack(side="right")

    def _build_preview(self, parent: ttk.Frame) -> None:
        plot_box = ttk.LabelFrame(parent, text="Ramp Preview", padding=6)
        plot_box.pack(fill="both", expand=True, padx=(6, 0))
        top_plot = ttk.Frame(plot_box)
        top_plot.pack(fill="x")
        ttk.Label(top_plot, textvariable=self.plot_info).pack(side="left")
        ttk.Button(top_plot, text="Refresh", command=self.refresh_plot).pack(side="right")
        self.plot_canvas = tk.Canvas(plot_box, background="white", highlightthickness=0)
        self.plot_canvas.pack(fill="both", expand=True, pady=(5, 0))
        self.plot_canvas.bind("<Configure>", self._redraw_plot)

    def _redraw_plot(self, _event: tk.Event) -> None:
        self._draw_plot(self.plot_canvas, self._plot_samples, self._plot_dt)

    def _add_default_sequence(self) -> None:
        # Matches the original C# default: negative ramp, zero, positive ramp, zero.
        for row in DEFAULT_SEQUENCE:
            self.table.insert("", "end", values=row)

    def add_row(self) -> None:
        selected = self.table.selection()
        values = self.table.item(selected[0], "values") if selected else DEFAULT_ROW
        item = self.table.insert("", "end", values=values)
        self.table.selection_set(item)
        self.table.focus(item)
        self._schedule_plot_refresh()

    def delete_row(self) -> None:
        for item in self.table.selection():
            self.table.delete(item)
        self._schedule_plot_refresh()

    def move_row(self, direction: int) -> None:
        selected = self.table.selection()
        if not selected:
            return
        item = selected[0]
        index = self.table.index(item)
        new_index = index + direction
        if 0 <= new_index < len(self.table.get_children()):
            self.table.move(item, "", new_index)
            self._schedule_plot_refresh()

    def clear_rows(self) -> None:
        if messagebox.askyesno("Clear Sequence", "Remove all rows from the sequence?"):
            for item in self.table.get_children():
                self.table.delete(item)
            self._schedule_plot_refresh()

    def _start_edit(self, event: tk.Event) -> None:
        if self._edit_widget is not None:
            self._finish_edit()
        row_id = self.table.identify_row(event.y)
        column_id = self.table.identify_column(event.x)
        if not row_id or not column_id:
            return
        column = int(column_id[1:]) - 1
        bbox = self.table.bbox(row_id, column_id)
        if not bbox:
            return
        current = self.table.item(row_id, "values")[column]
        editor = ttk.Entry(self.table)
        editor.insert(0, current)
        editor.select_range(0, "end")
        editor.focus_set()
        editor.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        editor.bind("<Return>", lambda _e: self._finish_edit(row_id, column))
        editor.bind("<Escape>", lambda _e: self._finish_edit())
        editor.bind("<FocusOut>", lambda _e: self._finish_edit(row_id, column))
        self._edit_widget = editor

    def _finish_edit(self, row_id: str | None = None, column: int | None = None) -> None:
        editor = self._edit_widget
        self._edit_widget = None
        if editor is None:
            return
        new_value = editor.get()
        editor.destroy()
        if row_id is not None and column is not None:
            values = list(self.table.item(row_id, "values"))
            values[column] = new_value
            self.table.item(row_id, values=values)
            self._schedule_plot_refresh()

    def _table_rows(self) -> list[tuple[str, ...]]:
        """Return the editor rows exactly as they appear in the table."""
        return [
            tuple(str(value) for value in self.table.item(item, "values"))
            for item in self.table.get_children()
        ]

    def _replace_table_rows(self, rows: list[tuple[str, ...]]) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        for row in rows:
            self.table.insert("", "end", values=row)

    def import_table(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Import Ramp Table",
            filetypes=CSV_FILE_TYPES,
        )
        if not file_path:
            return
        try:
            rows = read_table_csv(file_path)
        except ValueError as exc:
            messagebox.showerror("CSV Import Failed", str(exc))
            return

        self._replace_table_rows(rows)
        self.status.set(f"Imported {len(rows)} table rows.")
        self.refresh_plot()

    def _read_steps(self) -> tuple[list[Step], int, int]:
        dt, decim = parse_ramp_parameters(self.dt.get(), self.decim.get())
        steps = [
            step_from_table_values(self.table.item(item, "values"), row_number)
            for row_number, item in enumerate(self.table.get_children(), start=1)
        ]
        if len(steps) < 2:
            raise ValueError("At least two rows are required: an initial point and a target point.")
        return steps, dt, decim

    def export_sequence(self) -> None:
        try:
            steps, dt, decim = self._read_steps()
            samples = build_ramp(steps, decim)
        except ValueError as exc:
            messagebox.showerror("Invalid Sequence", str(exc))
            return

        file_path = filedialog.asksaveasfilename(
            title="Export Ramp Table",
            defaultextension=".csv",
            filetypes=CSV_FILE_TYPES,
            initialfile="epica_ramp.csv",
        )
        if not file_path:
            return
        try:
            write_table_csv(file_path, self._table_rows())
        except ValueError as exc:
            messagebox.showerror("CSV Export Failed", str(exc))
            return
        self._result = (dt, ramp_to_hex_string(samples, decim))
        self.destroy()

    def cancel(self) -> None:
        """Close the GUI without exporting a sequence."""
        self.destroy()

    @property
    def result(self) -> tuple[int, str] | None:
        return self._result

    def _schedule_plot_refresh(self, *_args: object) -> None:
        if self._plot_refresh_job is not None:
            self.after_cancel(self._plot_refresh_job)
        self._plot_refresh_job = self.after(120, self.refresh_plot)

    def refresh_plot(self) -> None:
        """Refresh the built-in preview without external dependencies."""
        self._plot_refresh_job = None
        try:
            steps, dt, decim = self._read_steps()
            samples = build_ramp(steps, decim)
        except ValueError as exc:
            self._plot_samples = []
            self.plot_info.set(f"Preview unavailable: {exc}")
            self._show_plot_error()
            return
        self._plot_samples = samples
        self._plot_dt = dt
        total_us = len(samples) * dt
        self.plot_info.set(
            f"{len(samples)} samples | ramp duration {self._format_time(total_us)} | "
            f"dt = {dt} µs · decim = {decim}"
        )
        self._draw_plot(self.plot_canvas, samples, dt)

    @staticmethod
    def _format_time(value_us: float) -> str:
        return f"{value_us / 1000:g} ms" if value_us >= 1000 else f"{value_us:g} µs"

    def _show_plot_error(self) -> None:
        self.plot_canvas.delete("all")
        self.plot_canvas.create_text(
            self.plot_canvas.winfo_width() / 2,
            self.plot_canvas.winfo_height() / 2,
            text="Invalid sequence",
            fill="#a00000",
        )

    def _draw_plot(self, canvas: tk.Canvas, samples: list[Step], dt: int) -> None:
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 160 or height < 180 or not samples:
            return

        left, right = 58, width - 28
        top, bottom = 10, height - 42
        gap = 18
        available_height = bottom - top
        digital_height = max(85, int(available_height * 0.22))
        analog_height = (available_height - digital_height - 3 * gap) / 3
        if analog_height < 45:
            return
        analog_panels = (
            ("PRE", "pre", "#1f77b4"),
            ("PWM", "pwm", "#d62728"),
            ("PWM4Q", "pwm4q", "#9467bd"),
        )
        for panel_index, (label, field, color) in enumerate(analog_panels):
            panel_top = top + panel_index * (analog_height + gap)
            panel_bottom = panel_top + analog_height
            values = [self._signed_value(sample, field) for sample in samples]
            self._draw_analog_panel(
                canvas,
                label,
                values,
                color,
                left,
                right,
                panel_top,
                panel_bottom,
            )

        digital_top = top + 3 * (analog_height + gap)
        digital_graph_top = digital_top + 18
        self._draw_digital_panel(canvas, samples, left, right, digital_top, digital_graph_top, bottom)
        self._draw_time_axis(canvas, len(samples) * dt, left, right, bottom, height)

    @staticmethod
    def _signed_value(sample: Step, field: str) -> int:
        polarity = 1 if sample.pol == 0 else -1
        return polarity * getattr(sample, field)

    def _draw_analog_panel(
        self,
        canvas: tk.Canvas,
        label: str,
        values: list[int],
        color: str,
        left: float,
        right: float,
        panel_top: float,
        panel_bottom: float,
    ) -> None:
        graph_top = panel_top + 18

        def analog_y(value: float) -> float:
            return panel_bottom - (panel_bottom - graph_top) * (value + 255) / 510

        canvas.create_text(
            left,
            panel_top,
            text=label,
            anchor="nw",
            fill=color,
            font=("Segoe UI", 10, "bold"),
        )
        for fraction in range(5):
            x = left + (right - left) * fraction / 4
            canvas.create_line(x, graph_top, x, panel_bottom, fill="#f0f0f0")
        for value in (-255, 0, 255):
            y = analog_y(value)
            canvas.create_line(left, y, right, y, fill="#c7c7c7" if value == 0 else "#e7e7e7")
            canvas.create_text(left - 6, y, text=str(value), anchor="e", fill="#555555")
        canvas.create_line(left, graph_top, left, panel_bottom, fill="#555555")
        canvas.create_line(left, panel_bottom, right, panel_bottom, fill="#555555")

        points: list[float] = []
        denominator = max(len(values) - 1, 1)
        for index, value in enumerate(values):
            x = left + (right - left) * index / denominator
            points.extend((x, analog_y(value)))
        if len(points) >= 4:
            canvas.create_line(*points, fill=color, width=2)
        else:
            canvas.create_oval(
                points[0] - 2,
                points[1] - 2,
                points[0] + 2,
                points[1] + 2,
                fill=color,
                outline=color,
            )

    def _draw_digital_panel(
        self,
        canvas: tk.Canvas,
        samples: list[Step],
        left: float,
        right: float,
        digital_top: float,
        digital_graph_top: float,
        bottom: float,
    ) -> None:
        canvas.create_text(
            left,
            digital_top,
            text="Digital states",
            anchor="nw",
            font=("Segoe UI", 10, "bold"),
        )
        lane_height = (bottom - digital_graph_top) / 3
        for lane, (label, field, color) in enumerate(DIGITAL_PLOT_LANES):
            values = [getattr(sample, field) for sample in samples]
            lane_top = digital_graph_top + lane * lane_height
            lane_bottom = lane_top + lane_height
            y0 = lane_bottom - 6
            y1 = lane_top + 6
            canvas.create_line(left, lane_bottom, right, lane_bottom, fill="#e7e7e7")
            canvas.create_text(
                left - 6,
                (lane_top + lane_bottom) / 2,
                text=label,
                anchor="e",
                font=("Segoe UI", 9, "bold"),
            )
            points = [left, y1 if values[0] else y0]
            for index, value in enumerate(values):
                x_end = left + (right - left) * (index + 1) / len(samples)
                points.extend((x_end, y1 if value else y0))
                if index < len(values) - 1:
                    points.extend((x_end, y1 if values[index + 1] else y0))
            canvas.create_line(*points, fill=color, width=2)
        canvas.create_line(left, digital_graph_top, left, bottom, fill="#555555")
        canvas.create_line(left, bottom, right, bottom, fill="#555555")

    def _draw_time_axis(
        self,
        canvas: tk.Canvas,
        total_us: int,
        left: float,
        right: float,
        bottom: float,
        height: float,
    ) -> None:
        for fraction in range(5):
            x = left + (right - left) * fraction / 4
            time_us = total_us * fraction / 4
            canvas.create_line(x, bottom, x, bottom + 5, fill="#555555")
            canvas.create_text(x, bottom + 17, text=self._format_time(time_us), anchor="n", fill="#555555")


def ramp_generator() -> tuple[int | None, str]:
    """Open the editor and return ``(dt, seq)`` after a successful export.

    ``seq`` has the format ``"0x01514D00, 0x81232100, ..."``. Closing the
    window without exporting returns ``(None, "")``.
    """
    app = RampGeneratorApp()
    app.mainloop()
    return app.result if app.result is not None else (None, "")


if __name__ == "__main__":
    dt, seq = ramp_generator()
    if dt is not None:
        print(dt)
        print(seq)
        print(len(seq.split(",")))
