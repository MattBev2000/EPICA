from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any
import re

import numpy as np


class PaperPlot:
    """Standalone plotting helper with the LangmuirProbe plot style.

    The class supports single-panel and multi-panel figures using a compact
    layout string such as "1x1", "1x2", "2x1", "2x2", or a tuple (n, m).

    Examples
    --------
    Single X-Y plot with multiple Y curves:

        plotter = PaperPlot()
        plotter.plot_xy(
            x,
            [y1, y2],
            plot_format="1x1",
            title="Signal comparison",
            xlabel="Time [s]",
            ylabel="Voltage [V]",
            legend=["Run A", "Run B"],
        )

    Two-panel X-Y plot:

        plotter.plot_xy(
            [x1, x2],
            [y1, [y2a, y2b]],
            plot_format="1x2",
            title=["First panel", "Second panel"],
            xlabel="Time [s]",
            ylabel=["Voltage [V]", "Current [A]"],
            legend=[["V"], ["I raw", "I filtered"]],
        )
    """

    DEFAULT_COLORS = (
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    )

    def __init__(self, 
                 output_dir: str | Path = ".", 
                 plot_dir: str | Path | None = None, 
                 dpi: int = 220, 
                 legend_fontsize: int = 14) -> None:
        self.output_dir = Path(output_dir)
        self.plot_dir = Path(plot_dir) if plot_dir is not None else self.output_dir / "plots"
        self.dpi = int(dpi)
        self.legend_fontsize = int(legend_fontsize)


    def plot_xy(self,
                x: Any,
                y: Any,
                plot_format: str | tuple[int, int] = "1x1",
                title: str | Sequence[str] | None = None,
                xlabel: str | Sequence[str] = "X",
                ylabel: str | Sequence[str] = "Y",
                legend: str | Sequence[str] | Sequence[Sequence[str]] | None = None,
                save_path: str | Path | None = None,
                show: bool = True,
                save: bool = True,
                marker: str | None = None,
                linestyle: str = "-",
                linewidth: float = 2.2,
                markersize: float = 4.0,
                figsize: tuple[float, float] | None = None,
                sharex: bool = False, 
                sharey: bool = False):
        """Plot Y as a function of X.

        Parameters
        ----------
        x, y:
            Data to plot. For a single panel, ``y`` can be one array or a list
            of arrays. For multiple panels, pass one item per panel; each panel
            item can still contain multiple Y arrays.
        plot_format:
            Layout in the form "nxm" or ``(n, m)``.
        title, xlabel, ylabel:
            A single string used for all panels, or one string per panel.
        legend:
            For one panel, one label per Y curve. For multiple panels, pass one
            legend list per panel.
        """

        plt = self._load_matplotlib()
        rows, cols = self._parse_plot_format(plot_format)
        panel_count = rows * cols
        fig, axes = plt.subplots(
            rows,
            cols,
            figsize=figsize or self._default_figsize(rows, cols),
            squeeze=False,
            sharex=sharex,
            sharey=sharey,
        )

        for index, ax in enumerate(axes.ravel()):
            x_panel = self._panel_data(x, index, panel_count, "x", allow_shared=True)
            y_panel = self._panel_data(y, index, panel_count, "y", allow_shared=False)
            xy_series = self._normalize_xy_series(x_panel, y_panel)
            legend_labels = self._panel_legend(legend, index, panel_count, len(xy_series))

            for series_index, (x_values, y_values) in enumerate(xy_series):
                ax.plot(
                    x_values,
                    y_values,
                    marker=marker,
                    linestyle=linestyle,
                    linewidth=linewidth,
                    markersize=markersize,
                    color=self.DEFAULT_COLORS[series_index % len(self.DEFAULT_COLORS)],
                    label=None if legend_labels is None else legend_labels[series_index],
                )

            self._style_axis(
                ax,
                title=self._panel_text(title, index, panel_count, None),
                xlabel=self._panel_text(xlabel, index, panel_count, "X"),
                ylabel=self._panel_text(ylabel, index, panel_count, "Y"),
                legend=legend_labels,
            )

        return self._finish_figure(
            fig,
            axes,
            save_path=save_path,
            save=save,
            default_suffix="xy",
            title=title,
            show=show,
        )

    def plot_histogram(self,
        data: Any,
        plot_format: str | tuple[int, int] = "1x1",
        title: str | Sequence[str] | None = None,
        xlabel: str | Sequence[str] = "Value",
        ylabel: str | Sequence[str] = "Counts",
        legend: str | Sequence[str] | Sequence[Sequence[str]] | None = None,
        bins: int | Sequence[int] = 50,
        density: bool = False,
        save_path: str | Path | None = None,
        show: bool = True,
        save: bool = True,
        alpha: float = 0.75,
        histtype: str = "step",
        linewidth: float = 2.0,
        figsize: tuple[float, float] | None = None,
        sharex: bool = False,
        sharey: bool = False,
    ):
        """Plot one or more histograms.

        For multiple panels, pass one data item per panel. Each panel data item
        can be one array or a list of arrays.
        """

        plt = self._load_matplotlib()
        rows, cols = self._parse_plot_format(plot_format)
        panel_count = rows * cols
        fig, axes = plt.subplots(
            rows,
            cols,
            figsize=figsize or self._default_figsize(rows, cols),
            squeeze=False,
            sharex=sharex,
            sharey=sharey,
        )

        for index, ax in enumerate(axes.ravel()):
            panel_data = self._panel_data(
                data,
                index,
                panel_count,
                "data",
                allow_shared=False,
            )
            series = self._series_list(panel_data)
            legend_labels = self._panel_legend(legend, index, panel_count, len(series))
            panel_bins = self._panel_text(bins, index, panel_count, bins)

            for series_index, values in enumerate(series):
                ax.hist(
                    values,
                    bins=panel_bins,
                    density=density,
                    alpha=alpha,
                    histtype=histtype,
                    linewidth=linewidth,
                    color=self.DEFAULT_COLORS[series_index % len(self.DEFAULT_COLORS)],
                    label=None if legend_labels is None else legend_labels[series_index],
                )

            self._style_axis(
                ax,
                title=self._panel_text(title, index, panel_count, None),
                xlabel=self._panel_text(xlabel, index, panel_count, "Value"),
                ylabel=self._panel_text(ylabel, index, panel_count, "Counts"),
                legend=legend_labels,
            )

        return self._finish_figure(
            fig,
            axes,
            save_path=save_path,
            save=save,
            default_suffix="histogram",
            title=title,
            show=show,
        )

    @staticmethod
    def _load_matplotlib():
        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ImportError(
                "PaperPlot requires matplotlib. Install matplotlib to create plots."
            ) from exc
        return plt

    @staticmethod
    def _parse_plot_format(plot_format: str | tuple[int, int]) -> tuple[int, int]:
        if isinstance(plot_format, tuple):
            if len(plot_format) != 2:
                raise ValueError("plot_format tuple must be (rows, columns).")
            rows, cols = plot_format
        else:
            cleaned = str(plot_format).lower().replace(" ", "")
            match = re.fullmatch(r"(\d+)x(\d+)", cleaned)
            if match is None:
                raise ValueError(
                    "plot_format must be like '1x1', '1x2', '2x2', or (n, m)."
                )
            rows, cols = int(match.group(1)), int(match.group(2))

        if rows < 1 or cols < 1:
            raise ValueError("plot_format rows and columns must be positive.")
        return int(rows), int(cols)

    @staticmethod
    def _default_figsize(rows: int, cols: int) -> tuple[float, float]:
        width = 12.0 if cols == 1 else 6.0 * cols
        height = 6.0 if rows == 1 else 4.5 * rows
        return width, height

    def _panel_data(
        self,
        data: Any,
        index: int,
        panel_count: int,
        name: str,
        allow_shared: bool,
    ) -> Any:
        if panel_count == 1:
            return data

        if self._looks_like_panel_sequence(data, panel_count):
            return data[index]

        if allow_shared:
            return data

        raise ValueError(
            f"{name} must provide one data item per panel for plot_format with "
            f"{panel_count} panels."
        )

    def _looks_like_panel_sequence(self, data: Any, panel_count: int) -> bool:
        if isinstance(data, np.ndarray):
            return data.ndim > 1 and data.shape[0] == panel_count
        if not self._is_sequence(data):
            return False
        return len(data) == panel_count and self._is_nested_sequence(data)

    def _normalize_xy_series(self, x_panel: Any, y_panel: Any) -> list[tuple[np.ndarray, np.ndarray]]:
        y_series = self._series_list(y_panel)
        x_series = self._series_list(x_panel)

        if len(x_series) == 1:
            x_series = x_series * len(y_series)
        elif len(x_series) != len(y_series):
            raise ValueError(
                "x must be either one shared array or one array for each y series."
            )

        xy_series: list[tuple[np.ndarray, np.ndarray]] = []
        for x_values, y_values in zip(x_series, y_series):
            if x_values.size != y_values.size:
                raise ValueError(
                    "Each x and y series must have the same number of samples."
                )
            xy_series.append((x_values, y_values))
        return xy_series

    def _series_list(self, data: Any) -> list[np.ndarray]:
        if isinstance(data, np.ndarray):
            if data.ndim == 0:
                raise ValueError("Plot data must contain at least one sample.")
            if data.ndim == 1:
                return [np.asarray(data, dtype=float).reshape(-1)]
            if data.ndim == 2:
                if data.shape[0] <= data.shape[1]:
                    return [np.asarray(row, dtype=float).reshape(-1) for row in data]
                return [
                    np.asarray(data[:, column], dtype=float).reshape(-1)
                    for column in range(data.shape[1])
                ]
            raise ValueError("Plot data can be at most two-dimensional.")

        if self._is_nested_sequence(data):
            return [np.asarray(item, dtype=float).reshape(-1) for item in data]

        return [np.asarray(data, dtype=float).reshape(-1)]

    def _panel_text(
        self,
        value: Any,
        index: int,
        panel_count: int,
        default: Any,
    ) -> Any:
        if value is None:
            return default
        if isinstance(value, str):
            return value
        if self._is_sequence(value) and len(value) == panel_count:
            return value[index]
        return value

    def _panel_legend(
        self,
        legend: str | Sequence[str] | Sequence[Sequence[str]] | None,
        index: int,
        panel_count: int,
        series_count: int,
    ) -> list[str] | None:
        if legend is None:
            return None

        panel_legend: Any = legend
        if panel_count > 1 and self._is_sequence(legend) and len(legend) == panel_count:
            panel_legend = legend[index]

        if panel_legend is None:
            return None
        if isinstance(panel_legend, str):
            labels = [panel_legend]
        elif self._is_sequence(panel_legend):
            labels = [str(item) for item in panel_legend]
        else:
            labels = [str(panel_legend)]

        if len(labels) != series_count:
            raise ValueError(
                f"Legend has {len(labels)} labels, but this panel has "
                f"{series_count} plotted series."
            )
        return labels

    def _style_axis(
        self,
        ax: Any,
        title: str | None,
        xlabel: str,
        ylabel: str,
        legend: list[str] | None,
    ) -> None:
        if title:
            ax.set_title(str(title))
        ax.set_xlabel(str(xlabel))
        ax.set_ylabel(str(ylabel))
        ax.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2))
        ax.grid(True, color="0.88")
        if legend is not None:
            ax.legend(frameon=True, fontsize=self.legend_fontsize)

    def _finish_figure(
        self,
        fig: Any,
        axes: Any,
        save_path: str | Path | None,
        save: bool,
        default_suffix: str,
        title: str | Sequence[str] | None,
        show: bool,
    ):
        fig.tight_layout()

        if save:
            plot_path = (
                Path(save_path)
                if save_path is not None
                else self._default_output_path(default_suffix, title)
            )
            plot_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(plot_path, dpi=self.dpi, bbox_inches="tight")

        if show:
            self._load_matplotlib().show()
        return fig, axes

    def _default_output_path(
        self,
        suffix: str,
        title: str | Sequence[str] | None,
    ) -> Path:
        if isinstance(title, str) and title.strip():
            safe_name = self._safe_filename(title)
        else:
            safe_name = "paperplot"
        return self.plot_dir / f"{safe_name}_{suffix}.png"

    @staticmethod
    def _safe_filename(name: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
        return safe.strip("._") or "paperplot"

    @staticmethod
    def _is_sequence(value: Any) -> bool:
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes))

    def _is_nested_sequence(self, value: Any) -> bool:
        if isinstance(value, np.ndarray):
            return value.ndim > 1
        if not self._is_sequence(value) or len(value) == 0:
            return False
        return any(
            isinstance(item, np.ndarray) or self._is_sequence(item)
            for item in value
        )
