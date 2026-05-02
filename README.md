# Buzzer Detector

A desktop tool that scans an audio recording for sustained tones in a configurable
frequency band (default 6700–6900 Hz) and flags events that exceed a chosen duration.
Useful for finding stuck buzzers, alarms, or any narrow-band continuous tone in a long
recording.

## Features

- Tk GUI for picking a file, tweaking detection parameters, and viewing results.
- Zero-phase Butterworth bandpass + short-time RMS envelope, processed in chunks so
  long files don't blow up memory.
- Auto threshold or manual threshold; configurable merge-gap and minimum-event
  duration; flags events longer than a "max on" cutoff.
- Plot view (matplotlib) and event list, with export to PNG/PDF/SVG and CSV.
- Single-file Windows `.exe` build via PyInstaller.

## Layout

```
source/
  buzzer_gui.py        # entry-point shim (used by PyInstaller)
  build_windows.bat    # one-click Windows build script
  buzzer/              # package
    analysis.py        # AnalysisService + config/result dataclasses
    audio_io.py        # file loading
    detection.py       # bandpass, envelope, thresholding, event extraction
    plotting.py        # figure rendering and result formatting
    gui.py             # Tk front-end (only module that imports tkinter)
coding_standard/       # shared lint / format tooling used by tasks.py
output/                # build artifacts, lint reports, PyInstaller output
tasks.py               # invoke tasks (clean / format / lint / executable)
requirements.txt
setup.cfg              # flake8 / mypy / pylint config
```

The package's public API is `AnalysisConfig`, `AnalysisResult`, and `AnalysisService`
from `buzzer`. The GUI module is the only place that depends on Tk or matplotlib's Tk
backend, so the rest of the code can be used and tested headlessly.

## Requirements

- Python 3.9+
- Packages in `requirements.txt`: `invoke`, `numpy`, `scipy`, `matplotlib`,
  `soundfile`, `pyinstaller`. `tkinter` ships with the standard Python installer on
  Windows and macOS; on Linux install your distro's `python3-tk` package.

## Run from source

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python source/buzzer_gui.py
```

Then click **Browse...**, pick a `.wav` / `.mp3` / `.flac` / `.ogg` / `.m4a` file,
adjust the band and thresholds if needed, and click **Analyze**.

## Detection settings

| Setting          | Meaning                                                                 |
|------------------|-------------------------------------------------------------------------|
| Use bandpass     | Apply a Butterworth bandpass before envelope detection.                 |
| Low / High (Hz)  | Bandpass edges. Default 6700–6900 Hz.                                   |
| Threshold        | Envelope level for "buzzer on", or `auto` for a percentile-based pick.  |
| Merge gap (ms)   | Off-gaps shorter than this are filled, joining nearby events.           |
| Min event (ms)   | On-runs shorter than this are dropped as blips.                         |
| Max on (s)       | Events longer than this are highlighted in the results.                 |

## Build a Windows executable

From a Windows shell, in the `source/` directory:

```bat
build_windows.bat
```

The script creates a clean venv, installs requirements, and runs PyInstaller. The
result is `source/dist/BuzzerDetector.exe` — a single self-contained file you can
copy to any Windows machine.

The same build is also available cross-platform via invoke (output goes to
`output/installer/`):

```bash
invoke executable
```

## Developer tasks

`tasks.py` exposes [invoke](https://www.pyinvoke.org/) tasks that wrap the shared
tooling in `coding_standard/`:

```bash
invoke clean       # alias: c    -- remove output/
invoke format      # alias: f    -- run formatters (use --check to verify only)
invoke lint        # alias: l    -- flake8 / mypy / pylint, reports to output/
invoke executable  # alias: exe  -- PyInstaller build
```

Lint and type-check config lives in `setup.cfg`. Reports land under `output/`,
which is gitignored.
