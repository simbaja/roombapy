import logging
from typing import Tuple

try:
    from PIL import Image, ImageDraw, ImageFont, ImageColor
    HAVE_PIL = True
except ImportError:
    pass 

from .const import (
    DEFAULT_ICON_BATTERY,
    DEFAULT_ICON_BIN_FULL,
    DEFAULT_ICON_CANCELLED,
    DEFAULT_ICON_CHARGING,
    DEFAULT_ICON_ERROR,
    DEFAULT_ICON_HOME,
    DEFAULT_ICON_PATH,
    DEFAULT_ICON_ROOMBA,
    DEFAULT_ICON_SIZE,
    DEFAULT_ICON_TANK_LOW
)
from .misc_helpers import get_mapper_asset

class RoombaIconSet:
    def __init__(self, 
        size: Tuple[int,int] = DEFAULT_ICON_SIZE, 
        show_direction: bool = True,
        log: logging.Logger = None):

        if log:
            self._log = log
        else:
            self._log = logging.getLogger(f"Roomba.{__name__}")
        
        self.size = size
        self.show_direction = show_direction
        self._icons: dict[str,Image.Image] = {}
        self._load_defaults()

    @property
    def roomba(self) -> Image.Image:
        return self._icons["roomba"]
    
    @roomba.setter
    def roomba(self, value):
        self._set_icon("roomba", value)

    @property
    def error(self) -> Image.Image:
        return self._icons["error"]
    
    @error.setter
    def error(self, value):
        self._set_icon("error", value)
    
    @property
    def cancelled(self) -> Image.Image:
        return self._icons["cancelled"]
    
    @cancelled.setter
    def cancelled(self, value):
        self._set_icon("cancelled", value)

    @property
    def battery_low(self) -> Image.Image:
        return self._icons["battery-low"]
    
    @battery_low.setter
    def battery_low(self, value):
        self._set_icon("battery-low", value)

    @property
    def charging(self) -> Image.Image:
        return self._icons["charging"]
    
    @charging.setter
    def charging(self, value):
        self._set_icon("charging", value)

    @property
    def bin_full(self) -> Image.Image:
        return self._icons["bin-full"]
    
    @bin_full.setter
    def bin_full(self, value):
        self._set_icon("bin-full", value)

    @property
    def tank_low(self) -> Image.Image:
        return self._icons["tank-low"]
    
    @tank_low.setter
    def tank_low(self, value):
        self._set_icon("tank-low", value)

    @property
    def home(self) -> Image.Image:
        return self._icons["home"]
    
    @home.setter
    def home(self, value):
        self._set_icon("home", value)

    def _load_defaults(self):
        self._load_icon_file("roomba", get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_ROOMBA))
        self._load_icon_file("error", get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_ERROR))
        self._load_icon_file("cancelled", get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_CANCELLED))
        self._load_icon_file("battery-low", get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_BATTERY))
        self._load_icon_file("charging", get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_CHARGING))
        self._load_icon_file("bin-full", get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_BIN_FULL))
        self._load_icon_file("tank-low", get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_TANK_LOW))
        self._load_icon_file("home", get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_HOME))

    def _set_icon(self, name, value):
        if value is None:
            return    
        if isinstance(value, str):
            self._load_icon_file(name, value)
            self._draw_direction(name)
        elif isinstance(value, Image.Image):
            resized = value.convert('RGBA').resize(self.size,Image.ANTIALIAS)
            self._icons[name] = resized
            self._draw_direction(name)
        else:
            raise ValueError()

    def _load_icon_file(self, name, filename, size=None):
        try:
            if not size:
                size = self.size
            icon = Image.open(filename).convert('RGBA').resize(
                size,Image.ANTIALIAS)
                    
            self._icons[name] = icon
        except IOError as e:
            self._log.warning(f'Error loading icon file: {filename}: {e}')

    def _draw_direction(self, name):
        icon = self._icons[name]
        if name == "roomba" and self.show_direction:
            draw_icon = ImageDraw.Draw(icon)
            draw_icon.pieslice([(5,5),(icon.size[0]-5,icon.size[1]-5)],
                265, 275, fill="red", outline="red")