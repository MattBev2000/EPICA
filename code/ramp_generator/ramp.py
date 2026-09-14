"""
EPICA Ramp Generator.

This module provides a Tkinter-based editor for EPICA power-supply ramps.
The user defines a list of target ``Step`` objects and calls
``ramp_generator()``.  When *Export* is pressed, the graphical interface
closes and returns ``(dt, seq)``:

* ``dt`` is the constant sample period in microseconds;
* ``seq`` is a comma-separated string of 32-bit hexadecimal register words,
  for example ``"0x01514D00, 0x81232100, ..."``.

No CSV file is created and no additional OFF words are appended to ``seq``.

Ramp generation
---------------
Each row is a target state.  For every transition from row ``i`` to row
``i + 1``, the ``step`` value of the destination row defines the number of
generated samples.  ``pre``, ``pwm`` and ``pwm4q`` are linearly interpolated
between the two rows.  The digital fields ``enable``, ``pol``, ``load`` and
``pwm4e`` instead take the destination value immediately and remain constant
for the whole segment.

32-bit register layout
----------------------
    31          28 27 26 25 24 23                 16 15                 8 7      0
    ┌─────────────┬──┬──┬──┬──┬─────────────────────┬─────────────────────┬────────┐
    │ pol │ decim │L │4E│0 │EN│       prereg        │         PWM         │   0    │
    └─────────────┴──┴──┴──┴──┴─────────────────────┴─────────────────────┴────────┘

* bit 31: ``pol``;
* bits 30:28: global ``decim`` value (fixed for the entire ramp);
* bit 27: ``load``;
* bit 26: ``pwm4e`` (also called ``4E``);
* bit 24: ``enable``;
* bits 23:16: effective preregulation value;
* bits 15:8: PWM duty-cycle value;
* bits 25 and 7:0: always zero.

PWM4Q and 4E logic
------------------
``pwm4e`` selects the source written into bits 23:16:

* when ``pwm4e = 0``, ``prereg = pre``;
* when ``pwm4e = 1``, ``prereg = pwm4q``.

``pre`` and ``pwm4q`` are always generated as ramps, but only the selected
one affects the register.  ``pwm`` is independent of this selector and is
always written into bits 15:8.  Since ``pwm4e`` is a digital destination
value, enabling or disabling it can cause an immediate change of the active
preregulation value.  To avoid a discontinuity at a 4E transition, make
``pre`` and ``pwm4q`` equal at the switching instant.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk


FIELDS = ("enable", "pol", "load", "pre", "pwm", "pwm4e", "pwm4q", "step", "note")
NUMERIC_FIELDS = FIELDS[:-1]
HEADINGS = ("EN", "POL", "LOAD", "PRE", "PWM", "4E", "PWM4Q", "STEP", "NOTA")


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
    """Compila la word dell'AS20P2 per un campione della rampa."""
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
    """Interpolazione lineare intera, con punto finale garantito."""
    if points == 1:
        return [start]
    return [
        stop if k == points - 1 else int(start + (stop - start) * k / (points - 1))
        for k in range(points)
    ]


def build_ramp(steps: list[Step], decim: int) -> list[Step]:
    """Crea i campioni: analogici interpolati, bit digitali al valore di arrivo."""
    samples: list[Step] = []
    for source, destination in zip(steps, steps[1:]):
        if destination.points <= 0:
            continue
        for pre, pwm, pwm4q in zip(
            interpolate_int(source.pre, destination.pre, destination.points),
            interpolate_int(source.pwm, destination.pwm, destination.points),
            interpolate_int(source.pwm4q, destination.pwm4q, destination.points),
        ):
            samples.append(
                Step(
                    destination.enable,
                    destination.pol,
                    destination.load,
                    pre,
                    pwm,
                    destination.pwm4e,
                    pwm4q,
                    destination.points,
                    destination.note,
                )
            )
    if not samples:
        raise ValueError("Nessun segmento valido: almeno una riga dopo la prima deve avere STEP > 0.")
    return samples


def ramp_to_hex_string(samples: list[Step], decim: int) -> str:
    """Converte i campioni nella stringa ``0xXXXXXXXX, 0xXXXXXXXX, ...``.

    Le righe OFF usate dalla precedente esportazione CSV non sono incluse:
    la stringa contiene solo i registri generati dalla sequenza.
    """
    return ", ".join(f"0x{compute_register(sample, decim):08X}" for sample in samples)


class RampGeneratorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("EPICA – Generatore rampa")
        self.geometry("1450x720")
        self.minsize(1100, 560)
        self.dt = tk.StringVar(value="600")
        self.decim = tk.StringVar(value="0")
        self.status = tk.StringVar(value="Modifica la sequenza, poi salva il CSV.")
        self.plot_info = tk.StringVar(value="Anteprima della rampa")
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

        params = ttk.Frame(editor, padding=(2, 2, 2, 4))
        params.pack(fill="x")
        ttk.Label(params, text="dt [µs]").pack(side="left")
        ttk.Entry(params, textvariable=self.dt, width=8).pack(side="left", padx=(5, 18))
        ttk.Label(params, text="decim (0–7)").pack(side="left")
        ttk.Spinbox(params, from_=0, to=7, textvariable=self.decim, width=5).pack(side="left", padx=5)
        ttk.Label(
            params,
            text="POL=0 positivo, POL=1 negativo · 4E=0 usa PRE, 4E=1 usa PWM4Q",
        ).pack(side="left", padx=20)

        table_box = ttk.Frame(editor, padding=(2, 4, 2, 4))
        table_box.pack(fill="both", expand=True)
        table_box.rowconfigure(0, weight=1)
        table_box.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(table_box, columns=FIELDS, show="headings", selectmode="browse")
        widths = (58, 58, 62, 76, 76, 58, 76, 70, 350)
        for field, heading, width in zip(FIELDS, HEADINGS, widths):
            self.table.heading(field, text=heading)
            self.table.column(field, width=width, minwidth=45, anchor="center" if field != "note" else "w")
        scrollbar = ttk.Scrollbar(table_box, orient="vertical", command=self.table.yview)
        horizontal_scrollbar = ttk.Scrollbar(table_box, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal_scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.table.bind("<Double-1>", self._start_edit)

        commands = ttk.Frame(editor, padding=(2, 4))
        commands.pack(fill="x")
        ttk.Button(commands, text="Aggiungi riga", command=self.add_row).pack(side="left")
        ttk.Button(commands, text="Elimina riga", command=self.delete_row).pack(side="left", padx=5)
        ttk.Button(commands, text="Sposta su", command=lambda: self.move_row(-1)).pack(side="left", padx=5)
        ttk.Button(commands, text="Sposta giù", command=lambda: self.move_row(1)).pack(side="left", padx=5)
        ttk.Button(commands, text="Azzera", command=self.clear_rows).pack(side="left", padx=5)
        ttk.Button(commands, text="Esporta", command=self.export_sequence).pack(side="right")

        plot_box = ttk.LabelFrame(preview, text="Anteprima rampa", padding=6)
        plot_box.pack(fill="both", expand=True, padx=(6, 0))
        top_plot = ttk.Frame(plot_box)
        top_plot.pack(fill="x")
        ttk.Label(top_plot, textvariable=self.plot_info).pack(side="left")
        ttk.Button(top_plot, text="Aggiorna", command=self.refresh_plot).pack(side="right")
        self.plot_canvas = tk.Canvas(plot_box, background="white", highlightthickness=0)
        self.plot_canvas.pack(fill="both", expand=True, pady=(5, 0))
        self.plot_canvas.bind("<Configure>", lambda _event: self._draw_plot(self.plot_canvas, self._plot_samples, self._plot_dt))

        self.dt.trace_add("write", self._schedule_plot_refresh)
        self.decim.trace_add("write", self._schedule_plot_refresh)
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=6).pack(fill="x", side="bottom")

    def _add_default_sequence(self) -> None:
        # Stessa sequenza di default del tool C#: rampa negativa, zero, rampa positiva, zero.
        values = [
            (1, 1, 0, 0, 0, 0, 0, 0, "inizio"),
            (1, 1, 0, 0, 0, 0, 0, 1, ""),
            (1, 1, 0, 210, 200, 0, 0, 60, "rampa negativa"),
            (1, 1, 0, 0, 0, 0, 0, 60, "ritorno a zero"),
            (1, 1, 0, 0, 0, 0, 0, 4, "attesa a zero"),
            (1, 0, 0, 0, 0, 0, 0, 1, "cambio polarità"),
            (1, 0, 0, 210, 200, 0, 0, 60, "rampa positiva"),
            (1, 0, 0, 0, 0, 0, 0, 60, "ritorno a zero"),
            (1, 0, 0, 0, 0, 0, 0, 4, "attesa finale"),
        ]
        for row in values:
            self.table.insert("", "end", values=row)

    def add_row(self) -> None:
        selected = self.table.selection()
        values = self.table.item(selected[0], "values") if selected else (1, 0, 0, 0, 0, 0, 0, 1, "")
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
        if messagebox.askyesno("Azzera sequenza", "Rimuovere tutte le righe della sequenza?"):
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

    def _read_steps(self) -> tuple[list[Step], int, int]:
        try:
            dt = int(self.dt.get())
            decim = int(self.decim.get())
        except ValueError as exc:
            raise ValueError("dt e decim devono essere numeri interi.") from exc
        if dt <= 0:
            raise ValueError("dt deve essere maggiore di zero.")
        if not 0 <= decim <= 7:
            raise ValueError("decim deve essere compreso tra 0 e 7.")

        steps: list[Step] = []
        for row_number, item in enumerate(self.table.get_children(), start=1):
            values = self.table.item(item, "values")
            try:
                numeric = [int(values[i]) for i in range(8)]
            except (ValueError, IndexError) as exc:
                raise ValueError(f"Riga {row_number}: i primi otto campi devono essere interi.") from exc
            enable, pol, load, pre, pwm, pwm4e, pwm4q, points = numeric
            if any(x not in (0, 1) for x in (enable, pol, load, pwm4e)):
                raise ValueError(f"Riga {row_number}: EN, POL, LOAD e 4E devono valere 0 oppure 1.")
            if not all(0 <= x <= 255 for x in (pre, pwm, pwm4q)):
                raise ValueError(f"Riga {row_number}: PRE, PWM e PWM4Q devono essere compresi tra 0 e 255.")
            if points < 0:
                raise ValueError(f"Riga {row_number}: STEP non può essere negativo.")
            steps.append(Step(*numeric, str(values[8]).replace("\r", " ").replace("\n", " ")))
        if len(steps) < 2:
            raise ValueError("Servono almeno due righe: punto iniziale e almeno un punto bersaglio.")
        return steps, dt, decim

    def export_sequence(self) -> None:
        try:
            steps, dt, decim = self._read_steps()
            samples = build_ramp(steps, decim)
        except ValueError as exc:
            messagebox.showerror("Sequenza non valida", str(exc))
            return
        self._result = (dt, ramp_to_hex_string(samples, decim))
        self.destroy()

    def cancel(self) -> None:
        """Chiude la GUI senza esportare una sequenza."""
        self.destroy()

    @property
    def result(self) -> tuple[int, str] | None:
        return self._result

    def _schedule_plot_refresh(self, *_args: object) -> None:
        if self._plot_refresh_job is not None:
            self.after_cancel(self._plot_refresh_job)
        self._plot_refresh_job = self.after(120, self.refresh_plot)

    def refresh_plot(self) -> None:
        """Aggiorna l'anteprima incorporata, senza dipendenze esterne."""
        self._plot_refresh_job = None
        try:
            steps, dt, decim = self._read_steps()
            samples = build_ramp(steps, decim)
        except ValueError as exc:
            self._plot_samples = []
            self.plot_info.set(f"Anteprima non disponibile: {exc}")
            self.plot_canvas.delete("all")
            self.plot_canvas.create_text(
                self.plot_canvas.winfo_width() / 2,
                self.plot_canvas.winfo_height() / 2,
                text="Sequenza non valida",
                fill="#a00000",
            )
            return
        self._plot_samples = samples
        self._plot_dt = dt
        total_us = len(samples) * dt
        self.plot_info.set(
            f"{len(samples)} campioni · durata rampa {self._format_time(total_us)} · "
            f"dt = {dt} µs · decim = {decim}"
        )
        self._draw_plot(self.plot_canvas, samples, dt)

    @staticmethod
    def _format_time(value_us: float) -> str:
        return f"{value_us / 1000:g} ms" if value_us >= 1000 else f"{value_us:g} µs"

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
        total_us = len(samples) * dt

        def x_at(sample_index: float) -> float:
            return left + (right - left) * sample_index / len(samples)

        sign = lambda sample: 1 if sample.pol == 0 else -1
        analog_panels = (
            ("PRE", [sign(s) * s.pre for s in samples], "#1f77b4"),
            ("PWM", [sign(s) * s.pwm for s in samples], "#d62728"),
            ("PWM4Q", [sign(s) * s.pwm4q for s in samples], "#9467bd"),
        )

        # Tre grafici distinti, con la stessa scala verticale e lo stesso asse dei tempi.
        for panel_index, (label, values, color) in enumerate(analog_panels):
            panel_top = top + panel_index * (analog_height + gap)
            panel_bottom = panel_top + analog_height
            graph_top = panel_top + 18

            def analog_y(value: float) -> float:
                return panel_bottom - (panel_bottom - graph_top) * (value + 255) / 510

            canvas.create_text(left, panel_top, text=label, anchor="nw", fill=color, font=("Segoe UI", 10, "bold"))
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
                canvas.create_oval(points[0] - 2, points[1] - 2, points[0] + 2, points[1] + 2, fill=color, outline=color)

        # Pannello digitale sotto ai tre grafici analogici.
        digital_top = top + 3 * (analog_height + gap)
        digital_graph_top = digital_top + 18
        canvas.create_text(left, digital_top, text="Stati digitali", anchor="nw", font=("Segoe UI", 10, "bold"))
        lane_data = (("POL", [s.pol for s in samples], "#2ca02c"),
                     ("EN", [s.enable for s in samples], "#ff7f0e"),
                     ("4E", [s.pwm4e for s in samples], "#8c564b"))
        lane_height = (bottom - digital_graph_top) / 3
        for lane, (label, values, color) in enumerate(lane_data):
            lane_top = digital_graph_top + lane * lane_height
            lane_bottom = lane_top + lane_height
            y0 = lane_bottom - 6
            y1 = lane_top + 6
            canvas.create_line(left, lane_bottom, right, lane_bottom, fill="#e7e7e7")
            canvas.create_text(left - 6, (lane_top + lane_bottom) / 2, text=label, anchor="e", font=("Segoe UI", 9, "bold"))
            points = [x_at(0), y1 if values[0] else y0]
            for index, value in enumerate(values):
                x_end = x_at(index + 1)
                points.extend((x_end, y1 if value else y0))
                if index < len(values) - 1:
                    points.extend((x_end, y1 if values[index + 1] else y0))
            canvas.create_line(*points, fill=color, width=2)
        canvas.create_line(left, digital_graph_top, left, bottom, fill="#555555")
        canvas.create_line(left, bottom, right, bottom, fill="#555555")

        # Asse dei tempi comune, sotto tutti e quattro i pannelli.
        for fraction in range(5):
            x = left + (right - left) * fraction / 4
            time_us = total_us * fraction / 4
            canvas.create_line(x, bottom, x, bottom + 5, fill="#555555")
            canvas.create_text(x, bottom + 17, text=self._format_time(time_us), anchor="n", fill="#555555")
        canvas.create_text((left + right) / 2, height - 8, text="Tempo", anchor="s")

def ramp_generator() -> tuple[int | None, str]:
    """Apre l'editor e restituisce ``(dt, seq)`` alla pressione di *Esporta*.

    ``seq`` ha il formato ``"0x01514D00, 0x81232100, ..."``. Se la finestra
    viene chiusa senza esportare, il risultato è ``(None, "")``.
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
