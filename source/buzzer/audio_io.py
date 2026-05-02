"""
Audio loading.

Returns mono float32 in [-1, 1] regardless of source format. This module has no GUI or signal-processing dependencies;
the only optional progress hook is a callable that receives a fraction in [0.0, 1.0]. The caller wires that up to
whatever progress UI it wants.

"""

import numpy as np
import os
from typing import Callable, Optional, Tuple

ProgressCallback = Callable[[float], None]


def _load_wav_soundfile(path: str, progress_cb: Optional[ProgressCallback] = None) -> Tuple[np.ndarray, int]:
    """Chunked WAV read via soundfile, mono-converted in float32."""
    import soundfile as sf  # pylint: disable=import-outside-toplevel

    with sf.SoundFile(path, "r") as f:
        sr = f.samplerate
        n_frames = len(f)
        # Pre-allocate the output as float32 (4 bytes/sample) -- about
        # 1.9 GB for a 3-hour 44.1 kHz file. Tolerable on a modern PC.
        out = np.empty(n_frames, dtype=np.float32)
        pos = 0
        chunk = 1_000_000  # ~22 seconds at 44.1 kHz
        while pos < n_frames:
            block = f.read(chunk, dtype="float32", always_2d=True)
            if block.size == 0:
                break
            if block.shape[1] > 1:
                # Mean across channels in float32 (no float64 promotion)
                mono = block.sum(axis=1, dtype=np.float32)
                mono *= np.float32(1.0 / block.shape[1])
            else:
                mono = block[:, 0]
            end = pos + len(mono)
            out[pos:end] = mono
            pos = end
            if progress_cb is not None:
                progress_cb(pos / max(1, n_frames))
        return out[:pos], sr


def _decode_wave_block(raw: bytes, dtype: type, channels: int, scale: np.float32) -> np.ndarray:
    """Decode one stdlib-wave raw byte block into mono float32 samples."""
    block: np.ndarray = np.frombuffer(raw, dtype=dtype)
    if channels > 1:
        block = block.reshape(-1, channels)
        mono = block.astype(np.float32).mean(axis=1)
    else:
        mono = block.astype(np.float32)
    mono *= scale
    return mono


def _load_wav_stdlib(path: str, progress_cb: Optional[ProgressCallback] = None) -> Tuple[np.ndarray, int]:
    """Chunked WAV read via the stdlib wave module (fallback when soundfile is unavailable)."""
    import wave  # pylint: disable=import-outside-toplevel

    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        ch = wf.getnchannels()
        dtype: type = {1: np.int8, 2: np.int16, 4: np.int32}[wf.getsampwidth()]
        scale = np.float32(1.0 / np.iinfo(dtype).max)
        out = np.empty(n_frames, dtype=np.float32)
        pos = 0
        chunk = 1_000_000
        while pos < n_frames:
            raw = wf.readframes(min(chunk, n_frames - pos))
            if not raw:
                break
            mono = _decode_wave_block(raw, dtype, ch, scale)
            end = pos + len(mono)
            out[pos:end] = mono
            pos = end
            if progress_cb is not None:
                progress_cb(pos / max(1, n_frames))
        return out[:pos], sr


def _load_via_soundfile(path: str) -> Tuple[np.ndarray, int]:
    """One-shot load via soundfile (FLAC, OGG, etc.)."""
    import soundfile as sf  # pylint: disable=import-outside-toplevel

    data, sr = sf.read(path, always_2d=True, dtype="float32")
    return data.mean(axis=1, dtype=np.float32), sr


def _load_via_pydub(path: str) -> Tuple[np.ndarray, int]:
    """One-shot load via pydub + ffmpeg (MP3 and similar)."""
    try:
        from pydub import AudioSegment  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RuntimeError(
            "MP3 (and other non-WAV) support needs pydub + ffmpeg.\n"
            "Install pydub with `pip install pydub` and put ffmpeg on the PATH."
        ) from exc
    seg = AudioSegment.from_file(path)
    sr = seg.frame_rate
    samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
    if seg.channels > 1:
        samples = samples.reshape(-1, seg.channels).mean(axis=1, dtype=np.float32)
    samples *= np.float32(1.0 / (1 << (8 * seg.sample_width - 1)))
    return samples, sr


def load_audio(path: str, progress_cb: Optional[ProgressCallback] = None) -> Tuple[np.ndarray, int]:
    """
    Load WAV/MP3 etc. as mono float32 in [-1, 1].

    For .wav files this uses chunked reading via soundfile so it never materialises the full stereo float64 array in
    memory (which would be ~6 GB for a 1.8 GB stereo file). For other formats it falls back to soundfile or pydub.

    progress_cb(fraction) is called occasionally during loading so the caller can show a progress percentage.

    """
    ext = os.path.splitext(path)[1].lower()

    if ext == ".wav":
        try:
            return _load_wav_soundfile(path, progress_cb=progress_cb)
        except ImportError:
            return _load_wav_stdlib(path, progress_cb=progress_cb)

    try:
        return _load_via_soundfile(path)
    except Exception:  # pylint: disable=broad-exception-caught
        # soundfile raises a variety of subclass exceptions for unsupported
        # formats; fall through to the pydub/ffmpeg path for any of them.
        return _load_via_pydub(path)
