import argparse
import configparser
import json
import logging
import os
import socket
import sys
import time
from ast import literal_eval
from logging.handlers import RotatingFileHandler

import six

import paho.mqtt.client as mqtt
from roomba import roomba
from roomba.password import Password


def parse_args():
    default_icon_path = os.path.join(os.path.dirname(__file__), "res")
    # -------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description="Forward MQTT data from Roomba 980 to local MQTT broker"
    )
    parser.add_argument(
        "-f",
        "--configfile",
        action="store",
        type=str,
        default="./config.ini",
        help="config file name (default: ./config.ini)",
    )
    parser.add_argument(
        "-n",
        "--roombaName",
        action="store",
        type=str,
        default="",
        help='optional Roomba name (default: "")',
    )
    parser.add_argument(
        "-t",
        "--topic",
        action="store",
        type=str,
        default="#",
        help="Roomba MQTT Topic to subscribe to (can use wildcards # and "
        "+ default: #)",
    )
    parser.add_argument(
        "-T",
        "--brokerFeedback",
        action="store",
        type=str,
        default="/roomba/feedback",
        help="Topic on broker to publish feedback to (default: "
        "/roomba/feedback</name>)",
    )
    parser.add_argument(
        "-C",
        "--brokerCommand",
        action="store",
        type=str,
        default="/roomba/command",
        help="Topic on broker to publish commands to (default: "
        "/roomba/command</name>)",
    )
    parser.add_argument(
        "-S",
        "--brokerSetting",
        action="store",
        type=str,
        default="/roomba/setting",
        help="Topic on broker to publish settings to (default: "
        "/roomba/setting</name>)",
    )
    parser.add_argument(
        "-b",
        "--broker",
        action="store",
        type=str,
        default=None,
        help="ipaddress of MQTT broker (default: None)",
    )
    parser.add_argument(
        "-p",
        "--port",
        action="store",
        type=int,
        default=1883,
        help="MQTT broker port number (default: 1883)",
    )
    parser.add_argument(
        "-U",
        "--user",
        action="store",
        type=str,
        default=None,
        help="MQTT broker user name (default: None)",
    )
    parser.add_argument(
        "-P",
        "--password",
        action="store",
        type=str,
        default=None,
        help="MQTT broker password (default: None)",
    )
    parser.add_argument(
        "-R",
        "--roombaIP",
        action="store",
        type=str,
        default=None,
        help="ipaddress of Roomba 980 (default: None)",
    )
    parser.add_argument(
        "-u",
        "--blid",
        action="store",
        type=str,
        default=None,
        help="Roomba 980 blid (default: None)",
    )
    parser.add_argument(
        "-w",
        "--roombaPassword",
        action="store",
        type=str,
        default=None,
        help="Roomba 980 password (default: None)",
    )
    parser.add_argument(
        "-i",
        "--indent",
        action="store",
        type=int,
        default=0,
        help="Default indentation=auto",
    )
    parser.add_argument(
        "-l",
        "--log",
        action="store",
        type=str,
        default="./Roomba.log",
        help="path/name of log file (default: ./Roomba.log)",
    )
    parser.add_argument(
        "-e",
        "--echo",
        action="store_false",
        default=True,
        help="Echo to Console (default: True)",
    )
    parser.add_argument(
        "-D", "--debug", action="store_true", default=False, help="debug mode"
    )
    parser.add_argument(
        "-r",
        "--raw",
        action="store_true",
        default=False,
        help="Output raw data to mqtt, no decoding of json data",
    )
    parser.add_argument(
        "-j",
        "--pretty_print",
        action="store_true",
        default=False,
        help="pretty print json in logs",
    )
    parser.add_argument(
        "-c",
        "--continuous",
        action="store_false",
        default=True,
        help="Continuous connection to Roomba (default: True)",
    )
    parser.add_argument(
        "-d",
        "--delay",
        action="store",
        type=int,
        default=1000,
        help="Disconnect period for non-continuous connection (default: " "1000ms)",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        action="store",
        type=str,
        default="",
        help='Exclude topics that have this in them (default: "")',
    )
    parser.add_argument(
        "--cert",
        action="store",
        type=str,
        default="/etc/ssl/certs/ca-certificates.crt",
        help="Set the certificate to use for MQTT communication with the Roomba",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s ({})".format(roomba.__version__),
        help="Display version of this program",
    )
    return parser.parse_args()


def main():
    arg = parse_args()

    # ----------- Local Routines ------------

    def broker_on_connect(client, userdata, flags, rc):
        log.debug("Broker Connected with result code " + str(rc))
        # subscribe to roomba feedback, if there is more than one roomba, the
        # roombaName is added to the topic to subscribe to
        if rc == 0:
            if brokerCommand != "":
                if len(roombas) == 1:
                    mqttc.subscribe(brokerCommand)
                else:
                    for myroomba in roomba_list:
                        mqttc.subscribe(brokerCommand + "/" + myroomba.roombaName)
            if brokerSetting != "":
                if len(roombas) == 1:
                    mqttc.subscribe(brokerSetting)
                else:
                    for myroomba in roomba_list:
                        mqttc.subscribe(brokerSetting + "/" + myroomba.roombaName)

    def broker_on_message(mosq, obj, msg):
        # publish to roomba, if there is more than one roomba, the roombaName
        # is added to the topic to publish to
        msg.payload = msg.payload.decode("utf-8")
        if "command" in msg.topic:
            log.info("Received COMMAND: %s" % str(msg.payload))
            if len(roombas) == 1:
                roomba_list[0].send_command(str(msg.payload))
            else:
                for myroomba in roomba_list:
                    if myroomba.roombaName in msg.topic:
                        myroomba.send_command(str(msg.payload))
        elif "setting" in msg.topic:
            log.info("Received SETTING: %s" % str(msg.payload))
            cmd = str(msg.payload).split()
            if len(roombas) == 1:
                roomba_list[0].set_preference(cmd[0], cmd[1])
            else:
                for myroomba in roomba_list:
                    if myroomba.roombaName in msg.topic:
                        myroomba.set_preference(cmd[0], cmd[1])
        else:
            log.warn("Unknown topic: %s" % str(msg.topic))

    def broker_on_publish(mosq, obj, mid):
        pass

    def broker_on_subscribe(mosq, obj, mid, granted_qos):
        log.debug("Broker Subscribed: %s %s" % (str(mid), str(granted_qos)))

    def broker_on_disconnect(mosq, obj, rc):
        log.debug("Broker disconnected")
        if rc == 0:
            sys.exit(0)

    def broker_on_log(mosq, obj, level, string):
        log.info(string)

    def read_config_file(file="./config.ini"):
        # read config file
        Config = configparser.ConfigParser()
        try:
            Config.read(file)
            log.info("reading info from config file %s" % file)
            roombas = {}
            for address in Config.sections():
                roomba_data = literal_eval(Config.get(address, "data"))
                roombas[address] = {
                    "blid": Config.get(address, "blid"),
                    "password": Config.get(address, "password"),
                    "roombaName": roomba_data.get("robotname", None),
                }
        except Exception as e:
            log.warn("Error reading config file %s" % e)
        return roombas


    def setup_logger(logger_name, log_file, level=logging.DEBUG, console=False):
        try:
            l = logging.getLogger(logger_name)
            if logger_name == __name__:
                formatter = logging.Formatter(
                    "[%(levelname)1.1s %(asctime)s] %(message)s"
                )
            else:
                formatter = logging.Formatter("%(message)s")
            fileHandler = RotatingFileHandler(
                log_file, mode="a", maxBytes=2000000, backupCount=5
            )
            fileHandler.setFormatter(formatter)
            if console == True:
                streamHandler = logging.StreamHandler()

            l.setLevel(level)
            l.addHandler(fileHandler)
            if console == True:
                streamHandler.setFormatter(formatter)
                l.addHandler(streamHandler)
        except IOError as e:
            if e[0] == 13:  # errno Permission denied
                print(
                    "Error: %s: You probably don't have permission to "
                    "write to the log file/directory - try sudo" % e
                )
            else:
                print("Log Error: %s" % e)
            sys.exit(1)

    args = parse_args()

    if arg.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # setup logging
    setup_logger(__name__, arg.log, level=log_level, console=arg.echo)

    log = logging.getLogger(__name__)

    log.debug("-- DEBUG Mode ON -")
    log.info("<CNTRL C> to Exit")
    log.info("Roomba 980 MQTT data Interface")

    roombas = {}

    if arg.blid is None or arg.roombaPassword is None:
        roombas = read_config_file(arg.configfile)
        if len(roombas) == 0:
            log.warn(
                "No roomba or config file defined, I will attempt to "
                "discover Roombas, please put the Roomba on the dock "
                "and follow the instructions:"
            )
            if arg.roombaIP is None:
                Password(file=arg.configfile)
            else:
                Password(arg.roombaIP, file=arg.configfile)
            roombas = read_config_file(arg.configfile)
            if len(roombas) == 0:
                log.error(
                    "No Roombas found! You must specify RoombaIP, blid "
                    "and roombaPassword to run this program, or have "
                    "a config file, use -h to show options."
                )
                sys.exit(0)
            else:
                log.info("Success! %d Roombas Found!" % len(roombas))
    else:
        roombas[arg.roombaIP] = {
            "blid": arg.blid,
            "password": arg.roombaPassword,
            "roombaName": arg.roombaName,
        }

    # set broker = "127.0.0.1"  # mosquitto broker is running on localhost
    mqttc = None
    if arg.broker is not None:
        brokerCommand = arg.brokerCommand
        brokerSetting = arg.brokerSetting

        # connect to broker
        mqttc = mqtt.Client()
        # Assign event callbacks
        mqttc.on_message = broker_on_message
        mqttc.on_connect = broker_on_connect
        mqttc.on_disconnect = broker_on_disconnect
        mqttc.on_publish = broker_on_publish
        mqttc.on_subscribe = broker_on_subscribe
        # uncomment to enable logging
        # mqttc.on_log = broker_on_log

        try:
            if arg.user != None:
                mqttc.username_pw_set(arg.user, arg.password)
            log.info("connecting to broker")
            # Ping MQTT broker every 60 seconds if no data is published
            # from this script.
            mqttc.connect(arg.broker, arg.port, 60)

        except socket.error:
            log.error("Unable to connect to MQTT Broker")
            mqttc = None

    roomba_list = []
    for addr, info in six.iteritems(roombas):
        log.info("Creating Roomba object %s" % addr)
        # NOTE: cert_name is a default certificate. change this if your
        # certificates are in a different place. any valid certificate will
        # do, it's not used but needs to be there to enable mqtt TLS encryption
        # instansiate Roomba object
        # minnimum required to connect on Linux Debian system
        # myroomba = Roomba(address, blid, roombaPassword)
        roomba_list.append(
            roomba.Roomba(
                addr,
                blid=info["blid"],
                password=info["password"],
                topic=arg.topic,
                continuous=arg.continuous,
                clean=False,
                cert_name=args.cert,
                roombaName=info["roombaName"],
            )
        )

    for myroomba in roomba_list:
        log.info("connecting Roomba %s" % myroomba.address)
        # all these are optional, if you don't include them, the defaults
        # will work just fine
        if arg.exclude != "":
            myroomba.exclude = arg.exclude
        myroomba.set_options(
            raw=arg.raw, indent=arg.indent, pretty_print=arg.pretty_print
        )
        if not arg.continuous:
            myroomba.delay = arg.delay // 1000
        if arg.broker is not None:
            # if you want to publish Roomba data to your own mqtt broker
            # (default is not to) if you have more than one roomba, and
            # assign a roombaName, it is addded to this topic
            # (ie brokerFeedback/roombaName)
            myroomba.set_mqtt_client(mqttc, arg.brokerFeedback)
        # finally connect to Roomba - (required!)
        myroomba.connect()

    try:
        if mqttc is not None:
            mqttc.loop_forever()
        else:
            while True:
                log.info(
                    "Roomba Data: %s" % json.dumps(myroomba.master_state, indent=2)
                )
                time.sleep(5)

    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        mqttc.disconnect()
        sys.exit(0)


if __name__ == "__main__":
    main()
