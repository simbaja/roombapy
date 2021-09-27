
import math
import logging
import time
from typing import TYPE_CHECKING, NamedTuple, Tuple
import textwrap

if TYPE_CHECKING:
    from .roomba import Roomba

from roombapy.const import (
    DEFAULT_MAP_MAX_ALLOWED_DISTANCE, 
    ROOMBA_STATES, 
    DEFAULT_MAP_SKIP_POINTS
)

# Import trickery
global HAVE_PIL
HAVE_PIL = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageColor
    HAVE_PIL = True
except ImportError:
    print("PIL module not found, maps are disabled")
        
transparent = (0, 0, 0, 0)  #transparent color

def clamp(num, min_value, max_value):
   return max(min(num, max_value), min_value)

def interpolate(value, in_range, out_range) -> float:
    
    #handle inverted ranges
    invert: False
    if in_range[0] > in_range[1]:
        in_range = in_range[1], in_range[0]
        invert = not invert
    if out_range[0] > out_range[1]:
        in_range = out_range[1], out_range[0]
        invert = not invert

    #make sure it's in the range
    value = clamp(value, in_range[0], in_range[1])

    out = float(value) / float((in_range[1] - in_range[0]) * (out_range[1] - out_range[0]))
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
            
def make_transparent(image, color=None):
    '''
    take image and make white areas transparent
    return transparent image
    '''
    image = image.convert("RGBA")
    datas = image.getdata()
    newData = []
    for item in datas:
        # white (ish)
        if item[0] >= 254 and item[1] >= 254 and item[2] >= 254:
            newData.append(transparent)
        else:
            if color:
                newData.append(color)
            else:
                newData.append(item)

    image.putdata(newData)
    return image
    
class icons():
    '''
    Roomba icons object
    '''
    def __init__(self, base_icon=None, angle=0, fnt=None, size=(50,50), log=None):
        if log:
            self.log = log
        else:
            self.log = logging.getLogger("Roomba.{}".format(__name__))
        self.angle = angle
        self.fnt = fnt
        self.size = size
        self.base_icon = base_icon
        if self.base_icon is None:
            self.base_icon = self.draw_base_icon()
        
        self.init_dict()
                        
    def init_dict(self):
        self.icons = {  'roomba'    : self.create_icon('roomba'),
                        'stuck'     : self.create_icon('stuck'),
                        'cancelled' : self.create_icon('cancelled'),
                        'battery'   : self.create_icon('battery'),
                        'bin full'  : self.create_icon('bin full'),
                        'tank low'  : self.create_icon('tank low'),
                        'home'      : self.create_icon('home', (32,32))
                     }
                        
    def __getitem__(self, name):
        return self.icons.get(name)
                        
    def set_font(self, fnt):
        self.fnt = fnt
        self.init_dict()
        
    def set_angle(self, angle):
        self.angle = angle
        
    def create_default_icon(self, name, size=None):
        self.icons[name] = self.create_icon(name, size)
            
    def load_icon_file(self, name, filename, size=None):
        try:
            if not size:
                size = self.size
            icon = Image.open(filename).convert('RGBA').resize(
                size,Image.ANTIALIAS)
            icon = make_transparent(icon)
            icon = icon.rotate(180-self.angle, expand=False)
            self.icons[name] = icon
            return True
        except IOError as e:
            self.log.warning('Error loading icon file: {} : {}'.format(filename, e))
            self.create_default_icon(name, size)
        return False
            
    def draw_base_icon(self, size=None):
        if not HAVE_PIL:
            return None
            
        icon = Image.new('RGBA', size if size else self.size, transparent)
        draw_icon = ImageDraw.Draw(icon)
        draw_icon.ellipse([(5,5),(icon.size[0]-5,icon.size[1]-5)],
                fill="green", outline="black")
        return icon

    def create_icon(self, icon_name, size=None):
        '''
        draw default icons, return icon drawing
        '''
        if not HAVE_PIL:
            return None
            
        if not size:
            size = self.size
            
        if icon_name in ['roomba', 'stuck', 'cancelled']:
            icon = self.base_icon.copy().resize(size,Image.ANTIALIAS)
        else:
            icon = Image.new('RGBA', size, transparent)
        draw_icon = ImageDraw.Draw(icon)
        if icon_name in ['stuck', 'cancelled']:
            draw_icon.pieslice([(5,5),(icon.size[0]-5,icon.size[1]-5)],
                175, 185, fill="red", outline="red")

        if icon_name == "roomba":
            draw_icon.pieslice([(5,5),(icon.size[0]-5,icon.size[1]-5)],
                355, 5, fill="red", outline="red")
        elif icon_name == "cancelled":
            if self.fnt is not None:
                draw_icon.text((4,-4), "X", font=self.fnt, fill=(255,0,0,255))
        elif icon_name == "stuck":
            draw_icon.polygon([(
                icon.size[0]//2,icon.size[1]), (0, 0), (0,icon.size[1])],
                fill = 'red')
            if self.fnt is not None:
                draw_icon.text((4,-4), "!", font=self.fnt,
                    fill=(255,255,255,255))
        elif icon_name == "bin full":
            draw_icon.rectangle([
                icon.size[0]-10, icon.size[1]-10,
                icon.size[0]+10, icon.size[1]+10],
                fill = "grey")
            if self.fnt is not None:
                draw_icon.text((4,-4), "F", font=self.fnt,
                    fill=(255,255,255,255))
        elif icon_name == "tank low":
            draw_icon.rectangle([
                icon.size[0]-10, icon.size[1]-10,
                icon.size[0]+10, icon.size[1]+10],
                fill = "blue")
            if self.fnt is not None:
                draw_icon.text((4,-4), "L", font=self.fnt,
                    fill=(255,255,255,255))
        elif icon_name == "battery":
            draw_icon.rectangle([icon.size[0]-10, icon.size[1]-10,
                icon.size[0]+10,icon.size[1]+10], fill = "orange")
            if self.fnt is not None:
                draw_icon.text((4,-4), "B", font=self.fnt,
                    fill=(255,255,255,255))
        elif icon_name == "home":
            draw_icon.rectangle([0,0,32,32], fill="red", outline="black")
            if self.fnt is not None:
                draw_icon.text((4,-4), "D", font=self.fnt,
                    fill=(255,255,255,255))
        else:
            return None
        #rotate icon 180 degrees
        icon = icon.rotate(180-self.angle, expand=False)
        return icon

class RoombaPosition(NamedTuple):
    x: int
    y: int
    theta: int

class RoombaMap:
    id: str
    name: str
    coords_start: Tuple[int,int]
    coords_end: Tuple[int,int]
    angle: float
    floorplan: Image = None
    walls: Image = None

    @property
    def img_width(self) -> int:
        if self.floorplan:
            x, _ = self.floorplan.size
            return x
        else:
            return 1000
    
    @property
    def img_height(self) -> int:
        if self.floorplan:
            _, y = self.floorplan.size
            return y
        else:
            return 1000

class RoombaMapper:
    def __init__(self, roomba: 'Roomba', font: ImageFont.ImageFont = None) -> None:
        self.log = logging.getLogger(__name__)
        self.roomba = roomba
        self.map_enabled = roomba.cap.get("pose", False) and HAVE_PIL

        #initialize the font
        self.font = font
        if self.font is None:
            try:
                self.font = ImageFont.truetype('FreeMono.ttf', 40)
            except IOError as e:
                self.log.warning("error loading font: %s, loading default font".format(e))
                self.font = ImageFont.load_default()

        #generate the default icons
        self.icons = icons(base_icon=None, angle=self.angle, fnt=self.font, size=(32,32), log=self.log)

        #mapping variables
        self.map: RoombaMap = None
        self.rendered_map: Image.Image = None
        self.points_to_skip = DEFAULT_MAP_SKIP_POINTS
        self.points_skipped = 0
        self.max_distance = DEFAULT_MAP_MAX_ALLOWED_DISTANCE
        self.history = []
        self.history_translated: list[RoombaPosition] = []

    @property
    def roomba_image_pos(self) -> RoombaPosition:       
        try:
            return self.history_translated[-1]
        except:
            return RoombaPosition(0,0,0)
    
    @property
    def origin_image_pos(self) -> RoombaPosition:
        return self._map_coord_to_image_coord(self.roomba.zero_coords())

    @property
    def state(self) -> Image.Image:
        return self.rendered_map

    def reset_map(self, map: RoombaMap, points_to_skip: int = DEFAULT_MAP_SKIP_POINTS):
        self.history = []
        self.history_translated = []
        self.map = map
        self.points_to_skip = points_to_skip
        self.points_skipped = 0

    def update_map(self, force_redraw = False):
        """Updates the cleaning map"""

        #if mapping not enabled, nothing to update
        if not self.map_enabled:
            return

        if self.roomba.is_set('update_after_completed') and not force_redraw:
            self.log.info('MAP [Update]: Skipping (mission complete), resume in {}s'
                .format(self.roomba.when_run('update_after_completed')))
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
            if self.roomba.co_ords == self.zero_coords(theta=0):
                #bogus pose received, can't have 0,0,0 when running, usually happens after recovering from an error condition
                self.log.warning('MAP [State Update]: received 0,0,0 pose when running - ignoring')
                position = None

        #if we have a position update, append to the history if it meets our criteria
        if position:
            #there's a few points at the beginning that are usually erroneous, skip them
            if self.points_skipped < self.points_to_skip:
                self.points_skipped += 1
                return

            #if we have history, we need to check a couple things
            if len(self.history) > 0:
                old = self.history[-1]
                old_x = old["x"]
                old_y = old["y"]
                new_x = position["x"]
                new_y = position["y"]

                #if we didn't actually move from the last recorded position, ignore it
                if (old_x,old_y) == (new_x,new_y):
                    return

                #at times, roomba reports erroneous points, ignore if too large of a gap
                #between measurements
                if self._map_distance((old_x,old_y),(new_x,new_y)) > self.max_distance:
                    return

            self.history.append(position)
            self.history_translated.append(self._map_coord_to_image_coord(position))

    def _map_coord_to_image_coord(self, coord: dict) -> RoombaPosition:
        x: float = float(coord["x"])
        y: float = float(coord["y"])
        theta: float = float(coord["theta"])
        
        #perform rotation: occurs about the map origin, so should
        #undo any rotation that exists
        x, y = rotate(x, y, self.map.angle,
            invert_x = self.map.coords_start[0] > self.map.coords_end[0],
            invert_y = self.map.coords_start[1] < self.map.coords_end[1]
        )

        #interpolate the x,y coordinates to scale to the appropriate output
        img_x = interpolate(
            x, 
            [self.map.coords_start[0], self.map.coords_end[0]],
            [0, self.map.img_width - 1]
        )
        img_y = interpolate(
            y, 
            [self.map.coords_start[1], self.map.coords_end[1]],
            [0, self.map.img_height - 1]
        )

        #make sure we stay within the bounds
        clamp(img_x, 0, self.map.img_width)
        clamp(img_y, 0, self.map.img_height)
        
        #adjust theta
        img_theta = theta + self.map.angle
        
        #return the tuple
        return RoombaPosition(int(img_x), int(img_y), int(img_theta))

    def _render_map(self):
        """Renders the map"""

        #generate the base on which other layers will be composed
        base = self._map_blank_image()

        #add the floorplan if available
        if self.map.floorplan:
            base = Image.alpha_composite(base, self.map.floorplan)

        #draw in the vacuum path
        base = self._draw_vacuum_path(base)

        #draw in the map walls (to hide overspray)
        if self.map.walls:
            base = Image.alpha_composite(base, self.map.walls)

        #draw the roomba and any problems
        base = self._draw_roomba(base)

        #finally, draw the text
        base = self._draw_text(base)

        #set the internal image
        self.rendered_map = base

        #call event handlers
        
    def _map_blank_image(self, color=transparent) -> Image.Image:
        return make_blank_image(self.map.img_width,self.map.img_height,color)

    def _draw_vacuum_path(self, base: Image.Image) -> Image.Image:
        if len(self.history_translated) > 1:        
            layer = self._map_blank_image()
            renderer = ImageDraw.Draw(layer)

            renderer.line(
                map(lambda p: (p.x,p.y), self.history_translated),
                fill=(255,0,0,180),
                width=2,
                joint="curve"
            )

            return Image.alpha_composite(base, layer)
        else:
            return base

    def _draw_roomba(self, base: Image.Image) -> Image.Image:
        layer = self._map_blank_image()

        #get the image coordinates of the roomba
        x, y, theta = self.roomba_image_pos
        icon = self.icons['roomba']

        #add in the roomba icon
        layer.paste(
            self.icons['roomba'].rotate(theta, expand=False),
            center_image(x, y, self.icons['roomba'], layer.size)            
        )

        #add the dock
        dock = self._map_blank_image()
        dock.paste(
            self.icons['home'],
            center_image(
                self.origin_image_pos.x, 
                self.origin_image_pos.y, 
                self.icons['home'], layer.size
            )
        )

        layer = Image.alpha_composite(layer, dock)

        #add the problem icon (pick one in a priority order)
        problem_icon = None
        if self.flags.get('stuck'):
            problem_icon = self.icons['stuck']
        elif self.flags.get('cancelled'):
            problem_icon = self.icons['cancelled']
        elif self.flags.get('bin_full'):
            problem_icon = self.icons['bin full']
        elif self.flags.get('battery_low'):
            problem_icon = self.icons['battery']
        elif self.flags.get('tank_low'):
            problem_icon = self.icons['tank low']

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
        renderer.rectangle(bbox, fill=(0, 0, 0, 180))

        #render the text
        renderer.multiline_text((margin,margin), combined_text, fill=(255,255,255,255))

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
            display_state = "Final Docking"
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
            if not self.roomba.is_set('ignore_run'):
                display_attributes = f"Bat: {self.roomba.batPct}%, Bin Full: {self.roomba.bin_full}"
        elif self.roomba.current_state == ROOMBA_STATES["hmUsrDock"]:
            display_state = "User Docking"
            show_time = True
        else:
            display_state = self.roomba.current_state
        
        if show_time:
            display_time = time.strftime("%a %b %d %H:%M:%S")

        return display_state, display_attributes, display_time    

    def _map_distance(self, pos1: Tuple(int,int), pos2: Tuple(int,int)):
        return int(math.sqrt(((pos2[0]-pos1[0])**2)+((pos2[1]-pos1[1])**2)))        

