import os.path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from roombapy import RoombaDiscovery, RoombaFactory
from roombapy.roomba_mapper import RoombaMap
from samples.secrets import ROOMBA_IP, ROOMBA_PW

roomba_discovery = RoombaDiscovery()
roomba_info = roomba_discovery.find(ROOMBA_IP)

roomba = RoombaFactory.create_roomba(
    roomba_info.ip, roomba_info.blid, ROOMBA_PW
)

def on_message(msg):
    print(msg)
    img = roomba.get_map()

map = RoombaMap(
    id = "YXxOmNqpTHurHTVbQixhVw",
    name = "Main Floor",
    coords_start=(-1100,-900),
    coords_end=(100,575),
    floorplan = "../blank_floorplan.png"
)

roomba.add_map_definition(map)

roomba.register_on_message_callback(on_message)
roomba.connect()

while True:
    pass