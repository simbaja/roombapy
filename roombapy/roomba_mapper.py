import io
import math
import logging
import os
import time
from typing import TYPE_CHECKING, NamedTuple, Tuple
import textwrap

if TYPE_CHECKING:
    from .roomba import Roomba

from roombapy.const import (
    DEFAULT_BG_COLOR,
    DEFAULT_ICON_BATTERY,
    DEFAULT_ICON_BIN_FULL,
    DEFAULT_ICON_CANCELLED,
    DEFAULT_ICON_CHARGING,
    DEFAULT_ICON_ERROR,
    DEFAULT_ICON_HOME,
    DEFAULT_ICON_PATH,
    DEFAULT_ICON_ROOMBA,
    DEFAULT_ICON_SIZE,
    DEFAULT_ICON_TANK_LOW,
    DEFAULT_IMG_HEIGHT,
    DEFAULT_IMG_WIDTH,
    DEFAULT_MAP_MAX_ALLOWED_DISTANCE,
    DEFAULT_PATH_COLOR,
    DEFAULT_PATH_WIDTH,
    DEFAULT_TEXT_BG_COLOR,
    DEFAULT_TEXT_COLOR, 
    ROOMBA_STATES, 
    DEFAULT_MAP_SKIP_POINTS
)

# Import trickery
global HAVE_PIL
HAVE_PIL = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageColor
    HAVE_PIL = True
except ImportError:
    print("PIL module not found, maps are disabled")

def _get_mapper_asset(path: str, resource: str):
    if path.startswith("{PKG}"):
        return os.path.normpath(os.path.join(os.path.dirname(__file__), path.replace("{PKG}","."), resource))
    else:
        return os.path.normpath(os.path.join(path, resource))
        
transparent = (0, 0, 0, 0)  #transparent color

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

class RoombaIconSet:
    def __init__(self, 
        size: Tuple[int,int] = (50,50), 
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
        self._load_icon_file("roomba", _get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_ROOMBA))
        self._load_icon_file("error", _get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_ERROR))
        self._load_icon_file("cancelled", _get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_CANCELLED))
        self._load_icon_file("battery-low", _get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_BATTERY))
        self._load_icon_file("charging", _get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_CHARGING))
        self._load_icon_file("bin-full", _get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_BIN_FULL))
        self._load_icon_file("tank-low", _get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_TANK_LOW))
        self._load_icon_file("home", _get_mapper_asset(DEFAULT_ICON_PATH, DEFAULT_ICON_HOME))

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

class RoombaPosition(NamedTuple):
    x: int
    y: int
    theta: int

class RoombaMap:
    id: str
    name: str
    coords_start: Tuple[int,int] = (-1000,-1000)
    coords_end: Tuple[int,int] = (1000,1000)
    angle: float = 0.0
    floorplan: Image.Image = None
    walls: Image.Image = None
    icon_set: str = None

    def __init__(
        self, 
        id,
        name,
        coords_start: Tuple[int,int] = (-1000,-1000),
        coords_end: Tuple[int,int] = (1000,1000),
        angle: float = 0,
        floorplan: str = None,
        walls: str = None,
        icon_set: str = None):

        self.log = logging.getLogger(__name__)
        self.id = id,
        self.name = name,
        self.coords_start = coords_start
        self.coords_end = coords_end
        self.angle = angle
        self.icon_set = icon_set
        
        if floorplan:
            try:
                self.floorplan = Image.open(floorplan).convert('RGBA')
            except:
                self.log.warning(f'Could not load floorplan from {floorplan}')
        if walls:
            try:
                self.walls = Image.open(walls).convert('RGBA')
            except:
                self.log.warning(f'Could not load walls from {floorplan}')

        if not self.floorplan:
            self.floorplan = make_blank_image(DEFAULT_IMG_WIDTH, DEFAULT_IMG_HEIGHT)

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

class RoombaMapper:
    def __init__(self, 
        roomba: 'Roomba', 
        font: ImageFont.ImageFont = None,
        bg_color = DEFAULT_BG_COLOR,
        path_color = DEFAULT_PATH_COLOR,
        path_width = DEFAULT_PATH_WIDTH,
        text_color = DEFAULT_TEXT_COLOR,
        text_bg_color = DEFAULT_TEXT_BG_COLOR,
        assets_path = "{PKG}/assets"
    ):
        self.log = logging.getLogger(__name__)
        self.roomba = roomba
        self.map_enabled = False
        self.bg_color = bg_color
        self.path_color = path_color
        self.text_color = text_color
        self.text_bg_color = text_bg_color
        self.path_width = path_width
        self.assets_path = assets_path

        #initialize the font
        self.font = font
        if self.font is None:
            try:
                self.font = ImageFont.truetype(_get_mapper_asset(assets_path, "monaco.ttf"), 40)
            except IOError as e:
                self.log.warning(f"Error loading font, loading default font")
                self.font = ImageFont.load_default()

        #generate the default icons
        self._icons: dict[str,RoombaIconSet] = {}
        self.add_icon_set("default"),
        self.add_icon_set("m", roomba_icon="m6_icon.png")
        self.add_icon_set("j", roomba_icon="j7_icon.png")
        self.add_icon_set("s", roomba_icon="s9_icon.png")

        #mapping variables
        self._map: RoombaMap = None
        self._rendered_map: bytes = None
        self._points_to_skip = DEFAULT_MAP_SKIP_POINTS
        self._points_skipped = 0
        self._max_distance = DEFAULT_MAP_MAX_ALLOWED_DISTANCE
        self._history = []
        self._history_translated: list[RoombaPosition] = []

    @property
    def roomba_image_pos(self) -> RoombaPosition:       
        try:
            return self._history_translated[-1]
        except:
            return RoombaPosition(0,0,0)
    
    @property
    def origin_image_pos(self) -> RoombaPosition:
        return self._map_coord_to_image_coord(self.roomba.zero_coords())

    @property
    def min_coords(self) -> Tuple[int,int]:
        if len(self._history) > 0:
            return min(self._history)[0], min(self._history)[1]
        else:
            return (0,0)

    @property
    def max_coords(self) -> Tuple[int,int]:
        if len(self._history) > 0:
            return max(self._history)[0], max(self._history)[1]
        else:
            return (0,0)          

    @property
    def rendered_map(self) -> bytes:
        return self._rendered_map

    @property
    def bg_color(self) -> Tuple[int,int,int,int]:
        return self._bg_color
    
    @bg_color.setter
    def bg_color(self, value):
        self._bg_color = validate_color(value, DEFAULT_BG_COLOR)
    
    @property
    def path_color(self) -> Tuple[int,int,int,int]:
        return self._path_color
    
    @path_color.setter
    def path_color(self, value):
        self._path_color = validate_color(value, DEFAULT_PATH_COLOR)

    @property
    def text_color(self) -> Tuple[int,int,int,int]:
        return self._text_color
    
    @text_color.setter
    def text_color(self, value):
        self._text_color = validate_color(value, DEFAULT_TEXT_COLOR)

    @property
    def text_bg_color(self) -> Tuple[int,int,int,int]:
        return self._text_bg_color      
    
    @text_bg_color.setter
    def text_bg_color(self, value):
        self._text_bg_color = validate_color(value, DEFAULT_TEXT_BG_COLOR)

    def add_icon_set(self,
        name: str,
        icon_path: str = "{PKG}/assets",                    
        home_icon = None,
        roomba_icon = None,
        error_icon = None,
        cancelled_icon = None,
        battery_low_icon = None,
        charging_icon = None,
        bin_full_icon = None,
        tank_low_icon = None,
        icon_size = DEFAULT_ICON_SIZE,
        show_direction = True
    ):
        if not name:
            self.log.error("Icon sets must have names")
            return

        i = RoombaIconSet(size=icon_size, show_direction=show_direction, log=self.log)

        if roomba_icon:
            i.roomba = self._get_mapper_asset(icon_path, roomba_icon)
        if error_icon:
            i.error = self._get_mapper_asset(icon_path, error_icon)
        if cancelled_icon:
            i.cancelled = self._get_mapper_asset(icon_path, cancelled_icon)
        if battery_low_icon:
            i.battery_low = self._get_mapper_asset(icon_path, battery_low_icon)
        if charging_icon:
            i.charging = self._get_mapper_asset(icon_path, charging_icon)
        if bin_full_icon:
            i.bin_full = self._get_mapper_asset(icon_path, bin_full_icon)
        if tank_low_icon:
            i.tank_low = self._get_mapper_asset(icon_path, tank_low_icon)
        if home_icon:
            i.home = self._get_mapper_asset(icon_path, home_icon)

        self._icons[name] = i

    def _get_mapper_asset(self, icon_path: str, icon):
        if isinstance(icon, str):
            return _get_mapper_asset(icon_path, icon)
        if isinstance(icon, Image.Image):
            return icon
        else:
            return None

    def reset_map(self, map: RoombaMap, points_to_skip: int = DEFAULT_MAP_SKIP_POINTS):
        self.map_enabled = self.roomba.cap.get("pose", False) and HAVE_PIL        
        self._history = []
        self._history_translated = []
        self._map = map
        self._points_to_skip = points_to_skip
        self._points_skipped = 0

    def update_map(self, force_redraw = False):
        """Updates the cleaning map"""

        #if mapping not enabled, nothing to update
        if not self.map_enabled:
            return

        if self.roomba.timer_active('update_after_completed') and not force_redraw:
            self.log.info('MAP [Update]: Skipping (mission complete), resume in {}s'
                .format(self.roomba.timer_duration('update_after_completed')))
            return

        if (self.roomba.changed('pose') or self.roomba.changed('phase') or 
            force_redraw) and self.map_enabled:

            #make sure we have phase info before trying to render
            if self.roomba.current_state is not None:
                self._update_state()
                self._render_map()

    def _update_state(self):
        position: dict[str,int] = None

        if self.roomba.changed('pose'):
            position = self.roomba.co_ords
        
        self.log.debug(f"MAP [State Update]: co-ords: {self.roomba.co_ords} \
                        phase: {self.roomba.phase}, \
                        state: {self.roomba.current_state}")

        if self.roomba.current_state == ROOMBA_STATES["charge"]:
            position = None
        elif self.roomba.current_state == ROOMBA_STATES["evac"]:
            position = None     
        elif self.roomba.current_state == ROOMBA_STATES["completed"]:
            self.log.info("MAP [State Update]: Mission Complete")  
        elif self.roomba.current_state == ROOMBA_STATES["run"]:            
            if self.roomba.co_ords == self.roomba.zero_coords(theta=0):
                #bogus pose received, can't have 0,0,0 when running, usually happens after recovering from an error condition
                self.log.warning('MAP [State Update]: received 0,0,0 pose when running - ignoring')
                position = None

        #if we have a position update, append to the history if it meets our criteria
        if position:
            #there's a few points at the beginning that are usually erroneous, skip them
            if self._points_skipped < self._points_to_skip:
                self._points_skipped += 1
                return

            #if we have history, we need to check a couple things
            if len(self._history) > 0:
                old = self._history[-1]
                old_x = old["x"]
                old_y = old["y"]
                new_x = position["x"]
                new_y = position["y"]

                #if we didn't actually move from the last recorded position, ignore it
                if (old_x,old_y) == (new_x,new_y):
                    return

                #at times, roomba reports erroneous points, ignore if too large of a gap
                #between measurements
                if self._map_distance((old_x,old_y),(new_x,new_y)) > self._max_distance:
                    return

            self._history.append(position)
            self._history_translated.append(self._map_coord_to_image_coord(position))

    def _map_coord_to_image_coord(self, coord: dict) -> RoombaPosition:
        x: float = float(coord["x"])
        y: float = float(coord["y"])
        theta: float = float(coord["theta"])
        
        #perform rotation: occurs about the map origin, so should
        #undo any rotation that exists
        x, y = rotate(x, y, self._map.angle,
            invert_x = self._map.coords_start[0] > self._map.coords_end[0],
            invert_y = self._map.coords_start[1] < self._map.coords_end[1]
        )

        #interpolate the x,y coordinates to scale to the appropriate output
        img_x = interpolate(
            x, 
            [self._map.coords_start[0], self._map.coords_end[0]],
            [0, self._map.img_width - 1]
        )
        img_y = interpolate(
            y, 
            [self._map.coords_start[1], self._map.coords_end[1]],
            [0, self._map.img_height - 1]
        )

        #make sure we stay within the bounds
        clamp(img_x, 0, self._map.img_width)
        clamp(img_y, 0, self._map.img_height)
        
        #adjust theta
        #from what I can see, it looks like the roomba uses a coordinate system:
        #0 = facing the dock, increasing angle clockwise
        #it looks like past 180, the roomba uses negative angles, but still seems
        #to be in the clockwise direction
        #PIL denotes angles in the counterclockwise direction
        #so, to compute the right angle, we need to:
        #1) add the map angle (clockwise)
        #2) add theta
        #3) mod 360, add 360 if negative
        #4) convert to counter-clockwise 360-x
        img_theta = (self._map.angle + 
            theta) % 360
        if img_theta < 0:
            img_theta += 360        
        img_theta = 360 - img_theta
        
        #return the tuple
        return RoombaPosition(int(img_x), int(img_y), int(img_theta))

    def _render_map(self):
        """Renders the map"""

        #generate the base on which other layers will be composed
        base = self._map_blank_image(color=self.bg_color)

        #add the floorplan if available
        if self._map.floorplan:
            base = Image.alpha_composite(base, self._map.floorplan)

        #draw in the vacuum path
        base = self._draw_vacuum_path(base)

        #draw in the map walls (to hide overspray)
        if self._map.walls:
            base = Image.alpha_composite(base, self._map.walls)

        #draw the roomba and any problems
        base = self._draw_roomba(base)

        #finally, draw the text
        base = self._draw_text(base)

        #save the internal image
        with io.BytesIO() as stream:
            base.save(stream, format="PNG")
            self._rendered_map = stream.getvalue()

        try:
            base.save('c:\\temp\\map.png',"PNG")
        except:
            pass
        #call event handlers
        
    def _map_blank_image(self, color=transparent) -> Image.Image:
        return make_blank_image(self._map.img_width,self._map.img_height,color)

    def _draw_vacuum_path(self, base: Image.Image) -> Image.Image:
        if len(self._history_translated) > 1:        
            layer = self._map_blank_image()
            renderer = ImageDraw.Draw(layer)

            renderer.line(
                list(map(lambda p: (p.x,p.y), self._history_translated)),
                fill=self.path_color,
                width=self.path_width,
                joint="curve"
            )

            return Image.alpha_composite(base, layer)
        else:
            return base

    def _get_icon_set(self):
        #get the default (should always exist)
        icon_set = self._icons["default"]

        #attempt to get the series specific set
        series = self._icons.get(self.roomba.sku[0],None)            
        if series:
            icon_set = series

        #override with the map set if needed
        if self._map.icon_set:
            try:
                icon_set = self._icons[self._map.icon_set]
            except:
                self.log.warn(f"Could not load icon set '{self._map.icon_set}' for map.")

        return icon_set

    def _draw_roomba(self, base: Image.Image) -> Image.Image:
        layer = self._map_blank_image()

        #get the image coordinates of the roomba
        x, y, theta = self.roomba_image_pos

        #get the icon set to use
        icon_set = self._get_icon_set()

        #add in the roomba icon
        rotated = icon_set.roomba.rotate(theta, expand=True)
        layer.paste(rotated, center_image(x, y, rotated, layer.size))

        #add the dock
        dock = self._map_blank_image()
        dock.paste(
            icon_set.home,
            center_image(
                self.origin_image_pos.x, 
                self.origin_image_pos.y, 
                icon_set.home, layer.size
            )
        )

        layer = Image.alpha_composite(layer, dock)

        #add the problem icon (pick one in a priority order)
        problem_icon = None
        if self.roomba._flags.get('stuck'):
            problem_icon = icon_set.error
        elif self.roomba._flags.get('cancelled'):
            problem_icon = icon_set.cancelled
        elif self.roomba._flags.get('bin_full'):
            problem_icon = icon_set.bin_full
        elif self.roomba._flags.get('battery_low'):
            problem_icon = icon_set.battery_low
        elif self.roomba._flags.get('tank_low'):
            problem_icon = icon_set.tank_low

        if problem_icon:
            problem = self._map_blank_image()
            problem.paste(
                problem_icon,
                center_image(x, y, problem_icon, layer.size)             
            )
            layer = Image.alpha_composite(layer, problem)

        return Image.alpha_composite(base, layer)

    def _draw_text(self, base: Image.Image) -> Image.Image:
        margin = 10

        layer = self._map_blank_image()
        state, attributes, time = self._get_display_text()
        renderer = ImageDraw.Draw(layer)

        #consider something like pynter, perhaps would look better

        combined_text = state.upper()
        if attributes:
            max_len = (base.size[0]-2*margin)//(self.font.getsize(attributes)[0]//len(attributes))
            attributes = textwrap.fill(attributes, max_len)
            combined_text = combined_text + "\n" + attributes
        if time:
            combined_text = combined_text + "\n" + "Time: " + time            
        
        #get the bounding box
        bbox = renderer.multiline_textbbox((margin,margin), combined_text, self.font)
        bbox = (bbox[0]-margin,bbox[1]-margin,bbox[2]+margin,bbox[3]+margin)

        #render a background box
        renderer.rectangle(bbox, fill=self.text_bg_color)

        #render the text
        renderer.multiline_text((margin,margin), combined_text, fill=self.text_color, font=self.font)

        return Image.alpha_composite(base, layer)

    def _get_display_text(self) -> Tuple[str,str,str]:
        display_state: str = None
        display_attributes: str = None
        display_time: str = None
        show_time: bool = False

        if  self.roomba.current_state == ROOMBA_STATES["charge"]:
            display_state = "Charging"
            display_attributes = f"Battery: {self.roomba.batPct}%"
        elif self.roomba.current_state == ROOMBA_STATES["recharge"]:
            display_state = "Recharging"
            display_attributes = f"Time: {self.roomba.rechrgM}m, \
                             Bat: {self.roomba.batPct}%"
        elif self.roomba.current_state == ROOMBA_STATES["pause"]:
            display_state = "Paused"
            display_attributes = f"{self.roomba.mssnM}m, \
                             Bat: {self.roomba.batPct}%"
        elif self.roomba.current_state == ROOMBA_STATES["hmPostMsn"]:
            display_state = "Returning Home"
            show_time = True
        elif self.roomba.current_state == ROOMBA_STATES["evac"]:
            display_state = "Emptying Bin"
        elif self.roomba.current_state == ROOMBA_STATES["completed"]:
            display_state = "Completed"
            show_time = True            
        elif self.roomba.current_state == ROOMBA_STATES["run"]:
            display_state = "Running"
            display_attributes = f"Time {self.roomba.mssnM}m, Bat: {self.roomba.batPct}%"
        elif self.roomba.current_state == ROOMBA_STATES["stop"]:
            display_state = "Stopped"
            display_attributes = f"Time {self.roomba.mssnM}m, Bat: {self.roomba.batPct}%"
        elif self.roomba.current_state == ROOMBA_STATES["new"]:
            display_state = "Starting"
        elif self.roomba.current_state == ROOMBA_STATES["stuck"]:
            expire = self.roomba.expireM
            expire_text = 'Job Cancel in {expire}m' if expire else 'Job Cancelled'
            display_state = "Stuck"
            display_attributes = f"{self.roomba.error_message} {expire_text}"
            show_time = True
        elif self.roomba.current_state == ROOMBA_STATES["cancelled"]:
            display_state = "Cancelled"
            show_time = True
        elif self.roomba.current_state == ROOMBA_STATES["hmMidMsn"]:
            display_state = "Docking"
            if not self.roomba.timer_active('ignore_run'):
                display_attributes = f"Bat: {self.roomba.batPct}%, Bin Full: {self.roomba.bin_full}"
        elif self.roomba.current_state == ROOMBA_STATES["hmUsrDock"]:
            display_state = "User Docking"
            show_time = True
        else:
            display_state = self.roomba.current_state
        
        if show_time:
            display_time = time.strftime("%a %b %d %H:%M:%S")

        return display_state, display_attributes, display_time    

    def _map_distance(self, pos1: 'Tuple[int,int]', pos2: 'Tuple[int,int]'):
        return int(math.sqrt(((pos2[0]-pos1[0])**2)+((pos2[1]-pos1[1])**2)))  

    def _interpolate_path_color(f_co, t_co, interval):
        det_co =[(t - f) / interval for f , t in zip(f_co, t_co)]
        for i in range(interval):
            yield [round(f + det * i) for f, det in zip(f_co, det_co)]  