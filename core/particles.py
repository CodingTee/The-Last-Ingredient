"""Visual Special Effects and Particle Systems for The Last Ingredient.
Includes realistic steam, fire embers, atmospheric rain, chopping splatters, and holograms.
"""
import math
import random
import arcade
from arcade.types import Color


class GourmetSteamParticle:
    """Photorealistic culinary vapor using soft feathered gaussian radial puffs."""
    def __init__(self, cx, cy, texture=None, spread=16.0, rise_speed=36.0, max_life=2.2):
        self.cx = cx
        self.cy = cy
        self.texture = texture
        self.spread = spread
        self.rise_speed = rise_speed
        self.max_life = max_life
        self.reset()
        self.life = random.uniform(0.1, self.max_life)

    def reset(self):
        self.x = self.cx + random.uniform(-self.spread, self.spread)
        self.y = self.cy + random.uniform(-3, 4)
        self.vx = random.uniform(-4, 4)
        self.vy = self.rise_speed * random.uniform(0.85, 1.35)
        self.start_size = random.uniform(10, 16)
        self.end_size = random.uniform(42, 62)
        self.size = self.start_size
        self.life = self.max_life * random.uniform(0.85, 1.15)
        self.cur_max_life = self.life
        self.wobble_freq = random.uniform(2.0, 3.8)
        self.wobble_phase = random.uniform(0, math.pi * 2)
        self.angle = random.uniform(0, 360)
        self.angular_vel = random.uniform(-25, 25)
        self.max_alpha = random.randint(75, 125)

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.reset()
            return
        progress = 1.0 - (self.life / self.cur_max_life)
        sway = math.sin(progress * math.pi * self.wobble_freq + self.wobble_phase) * 18.0 * dt
        self.x += (self.vx + sway) * dt
        self.y += self.vy * dt
        self.angle += self.angular_vel * dt
        self.size = self.start_size + (self.end_size - self.start_size) * (progress ** 0.75)

    def draw(self):
        if self.life <= 0 or not self.texture:
            return
        progress = 1.0 - (self.life / self.cur_max_life)
        if progress < 0.22:
            alpha = int(self.max_alpha * (progress / 0.22))
        else:
            alpha = int(self.max_alpha * ((1.0 - progress) / 0.78))
        if alpha > 0:
            arcade.draw_texture_rect(
                self.texture,
                arcade.XYWH(self.x, self.y, self.size, self.size),
                color=Color(255, 252, 246, alpha),
                angle=self.angle,
            )


class SteamParticle:
    """Rising aromatic steam from hot noodle broth or boiling soups."""
    def __init__(self, cx, cy, spread=20.0, base_radius=10.0):
        self.cx = cx
        self.cy = cy
        self.spread = spread
        self.base_radius = base_radius
        self.reset()

    def reset(self):
        self.x = self.cx + random.uniform(-self.spread, self.spread)
        self.y = self.cy + random.uniform(-5, 5)
        self.vx = random.uniform(-6, 6)
        self.vy = random.uniform(32, 60)
        self.radius = self.base_radius * random.uniform(0.6, 1.1)
        self.max_life = random.uniform(1.4, 2.2)
        self.life = self.max_life
        self.alpha_peak = random.randint(45, 80)
        self.wobble_freq = random.uniform(2.5, 4.0)
        self.wobble_phase = random.uniform(0, math.pi * 2)

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.reset()
            return

        progress = 1.0 - (self.life / self.max_life)
        # Sinusoidal lateral sway
        sway = math.sin(progress * math.pi * self.wobble_freq + self.wobble_phase) * 18.0 * dt
        self.x += (self.vx + sway) * dt
        self.y += self.vy * dt
        # Expansion as it rises
        self.radius += 10.0 * dt

    def draw(self):
        if self.life <= 0:
            return
        progress = 1.0 - (self.life / self.max_life)
        # Bell curve alpha fade
        alpha = int(self.alpha_peak * math.sin(progress * math.pi))
        color = (245, 240, 230, alpha)
        arcade.draw_circle_filled(self.x, self.y, self.radius, color)


class FireEmber:
    """Sizzling hot ember spark emitted from prehistoric hearth or stove fire."""
    def __init__(self, cx, cy, spread=35.0):
        self.cx = cx
        self.cy = cy
        self.spread = spread
        self.reset()

    def reset(self):
        self.x = self.cx + random.uniform(-self.spread, self.spread)
        self.y = self.cy + random.uniform(-8, 12)
        self.vx = random.uniform(-18, 18)
        self.vy = random.uniform(45, 110)
        self.r = random.uniform(1.8, 4.2)
        self.max_life = random.uniform(0.7, 1.5)
        self.life = self.max_life
        # Color temperature from bright yellow-white to glowing orange-red
        temp = random.random()
        if temp > 0.7:
            self.color = (255, 235, 120)
        elif temp > 0.3:
            self.color = (255, 140, 40)
        else:
            self.color = (235, 70, 30)

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.reset()
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += random.uniform(-10, 10) * dt
        self.r = max(0.5, self.r - 0.8 * dt)

    def draw(self):
        if self.life <= 0:
            return
        fade = self.life / self.max_life
        alpha = int(240 * fade)
        arcade.draw_circle_filled(self.x, self.y, self.r, (*self.color, alpha))


class Raindrop:
    """Wind-swept raindrops with impact splash rings for the stormy modern night."""
    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.reset(random_y=True)

    def reset(self, random_y=False):
        self.x = random.uniform(-50, self.sw + 50)
        self.y = random.uniform(0, self.sh + 50) if random_y else self.sh + random.uniform(5, 30)
        self.speed = random.uniform(650, 950)
        self.length = random.uniform(14, 26)
        self.angle_rad = math.radians(105) # slanted fall
        self.splash_active = False
        self.splash_radius = 1.0
        self.splash_life = 0.0

    def update(self, dt):
        if self.splash_active:
            self.splash_life -= dt
            self.splash_radius += 35.0 * dt
            if self.splash_life <= 0:
                self.reset()
            return

        self.x += math.cos(self.angle_rad) * self.speed * dt
        self.y -= math.sin(self.angle_rad) * self.speed * dt

        if self.y <= 120:  # Hit windowsill/ground
            self.splash_active = True
            self.splash_life = 0.2
            self.splash_radius = 2.0

    def draw(self):
        if self.splash_active:
            alpha = int(140 * (self.splash_life / 0.2))
            arcade.draw_ellipse_outline(self.x, self.y, self.splash_radius * 2, self.splash_radius * 0.8,
                                        (180, 205, 230, alpha), 1)
        else:
            dx = math.cos(self.angle_rad) * self.length
            dy = math.sin(self.angle_rad) * self.length
            arcade.draw_line(self.x, self.y, self.x + dx, self.y - dy, (175, 200, 235, 120), 1.5)


class HoloMote:
    """Floating digital quantum data motes in the future laboratory."""
    def __init__(self, cx, cy, w, h):
        self.cx = cx
        self.cy = cy
        self.w = w
        self.h = h
        self.x = random.uniform(cx - w / 2, cx + w / 2)
        self.y = random.uniform(cy - h / 2, cy + h / 2)
        self.vx = random.uniform(-10, 10)
        self.vy = random.uniform(15, 45)
        self.r = random.uniform(1.5, 3.5)
        self.phase = random.uniform(0, math.pi * 2)

    def update(self, dt, t):
        self.x += (self.vx + math.sin(t * 2.0 + self.phase) * 8.0) * dt
        self.y += self.vy * dt
        if self.y > self.cy + self.h / 2:
            self.y = self.cy - self.h / 2
            self.x = random.uniform(self.cx - self.w / 2, self.cx + self.w / 2)

    def draw(self):
        alpha = int(180 + 70 * math.sin(self.phase))
        arcade.draw_circle_filled(self.x, self.y, self.r, (70, 210, 255, alpha))


class ChopParticle:
    """Slicing burst particles when vegetables or meats are prepared."""
    def __init__(self, x, y, color):
        self.x = x + random.uniform(-6, 6)
        self.y = y + random.uniform(-4, 4)
        angle = random.uniform(0.3, math.pi - 0.3)
        spd = random.uniform(80, 240)
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd
        self.r = random.uniform(2.5, 5.0)
        self.color = color
        self.life = random.uniform(0.4, 0.75)
        self.max_life = self.life

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy -= 420.0 * dt  # Gravity
        self.life -= dt

    def draw(self):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            arcade.draw_circle_filled(self.x, self.y, self.r, (*self.color, alpha))


class FootstepDust:
    """Subtle dust puff generated on character footsteps."""
    def __init__(self, x, y):
        self.x = x + random.uniform(-4, 4)
        self.y = y + random.uniform(-2, 2)
        self.r = random.uniform(3.0, 5.0)
        self.max_life = 0.35
        self.life = self.max_life

    def update(self, dt):
        self.life -= dt
        self.r += 4.0 * dt

    def draw(self):
        if self.life > 0:
            alpha = int(130 * (self.life / self.max_life))
            arcade.draw_circle_filled(self.x, self.y, self.r, (200, 190, 175, alpha))
