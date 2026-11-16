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
        self._current_footstep_player = None
        self._normal_step_counter = 0
        self._wood_step_counter = 0
        self._leather_step_counter = 0
        self.looping_players = {}
        self._load_all_sounds()

    def _load_all_sounds(self):
        if SOUNDS_DIR.exists():
            for sound_file in SOUNDS_DIR.iterdir():
                if sound_file.suffix.lower() in (".wav", ".mp3", ".ogg"):
                    try:
                        snd = arcade.load_sound(str(sound_file))
                        self.sounds[sound_file.stem] = snd
                        self.sounds[sound_file.stem.lower()] = snd
                        self.sounds[sound_file.stem.lower().replace(" ", "_")] = snd
                    except Exception as e:
                        print(f"Warning: Failed to load sound {sound_file.stem}: {e}")

    def play_footstep(self, sound_name="Normal Walk", min_interval=0.14, volume_scale=None):
        """Play a single crisp footstep slice, immediately cutting off any ongoing step to prevent overlap."""
        if not self.sound_enabled:
            return None

        self.stop_footstep()

        target_name = sound_name
        if sound_name in ("Normal Walk", "normal_walk", "Normal Walk.MP3"):
            self._normal_step_counter = (getattr(self, "_normal_step_counter", 0) % 12) + 1
            target_name = f"normal_step_{self._normal_step_counter}"
            effective_volume = 0.13 if volume_scale is None else volume_scale * 0.22
        elif sound_name in ("Walk on wooden land", "wood_step"):
            self._wood_step_counter = (getattr(self, "_wood_step_counter", 0) % 8) + 1
            target_name = f"wood_step_{self._wood_step_counter}"
            effective_volume = 0.12 if volume_scale is None else volume_scale * 0.20
        elif sound_name in (
            "Walk with leather shoes", "Walk with leather shoes.MP3", "walk_with_leather_shoes",
            "royal_leather_step", "leather_shoes", "leather_step"
        ):
            self._leather_step_counter = (getattr(self, "_leather_step_counter", 0) % 10) + 1
            target_name = f"leather_step_{self._leather_step_counter}"
            effective_volume = 0.07 if volume_scale is None else volume_scale * 0.11
        elif sound_name == "Walk on puddle":
            effective_volume = 0.16 if volume_scale is None else volume_scale * 0.25
        else:
            effective_volume = 0.13 if volume_scale is None else volume_scale * 0.22

        player = self.play(target_name, min_interval=min_interval, volume_scale=effective_volume, _is_footstep=True)
        self._current_footstep_player = player
        return player

    def stop_footstep(self):
        """Immediately stop footstep playback so silence ensues the instant movement halts."""
        if self._current_footstep_player is not None:
            try:
                arcade.stop_sound(self._current_footstep_player)
            except Exception:
                pass
            self._current_footstep_player = None

    def play(self, sound_name, min_interval=0.08, volume_scale=1.0, _is_footstep=False, loop=False):
        if not self.sound_enabled:
            return None

        # Route raw multi-second footstep files through play_footstep to avoid overlapping loops
        if not _is_footstep and sound_name in (
            "Normal Walk", "normal_walk", "Normal Walk.MP3",
            "Walk with leather shoes", "walk_with_leather_shoes", "Walk with leather shoes.MP3",
            "royal_leather_step"
        ):
            return self.play_footstep(sound_name, min_interval=min_interval, volume_scale=volume_scale)

        if loop and sound_name in self.looping_players:
            existing = self.looping_players[sound_name]
            if existing is not None and getattr(existing, "playing", False):
                return existing

        snd = self.sounds.get(sound_name)
        if not snd:
            snd = self.sounds.get(sound_name.lower())
        if not snd:
            snd = self.sounds.get(sound_name.lower().replace(" ", "_"))
        if not snd:
            snd = self.sounds.get(sound_name.lower().replace("_", " "))
        if not snd:
            for ext in (".wav", ".mp3", ".MP3", ".ogg"):
                for name_variant in (sound_name, sound_name.replace("_", " "), sound_name.replace(" ", "_")):
                    path = SOUNDS_DIR / f"{name_variant}{ext}"
                    if path.exists():
                        try:
                            snd = arcade.load_sound(str(path))
                            self.sounds[sound_name] = snd
                            break
                        except Exception:
                            pass
                if snd:
                    break
        if not snd:
            return None

        now = time.time()
        last = self.last_played.get(sound_name, 0.0)
        if not loop and (now - last < min_interval):
            return None

        self.last_played[sound_name] = now
        try:
            vol = min(1.0, max(0.0, self.volume * volume_scale))
            player = arcade.play_sound(snd, volume=vol, loop=loop)
            if loop:
                self.looping_players[sound_name] = player
            return player
        except Exception as e:
            return None

    def stop_sound(self, sound_name_or_player):
        """Stop a looping sound or a specific player instance."""
        if sound_name_or_player is None:
            return
        if isinstance(sound_name_or_player, str):
            player = self.looping_players.pop(sound_name_or_player, None)
            if not player:
                player = self.looping_players.pop(sound_name_or_player.lower(), None)
            if not player:
                player = self.looping_players.pop(sound_name_or_player.lower().replace(" ", "_"), None)
            if player:
                try:
                    arcade.stop_sound(player)
                except Exception:
                    pass
        else:
            try:
                arcade.stop_sound(sound_name_or_player)
            except Exception:
                pass
            to_remove = [k for k, p in self.looping_players.items() if p == sound_name_or_player]
            for k in to_remove:
                self.looping_players.pop(k, None)

    def stop_all_loops(self):
        """Stop all currently looping sounds (e.g. ambient rain, music)."""
        for name, player in list(self.looping_players.items()):
            try:
                arcade.stop_sound(player)
            except Exception:
                pass
        self.looping_players.clear()
