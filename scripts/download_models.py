#!/usr/bin/env python3
"""Descarga modelos Hugging Face para inferencia local."""

import argparse
import sys
from pathlib import Path

MODELS = {
    "embedding": {
        "repo": "BAAI/bge-m3",
        "type": "sentence-transformers",
        "size_hint": "~2.2 GB",
    },
    "llm-7b": {
        "repo": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "type": "gguf",
        "size_hint": "~4.5 GB (Q4_K_M)",
        "file": "qwen2.5-7b-instruct-q4_k_m.gguf",
    },
    "llm-3b": {
        "repo": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "type": "gguf",
        "size_hint": "~2.0 GB (Q4_K_M)",
        "file": "qwen2.5-3b-instruct-q4_k_m.gguf",
    },
    "whisper": {
        "repo": "Systran/faster-whisper-large-v3",
        "type": "faster-whisper",
        "size_hint": "~3.0 GB",
    },
}


def download_embedding(model_dir: Path, repo: str) -> None:
    print(f"Descargando embeddings: {repo}")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(repo, cache_folder=str(model_dir / "embeddings"))
        model.encode("Prueba de embedding legal en español")
        print(f"  ✓ Embeddings listos en {model_dir / 'embeddings'}")
    except ImportError:
        print("  ⚠ sentence-transformers no instalado. Ejecuta: pip install sentence-transformers")
        sys.exit(1)


def download_gguf(model_dir: Path, repo: str, filename: str) -> None:
    print(f"Descargando LLM GGUF: {repo}/{filename}")
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id=repo,
            filename=filename,
            local_dir=str(model_dir / "llm"),
        )
        print(f"  ✓ LLM descargado en {path}")
    except ImportError:
        print("  ⚠ huggingface-hub no instalado. Ejecuta: pip install huggingface-hub")
        sys.exit(1)


def download_whisper(model_dir: Path, repo: str) -> None:
    print(f"Descargando Whisper STT: {repo}")
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(
            "large-v3",
            device="cpu",
            compute_type="int8",
            download_root=str(model_dir / "whisper"),
        )
        segments, _ = model.transcribe("prueba", language="es")
        list(segments)
        print(f"  ✓ Whisper listo en {model_dir / 'whisper'}")
    except ImportError:
        print("  ⚠ faster-whisper no instalado. Ejecuta: pip install faster-whisper")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Descargar modelos Hugging Face")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=list(MODELS.keys()) + ["all"],
        default=["all"],
        help="Modelos a descargar",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("models"),
        help="Directorio de destino",
    )
    args = parser.parse_args()

    model_dir = args.dir
    model_dir.mkdir(parents=True, exist_ok=True)

    selected = list(MODELS.keys()) if "all" in args.models else args.models

    print("=" * 60)
    print("Examen de Grado — Descarga de Modelos IA")
    print("=" * 60)

    for key in selected:
        info = MODELS[key]
        print(f"\n[{key}] {info['repo']} ({info['size_hint']})")

        if info["type"] == "sentence-transformers":
            download_embedding(model_dir, info["repo"])
        elif info["type"] == "gguf":
            download_gguf(model_dir, info["repo"], info["file"])
        elif info["type"] == "faster-whisper":
            download_whisper(model_dir, info["repo"])

    print("\n" + "=" * 60)
    print("Descarga completada.")
    print("=" * 60)


if __name__ == "__main__":
    main()
