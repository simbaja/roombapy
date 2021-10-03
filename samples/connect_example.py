from roombapy import RoombaDiscovery, RoombaFactory
from samples.secrets import ROOMBA_IP, ROOMBA_PW

roomba_discovery = RoombaDiscovery()
roomba_info = roomba_discovery.find(ROOMBA_IP)

roomba = RoombaFactory.create_roomba(
    roomba_info.ip, roomba_info.blid, ROOMBA_PW
)
roomba.register_on_message_callback(lambda msg: print(msg))
roomba.connect()

while True:
    pass
