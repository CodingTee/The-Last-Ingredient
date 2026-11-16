"""Uniform canvas scaling and pixel-preserving background crops for Royal chapter."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Canvas:
    """Cover the window uniformly, with a centered crop and matching input transform."""
    width: int
    height: int
    logical_width: int = 1440
    logical_height: int = 900

    @property
    def scale(self):
        return max(self.width / self.logical_width, self.height / self.logical_height)

    @property
    def viewport(self):
        w, h = self.logical_width * self.scale, self.logical_height * self.scale
        return ((self.width - w) / 2, (self.height - h) / 2, w, h)

    def unproject(self, x, y):
        left, bottom, _, _ = self.viewport
        return ((x - left) / self.scale, (y - bottom) / self.scale)


def centered_crop(width, height, ratio):
    """Integer crop only: never resample or distort the original pixels."""
    if width / height > ratio:
        w, h = int(height * ratio), height
    else:
        w, h = width, int(width / ratio)
    return ((width - w) // 2, (height - h) // 2, w, h)


@dataclass(frozen=True)
class MapCanvas:
    """Full-window world with one uniform scale and centered cropping."""
    width: int
    height: int

    @property
    def scale(self):
        return max(self.width / 1440, self.height / 900)

    @property
    def view_width(self):
        return self.width / self.scale

    @property
    def view_height(self):
        return self.height / self.scale

    @property
    def crop_rect(self):
        return centered_crop(1440, 900, self.width / self.height)

    def unproject(self, x, y):
        cx, cy, _, _ = self.crop_rect
        return (cx + x / self.scale, cy + y / self.scale)
