from typing import Tuple, Optional

from .const import (
    DEFAULT_BG_COLOR,
    DEFAULT_PATH_COLOR,
    DEFAULT_PATH_WIDTH
)
from .image_helpers import validate_color

class RoombaMapDevice:
    def __init__(
        self,
        blid: str,
        icon_set: str,
        bg_color,
        path_color,
        path_width
    ):
        self.blid = blid
        self.icon_set = icon_set
        self.bg_color = bg_color
        self.path_color = path_color
        self.path_width = path_width

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
        if value <= 0:
            value = DEFAULT_PATH_WIDTH
        self._path_width = value   