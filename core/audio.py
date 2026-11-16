"""Sound manager for playing game SFX safely with volume control."""
import os
import time
import arcade
from core.constants import SOUNDS_DIR


class AudioManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.sounds = {}
        self.last_played = {}
        self.sound_enabled = True
        self.volume = 0.8
        self._load_all_sounds()

    def _load_all_sounds(self):
        if SOUNDS_DIR.exists():
            for wav_file in SOUNDS_DIR.glob("*.wav"):
                try:
                    self.sounds[wav_file.stem] = arcade.load_sound(str(wav_file))
                except Exception as e:
                    print(f"Warning: Failed to load sound {wav_file.stem}: {e}")

    def play(self, sound_name, min_interval=0.08, volume_scale=1.0):
        if not self.sound_enabled:
            return
        snd = self.sounds.get(sound_name)
        if not snd:
            path = SOUNDS_DIR / f"{sound_name}.wav"
            if path.exists():
                try:
                    snd = arcade.load_sound(str(path))
                    self.sounds[sound_name] = snd
                except Exception:
                    pass
        if not snd:
            return

        now = time.time()
        last = self.last_played.get(sound_name, 0.0)
        if now - last < min_interval:
            return

        self.last_played[sound_name] = now
        try:
            vol = min(1.0, max(0.0, self.volume * volume_scale))
            arcade.play_sound(snd, volume=vol)
        except Exception as e:
            pass
