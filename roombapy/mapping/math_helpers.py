import math
from typing import Tuple

def clamp(num, min_value, max_value):
   return max(min(num, max_value), min_value)

def interpolate(value, in_range, out_range) -> float:
    
    #handle inverted ranges
    invert = False
    if in_range[0] > in_range[1]:
        in_range = in_range[1], in_range[0]
        invert = not invert
    if out_range[0] > out_range[1]:
        in_range = out_range[1], out_range[0]
        invert = not invert

    #make sure it's in the range
    value = clamp(value, in_range[0], in_range[1])

    out = float(value - in_range[0]) / float(in_range[1] - in_range[0]) * float(out_range[1] - out_range[0])
    if invert:
        out = float(out_range[1]) - out

    return out

def rotate(x, y, angle, invert_x: bool = False, invert_y: bool = False) -> Tuple[float,float]:
    xx = x*math.cos(math.radians(angle)) - \
         y*math.sin(math.radians(angle))
    yy = x*math.sin(math.radians(angle)) + \
         y*math.cos(math.radians(angle))    
    
    if invert_x:
        xx = x - (xx - x)
    if invert_y:
        yy = y - (yy - y)
    return xx, yy
