"""Persistent achievement storage for The Last Ingredient."""
from __future__ import annotations
import json
from pathlib import Path
from core.constants import GAME_ROOT

PROGRESS_FILE = GAME_ROOT / "user_progress.json"


def _load_data() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_data(data: dict) -> None:
    try:
        PROGRESS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"Warning: Failed to save user progress: {e}")


def unlock_achievement(name: str) -> bool:
    """Unlock an achievement. Returns True if newly unlocked, False if already unlocked."""
    data = _load_data()
    achievements = data.setdefault("achievements", {})
    if achievements.get(name):
        return False
    achievements[name] = True
    _save_data(data)
    return True


def is_achievement_unlocked(name: str) -> bool:
    data = _load_data()
    return bool(data.get("achievements", {}).get(name, False))


def get_all_unlocked_achievements() -> set[str]:
    data = _load_data()
    return {k for k, v in data.get("achievements", {}).items() if v}
