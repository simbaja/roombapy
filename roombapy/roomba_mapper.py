from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .roomba import Roomba

class RoombaMapper:
    def __init__(self, roomba: 'Roomba') -> None:
        self.roomba = roomba
        self.map_enabled = roomba.cap.get("pose", False)
        self.old_x_y = None

    def draw_map(self, force_redraw = False):
        '''
        Draw map of Roomba cleaning progress
        '''
        if (self.roomba.changed('pose') or self.roomba.changed('phase') or 
            force_redraw) and self.map_enabled:
            #program just started, initialize old_x_y
            if self.old_x_y is None:
                self.old_x_y, _ = self.offset_coordinates(self.co_ords)
            
            #make sure we have phase info
            if self.roomba.current_state is not None:
                self.render_map()
    
    def render_map(self):
        pass
    
    def offset_coordinates(self, co_ords: dict):
        pass