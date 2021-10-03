#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Python 3.* (thanks to pschmitt for adding Python 3 compatibility).

Program to connect to Roomba 980 vacuum cleaner, dcode json, and forward to mqtt
server.
Nick Waterton 24th April 2017: V 1.0: Initial Release
Nick Waterton 4th July   2017  V 1.1.1: Fixed MQTT protocol version, and map
paths, fixed paho-mqtt tls changes
Nick Waterton 5th July   2017  V 1.1.2: Minor fixes, CV version 3 .2 support
Nick Waterton 7th July   2017  V1.2.0: Added -o option "roomOutline" allows
enabling/disabling of room outline drawing, added auto creation of css/html
files Nick Waterton 11th July  2017  V1.2.1: Quick (untested) fix for room
outlines if you don't have OpenCV
"""
import asyncio
import datetime
import json
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Mapping
from datetime import datetime

from roombapy.const import ROOMBA_ERROR_MESSAGES, ROOMBA_READY_MESSAGES, ROOMBA_STATES
from roombapy.roomba_mapper import RoombaMap, RoombaMapper

MAX_CONNECTION_RETRIES = 3


class RoombaConnectionError(Exception):
    """Roomba connection exception."""
    pass

class Roomba:
    """
    This is a Class for Roomba 900 series WiFi connected Vacuum cleaners.

    Requires firmware version 2.0 and above (not V1.0). Tested with Roomba 980
    username (blid) and password are required, and can be found using the
    password() class above (or can be auto discovered)
    Most of the underlying info was obtained from here:
    https://github.com/koalazak/dorita980 many thanks!
    The values received from the Roomba as stored in a dictionay called
    master_state, and can be accessed at any time, the contents are live, and
    will build with time after connection.
    This is not needed if the forward to mqtt option is used, as the events will
    be decoded and published on the designated mqtt client topic.
    """

    def __init__(self, remote_client, continuous=True, delay=1):
        """Roomba client initialization."""
        self.log = logging.getLogger(__name__)
        self.loop = asyncio.get_event_loop()        

        self.remote_client = remote_client
        self._init_remote_client_callbacks()
        self.continuous = continuous
        if self.continuous:
            self.log.debug("CONTINUOUS connection")
        else:
            self.log.debug("PERIODIC connection")

        self.stop_connection = False
        self.periodic_connection_running = False
        self.topic = "#"
        self.exclude = ""
        self.delay = delay
        self.periodic_connection_duration = 10
        self.roomba_connected = False
        self.indent = 0
        self.master_indent = 0
        self.current_state = None
        self.master_state = {}  # all info from roomba stored here
        self.time = time.time()
        self._thread = threading.Thread(
            target=self.periodic_connection, name="roombapy"
        )
        self.on_message_callbacks = []
        self.on_disconnect_callbacks = []
        self.client_error = None

        #create the mapper
        self._mapper = RoombaMapper(self)
        #replace the crude icons with ones loaded from our assets and make default
        self._mapper.add_icon_set("default")
        self._history = {}
        self._timers = {}
        self._flags = {}
        self._new_mission_start_time: float = None

        self._pmap_id: str = None
        self._maps: dict[str,RoombaMap] = {}

    @property    
    def co_ords(self):
        co_ords = self.pose
        if isinstance(co_ords, dict):
            return {'x': co_ords['point']['y'],
                    'y': co_ords['point']['x'],
                    'theta': co_ords['theta']}
        return self.zero_coords()

    @property
    def current_pmap_id(self):
        return self._pmap_id
        
    @property
    def error_num(self):
        try:
            return self.cleanMissionStatus.get('error')
        except AttributeError:
            pass
        return 0
        
    @property
    def error_message(self):
        return self._get_error_message(self.error_num)

    @property
    def not_ready_num(self):
        try:
            return self.cleanMissionStatus.get('notReady')
        except:
            pass
        return 0
    
    @property
    def not_ready_message(self):
        return self._get_not_ready_message(self.not_ready_num)    
        
    @property
    def cleanMissionStatus(self):
        return self.get_property("cleanMissionStatus")
        
    @property
    def pose(self):
        return self.get_property("pose")
        
    @property
    def batPct(self):
        return self.get_property("batPct")
                 
    @property
    def bin_full(self):
        return self.get_property("bin_full")
        
    @property
    def tanklvl(self):
        return self.get_property("tankLvl")
        
    @property
    def rechrgM(self):
        return self.get_property("rechrgM")
        
    def calc_mssM(self):
        start_time = self.get_property("mssnStrtTm")
        if start_time:
            return int((datetime.now() - datetime.fromtimestamp(start_time)).total_seconds()//60)
        start = self._timers.get('start')
        if start:
            return int((time.time()-start)//60)
        return None
        
    @property
    def mssnM(self):
        mssM = self.get_property("mssnM")
        if not mssM:
            run_time = self.calc_mssM()
            return run_time if run_time else mssM
        return mssM
    
    @property
    def expireM(self):
        return self.get_property("expireM")
    
    @property
    def cap(self):
        return self.get_property("cap")
    
    @property
    def sku(self):
        return self.get_property("sku")
        
    @property
    def mission(self):
        return self.get_property("cycle")
        
    @property
    def phase(self):
        return self.get_property("phase")
        
    @property
    def cleanMissionStatus_phase(self):
        return self.phase
        
    @property
    def cleanMissionStatus(self):
        return self.get_property("cleanMissionStatus")
        
    @property
    def pmaps(self):
        return self.get_property("pmaps")
        
    @property
    def regions(self):
        return self.get_property("regions")        

    def register_on_message_callback(self, callback):
        self.on_message_callbacks.append(callback)

    def register_on_disconnect_callback(self, callback):
        self.on_disconnect_callbacks.append(callback)

    def _init_remote_client_callbacks(self):
        self.remote_client.set_on_message(self.on_message)
        self.remote_client.set_on_connect(self.on_connect)
        self.remote_client.set_on_disconnect(self.on_disconnect)

    def connect(self):
        if self.roomba_connected or self.periodic_connection_running:
            return

        if self.continuous:
            self._connect()
        else:
            self._thread.daemon = True
            self._thread.start()

        self.time = time.time()  # save connection time

    def _connect(self):
        is_connected = self.remote_client.connect()
        if not is_connected:
            raise RoombaConnectionError(
                "Unable to connect to Roomba at {}".format(
                    self.remote_client.address
                )
            )
        return is_connected

    def disconnect(self):
        if self.continuous:
            self.remote_client.disconnect()
        else:
            self.stop_connection = True

    def periodic_connection(self):
        # only one connection thread at a time!
        if self.periodic_connection_running:
            return
        self.periodic_connection_running = True
        while not self.stop_connection:
            try:
                self._connect()
            except RoombaConnectionError as error:
                self.periodic_connection_running = False
                self.on_disconnect(error)
                return
            time.sleep(self.delay)

        self.remote_client.disconnect()
        self.periodic_connection_running = False

    def on_connect(self, error):
        self.log.info("Connecting to Roomba %s", self.remote_client.address)
        self.client_error = error
        if error is not None:
            self.log.error(
                "Roomba %s connection error, code %s",
                self.remote_client.address,
                error,
            )
            return

        self.roomba_connected = True
        self.remote_client.subscribe(self.topic)

    def on_disconnect(self, error):
        self.roomba_connected = False
        self.client_error = error
        if error is not None:
            self.log.warning(
                "Unexpectedly disconnected from Roomba %s, code %s",
                self.remote_client.address,
                error,
            )

            # call the callback functions
            for callback in self.on_disconnect_callbacks:
                callback(error)

            return

        self.log.info("Disconnected from Roomba %s", self.remote_client.address)

    def on_message(self, mosq, obj, msg):
        if self.exclude != "":
            if self.exclude in msg.topic:
                return

        if self.indent == 0:
            self.master_indent = max(self.master_indent, len(msg.topic))

        log_string, json_data = self._decode_payload(msg.topic, msg.payload)
        self.dict_merge(self.master_state, json_data)

        self.log.debug(
            "Received Roomba Data %s: %s, %s",
            self.remote_client.address,
            str(msg.topic),
            str(msg.payload),
        )

        #update the state machine and history
        self._update_state_machine()

        # call the callback functions
        for callback in self.on_message_callbacks:
            callback(json_data)

    def send_command(self, command, params=None):
        if params is None:
            params = {}

        self.log.debug("Send command: %s", command)
        roomba_command = {
            "command": command,
            "time": int(datetime.timestamp(datetime.now())),
            "initiator": "localApp",
        }
        roomba_command.update(params)

        str_command = json.dumps(roomba_command)
        self.log.debug("Publishing Roomba Command : %s", str_command)
        self.remote_client.publish("cmd", str_command)

    def set_preference(self, preference, setting):
        self.log.debug("Set preference: %s, %s", preference, setting)
        val = setting
        # Parse boolean string
        if isinstance(setting, str):
            if setting.lower() == "true":
                val = True
            elif setting.lower() == "false":
                val = False
        tmp = {preference: val}
        roomba_command = {"state": tmp}
        str_command = json.dumps(roomba_command)
        self.log.debug("Publishing Roomba Setting : %s" % str_command)
        self.remote_client.publish("delta", str_command)

    def add_map_definition(self, map: RoombaMap):
        """Adds a map definition"""
        if not map.id:
            raise ValueError(map.id)   
        self._maps[map.id] = map

    def add_map_icon_set(
        self,
        name: str,
        icon_path: str = "{PKG}/assets",                    
        home_icon_file: str = "home.png",
        roomba_icon_file: str = "roomba.png",
        roomba_error_file: str = "roombaerror.png",
        roomba_cancelled_file: str = "roombacancelled.png",
        roomba_battery_file: str = "roomba-charge.png",
        bin_full_file: str = "binfull.png",
        tank_low_file: str = "tanklow.png",
        roomba_size=(50,50)):
        """Adds a set of icons for map drawing use"""
        self._mapper.add_icon_set(name, icon_path, home_icon_file, roomba_icon_file,
        roomba_error_file, roomba_cancelled_file, roomba_battery_file, bin_full_file,
        tank_low_file, roomba_size)  

    def dict_merge(self, dct, merge_dct):
        """
        Recursive dict merge.

        Inspired by :meth:``dict.update()``, instead
        of updating only top-level keys, dict_merge recurses down into dicts
        nested to an arbitrary depth, updating keys. The ``merge_dct`` is
        merged into ``dct``.
        :param dct: dict onto which the merge is executed
        :param merge_dct: dct merged into dct
        :return: None
        """
        for k, v in merge_dct.items():
            if (
                k in dct
                and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], Mapping)
            ):
                self.dict_merge(dct[k], merge_dct[k])
            else:
                dct[k] = merge_dct[k]

    def recursive_lookup(self, search_dict, key, cap=False):
        '''
        recursive dictionary lookup
        if cap is true, return key if it's in the 'cap' dictionary,
        else return the actual key value
        '''
        for k, v in search_dict.items():
            if cap:
                if k == 'cap':
                    return self.recursive_lookup(v, key, False)
            elif k == key:
                return v 
            elif isinstance(v, dict) and k != 'cap':
                val = self.recursive_lookup(v, key, cap)
                if val is not None:
                    return val
        return None

    def get_property(self, property, cap=False):
        '''
        Only works correctly if property is a unique key
        '''
        if property in ['cleanSchedule', 'langs']:
            value = self.recursive_lookup(self.master_state, property+'2', cap)
            if value is not None:
                return value
        return self.recursive_lookup(self.master_state, property, cap)

    def set_flags(self, flags=None):
        self._handle_flags(flags, True)
        
    def clear_flags(self, flags=None):
        self._handle_flags(flags)
        
    def flag_set(self, flag) -> bool:
        try:
            return self._flags.get(flag, False)
        except KeyError:
            pass
        return False
            
    def _handle_flags(self, flags=None, set=False):
        if isinstance(flags, str):
            flags = [flags]
        if flags:
            for flag in flags:
                if set:
                    self._flags[flag] = True
                else:
                    self._flags.pop(flag, None)
        else:
            self._flags = {}

    def timer_active(self, name) -> bool:
        return self._timers.get(name, {}).get('value', False)
        
    def timer_duration(self, name) -> int:
        th = self._timers.get(name, {}).get('reset', None)
        if th:
            return max(0, int(th._when - self.loop.time()))
        return 0
    
    def _set_timer(self, name, value=False, duration=10):
        self._timers.setdefault(name, {})
        self._timers[name]['value'] = value
        self.log.info('Set {} to: {}'.format(name, value))
        if self._timers[name].get('reset'):
            self._timers[name]['reset'].cancel()    
        if value:
            self._timers[name]['reset'] = self.loop.call_later(duration, self._set_timer, name)  #reset reset timer in duration seconds

    def _update_history(self, property, value=None, cap=False):
        '''
        keep previous value
        '''
        if value is not None:
            current = value
        else:
            current = self.get_property(property, cap)
        if isinstance(current, dict):
            current = current.copy()
        previous = self._history.get(property, {}).get('current')
        if previous is None:
            previous = current
        self._history[property] = {'current' : current,
                                  'previous': previous}
        return current
        
    def _set_history(self, property, value=None):
        if isinstance(value, dict):
            value = value.copy()
        self._history[property] = {'current' : value,
                                  'previous': value}
        
    def current(self, property):
        return self._history.get(property, {}).get('current')
        
    def previous(self, property):
        return self._history.get(property, {}).get('previous')
        
    def changed(self, property):
        changed = self._history.get(property, {}).get('current') != self._history.get(property, {}).get('previous')
        return changed

    def zero_coords(self, theta=180):
        '''
        returns dictionary with default zero coords
        '''
        return {"x": 0, "y": 0, "theta": theta}
        
    def zero_pose(self, theta=180):
        '''
        returns dictionary with default zero coords
        '''
        return {"theta":theta,"point":{"x":0,"y":0}}  

    def _get_error_message(self, error_num):
        try:
            error_message = ROOMBA_ERROR_MESSAGES[error_num]
        except KeyError as e:
            self.log.warning(
                "Error looking up error message {}".format(e))
            error_message = "Unknown Error number: {}".format(error_num)
        return error_message   

    def _get_not_ready_message(self, not_ready_num):
        try:
            message = ROOMBA_READY_MESSAGES[not_ready_num]
        except KeyError as e:
            self.log.warning(
                "Error looking up not ready message {}".format(e))
            message = "Unknown not ready number: {}".format(not_ready_num)
        return message        

    def _get_mission_map(self) -> RoombaMap:
        return self._get_map(self._pmap_id)

    def _get_map(self, map_id: str) -> RoombaMap:
        try:
            return self._maps[map_id]
        except:
            return self._get_default_map()

    def _get_default_map(self) -> RoombaMap:
        return RoombaMap("default","Default")                     

    def _decode_payload(self, topic, payload):
        """
        Format json for pretty printing.

        Returns string sutiable for logging, and a dict of the json data
        """
        indent = self.master_indent + 31  # number of spaces to indent json data

        json_data = None
        try:
            # if it's json data, decode it (use OrderedDict to preserve keys
            # order), else return as is...
            json_data = json.loads(
                payload.decode("utf-8")
                .replace(":nan", ":NaN")
                .replace(":inf", ":Infinity")
                .replace(":-inf", ":-Infinity"),
                object_pairs_hook=OrderedDict,
            )
            # if it's not a dictionary, probably just a number
            if not isinstance(json_data, dict):
                return json_data, dict(json_data)
            json_data_string = "\n".join(
                (indent * " ") + i
                for i in (json.dumps(json_data, indent=2)).splitlines()
            )

            formatted_data = "Decoded JSON: \n%s" % json_data_string

        except ValueError:
            formatted_data = payload
        return formatted_data, dict(json_data)

    def _update_state_machine(self):
        '''
        Roomba progresses through states (phases), current identified states
        are:
        ""              : program started up, no state yet
        "run"           : running on a Cleaning Mission
        "hmUsrDock"     : returning to Dock
        "hmMidMsn"      : need to recharge
        "hmPostMsn"     : mission completed
        "charge"        : charging
        "stuck"         : Roomba is stuck
        "stop"          : Stopped
        "pause"         : paused
        "evac"          : emptying bin
        "chargingerror" : charging base is unplugged

        available states:
        states = {"charge"          : "Charging",
                  "new"             : "New Mission",
                  "run"             : "Running",
                  "resume"          : "Running",
                  "hmMidMsn"        : "Docking",
                  "recharge"        : "Recharging",
                  "stuck"           : "Stuck",
                  "hmUsrDock"       : "User Docking",
                  "completed"       : "Mission Completed",
                  "cancelled"       : "Cancelled",
                  "stop"            : "Stopped",
                  "pause"           : "Paused",
                  "evac"            : "Emptying",
                  "hmPostMsn"       : "Docking - End Mission",
                  "chargingerror"   : "Base Unplugged",
                  ""                :  None}

        Normal Sequence is "" -> charge -> run -> hmPostMsn -> charge
        Mid mission recharge is "" -> charge -> run -> hmMidMsn -> charge
                                   -> run -> hmPostMsn -> charge
        Stuck is "" -> charge -> run -> hmPostMsn -> stuck
                    -> run/charge/stop/hmUsrDock -> charge
        Start program during run is "" -> run -> hmPostMsn -> charge
        Note: Braava M6 goes run -> hmPostMsn -> run -> charge when docking
        Note: S9+ goes run -> hmPostMsn -> charge -> run -> charge on a training mission (ie cleanMissionStatus_cycle = 'train')
        Note: The first 3 "pose" (x, y) co-ordinate in the first 10 seconds during undocking at mission start seem to be wrong
              for example, during undocking:
              {"x": 0, "y": 0},
              {"x": -49, "y": 0},
              {"x": -47, "y": 0},
              {"x": -75, "y": -11}... then suddenly becomes normal co-ordinates
              {"x": -22, "y": 131}
              {"x": -91, "y": 211}
              also during "hmPostMsn","hmMidMsn", "hmUsrDock" the co-ordinates system also seems to change to bogus values
              For example, in "run" phase, co-ordinates are reported as:
              {"x": -324, "y": 824},
              {"x": -324, "y": 826} ... etc, then some time after hmMidMsn (for example) they change to:
              {"x": 417, "y": -787}, which continues for a while
              {"x": 498, "y": -679}, and then suddenly changes back to normal co-ordinates
              {"x": -348, "y": 787},
              {"x": -161, "y": 181},
              {"x": 0, "y": 0}
              
        Need to identify a new mission to initialize map, and end of mission to
        finalise map.
        mission goes from 'none' to 'clean' (or another mission name) at start of mission (init map)
        mission goes from 'clean' (or other mission) to 'none' at end of missions (finalize map)
        Anything else = continue with existing map
        '''

        mission = self._update_history("cycle")      #mission
        phase = self._update_history("phase")        #mission phase
        self._update_history("pose")                 #update co-ordinates
        self._update_flags()
        self._update_map_id()

        if phase is None or mission is None:
            return
        
        current_mission = self.current_state
        
        self.log.info('current_state: {}, \
            current phase: {}, \
            mission: {}, \
            mission_min: {}, \
            recharge_min: {}, \
            co-ords changed: {}'.format(self.current_state,
                                            phase,
                                            mission,
                                            self.mssnM,
                                            self.rechrgM,
                                            self.changed('pose')))

        if phase == "charge":
            #self.set_history('pose', self.zero_pose())
            current_mission = None
            
        if self.current_state == ROOMBA_STATES["new"] and phase != 'run':
            self.log.info('waiting for run state for New Missions')
            if time.time() - self._new_mission_start_time >= 20:
                self.log.warning('Timeout waiting for run state')
                self.current_state = ROOMBA_STATES[phase]

        elif phase == "run" and (self.timer_active('ignore_run') or mission == 'none'):
            self.log.info('Ignoring bogus run state')
            
        elif phase == "charge" and mission == 'none' and self.timer_active('ignore_run'):
            self.log.info('Ignoring bogus charge/mission state')
            self._update_history("cycle", self.previous('cycle'))
            
        elif phase in ["hmPostMsn","hmMidMsn", "hmUsrDock"]:
            self._set_timer('ignore_run', True, 10)
            self.current_state = ROOMBA_STATES[phase]
            
        elif self.changed('cycle'): #if mission has changed
            if mission != 'none':
                self.current_state = ROOMBA_STATES["new"]
                self._new_mission_start_time = time.time()
                self._mapper.reset_map(self._get_mission_map())
                if isinstance(self.sku, str) and self.sku[0].lower() in ['i', 's', 'm']:
                    #self.timer('ignore_coordinates', True, 30)  #ignore updates for 30 seconds at start of new mission
                    pass
            else:
                self._new_mission_start_time = None
                if self.bin_full:
                    self.current_state = ROOMBA_STATES["cancelled"]
                else:
                    self.current_state = ROOMBA_STATES["completed"]
                self._set_timer('ignore_run', True, 5)  #still get bogus 'run' states after mission complete.
            
        elif phase == "charge" and self.rechrgM:
            if self.bin_full:
                self.current_state = ROOMBA_STATES["pause"]
            else:
                self.current_state = ROOMBA_STATES["recharge"]
            
        else:
            try:
                self.current_state = ROOMBA_STATES[phase]
            except KeyError:
                self.log.error(
                    "Can't find state %s in predefined Roomba states, "
                    "please create a new issue: "
                    "https://github.com/pschmitt/roombapy/issues/new",
                    phase,
                )
                self.current_state = None

        if self.current_state != current_mission:
            self.log.info("updated state to: {}".format(self.current_state))

        #draw the map, forcing a redraw if needed
        if current_mission:
            self._mapper.update_map(current_mission != self.current_state)

    def _update_flags(self):
        if not self.bin_full:
            self.clear_flags('bin_full')
            
        if self.tanklvl is not None:
            if self.tanklvl < 100:
                self.set_flags('tank_low')
            else:
                self.clear_flags('tank_low')

        if  self.current_state == ROOMBA_STATES["charge"]:
            self.clear_flags(['battery_low', 'stuck'])

        elif self.current_state == ROOMBA_STATES["recharge"]:
            self.clear_flags(['battery_low', 'stuck'])

        elif self.current_state == ROOMBA_STATES["run"]:
            self.clear_flags(['stuck', 'new_mission'])

        elif self.current_state == ROOMBA_STATES["new"]:
            self.clear_flags()
            self.set_flags('new_mission')

        elif self.current_state == ROOMBA_STATES["stuck"]:
            self.set_flags('stuck')

        elif self.current_state == ROOMBA_STATES["cancelled"]:
            self.set_flags('cancelled')

        elif self.current_state == ROOMBA_STATES["hmMidMsn"]:
            if not self.timer_active('ignore_run'):
                if self.bin_full:
                    self.set_flags('bin_full')
                else:
                    self.set_flags('battery_low')

    def _update_map_id(self):
        try:
            self._pmap_id = self.get_property("pmap_id")
        except:
            pass
