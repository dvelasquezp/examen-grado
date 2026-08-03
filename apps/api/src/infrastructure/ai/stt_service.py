"""Transcripción de audio (faster-whisper, carga perezosa)."""

import logging
import tempfile
from pathlib import Path

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        settings = get_settings()
        _model = WhisperModel(
            settings.stt_model.split("/")[-1] if "/" in settings.stt_model else settings.stt_model,
            device="cpu",
            compute_type="int8",
        )
    return _model


def transcribe_audio(data: bytes, filename: str = "audio.webm") -> dict:
    """Transcribe audio bytes a texto en español."""
    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        model = _get_model()
        segments, info = model.transcribe(tmp_path, language="es", beam_size=3)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return {
            "text": text,
            "language": info.language or "es",
            "duration": round(info.duration, 2) if info.duration else None,
        }
    except Exception as exc:
        logger.exception("STT failed")
        raise RuntimeError(f"No se pudo transcribir el audio: {exc}") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)
