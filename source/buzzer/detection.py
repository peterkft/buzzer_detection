"""
Pure signal-processing primitives for buzzer detection.

No GUI, audio I/O, or plotting: just NumPy arrays in, NumPy arrays / event lists out. Everything here is a pure function
of its inputs and is straightforward to unit-test in isolation.

"""

import numpy as np
from typing import Callable, List, Optional, Tuple

ProgressCallback = Callable[[float], None]


def _filter_chunk_with_overlap(sos: np.ndarray, audio: np.ndarray, pos: int, chunk: int, overlap: int) -> np.ndarray:
    """Filter ``audio`` around index ``pos`` and return the inner (non-overlap) slice."""
    from scipy.signal import sosfiltfilt  # pylint: disable=import-outside-toplevel

    n = len(audio)
    start = max(0, pos - overlap)
    end = min(n, pos + chunk + overlap)
    block = audio[start:end]
    padlen = min(3 * sos.shape[0] * 2, len(block) - 1)
    filtered = sosfiltfilt(sos, block, padlen=padlen).astype(np.float32)
    inner_start = pos - start
    inner_end = inner_start + min(chunk, n - pos)
    return filtered[inner_start:inner_end]


def _apply_sosfiltfilt_chunked(
    sos: np.ndarray,
    audio: np.ndarray,
    sr: int,
    progress_cb: Optional[ProgressCallback] = None,
) -> np.ndarray:
    """
    Run sosfiltfilt over ``audio`` in 30 s chunks with 1 s overlap on each side.

    The overlap lets the filter state settle cleanly at chunk boundaries, so the chunked output matches the one-shot
    output to within float rounding. Peak memory stays bounded regardless of file length.

    """
    n = len(audio)
    chunk = sr * 30
    overlap = sr * 1

    out = np.empty(n, dtype=np.float32)
    pos = 0
    while pos < n:
        inner = _filter_chunk_with_overlap(sos, audio, pos, chunk, overlap)
        out[pos : pos + len(inner)] = inner
        pos += chunk
        if progress_cb is not None:
            progress_cb(min(1.0, pos / n))
    return out


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def bandpass(
    audio: np.ndarray,
    sr: int,
    low_hz: float,
    high_hz: float,
    order: int = 6,
    progress_cb: Optional[ProgressCallback] = None,
) -> np.ndarray:
    """
    Zero-phase Butterworth bandpass that processes the signal in chunks.

    For short files this is identical to a one-shot sosfiltfilt. For long files it processes ~30 second chunks with
    overlap so the filter state settles cleanly at the boundaries, which keeps peak memory bounded regardless of the
    file length.

    """
    from scipy.signal import butter, sosfiltfilt  # pylint: disable=import-outside-toplevel

    nyq = sr / 2.0
    low = max(1.0, low_hz) / nyq
    high = min(nyq - 1.0, high_hz) / nyq
    sos = butter(order, [low, high], btype="band", output="sos")

    # For files under ~5 minutes at 44.1 kHz, just do it in one shot
    if len(audio) < 15_000_000:
        return sosfiltfilt(sos, audio).astype(np.float32)
    return _apply_sosfiltfilt_chunked(sos, audio, sr, progress_cb=progress_cb)


def compute_envelope(audio: np.ndarray, sr: int, window_ms: float = 10.0) -> Tuple[np.ndarray, float]:
    """
    Short-time RMS envelope computed in chunks to keep memory bounded.

    Returns the envelope and the per-bin hop in seconds (so ``len(env) * hop_s`` is the covered duration).

    """
    win = max(1, int(sr * window_ms / 1000.0))
    n_full = len(audio) // win
    if n_full == 0:
        return np.empty(0, dtype=np.float32), win / sr

    env = np.empty(n_full, dtype=np.float32)
    # Process ~1M output frames at a time = ~10 seconds of envelope per pass
    bins_per_chunk = 1_000_000
    pos = 0
    while pos < n_full:
        end = min(pos + bins_per_chunk, n_full)
        seg = audio[pos * win : end * win].reshape(end - pos, win)
        # square-mean-sqrt without an intermediate large float64 array
        sq = seg.astype(np.float32) ** 2
        env[pos:end] = np.sqrt(sq.mean(axis=1, dtype=np.float32))
        pos = end
    return env, win / sr


def auto_threshold(env: np.ndarray) -> float:
    """Median of lower half vs upper half: robust to spikes, good for sustained tones."""
    if len(env) < 2:
        return float("inf")
    low = float(np.percentile(env, 10))
    high = float(np.percentile(env, 99))
    if high > max(low, 1e-9) * 10:
        return max(np.sqrt(max(low, 1e-9) * high), low * 5.0, 1e-6)
    return float(np.percentile(env, 99.9)) * 1.5


def _fill_short_runs(binary: np.ndarray, target_value: int, max_run: int) -> np.ndarray:
    out = binary.copy()
    n = len(out)
    if n == 0:
        return out
    changes = np.diff(out, prepend=1 - out[0])
    starts = np.where(changes != 0)[0]
    ends = np.append(starts[1:], n)
    flip_to = 1 - target_value
    for s, e in zip(starts, ends):
        if out[s] == target_value and (e - s) < max_run:
            out[s:e] = flip_to
    return out


def detect_events(
    env: np.ndarray,
    hop_s: float,
    threshold: float,
    merge_gap_ms: float = 300.0,
    min_event_ms: float = 1000.0,
) -> Tuple[np.ndarray, List[Tuple[float, float]]]:
    """Threshold ``env``, merge short gaps, drop short blips; return the binary mask and (start, end) event pairs."""
    binary = (env >= threshold).astype(np.int8)
    if len(binary) == 0:
        return binary, []
    merge_gap = max(1, int(merge_gap_ms / 1000.0 / hop_s))
    min_event = max(1, int(min_event_ms / 1000.0 / hop_s))
    binary = _fill_short_runs(binary, target_value=0, max_run=merge_gap)
    binary = _fill_short_runs(binary, target_value=1, max_run=min_event)
    diff = np.diff(binary.astype(int), prepend=0, append=0)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    events = [(s * hop_s, e * hop_s) for s, e in zip(starts, ends)]
    return binary, events
