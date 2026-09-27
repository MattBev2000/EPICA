# EPICA Ramp Generator

Tkinter application for building 32-bit EPICA power-supply register sequences.
The editor lets you compose the target points of a ramp, inspect its preview,
save the source table as CSV, and reload a saved table later.

The project consists of one Python module, `ramp.py`, and uses only the Python
standard library.

## Requirements and startup

Python 3.10 or newer is required. No additional packages are needed.

From the project folder on Windows:

```powershell
py -3 ramp.py
```

Alternatively:

```bash
python ramp.py
```

After a successful CSV export, the standalone program prints:

1. `dt` in microseconds;
2. the register sequence as `0xXXXXXXXX, 0xXXXXXXXX, ...`;
3. the number of generated samples.

## Editor workflow

Each table row represents a target state. The first row is the initial point;
each later row defines the segment that starts at the preceding row.

| Field | Allowed values | Meaning |
| --- | --- | --- |
| `EN` | `0` or `1` | Output enable. |
| `POL` | `0` or `1` | Polarity: `0` positive, `1` negative. |
| `LOAD` | `0` or `1` | Load bit. |
| `PRE` | `0`-`255` | Standard preregulation value. |
| `PWM` | `0`-`255` | PWM duty-cycle value. |
| `4E` | `0` or `1` | Preregulation source selector. |
| `PWM4Q` | `0`-`255` | Alternative preregulation value used when `4E=1`. |
| `STEP` | Integer greater than or equal to `0` | Number of samples in the incoming segment. |
| `NOTE` | Free text | Row annotation; it is not written to the register. |

Double-click a table cell to edit it. The row controls add, remove, move, or
clear rows. The preview refreshes shortly after an edit, or immediately with
**Refresh**.

`dt` is the constant period between samples, in microseconds. `decim` is a
global value from `0` to `7`, written into every generated register word.

## CSV import and export

**Export CSV** validates the current sequence, opens a save dialog, then
writes the table on the left. It also preserves the existing API result:
`ramp_generator()` returns `(dt, sequence)` after the file has been saved.
Cancelling the save dialog leaves the editor open.

**Import CSV** opens a file dialog, validates all rows before changing the
editor, replaces the current table, and immediately redraws the ramp preview.

The exported CSV uses UTF-8 encoding and this header:

```csv
enable,pol,load,pre,pwm,pwm4e,pwm4q,step,note
```

The importer requires that header and at least two valid table rows. It also
accepts the visible uppercase column headings for compatibility with manually
prepared tables, including the legacy `NOTA` heading. Notes can contain commas
and are handled as standard quoted CSV fields.

Example:

```csv
enable,pol,load,pre,pwm,pwm4e,pwm4q,step,note
1,1,0,0,0,0,0,0,start
1,1,0,210,200,0,0,60,negative ramp
1,1,0,0,0,0,0,60,return to zero
```

The CSV stores only the table. `dt` and `decim` remain editor-wide settings,
so set them before exporting or after importing a table.

## Ramp generation rules

For the transition from row `i` to row `i + 1`:

- `STEP` in the destination row determines the number of generated samples;
- `PRE`, `PWM`, and `PWM4Q` are linearly interpolated, including the starting
  and ending values;
- `EN`, `POL`, `LOAD`, and `4E` immediately use the destination-row value and
  stay constant throughout the segment;
- a destination row with `STEP = 0` does not generate samples.

At least one valid segment is required. The editor reports invalid values in
both the preview and export workflow.

When `4E = 0`, the preregulation bits receive `PRE`; when `4E = 1`, they
receive `PWM4Q`. Both source values are still interpolated. To avoid a
discontinuity when `4E` changes, make `PRE` and `PWM4Q` equal at the switching
point.

## 32-bit register layout

```
31          28 27 26 25 24 23                 16 15                 8 7      0
┌─────────────┬──┬──┬──┬──┬─────────────────────┬─────────────────────┬────────┐
│ pol │ decim │L │4E│0 │EN│       prereg        │         PWM         │   0    │
└─────────────┴──┴──┴──┴──┴─────────────────────┴─────────────────────┴────────┘
```

- bit 31: `pol`;
- bits 30:28: global `decim` value, fixed for the entire ramp;
- bit 27: `load`;
- bit 26: `pwm4e`, also called `4E`;
- bit 24: `enable`;
- bits 23:16: effective preregulation value;
- bits 15:8: PWM duty-cycle value;
- bits 25 and 7:0: always zero.

## Python integration

The public `ramp_generator()` function opens the editor and returns
`(dt, sequence)`:

```python
from ramp import ramp_generator

dt, sequence = ramp_generator()
if dt is not None:
    words = sequence.split(",")
```

Closing the window without exporting returns `(None, "")`.

The pure functions can also be used independently:

- `build_ramp(steps, decim)` creates the list of `Step` samples;
- `compute_register(step, decim)` compiles one register word;
- `ramp_to_hex_string(samples, decim)` returns the register string;
- `read_table_csv(path)` and `write_table_csv(path, rows)` implement the CSV
  table format;
- `parse_ramp_parameters(...)` and `step_from_table_values(...)` provide the
  validation rules used by the interface.

## Code structure

`Step` represents one ramp state. CSV I/O, validation, and ramp-generation
functions are in the first part of `ramp.py` and have no graphical dependency.
`RampGeneratorApp` provides the Tkinter interface: table editing, CSV import
and export, and preview drawing.

To change ramp behavior, modify the pure functions first. To change the user
interface or chart presentation, modify the `_build_*` and `_draw_*` methods
of `RampGeneratorApp`.

## Quick verification

Check the module syntax with:

```powershell
py -3 -m py_compile ramp.py
```
