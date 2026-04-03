"""
apps/voice/audio_utils.py
==========================
Audio helper utilities used by both the STT and TTS pipelines.

Functions:
  convert_to_vosk_format()  — ensure any audio is 16 kHz 16-bit mono WAV
  detect_silence()          — check if a chunk is below an energy threshold
  save_pcm_to_wav()         — wrap raw PCM bytes in a proper WAV header
  cleanup_old_files()       — remove audio files older than N hours
  get_audio_duration()      — return duration in seconds from a WAV
"""

import logging
import os
import struct
import time
import wave
from pathlib import Path
from typing import Optional

log = logging.getLogger("vicidial_bot.voice.audio")

SAMPLE_RATE  = 16_000
CHANNELS     = 1
SAMPLE_WIDTH = 2    # bytes — 16-bit PCM


# ── Format conversion ─────────────────────────────────────────────────────────

def convert_to_vosk_format(src_path: str, dst_path: Optional[str] = None) -> str:
    """
    Convert any audio file to 16 kHz · 16-bit · mono WAV.
    Requires pydub + ffmpeg installed on the server.

    Returns the path to the converted file.
    """
    from pydub import AudioSegment

    src  = Path(src_path)
    dst  = Path(dst_path) if dst_path else src.with_suffix(".vosk.wav")

    fmt  = src.suffix.lstrip(".").lower()
    fmt  = "mp3" if fmt == "mp3" else "wav"

    audio = (
        AudioSegment.from_file(str(src), format=fmt)
        .set_frame_rate(SAMPLE_RATE)
        .set_channels(CHANNELS)
        .set_sample_width(SAMPLE_WIDTH)
    )
    audio.export(str(dst), format="wav")
    log.debug("Converted %s → %s", src, dst)
    return str(dst)


def save_pcm_to_wav(pcm_data: bytes, output_path: str) -> str:
    """
    Wrap raw PCM bytes (16 kHz · 16-bit · mono) in a WAV container.
    Needed when Asterisk pipes raw audio to our script.
    """
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)
    return output_path


# ── Silence detection ─────────────────────────────────────────────────────────

def is_silence(
    chunk: bytes,
    threshold: int = 500,    # RMS threshold — tune for your environment
    min_silence_ms: int = 700,
    sample_rate: int = SAMPLE_RATE,
) -> bool:
    """
    Return True if the audio chunk is below the silence threshold.
    Uses simple RMS energy over 16-bit signed samples.

    threshold    — lower = more sensitive to quiet audio
    min_silence_ms — only mark silence if the chunk is this long
    """
    if len(chunk) < 2:
        return True

    # Minimum bytes needed for min_silence_ms
    min_bytes = int(sample_rate * SAMPLE_WIDTH * min_silence_ms / 1000)
    if len(chunk) < min_bytes:
        return False

    # Unpack 16-bit signed samples and compute RMS
    n_samples = len(chunk) // SAMPLE_WIDTH
    samples   = struct.unpack(f"<{n_samples}h", chunk[:n_samples * SAMPLE_WIDTH])
    rms       = (sum(s * s for s in samples) / n_samples) ** 0.5
    return rms < threshold


def trim_silence(
    wav_path: str,
    silence_thresh_dbfs: int = -40,
    min_silence_len_ms:  int = 500,
) -> str:
    """
    Remove leading/trailing silence from a WAV file.
    Returns path to the trimmed file (in-place replacement).
    """
    try:
        from pydub import AudioSegment, silence as pydub_silence

        audio   = AudioSegment.from_wav(wav_path)
        trimmed = pydub_silence.detect_nonsilent(
            audio,
            min_silence_len=min_silence_len_ms,
            silence_thresh=silence_thresh_dbfs,
        )
        if trimmed:
            start_ms, end_ms = trimmed[0][0], trimmed[-1][1]
            audio[start_ms:end_ms].export(wav_path, format="wav")

    except ImportError:
        log.warning("pydub not installed — silence trimming skipped")
    except Exception as exc:
        log.warning("trim_silence failed: %s", exc)

    return wav_path


# ── WAV info ──────────────────────────────────────────────────────────────────

def get_audio_duration(wav_path: str) -> float:
    """Return duration of a WAV file in seconds."""
    try:
        with wave.open(wav_path, "rb") as wf:
            return wf.getnframes() / wf.getframerate()
    except Exception as exc:
        log.warning("get_audio_duration failed for %s: %s", wav_path, exc)
        return 0.0


def validate_wav_format(wav_path: str) -> tuple[bool, str]:
    """
    Check that a WAV file matches Asterisk/Vosk requirements.
    Returns (ok: bool, message: str).
    """
    try:
        with wave.open(wav_path, "rb") as wf:
            ch    = wf.getnchannels()
            sw    = wf.getsampwidth()
            fr    = wf.getframerate()
            ok    = (ch == CHANNELS and sw == SAMPLE_WIDTH and fr == SAMPLE_RATE)
            msg   = (
                "OK" if ok else
                f"Expected mono/16-bit/16kHz, got ch={ch} sw={sw*8}bit fr={fr}"
            )
            return ok, msg
    except Exception as exc:
        return False, str(exc)


# ── File management ───────────────────────────────────────────────────────────

def cleanup_old_files(directory: str, max_age_hours: int = 24) -> int:
    """
    Delete audio files in a directory that are older than max_age_hours.
    Returns the number of files deleted.

    Call from a Celery beat task or management command periodically.
    """
    cutoff  = time.time() - max_age_hours * 3600
    deleted = 0

    for filepath in Path(directory).glob("*.wav"):
        try:
            if filepath.stat().st_mtime < cutoff:
                filepath.unlink()
                deleted += 1
        except Exception as exc:
            log.warning("Could not delete %s: %s", filepath, exc)

    log.info("Cleaned %d old audio files from %s", deleted, directory)
    return deleted


def wav_path_for_asterisk(wav_path: str) -> str:
    """
    Asterisk STREAM FILE expects the path WITHOUT the .wav extension.
    This helper strips it so you can pass the result directly to AGI.
    """
    return wav_path.replace(".wav", "")