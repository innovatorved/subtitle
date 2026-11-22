"""Subtitle file translator preserving exact cue timestamps.

Supports:
- Local offline translation via ``argostranslate`` (`pip install subtitle-generator[translate]`)
- Fast LLM translation via OpenAI / Groq (`pip install subtitle-generator[cloud]`)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from .exceptions import SubtitleError
from .formatters import SubtitleFormatterFactory, SubtitleSegment

logger = logging.getLogger(__name__)


def _translate_with_argos(
    texts: list[str],
    source_lang: str,
    target_lang: str,
) -> list[str]:
    try:
        import argostranslate.translate as argos_translate  # type: ignore
    except ImportError as e:
        raise SubtitleError(
            "Local subtitle translation requires `argostranslate`. "
            "Install with: pip install 'subtitle-generator[translate]'",
            cause=e,
        )

    src = "en" if source_lang in {"auto", ""} else source_lang
    return [argos_translate.translate(t, src, target_lang) for t in texts]


def _translate_with_llm(
    texts: list[str],
    target_lang: str,
    provider: str = "openai",
    model: Optional[str] = None,
    batch_size: int = 40,
) -> list[str]:
    try:
        import openai  # type: ignore
    except ImportError as e:
        raise SubtitleError(
            "LLM subtitle translation requires `openai`. "
            "Install with: pip install 'subtitle-generator[cloud]'",
            cause=e,
        )

    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise SubtitleError("GROQ_API_KEY environment variable is required for Groq translation.")
        client = openai.OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        model_name = model or "llama-3.3-70b-versatile"
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise SubtitleError("OPENAI_API_KEY environment variable is required for OpenAI translation.")
        client = openai.OpenAI(api_key=api_key)
        model_name = model or "gpt-4o-mini"

    translated: list[str] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        prompt = (
            f"Translate each subtitle string in this JSON array into {target_lang}. "
            "Preserve line breaks (\\n), tone, and conciseness suitable for subtitles. "
            'Return ONLY a JSON object of the form {"translations": [...]} with the exact same number of items.'
        )
        resp = client.chat.completions.create(
            model=model_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(chunk, ensure_ascii=False)},
            ],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise SubtitleError(f"Translator returned invalid JSON: {e}", cause=e)
        items = parsed.get("translations")
        if not isinstance(items, list) or len(items) != len(chunk):
            raise SubtitleError(
                f"Translator returned {len(items) if isinstance(items, list) else 'invalid'} "
                f"items for batch of {len(chunk)}"
            )
        translated.extend(str(x) for x in items)

    return translated


def translate_segments(
    segments: list[SubtitleSegment],
    target_lang: str,
    source_lang: str = "auto",
    provider: str = "auto",
    model: Optional[str] = None,
) -> list[SubtitleSegment]:
    """Translate subtitle segments while preserving timestamps and indices."""
    if not segments:
        return []

    texts = [s.text for s in segments]
    chosen = provider.lower()
    if chosen == "auto":
        if os.environ.get("OPENAI_API_KEY"):
            chosen = "openai"
        elif os.environ.get("GROQ_API_KEY"):
            chosen = "groq"
        else:
            chosen = "argos"

    if chosen == "argos":
        translated_texts = _translate_with_argos(texts, source_lang, target_lang)
    elif chosen in {"openai", "groq"}:
        translated_texts = _translate_with_llm(texts, target_lang, provider=chosen, model=model)
    else:
        raise SubtitleError(f"Unknown translation provider: {provider}. Use auto, argos, openai, or groq.")

    return [
        SubtitleSegment(
            index=seg.index,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=new_text,
            speaker=seg.speaker,
        )
        for seg, new_text in zip(segments, translated_texts)
    ]


def translate_subtitle_file(
    input_path: str,
    target_lang: str,
    output_path: Optional[str] = None,
    source_lang: str = "auto",
    provider: str = "auto",
    model: Optional[str] = None,
) -> str:
    """Translate a subtitle file on disk and write the translated file."""
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Subtitle file not found: {input_path}")

    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    formatter = SubtitleFormatterFactory.create(ext)
    with open(input_path, "r", encoding="utf-8") as f:
        segments = formatter.parse(f.read())

    translated = translate_segments(
        segments,
        target_lang=target_lang,
        source_lang=source_lang,
        provider=provider,
        model=model,
    )

    if not output_path:
        base, dot_ext = os.path.splitext(input_path)
        output_path = f"{base}.{target_lang}{dot_ext}"

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(formatter.format(translated))
    return output_path
