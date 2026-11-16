"""Distance grading for B03 sprites; original alpha/masks remain unchanged."""
import math
import arcade
from PIL import Image, ImageEnhance, ImageFilter


def distance_texture(source, *, scoped=False, far=False):
    """Compress cream highlights and blend green air into the RGB channels.

    Preserve alpha exactly so graded art has the same occlusion and hit mask.
    The scope resolves more surface detail without removing atmospheric haze.
    """
    image=source.image.convert('RGBA')
    alpha=image.getchannel('A')
    rgb=image.convert('RGB')
    rgb=ImageEnhance.Color(rgb).enhance(.58 if scoped else .40)
    rgb=ImageEnhance.Contrast(rgb).enhance(.79 if scoped else .65)
    rgb=ImageEnhance.Brightness(rgb).enhance(.82 if scoped else .76)
    mist=.15 if scoped else (.26 if far else .22)
    rgb=Image.blend(rgb,Image.new('RGB',rgb.size,(78,105,83)),mist)
    rgb=rgb.filter(ImageFilter.GaussianBlur(.18 if scoped else .5))
    rgb.putalpha(alpha)
    return arcade.Texture(rgb)


def forest_shade(x,y,trees):
    """Soft projected crown shadows near trees, bounded to avoid black art."""
    darkness=0.
    for tree in trees:
        # Ground shadows extend slightly upslope and right of the trunk.
        dx=(x-tree.x-24)/max(35,tree.width*.55)
        dy=(y-tree.foot_y-70)/max(35,tree.height*.23)
        darkness=max(darkness,math.exp(-1.6*(dx*dx+dy*dy)))
    return darkness


def shade_color(amount):
    amount=max(0.,min(1.,amount))
    return arcade.types.Color(255-int(42*amount),255-int(35*amount),255-int(45*amount),255)
