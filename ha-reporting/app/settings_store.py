from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SETTINGS_FILE = Path('/config/ha_reporting_settings.yaml')
AI_CONTEXT_LEVELS = {'optimized', 'extended', 'complete', 'automatic'}
DEFAULT_AI_CONTEXT_LEVEL = 'optimized'


def normalize_ai_context_level(value: Any) -> str:
    level = str(value or DEFAULT_AI_CONTEXT_LEVEL).strip().lower()
    if level not in AI_CONTEXT_LEVELS:
        raise ValueError(
            'AI context level must be one of: optimized, extended, complete, automatic'
        )
    return level


def default_settings() -> dict[str, Any]:
    return {'settings_version': 1, 'ai': {'context_level': DEFAULT_AI_CONTEXT_LEVEL}}


def load_settings(path: Path | None = None) -> dict[str, Any]:
    target = path or SETTINGS_FILE
    data: dict[str, Any] = {}
    if target.exists():
        loaded = yaml.safe_load(target.read_text(encoding='utf-8')) or {}
        if isinstance(loaded, dict):
            data = loaded
    ai = data.get('ai') if isinstance(data.get('ai'), dict) else {}
    return {
        'settings_version': 1,
        'ai': {'context_level': normalize_ai_context_level(ai.get('context_level', DEFAULT_AI_CONTEXT_LEVEL))},
    }


def save_ai_settings(payload: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    target = path or SETTINGS_FILE
    current = load_settings(target)
    raw = payload.get('context_level', (payload.get('ai') or {}).get('context_level') if isinstance(payload.get('ai'), dict) else None)
    current['ai']['context_level'] = normalize_ai_context_level(raw)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + '.tmp')
    temporary.write_text(yaml.safe_dump(current, allow_unicode=True, sort_keys=False), encoding='utf-8')
    temporary.replace(target)
    return current
