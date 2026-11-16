"""S20: Return to the modern dining room and follow the Gear."""
from scenes.scene_13_view import Scene13View


class Scene20View(Scene13View):
    clock_asset = "06_00"
    active_card = "gear"
    wake_line = "Someone entered while I was away. If only I had stayed..."
    card_thoughts = {
        "beast": "I can still hear the whistle hitting the ground.",
        "crown": "The spoon slipped from her hand. I can still hear it.",
    }
    wake_sound = "clock_chime"
    transition_color = (110, 196, 239)

    def next_view(self):
        from scenes.future_integrated_view import FutureLabView

        return FutureLabView()
