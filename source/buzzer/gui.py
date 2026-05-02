"""
Tk front-end.

The only place in the package that imports tkinter or matplotlib's Tk backend. The GUI's job is widget layout,
threading, dialog handling, and translating Tk variable values into an ``AnalysisConfig``. All signal processing is
delegated to ``AnalysisService``; all plot drawing is delegated to ``buzzer.plotting``. That keeps this module focused
on user-interaction concerns and makes the rest of the package testable without ever instantiating Tk.

"""

import matplotlib
import numpy as np
import os
import threading
import tkinter as tk  # pylint: disable=import-error
import traceback
from buzzer.analysis import AnalysisConfig, AnalysisResult, AnalysisService
from buzzer.plotting import count_long_events, format_results_text, render_analysis
from tkinter import filedialog, messagebox, ttk  # pylint: disable=import-error
from typing import Optional

# Pin the Tk backend before any matplotlib.backends import. The actual backend imports
# happen inside _build_layout, which is the only place that needs them.
matplotlib.use("TkAgg")


class BuzzerApp(tk.Tk):  # pylint: disable=too-many-instance-attributes
    """Top-level Tk window for the buzzer detector."""

    def __init__(self, service: Optional[AnalysisService] = None):
        super().__init__()
        self.title("Buzzer Detector")
        self.geometry("1100x780")
        self.minsize(800, 600)

        # The service is injected so a future test or alternative front-end can swap it out (DIP).
        self._service = service if service is not None else AnalysisService()

        # State
        self.audio_path = tk.StringVar(value="")
        self.band_low = tk.DoubleVar(value=6700.0)
        self.band_high = tk.DoubleVar(value=6900.0)
        self.threshold_str = tk.StringVar(value="0.01")
        self.merge_gap_ms = tk.DoubleVar(value=300.0)
        self.min_event_ms = tk.DoubleVar(value=1000.0)
        self.max_on_s = tk.DoubleVar(value=7.5)
        self.use_bandpass = tk.BooleanVar(value=True)

        self.last_result: Optional[AnalysisResult] = None  # for plot redraw and CSV export

        self._build_layout()

    def _build_layout(self):
        """Construct all child widgets."""
        # pylint: disable=import-outside-toplevel
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        from matplotlib.figure import Figure

        # Top: file picker
        top = ttk.Frame(self, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top, text="Audio file:").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.audio_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(top, text="Browse...", command=self.choose_file).pack(side=tk.LEFT)

        # Settings panel
        opts = ttk.LabelFrame(self, text="Detection settings", padding=8)
        opts.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(0, 4))

        ttk.Checkbutton(opts, text="Use bandpass filter", variable=self.use_bandpass).grid(
            row=0, column=0, sticky="w", padx=4, pady=2
        )
        ttk.Label(opts, text="Low (Hz):").grid(row=0, column=1, sticky="e", padx=4)
        ttk.Entry(opts, textvariable=self.band_low, width=8).grid(row=0, column=2, sticky="w")
        ttk.Label(opts, text="High (Hz):").grid(row=0, column=3, sticky="e", padx=4)
        ttk.Entry(opts, textvariable=self.band_high, width=8).grid(row=0, column=4, sticky="w")

        ttk.Label(opts, text="Threshold:").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        ttk.Entry(opts, textvariable=self.threshold_str, width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(opts, text='(or "auto")').grid(row=1, column=2, sticky="w")

        ttk.Label(opts, text="Merge gap (ms):").grid(row=1, column=3, sticky="e", padx=4)
        ttk.Entry(opts, textvariable=self.merge_gap_ms, width=8).grid(row=1, column=4, sticky="w")

        ttk.Label(opts, text="Min event (ms):").grid(row=2, column=3, sticky="e", padx=4, pady=2)
        ttk.Entry(opts, textvariable=self.min_event_ms, width=8).grid(row=2, column=4, sticky="w")

        ttk.Label(opts, text="Max on (s):").grid(row=2, column=0, sticky="e", padx=4, pady=2)
        ttk.Entry(opts, textvariable=self.max_on_s, width=8).grid(row=2, column=1, sticky="w")
        ttk.Label(opts, text="(events longer than this are flagged)").grid(row=2, column=2, sticky="w", columnspan=1)

        # Action buttons
        actions = ttk.Frame(self, padding=4)
        actions.pack(side=tk.TOP, fill=tk.X)
        self.run_btn = ttk.Button(actions, text="Analyze", command=self.run_analysis)
        self.run_btn.pack(side=tk.LEFT, padx=8)
        ttk.Button(actions, text="Save plot...", command=self.save_plot).pack(side=tk.LEFT)
        ttk.Button(actions, text="Save CSV...", command=self.save_csv).pack(side=tk.LEFT, padx=4)
        self.status = ttk.Label(actions, text="Choose an audio file to begin.")
        self.status.pack(side=tk.LEFT, padx=12)

        # Plot area
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        NavigationToolbar2Tk(self.canvas, self).update()

        # Results panel
        results_frame = ttk.LabelFrame(self, text="Detected events", padding=4)
        results_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))
        self.results = tk.Text(results_frame, height=6, wrap="none")
        self.results.pack(fill=tk.X)

    # ----- callbacks -----

    def choose_file(self):
        """Prompt the user for an audio file and store its path."""
        path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.ogg *.m4a"),
                ("WAV files", "*.wav"),
                ("MP3 files", "*.mp3"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.audio_path.set(path)

    def set_status(self, msg):
        """Update the status label and force a redraw."""
        self.status.config(text=msg)
        self.update_idletasks()

    def run_analysis(self):
        """Validate the chosen file and start the analysis worker thread."""
        path = self.audio_path.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("No file", "Please choose a valid audio file first.")
            return
        # Run in a worker thread so the UI stays responsive
        self.run_btn.config(state="disabled")
        self.set_status("Loading audio...")
        threading.Thread(target=self._analyze_worker, args=(path,), daemon=True).start()

    def _post_status(self, msg):
        """Marshal a status update onto the Tk main thread."""
        self.after(0, lambda: self.set_status(msg))

    def _build_config(self) -> AnalysisConfig:
        """Translate the current Tk variable values into an immutable config dataclass."""
        thr_str = self.threshold_str.get().strip().lower()
        threshold = None if thr_str in ("", "auto") else float(thr_str)
        return AnalysisConfig(
            band_low=float(self.band_low.get()),
            band_high=float(self.band_high.get()),
            threshold=threshold,
            merge_gap_ms=float(self.merge_gap_ms.get()),
            min_event_ms=float(self.min_event_ms.get()),
            use_bandpass=bool(self.use_bandpass.get()),
        )

    def _on_progress(self, path: str, config: AnalysisConfig, phase: str, frac: float):
        """Translate a (phase, fraction) callback from the service into a human-readable status line."""
        if phase == "load":
            self._post_status(f"Loading audio... {int(frac * 100)}%")
        elif phase == "bandpass":
            self._post_status(
                f"Bandpass filtering {config.band_low:.0f}-{config.band_high:.0f} Hz... {int(frac * 100)}%"
            )
        elif phase == "envelope":
            if frac <= 0.0:
                self._post_status("Computing envelope...")
        # Note: ``path`` is unused right now but accepted so the callback can be enriched later
        # (e.g. file size in the load message) without changing the service's signature.
        del path

    def _analyze_worker(self, path):
        """Worker-thread entry point: build config, run service, hand off to plot renderer."""
        try:
            config = self._build_config()
            file_mb = os.path.getsize(path) / (1024 * 1024)
            self._post_status(f"Loading {file_mb:.0f} MB audio...")

            self.last_result = self._service.run(
                path,
                config,
                progress_cb=lambda phase, frac: self._on_progress(path, config, phase, frac),
            )
            self._post_status(
                f"Loaded {os.path.basename(path)} - "
                f"{len(self.last_result.audio) / self.last_result.sr:.1f}s @ {self.last_result.sr}Hz"
            )
            self.after(0, self._draw_result)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # GUI worker boundary: surface any failure as a dialog rather than crashing the thread.
            err_msg = f"{exc}\n\n{traceback.format_exc()}"
            self.after(0, lambda: messagebox.showerror("Error", err_msg))
            self.after(0, lambda: self.set_status("Error - see dialog."))
        finally:
            self.after(0, lambda: self.run_btn.config(state="normal"))

    def _get_max_on_seconds(self):
        """Read the max-on threshold from the entry box, with a 7.5s fallback for empty/invalid input."""
        try:
            return float(self.max_on_s.get())
        except (ValueError, tk.TclError):
            return 7.5

    def _draw_result(self):
        """Draw the plot and write the events text from ``self.last_result``."""
        result = self.last_result
        if result is None:
            return
        max_on = self._get_max_on_seconds()
        self.set_status(f"Rendering plot ({len(result.audio):,} samples)...")
        try:
            render_analysis(self.fig, result, max_on)
            self.canvas.draw()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Plotting failures should not bring the GUI down; surface them as a dialog.
            tb_str = traceback.format_exc()
            messagebox.showerror("Plot error", f"Failed to draw plot:\n\n{exc}\n\n{tb_str}")
            self.set_status("Plot error - see dialog.")
            return

        self.results.delete("1.0", tk.END)
        self.results.insert(tk.END, format_results_text(result, max_on))

        long_count = count_long_events(result, max_on)
        self.set_status(f"Done - {len(result.events)} event(s), {long_count} over {max_on:.2f}s.")

    def save_plot(self):
        """Save the current matplotlib figure to a user-chosen file."""
        if self.last_result is None:
            messagebox.showinfo("Nothing to save", "Run an analysis first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
            title="Save plot as...",
        )
        if path:
            self.fig.savefig(path, dpi=150)
            self.set_status(f"Saved plot to {path}")

    def save_csv(self):
        """Export the per-window buzzer-state binary signal to a CSV file."""
        if self.last_result is None:
            messagebox.showinfo("Nothing to save", "Run an analysis first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Save signal as CSV...",
        )
        if not path:
            return
        r = self.last_result
        t = np.arange(len(r.binary)) * r.hop_s
        np.savetxt(
            path,
            np.column_stack([t, r.binary]),
            fmt=["%.4f", "%d"],
            delimiter=",",
            header="time_s,buzzer_on",
            comments="",
        )
        self.set_status(f"Saved CSV to {path}")


def main():
    """Entry point: create the application window and run the Tk main loop."""
    app = BuzzerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
