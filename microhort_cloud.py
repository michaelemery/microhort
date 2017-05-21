#!/usr/bin/env python
# --------------------------------------
#
# microhort.py
#  Central control module for micro-
#  horticulture project. Generates
#  events based on sensor readings.
#
# Massey University
# 158.335
# Creative Design Project 2017
# Microhort (Group 8)
#
# Authors:  Michael Emery,
#           Karl Judd,
#           Cliff Whiting.
#
# --------------------------------------

import RPi.GPIO as GPIO
import mysql.connector
import Adafruit_DHT
import json
import time
import copy
import data_log_request
import requests
from datetime import datetime

# --- SET GLOBAL CONSTANTS ---
SERVER = "http://ec2-54-70-146-220.us-west-2.compute.amazonaws.com"
# TODO - replace this with microhort.com


# # connection
# CONN = mysql.connector.connect(
#     user='iotcc_user',
#     password='158335danish',
#     host='iotcc-db-instance.cqmmjgzwow7o.us-west-2.rds.amazonaws.com',
#     database='microhort')
# CURSOR = CONN.cursor()

# set profile state constants
LOW = -1
STABLE = 0
HIGH = 1

# hardware info
SWITCH = 26
HT_SENSOR_MODEL = Adafruit_DHT.DHT22

# set GPIO state constants
OFF = GPIO.LOW
ON  = GPIO.HIGH

# configure GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(SWITCH, GPIO.FALLING)


def main():
    while True:
        config = init()
        previous_sensor_type_states = init_sensor_type_states(config['sensor'])
        while not GPIO.event_detected(SWITCH):
            sensor_type_states = evaluate_sensor_type_states(
                copy.deepcopy(previous_sensor_type_states), config['sensor'], config['profile_sensor']
            )
            for sensor_type_id in sensor_type_states:
                if sensor_type_states[sensor_type_id] != previous_sensor_type_states[sensor_type_id]:
                    previous_sensor_type_states[sensor_type_id] = init_sensor_type_states(config['sensor'])
                    signal_event(sensor_type_states, sensor_type_id, config)
            previous_sensor_type_states = sensor_type_states
        flush_event()
        print('\n\n======= SYSTEM RESTARTED =======\n')


# configure application with all start-up information
def init():
    mac = get_mac('eth0')
    # send HTTP GET to retrieve hub information	
    url = SERVER + "/getconfig"
    params = {"mac":str(mac)}
    resp = requests.get(url=url, params=params)
    config = convertMicroHortDictionary(json.loads(resp.text))
    if not any(config):
        print("something went wrong populating the config dict.")
        exit()
    return config


# build list of unique sensor types and initialise them with state of OPTIMAL
def init_sensor_type_states(sensors):
    sensor_type_states = {}
    for sensor in sensors:
        if sensor['sensor_type_id'] not in sensor_type_states:
            sensor_type_states[sensor['sensor_type_id']] = STABLE
    return sensor_type_states


# returns the state (LOW, OPTIMAL, HIGH) of all sensor types
def evaluate_sensor_type_states(sensor_type_states, sensors, profile):
    for sensor_type_id in sensor_type_states:
        average = get_average_value(sensor_type_id, sensors)
        if profile[sensor_type_id]['profile_sensor_low'] is not None and \
                average <= profile[sensor_type_id]['profile_sensor_low']:
            sensor_type_states[sensor_type_id] = LOW
        elif profile[sensor_type_id]['profile_sensor_high'] is not None and \
                average >= profile[sensor_type_id]['profile_sensor_high']:
            sensor_type_states[sensor_type_id] = HIGH
        else:
            sensor_type_states[sensor_type_id] = STABLE
    return sensor_type_states


# returns the average sensor reading for the specified sensor type
def get_average_value(sensor_type_id, sensors):
    total = 0
    count = 0
    for sensor in sensors:
        if sensor['sensor_type_id'] == sensor_type_id:
            if sensor['sensor_type_id'] == 1:
                humidity, temperature = Adafruit_DHT.read_retry(HT_SENSOR_MODEL, sensor['sensor_gpio'])
                total += temperature
                count += 1
                print('Temperature: {}'.format(int(total / count)))
            if sensor['sensor_type_id'] == 2:
                humidity, temperature = Adafruit_DHT.read_retry(HT_SENSOR_MODEL, sensor['sensor_gpio'])
                total += humidity
                count += 1
                print('   Humidity: {}'.format(int(total / count)))
        time.sleep(2)
    return int(total / count)


# generates an event log and signals an event to be controlled
def signal_event(sensor_type_state, sensor_type_id, config):
    state_dictionary = {-1: 'Low', -0: 'Stable', 1: 'High'}
    event_message = "{}: {} {} {}".format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        config['hub']['hub_name'],
        config['sensor_type'][sensor_type_id]['sensor_type_name'],
        state_dictionary[sensor_type_state[sensor_type_id]]
    )
    print("\n[SENSOR] {}\n".format(event_message))
    event_entry = {
        'event_dtg:': datetime.now(),
        'event_hub_id': config['hub']['hub_id'],
        'event_profile_id': config['hub']['hub_profile_id'],
        'event_sensor_type_id': sensor_type_id,
        'event_state': sensor_type_state[sensor_type_id],
        'event_message': event_message
    }
    append_event(event_entry)
    action_controller(event_entry, config['controller_type'], config['controller'])


# writes an entry in the event log
def append_event(event_entry):
    data_log_request.http_request(event_entry)
    pass


# stabilises the profile when in a non-stable event state
def action_controller(event_entry, controller_type, controller):
    pass


# return mac address of interface
def get_mac(interface):
    try:
        mac = open('/sys/class/net/' + interface + '/address').read()
    except IOError:
        print("Unknown interface (" + interface + ")\n")
        exit()
    return mac[0:17]


# return hub info dictionary matching a mac address
def get_hub(mac):
    query = (
        "SELECT hub_id, hub_mac, hub_name, hub_profile_id "
        "FROM hub "
        "WHERE hub_mac "
        "LIKE ('{}')".format(mac)
    )
    CURSOR.execute(query)
    hub = {}
    for hub_id, hub_mac, hub_name, hub_profile_id in CURSOR:
        hub.update({
            'hub_id': hub_id,
            'hub_mac': hub_mac,
            'hub_name': hub_name,
            'hub_profile_id': hub_profile_id})
    if not any(hub):
        print("Unregistered MAC (" + mac + ")\nDevice could not be configured.\n")
        exit()
    return hub


# returns a dictionary of controller types indexed by type id
def get_controller_types():
    query = (
        "SELECT controller_type_id, controller_type_name, controller_type_max_run_time, controller_type_min_rest_time  "
        "FROM controller_type "
    )
    CURSOR.execute(query)
    controller_types = {}
    for controller_type_id, controller_type_name, controller_type_max_run_time, controller_type_min_rest_time in CURSOR:
        controller_types.update({controller_type_id: {
            'controller_type_name': controller_type_name,
            'controller_type_max_run_time': controller_type_max_run_time,
            'controller_type_min_rest_time': controller_type_min_rest_time}})
    return controller_types


# returns a list of dictionaries for each controller
def get_controllers(hub_id):
    query = (
        "SELECT controller_id, controller_gpio, controller_type_id  "
        "FROM controller "
        "WHERE controller_hub_id "
        "LIKE ('{}')".format(hub_id)
    )
    CURSOR.execute(query)
    controller = []
    for controller_id, controller_gpio, controller_type_id in CURSOR:
        controller.append({
            'controller_id': controller_id,
            'controller_gpio': controller_gpio,
            'controller_type_id': controller_type_id})
    if not any(controller):
        print("No configured controllers. Add controllers then restart.\n")
        exit()
    return controller


# returns a dictionary of sensor types indexed by type id
def get_sensor_types():
    query = (
        "SELECT sensor_type_id, sensor_type_name, sensor_type_low_controller_type_id, "
        "sensor_type_high_controller_type_id "
        "FROM sensor_type "
    )
    CURSOR.execute(query)
    sensor_types = {}
    for sensor_type_id, sensor_type_name, sensor_type_low_controller_type_id, sensor_type_high_controller_type_id \
            in CURSOR:
        sensor_types.update({sensor_type_id: {
            'sensor_type_name': sensor_type_name,
            'sensor_type_low_controller_type_id': sensor_type_low_controller_type_id,
            'sensor_type_high_controller_type_id': sensor_type_high_controller_type_id}})
    return sensor_types


# returns a list of dictionaries for each sensor
def get_sensors(hub_id):
    query = (
        "SELECT sensor_id, sensor_gpio, sensor_type_id "
        "FROM sensor "
        "WHERE sensor_hub_id "
        "LIKE ('{}')".format(hub_id)
    )
    CURSOR.execute(query)
    sensor = []
    for sensor_id, sensor_gpio, sensor_type_id in CURSOR:
        sensor.append({
            'sensor_id': sensor_id,
            'sensor_gpio': sensor_gpio,
            'sensor_type_id': sensor_type_id})
    if not any(sensor):
        print("No configured sensors. Add sensors then restart.\n")
        exit()
    return sensor


# return profile information for given profile id
def get_profile(hub_profile_id):
    query = (
        "SELECT profile_id, profile_name "
        "FROM profile "
        "WHERE profile.profile_id "
        "LIKE ({})".format(hub_profile_id)
    )
    CURSOR.execute(query)
    profile = {}
    for profile_id, profile_name in CURSOR:
        profile = {'profile_id': profile_id, 'profile_name': profile_name}
    return profile


# return sensor profiles for given hub profile
def get_profile_sensor(hub_profile_id):
    query = (
        "SELECT profile_sensor_id, profile_id, sensor_type_id, profile_sensor_low, "
        "profile_sensor_high "
        "FROM profile_sensor "
        "WHERE profile_id "
        "LIKE %s"
    )
    CURSOR.execute(query, str(hub_profile_id))
    profile_sensor = {}
    for profile_sensor_id, profile_id, sensor_type_id, profile_sensor_low, profile_sensor_high in CURSOR:
        profile_sensor.update({
            sensor_type_id: {
                'profile_sensor_low': profile_sensor_low,
                'profile_sensor_high': profile_sensor_high
            }
        })
    return profile_sensor


# output configuration summary to the console
def show_config(config):
    print("\nIdentified MAC {}".format(config['hub']['hub_mac']))
    print("Welcome to {} running {}.".format(config['hub']['hub_name'], config['profile']['profile_name']))
    print("\nLimits:")
    for sensor_type in config['sensor_type']:
        print("  {} ({} <-> {})".format(
            config['sensor_type'][sensor_type]['sensor_type_name'],
            config['profile_sensor'][sensor_type]['profile_sensor_low'],
            config['profile_sensor'][sensor_type]['profile_sensor_high']))
    print("\nGPIO <-- Sensor Register:")
    for sensor_type in config['sensor']:
        print("  {:2d} <-- {}".format(sensor_type['sensor_gpio'],
                                      config['sensor_type'][sensor_type['sensor_type_id']]['sensor_type_name']));
    print("\nGPIO --> Controller Register:")
    for controller in config['controller']:
        print("  {:2d} --> {}".format(controller['controller_gpio'],
                                      config['controller_type'][controller['controller_type_id']][
                                          'controller_type_name']))
    print("")


# write configuration data to file
def write_config(config, filename):
    with open(filename, 'w') as f:
        json.dump(config, f)


# read configuration data from file
def read_config(filename):
    with open(filename, 'r') as f:
        config = ConvertMicroHortDictionary(json.load(f))
    return config

# Convert the JSON to work a PY dict with int keys.
# This makes any keys that are int+strings become ints.
# if something is broken loading from read_config(), it could definitely be this code.
def convertIfDigit(dictionary):
    for k in dictionary:
        if (type(k) is str or type(k) is unicode) and k.isdigit():
            dictionary[int(k)] = dictionary.pop(k)
    return dictionary

def convertMicroHortDictionary(dictionary):
    if type(dictionary) is not dict:
        return
    for k in dictionary:
        if type(dictionary[k]) is dict:
            convertIfDigit(dictionary[k])
            convertMicroHortDictionary(dictionary[k])
    return dictionary

# flush residual button presses to prevent false events
def flush_event():
    time.sleep(0.5)
    GPIO.event_detected(SWITCH)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        pass