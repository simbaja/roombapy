from typing import Tuple
from .math_helpers import clamp

try:
    from PIL import Image, ImageDraw, ImageFont, ImageColor
    HAVE_PIL = True
except ImportError:
    pass

transparent = (0, 0, 0, 0)  #transparent color

def make_blank_image(width, height, color=transparent) -> Image.Image:
    return Image.new('RGBA',(width,height), color)

def transparent_paste(base_image: Image.Image, overlay_image: Image.Image, position: Tuple = None):
    '''
    needed because PIL pasting of transparent images gives weird results
    '''
    image = make_blank_image(base_image.size[0],base_image.size[1])
    image.paste(overlay_image,position)
    base_image = Image.alpha_composite(base_image, image)
    return base_image

def center_image(ox: int, oy: int, image: Image.Image, bounds: Tuple[int,int]) -> Tuple[int,int]:
    xx, yy = (ox - image.size[0] // 2, oy - image.size[1] // 2)
    if bounds:
        xx = clamp(xx, 0, bounds[0])
        yy = clamp(yy, 0, bounds[1])
        
    return (xx, yy)
            
def validate_color(color, default) -> Tuple[int,int,int,int]:      
    try:
        return ImageColor.getcolor(color,"RGBA")
    except:
        return default
