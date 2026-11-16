"""Global constants, robust path resolvers, and color tokens for The Last Ingredient.
All paths are dynamically resolved relative to this project root, ensuring 100% portability.
"""
from pathlib import Path

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "The Last Ingredient - One Chance to Begin Again"
# Window Display Mode: Set to True for Fullscreen, False for 1280x720 Windowed (Press F11 at any time to toggle)
START_FULLSCREEN = True



# ---- Dynamic Path Resolution (Zero Hardcoded Paths)
GAME_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = GAME_ROOT / "assets"
CHARACTERS_DIR = ASSETS_DIR / "characters"
SOUNDS_DIR = ASSETS_DIR / "sounds"
RENDERS_DIR = GAME_ROOT / "renders"

# Per-Scene Asset Subdirectories (Standardized to "Scene X")
SCENE_1_DIR = ASSETS_DIR / "Scene 1"
SCENE_2_DIR = ASSETS_DIR / "Scene 2"
SCENE_3_DIR = ASSETS_DIR / "Scene 3"
SCENE_4_DIR = ASSETS_DIR / "Scene 4"
SCENE_5_DIR = ASSETS_DIR / "Scene 5"
SCENE_6_DIR = ASSETS_DIR / "Scene 6"
SCENE_7_DIR = ASSETS_DIR / "Scene 7"
SCENE_9_DIR = ASSETS_DIR / "Scene 9"

# Ensure essential output folders exist
RENDERS_DIR.mkdir(parents=True, exist_ok=True)
SCENE_1_DIR.mkdir(parents=True, exist_ok=True)
SCENE_2_DIR.mkdir(parents=True, exist_ok=True)
SCENE_3_DIR.mkdir(parents=True, exist_ok=True)
SCENE_4_DIR.mkdir(parents=True, exist_ok=True)
SCENE_5_DIR.mkdir(parents=True, exist_ok=True)
SCENE_6_DIR.mkdir(parents=True, exist_ok=True)
SCENE_7_DIR.mkdir(parents=True, exist_ok=True)
SCENE_9_DIR.mkdir(parents=True, exist_ok=True)


def get_asset_path(*parts) -> str:
    """Safely resolve an asset path relative to ASSETS_DIR."""
    return str(ASSETS_DIR.joinpath(*parts).resolve())


def get_sound_path(sound_name: str) -> str:
    """Safely resolve a sound effect path."""
    return str((SOUNDS_DIR / f"{sound_name}.wav").resolve())


def get_character_sprite_path(character_id: str, direction: str, action: str) -> str:
    """Safely resolve a character sprite path (down, up, left, right | idle, walk1, walk2)."""
    filename = f"char_{direction}_{action}.png"
    return str((CHARACTERS_DIR / character_id / filename).resolve())


# ---- Character Era Metadata
CHARACTERS = {
    "modern": {
        "id": "modern",
        "name": "Modern Chef",
        "era": "Act I: Modern Era Â· The Fall & Midnight Soup",
        "theme_color": (210, 175, 120),
    },
    "savage": {
        "id": "savage",
        "name": "Prehistoric Hunter",
        "era": "Act II: Prehistory Â· The Whistle That Never Sounded",
        "theme_color": (230, 140, 80),
    },
    "chef": {
        "id": "chef",
        "name": "Royal Cook",
        "era": "Act III: Royal Court Â· Something to Pass On",
        "theme_color": (220, 190, 140),
    },
    "astronaut": {
        "id": "astronaut",
        "name": "Future Researcher",
        "era": "Act IV: Future Era Â· The Quantum Laboratory",
        "theme_color": (100, 210, 255),
    },
}

# ---- Atmospheric Color Palette Tokens
COLOR_DARK_BG = (18, 14, 16)
COLOR_GOLD = (235, 198, 110)
COLOR_GOLD_DARK = (180, 140, 65)
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_TEXT_MUTED = (220, 225, 235)
COLOR_BLUE_COMPOUND = (70, 170, 255)
COLOR_DANGER_RED = (220, 65, 55)
COLOR_SUCCESS_GREEN = (60, 195, 120)
COLOR_VIOLET_ARCANE = (165, 95, 240)
