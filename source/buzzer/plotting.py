"""
Plot rendering and results-text formatting.

Backend-agnostic — no Tk imports. ``render_analysis`` writes into a Matplotlib ``Figure`` provided by the caller, so the
same code works from the Tk GUI, a headless ``Agg`` figure for batch CSV/PNG export, or a Jupyter notebook.

"""

import numpy as np
from buzzer.analysis import AnalysisResult
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from typing import Tuple


def _downsample_for_plot(y: np.ndarray, t: np.ndarray, max_points: int = 200_000) -> Tuple[np.ndarray, np.ndarray]:
    """
    Reduce a long signal to ~max_points for plotting, preserving peaks.

    Bins the signal into ~max_points groups and keeps the min and max of each bin (interleaved). This way short
    transients still show up as spikes and the visual envelope of the waveform looks identical to the full-resolution
    plot, but matplotlib only has to draw a manageable number of points.

    """
    n = len(y)
    if n <= max_points:
        return t, y
    n_bins = max(1, max_points // 2)
    bin_size = n // n_bins
    usable = n_bins * bin_size
    y_trim = y[:usable].reshape(n_bins, bin_size)
    t_trim = t[:usable].reshape(n_bins, bin_size)
    y_min = y_trim.min(axis=1)
    y_max = y_trim.max(axis=1)
    t_mid = t_trim[:, bin_size // 2]
    out_y = np.empty(n_bins * 2, dtype=y.dtype)
    out_t = np.empty(n_bins * 2, dtype=t.dtype)
    out_y[0::2] = y_min
    out_y[1::2] = y_max
    out_t[0::2] = t_mid
    out_t[1::2] = t_mid
    return out_t, out_y


def _draw_state_axis(ax: Axes, t_env: np.ndarray, result: AnalysisResult, max_on: float) -> None:
    """Draw the buzzer-state strip with red highlights on events that exceed ``max_on`` seconds."""
    tb, yb = _downsample_for_plot(result.binary.astype(np.float32), t_env)
    ax.fill_between(tb, 0, yb, step="mid", alpha=0.4, color="#117733")
    ax.plot(tb, yb, color="#117733", lw=1.0)

    long_events = [(s, e) for s, e in result.events if (e - s) > max_on]
    for s, e in long_events:
        ax.axvspan(s, e, color="#CC3311", alpha=0.35, zorder=0)
    if long_events:
        ax.set_title(f"Buzzer state (1 = on, 0 = off) - {len(long_events)} event(s) over {max_on:.2f}s flagged in red")
    else:
        ax.set_title("Buzzer state (1 = on, 0 = off)")
    ax.set_ylim(-0.1, 1.1)
    ax.set_yticks([0, 1])
    ax.set_ylabel("Buzzer state")
    ax.set_xlabel("Time (s)")
    ax.grid(alpha=0.3)


def render_analysis(fig: Figure, result: AnalysisResult, max_on: float) -> None:
    """
    Render the three-panel waveform/envelope/state plot into ``fig``.

    The figure is cleared first; the caller is responsible for refreshing whatever canvas owns the figure.

    """
    fig.clear()
    axes = fig.subplots(3, 1, sharex=True)

    t_env = np.arange(len(result.env)) * result.hop_s
    tw, yw = _downsample_for_plot(result.audio, np.arange(len(result.audio)) / result.sr)
    te, ye = _downsample_for_plot(result.env, t_env)

    axes[0].plot(tw, yw, lw=0.4, color="#4477AA")
    axes[0].set_title(f"Waveform ({len(result.audio) / result.sr:.1f}s @ {result.sr}Hz)")
    axes[0].set_ylabel("Amplitude")
    axes[0].grid(alpha=0.3)

    axes[1].plot(te, ye, lw=0.8, color="#CC6677")
    axes[1].axhline(result.threshold, color="black", ls="--", lw=0.8, label=f"threshold = {result.threshold:.5f}")
    axes[1].set_ylabel("RMS envelope")
    axes[1].set_title("Short-time energy")
    axes[1].legend(loc="upper right")
    axes[1].grid(alpha=0.3)

    _draw_state_axis(axes[2], t_env, result, max_on)

    fig.tight_layout()


def format_results_text(result: AnalysisResult, max_on: float) -> str:
    """Produce the multi-line per-event breakdown shown in the results text area."""
    long_count = sum(1 for s, e in result.events if (e - s) > max_on)
    lines = [f"Threshold used: {result.threshold:.5f}"]
    if long_count > 0:
        lines.append(f"** {long_count} event(s) longer than {max_on:.2f}s detected **")
    else:
        lines.append(f"All events were under {max_on:.2f}s.")
    lines.append(f"Detected {len(result.events)} buzzer-on event(s):")
    for i, (s, e) in enumerate(result.events, 1):
        dur = e - s
        flag = "  >>> LONG" if dur > max_on else ""
        lines.append(f"  {i:3d}: {s:8.3f} s -> {e:8.3f} s  (duration {dur:6.3f} s){flag}")
    return "\n".join(lines) + "\n"


def count_long_events(result: AnalysisResult, max_on: float) -> int:
    """
    Return how many detected events exceed ``max_on`` seconds.

    Used by the GUI for the status line.

    """
    return sum(1 for s, e in result.events if (e - s) > max_on)
