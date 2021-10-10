# https://homesupport.irobot.com/app/answers/detail/a_id/21127/kw/charging%20error
MQTT_ERROR_MESSAGES = {
    0: None,
    1: "Bad protocol",
    2: "Bad client id",
    3: "Server unavailable",
    4: "Bad username or password",
    5: "Not authorised",
}

ROOMBA_ERROR_MESSAGES = {
    0: "None",
    1: "Left wheel off floor",
    2: "Main brushes stuck",
    3: "Right wheel off floor",
    4: "Left wheel stuck",
    5: "Right wheel stuck",
    6: "Stuck near a cliff",
    7: "Left wheel error",
    8: "Bin error",
    9: "Bumper stuck",
    10: "Right wheel error",
    11: "Bin error",
    12: "Cliff sensor issue",
    13: "Both wheels off floor",
    14: "Bin missing",
    15: "Reboot required",
    16: "Bumped unexpectedly",
    17: "Path blocked",
    18: "Docking issue",
    19: "Undocking issue",
    20: "Docking issue",
    21: "Navigation problem",
    22: "Navigation problem",
    23: "Battery issue",
    24: "Navigation problem",
    25: "Reboot required",
    26: "Vacuum problem",
    27: "Vacuum problem",
    29: "Software update needed",
    30: "Vacuum problem",
    31: "Reboot required",
    32: "Smart map problem",
    33: "Path blocked",
    34: "Reboot required",
    35: "Unrecognised cleaning pad",
    36: "Bin full",
    37: "Tank needed refilling",
    38: "Vacuum problem",
    39: "Reboot required",
    40: "Navigation problem",
    41: "Timed out",
    42: "Localization problem",
    43: "Navigation problem",
    44: "Pump issue",
    45: "Lid open",
    46: "Low battery",
    47: "Reboot required",
    48: "Path blocked",
    52: "Pad required attention",
    53: "Software update required",
    65: "Hardware problem detected",
    66: "Low memory",
    68: "Hardware problem detected",
    73: "Pad type changed",
    74: "Max area reached",
    75: "Navigation problem",
    76: "Hardware problem detected",
    88: "Back-up refused",
    89: "Mission runtime too long",
    101: "Battery isn't connected",
    102: "Charging error",
    103: "Charging error",
    104: "No charge current",
    105: "Charging current too low",
    106: "Battery too warm",
    107: "Battery temperature incorrect",
    108: "Battery communication failure",
    109: "Battery error",
    110: "Battery cell imbalance",
    111: "Battery communication failure",
    112: "Invalid charging load",
    114: "Internal battery failure",
    115: "Cell failure during charging",
    116: "Charging error of Home Base",
    118: "Battery communication failure",
    119: "Charging timeout",
    120: "Battery not initialized",
    122: "Charging system error",
    123: "Battery not initialized",
}

ROOMBA_READY_MESSAGES = {
    0: 'N/A',
    2: 'Uneven Ground',
    15: 'Low Battery',
    39: 'Pending',
    48: 'Path Blocked'   
}

ROOMBA_STATES = {
    "charge": "Charging",
    "new": "New Mission",
    "run": "Running",
    "resume": "Running",
    "hmMidMsn": "Recharging",
    "recharge": "Recharging",
    "stuck": "Stuck",
    "hmUsrDock": "User Docking",
    "dock": "Docking",
    "dockend": "Docking - End Mission",
    "cancelled": "Cancelled",
    "completed": "Mission Completed",    
    "stop": "Stopped",
    "pause": "Paused",
    "hmPostMsn": "End Mission",
    "evac": "Emptying Bin",
    "chargingerror": "Base Unplugged",
    "": None,
}


DEFAULT_MAP_SKIP_POINTS = 3
DEFAULT_MAP_MAX_ALLOWED_DISTANCE = 500
DEFAULT_BG_COLOR = (0,0,0,0)
DEFAULT_PATH_COLOR = (0,0,180,127)
DEFAULT_TEXT_COLOR = (255,255,255,255)
DEFAULT_TEXT_BG_COLOR = (0,0,0,180)
DEFAULT_IMG_HEIGHT = 1000
DEFAULT_IMG_WIDTH = 1000
DEFAULT_PATH_WIDTH = 2
DEFAULT_MAP_MIN_COORDS = (-1000,-1000)
DEFAULT_MAP_MAX_COORDS = (1000,1000)
DEFAULT_MAP_ANGLE = 0.0

DEFAULT_ICON_PATH = "{PKG}/assets"
DEFAULT_ICON_SIZE = (50,50)
DEFAULT_ICON_HOME = "home.png"
DEFAULT_ICON_ROOMBA = "r865_icon.png"
DEFAULT_ICON_ERROR = "overlay-error.png"
DEFAULT_ICON_CANCELLED = "overlay-cancelled.png"
DEFAULT_ICON_CHARGING = "overlay-charging.png"
DEFAULT_ICON_BATTERY = "overlay-battery-low.png"
DEFAULT_ICON_BIN_FULL = "overlay-bin-full.png"
DEFAULT_ICON_TANK_LOW = "overlay-tank-low.png"
