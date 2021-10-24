import io
import math
import logging
import os
import time
from typing import TYPE_CHECKING, NamedTuple, Tuple
import textwrap

# Import trickery
global HAVE_PIL
HAVE_PIL = False

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PIL = True
except ImportError:
    print("PIL module not found, maps are disabled")

if TYPE_CHECKING:
    from ..roomba import Roomba

from ..const import ROOMBA_STATES
from .const import (
    DEFAULT_BG_COLOR,
    DEFAULT_ICON_SIZE,
    DEFAULT_MAP_MAX_ALLOWED_DISTANCE,
    DEFAULT_MAP_SKIP_POINTS,
    DEFAULT_PATH_COLOR,
    DEFAULT_PATH_WIDTH
)
from .math_helpers import clamp, rotate, interpolate
from .image_helpers import transparent, make_blank_image, center_image
from .misc_helpers import get_mapper_asset
from .roomba_icon_set import RoombaIconSet
from .roomba_map_device import RoombaMapDevice
from .roomba_map import RoombaMap

class RoombaPosition(NamedTuple):
    x: int
    y: int
    theta: int

class MapRenderParameters(NamedTuple):
    icon_set: str
    device: str
    bg_color: Tuple[int,int,int,int]
    path_color: Tuple[int,int,int,int]
    path_width: int
    
class RoombaMapper:
    def __init__(self, 
        roomba: 'Roomba', 
        font: ImageFont.ImageFont = None,

        assets_path = "{PKG}/assets"
    ):
        self.log = logging.getLogger(__name__)
        self.roomba = roomba
        self.map_enabled = False
        self.assets_path = assets_path

        #initialize the font
        self.font = font
        if self.font is None:
            try:
                self.font = ImageFont.truetype(get_mapper_asset(assets_path, "monaco.ttf"), 30)
            except Exception as e:
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
        self._device: RoombaMapDevice = None
        self._render_params: MapRenderParameters = None
        self._rendered_map: Image.Image = None
        self._base_rendered_map: Image.Image = None
        self._points_to_skip = DEFAULT_MAP_SKIP_POINTS
        self._points_skipped = 0
        self._max_distance = DEFAULT_MAP_MAX_ALLOWED_DISTANCE
        self._history = []
        self._history_translated: list[RoombaPosition] = []

        #initialize a base map
        self._initialize_map()

    @property
    def roomba_image_pos(self) -> RoombaPosition:       
        try:
            #roomba sometimes doesn't show the right coords when docked,
            #override the coordinates just in case
            if self.roomba.docked:
                return self._map_coord_to_image_coord(self.roomba.zero_coords())
            return self._history_translated[-1]
        except:
            return RoombaPosition(None,None,None)
    
    @property
    def origin_image_pos(self) -> RoombaPosition:
        return self._map_coord_to_image_coord(self.roomba.zero_coords())

    @property
    def min_coords(self) -> Tuple[int,int]:

        if len(self._history) > 0:
            return (
                min(list(map(lambda p: p["x"], self._history))), 
                min(list(map(lambda p: p["y"], self._history)))
            )
        else:
            return (0,0)

    @property
    def max_coords(self) -> Tuple[int,int]:
        if len(self._history) > 0:
            return (
                max(list(map(lambda p: p["x"], self._history))), 
                max(list(map(lambda p: p["y"], self._history)))
            )
        else:
            return (0,0)          

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

    def add_map_device(self, name: str, device: RoombaMapDevice):
        if not name:
            self.log.error("Devices must have names")
            return

        self._devices[name] = device

    def _get_mapper_asset(self, icon_path: str, icon):
        if isinstance(icon, str):
            return get_mapper_asset(icon_path, icon)
        if isinstance(icon, Image.Image):
            return icon
        else:
            return None

    def reset_map(self, map: RoombaMap, device: RoombaMapDevice = None, points_to_skip: int = DEFAULT_MAP_SKIP_POINTS):
        self.map_enabled = self.roomba.cap.get("pose", False) and HAVE_PIL        
        self._history = []
        self._history_translated = []
        self._map = map
        self._device = device
        self._points_to_skip = points_to_skip
        self._points_skipped = 0

        self._initialize_map()

    def _initialize_map(self):
        self._render_params = self._get_render_parameters()

        #generate the base on which other layers will be composed
        base = self._map_blank_image(color=self._render_params.bg_color)

        #add the floorplan if available
        if self._map and self._map.floorplan:
            base = Image.alpha_composite(base, self._map.floorplan)

        #set our internal variables so that we can get the default
        self._base_rendered_map = base
        self._rendered_map = base
    
    def update_map(self, force_redraw = False):
        """Updates the cleaning map"""

        #if mapping not enabled, nothing to update
        if not self.map_enabled:
            return

        if (self.roomba.changed('pose') or self.roomba.changed('phase') or 
            force_redraw) and self.map_enabled:

            #make sure we have phase info before trying to render
            if self.roomba.current_state is not None:
                self._update_state()
                self._render_map()

    def get_map(self, width: int = None, height: int = None) -> bytes:

        #get the default map
        map = self._rendered_map

        #if we haven't rendered anything, just return
        if map is None:
            return None

        #if we have a requested size, resize it
        if width and height:
            map = map.resize((width,height))
            pass 

        #save the internal image
        with io.BytesIO() as stream:
            map.save(stream, format="PNG")
            return stream.getvalue()

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
        #0 = facing away from the dock, increasing angle counter-clockwise
        #it looks like past 180, the roomba uses negative angles, but still seems
        #to be in the counter-clockwise direction
        #PIL denotes angles in the counterclockwise direction
        #so, to compute the right angle, we need to:
        #1) add map angle
        #2) add 180 degrees (roomba image faces up, but should face away at 0)
        #2) add theta
        #3) mod 360, add 360 if negative
        img_theta = (self._map.angle + theta + 180) % 360
        if img_theta < 0:
            img_theta += 360        
        
        #return the tuple
        return RoombaPosition(int(img_x), int(img_y), int(img_theta))

    def _render_map(self):
        """Renders the map"""

        #draw in the vacuum path
        base = self._draw_vacuum_path(self._base_rendered_map)

        #draw in the map walls (to hide overspray)
        if self._map.walls:
            base = Image.alpha_composite(base, self._map.walls)

        #draw the roomba and any problems
        base = self._draw_roomba(base)

        #finally, draw the text
        #base = self._draw_text(base)

        #save the map
        self._rendered_map = base
        
    def _get_render_parameters(self) -> MapRenderParameters:
        if self._map:
            icon_set = self._map.icon_set
            bg_color = self._map.bg_color
            path_color = self._map.path_color
            path_width = self._map.path_width
        else:
            icon_set = self._get_icon_set()
            bg_color = DEFAULT_BG_COLOR
            path_color = DEFAULT_PATH_COLOR
            path_width = DEFAULT_PATH_WIDTH

        if self._device:
            if self._device.icon_set:
                icon_set = self._device.icon_set
            if self._device.bg_color:
                bg_color = self._device.bg_color
            if self._device.path_color:
                path_color = self._device.path_color
            if self._device.path_width:
                path_width = self._device.path_width

        return MapRenderParameters(
            icon_set,
            self._device.blid,
            bg_color,
            path_color,
            path_width
        )

    def _map_blank_image(self, color=transparent) -> Image.Image:
        return make_blank_image(self._map.img_width,self._map.img_height,color)

    def _draw_vacuum_path(self, base: Image.Image) -> Image.Image:
        if len(self._history_translated) > 1:        
            layer = self._map_blank_image()
            renderer = ImageDraw.Draw(layer)

            renderer.line(
                list(map(lambda p: (p.x,p.y), self._history_translated)),
                fill=self._render_params.path_color,
                width=self._render_params.path_width,
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
        if self._render_params and self._render_params.icon_set:
            try:
                icon_set = self._icons[self._render_params.icon_set]
            except:
                self.log.warn(f"Could not load icon set '{self._render_params.icon_set}' for map.")

        return icon_set

    def _draw_roomba(self, base: Image.Image, render_params: MapRenderParameters) -> Image.Image:
        layer = self._map_blank_image()

        #get the image coordinates of the roomba
        x, y, theta = self.roomba_image_pos

        #get the icon set to use
        icon_set = self._get_icon_set(render_params)

        #add in the roomba icon
        if x and y:
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

        if x and y and problem_icon:
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
        renderer.rectangle(bbox, fill=self._map.text_bg_color)

        #render the text
        renderer.multiline_text((margin,margin), combined_text, fill=self._map.text_color, font=self.font)

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