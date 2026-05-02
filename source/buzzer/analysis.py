"""
Analysis orchestration: load → bandpass → envelope → threshold → detect.

Front-ends (Tk GUI, future CLI, future batch runner) depend on this module's ``AnalysisService`` and the dataclasses
below. They never import ``audio_io`` or ``detection`` directly, which keeps the dependency graph one-directional (GUI →
analysis → audio_io / detection) and lets the lower layers be unit-tested without ever constructing a service.

"""

import numpy as np
from buzzer.audio_io import load_audio
from buzzer.detection import auto_threshold, bandpass, compute_envelope, detect_events
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

# (phase, fraction-in-[0,1]) — phase is one of: "load", "bandpass", "envelope".
ProgressCallback = Callable[[str, float], None]


@dataclass(frozen=True)
class AnalysisConfig:
    """
    User-tunable parameters that affect detection (not display).

    ``threshold=None`` means "auto" — compute it from the envelope distribution. Note that ``max_on_s`` is a *display*
    threshold and lives on the plotting/results side, not here.

    """

    band_low: float = 6700.0
    band_high: float = 6900.0
    threshold: Optional[float] = None
    merge_gap_ms: float = 300.0
    min_event_ms: float = 1000.0
    use_bandpass: bool = True


@dataclass
class AnalysisResult:
    """Everything downstream consumers (plotting, CSV export, results text) need."""

    audio: np.ndarray
    sr: int
    env: np.ndarray
    hop_s: float
    binary: np.ndarray
    threshold: float
    events: List[Tuple[float, float]]


class AnalysisService:  # pylint: disable=too-few-public-methods
    """
    Stateless façade that runs one full detection pass.

    The service holds no state between calls; each ``run`` is independent. This makes it trivial to swap in for a test,
    share between threads (one service per thread, since underlying NumPy/SciPy calls release the GIL), or call from a
    CLI that has no notion of a GUI thread.

    """

    def run(
        self,
        path: str,
        config: AnalysisConfig,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> AnalysisResult:
        """
        Execute the full pipeline and return the result.

        Raises ValueError on bad bandpass settings.

        """
        audio, sr = load_audio(path, progress_cb=self._phase_cb(progress_cb, "load"))

        signal = self._maybe_bandpass(audio, sr, config, progress_cb)

        if progress_cb is not None:
            progress_cb("envelope", 0.0)
        env, hop_s = compute_envelope(signal, sr, window_ms=10.0)
        if progress_cb is not None:
            progress_cb("envelope", 1.0)

        # Free the filtered signal (can be ~2 GB) before threshold/detection.
        if signal is not audio:
            del signal

        threshold = config.threshold if config.threshold is not None else auto_threshold(env)
        binary, events = detect_events(
            env,
            hop_s,
            threshold,
            merge_gap_ms=config.merge_gap_ms,
            min_event_ms=config.min_event_ms,
        )

        return AnalysisResult(
            audio=audio,
            sr=sr,
            env=env,
            hop_s=hop_s,
            binary=binary,
            threshold=threshold,
            events=events,
        )

    @staticmethod
    def _maybe_bandpass(
        audio: np.ndarray,
        sr: int,
        config: AnalysisConfig,
        progress_cb: Optional[ProgressCallback],
    ) -> np.ndarray:
        if not config.use_bandpass:
            return audio
        if config.band_high <= config.band_low:
            raise ValueError("Band high must be greater than band low.")
        return bandpass(
            audio,
            sr,
            config.band_low,
            config.band_high,
            progress_cb=AnalysisService._phase_cb(progress_cb, "bandpass"),
        )

    @staticmethod
    def _phase_cb(progress_cb: Optional[ProgressCallback], phase: str) -> Optional[Callable[[float], None]]:
        """Wrap a phase-aware callback into the single-fraction form the lower layers expect."""
        if progress_cb is None:
            return None
        return lambda frac: progress_cb(phase, frac)
