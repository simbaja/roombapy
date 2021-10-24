import logging
from typing import Tuple, Optional

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    pass 

from .const import (
    DEFAULT_BG_COLOR,
    DEFAULT_IMG_HEIGHT,
    DEFAULT_IMG_WIDTH,
    DEFAULT_MAP_ANGLE,
    DEFAULT_MAP_MAX_COORDS,
    DEFAULT_MAP_MIN_COORDS,
    DEFAULT_PATH_COLOR,
    DEFAULT_PATH_WIDTH,
    DEFAULT_TEXT_BG_COLOR,
    DEFAULT_TEXT_COLOR
)
from .image_helpers import make_blank_image, validate_color

class RoombaMap:
    _id: str
    _name: str
    _coords_start: Tuple[int,int] = DEFAULT_MAP_MIN_COORDS
    _coords_end: Tuple[int,int] = DEFAULT_MAP_MAX_COORDS
    _angle: float = DEFAULT_MAP_ANGLE
    _floorplan: Image.Image = None
    _walls: Image.Image = None
    _bg_color: Tuple[int,int,int,int] = None
    _path_color: Tuple[int,int,int,int] = None
    _text_color: Tuple[int,int,int,int] = None
    _text_bg_color: Tuple[int,int,int,int] = None
    icon_set: str = None
    device: str = None
    
    def __init__(
        self, 
        id,
        name,
        coords_start: Tuple[int,int] = DEFAULT_MAP_MIN_COORDS,
        coords_end: Tuple[int,int] = DEFAULT_MAP_MAX_COORDS,
        angle: float = DEFAULT_MAP_ANGLE,
        floorplan: str = None,
        walls: str = None,
        icon_set: str = None,
        bg_color = DEFAULT_BG_COLOR,
        path_color = DEFAULT_PATH_COLOR,
        path_width = DEFAULT_PATH_WIDTH,
        text_color = DEFAULT_TEXT_COLOR,
        text_bg_color = DEFAULT_TEXT_BG_COLOR):

        self._log = logging.getLogger(__name__)
        self._id = id
        self._name = name
        self.coords_start = coords_start
        self.coords_end = coords_end
        self.angle = angle
        self.icon_set = icon_set
        self.floorplan = floorplan
        self.walls = walls
        self.bg_color = bg_color
        self.path_color = path_color
        self.path_width = path_width
        self.text_color = text_color
        self.text_bg_color = text_bg_color

    @property
    def id(self) -> str:
        return self._id  

    @property
    def name(self) -> str:
        return self._name

    @property
    def coords_start(self) -> Tuple[int,int]:
        return self._coords_start
    
    @coords_start.setter
    def coords_start(self, value):
        self._coords_start = self._validate_coords(value, self._coords_start or DEFAULT_MAP_MIN_COORDS)

    @property
    def coords_end(self) -> Tuple[int,int]:
        return self._coords_end
    
    @coords_end.setter
    def coords_end(self, value):
        self._coords_end = self._validate_coords(value, self._coords_end or DEFAULT_MAP_MAX_COORDS)

    @property
    def angle(self) -> float:
        return self._angle
    
    @angle.setter
    def angle(self, value):
        self._angle = self._validate_angle(value, self._angle or DEFAULT_MAP_ANGLE)        

    @property
    def floorplan(self) -> Image.Image:
        return self._floorplan
    
    @floorplan.setter
    def floorplan(self, value):
        self._floorplan = self._set_image(value)
        if not self._floorplan:
            self._floorplan = make_blank_image(DEFAULT_IMG_WIDTH, DEFAULT_IMG_HEIGHT)

    @property
    def walls(self) -> Image.Image:
        return self._walls
    
    @walls.setter
    def walls(self, value):
        self._walls = self._set_image(value)        

    @property
    def bg_color(self) -> Tuple[int,int,int,int]:
        return self._bg_color
    
    @bg_color.setter
    def bg_color(self, value):
        self._bg_color = validate_color(value, self._bg_color or DEFAULT_BG_COLOR)
    
    @property
    def path_color(self) -> Tuple[int,int,int,int]:
        return self._path_color
    
    @path_color.setter
    def path_color(self, value):        
        self._path_color = validate_color(value, self._path_color or DEFAULT_PATH_COLOR)

    @property
    def path_width(self) -> int:
        return self._path_width
    
    @path_width.setter
    def path_width(self, value: Optional[int]) -> int:
        if value == None:
            return
        self._path_width = value

    @property
    def text_color(self) -> Tuple[int,int,int,int]:
        return self._text_color
    
    @text_color.setter
    def text_color(self, value):
        self._text_color = validate_color(value, self._text_color or DEFAULT_TEXT_COLOR)

    @property
    def text_bg_color(self) -> Tuple[int,int,int,int]:
        return self._text_bg_color      
    
    @text_bg_color.setter
    def text_bg_color(self, value):
        self._text_bg_color = validate_color(value, self._text_bg_color or DEFAULT_TEXT_BG_COLOR)

    @property
    def img_width(self) -> int:
        if self.floorplan:
            x, _ = self.floorplan.size
            return x
        else:
            return DEFAULT_IMG_WIDTH
    
    @property
    def img_height(self) -> int:
        if self.floorplan:
            _, y = self.floorplan.size
            return y
        else:
            return DEFAULT_IMG_HEIGHT

    def _set_image(self, value):
        if value is None:
            return None   
        if isinstance(value, str):
            return Image.open(value).convert('RGBA')
        elif isinstance(value, Image.Image):
            return value
        else:
            self._log.warning(f'Could not load image from {value}')
            return None      

    def _validate_coords(self, value, default) -> Tuple[int,int]:
        if value is None:
            return default
        if not isinstance(value, tuple):
            return default
        if len(value) != 2:
            return default
        return value

    def _validate_angle(self, value, default) -> float:
        if value is None:
            return default
        try:
            v = float(value)
            v %= 360
            if v < 0:
                v += 360
            return v
        except:
            return default