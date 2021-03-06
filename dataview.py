#!/usr/bin/env python
# --------------------------------------
#
# dataview.py
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

import mysql.connector

cnx = mysql.connector.connect(user='iotcc_user', password='158335danish',
                              host='iotcc-db-instance.cqmmjgzwow7o.us-west-2.rds.amazonaws.com', database='microhort')
cursor = cnx.cursor()


def main():
    view_owner()
    view_hub()
    view_controller_type()
    view_controller()
    view_sensor_type()
    view_sensor()
    view_profile()
    view_profile_sensor()
    print("")
    cursor.close()
    cnx.close()


def view_owner():
    heading("Owner")
    query = (
        "SELECT owner_id, owner_name, owner_email "
        "FROM owner"
    )
    cursor.execute(query)
    for (owner_id, owner_name, owner_email) in cursor:
        print("{0:6d} {1:20} {2}".format(owner_id, owner_name, owner_email))


def view_hub():
    heading("Hub")
    query = (
        "SELECT hub_id, hub_mac, hub_name, owner_name "
        "FROM hub "
        "JOIN owner ON hub.hub_owner_id=owner.owner_id"
    )
    cursor.execute(query)
    for (hub_id, hub_mac, hub_name, hub_owner_id) in cursor:
        print("{0:6d} {1:20} {2:18} {3:20}".format(hub_id, hub_mac, hub_name, hub_owner_id))


def view_controller_type():
    heading("Controller Type")
    query = (
        "SELECT controller_type_id, controller_type_name, controller_type_max_run_time, controller_type_min_rest_time "
        "FROM controller_type"
    )
    cursor.execute(query)
    for (controller_type_id, controller_type_name, controller_type_max_run_time, controller_type_min_rest_time) \
            in cursor:
        print("{0:6d} {1:20s} {2:6d} {3:6d}".format(controller_type_id, controller_type_name,
                                                    controller_type_max_run_time, controller_type_min_rest_time))


def view_controller():
    heading("Controller")
    query = (
        "SELECT controller_id, hub_name, controller_gpio, controller_type_name "
        "FROM controller "
        "JOIN hub ON controller.hub_id=hub.hub_id "
        "JOIN controller_type ON controller.controller_type_id=controller_type.controller_type_id"
    )
    cursor.execute(query)
    for (controller_id, hub_name, controller_gpio, controller_type_name) in cursor:
        print("{0:6d} {1:20} {2:6} {3:20}".format(controller_id, hub_name, controller_gpio, controller_type_name))


def view_sensor_type():
    heading("Sensor Type")
    query = (
        "SELECT sensor_type_id, sensor_type_name "
        "FROM sensor_type"
    )
    cursor.execute(query)
    for (sensor_type_id, sensor_type_name) in cursor:
        print("{0:6d} {1:20}".format(sensor_type_id, sensor_type_name))


def view_sensor():
    heading("Sensor")
    query = (
        "SELECT sensor_id, hub_name, sensor_gpio, sensor_type_name "
        "FROM sensor "
        "JOIN hub ON sensor.hub_id=hub.hub_id "
        "JOIN sensor_type ON sensor.sensor_type_id=sensor_type.sensor_type_id"
    )
    cursor.execute(query)
    for (sensor_id, hub_name, sensor_gpio, sensor_type_name) in cursor:
        print("{0:6d} {1:20} {2:6} {3:20}".format(sensor_id, hub_name, sensor_gpio, sensor_type_name))


def view_profile():
    heading("Profile")
    query = ("SELECT profile_id, profile_name "
             "FROM profile"
    )
    cursor.execute(query)
    for (profile_id, profile_name) in cursor:
        print("{0:6d} {1:20}".format(profile_id, profile_name))


def view_profile_sensor():
    heading("Profile Sensors")
    query = (
        "SELECT profile_sensor.profile_sensor_id, profile_name, sensor_type_name, profile_sensor_low, "
        "profile_sensor_optimal, profile_sensor_high "
        "FROM profile_sensor "
        "JOIN profile ON profile_sensor.profile_id=profile.profile_id "
        "JOIN sensor_type ON profile_sensor.sensor_type_id=sensor_type.sensor_type_id"
    )
    cursor.execute(query)
    for (profile_sensor_id, profile_name, sensor_type_name, profile_sensor_low, profile_sensor_optimal,
         profile_sensor_high) in cursor:
        print("{0:6d} {1:20} {2:12} {3:>6} {4:>6} {5:>6}".format(profile_sensor_id, profile_name, sensor_type_name,
                                                                 profile_sensor_low, profile_sensor_optimal,
                                                                 profile_sensor_high))


def heading(heading_name):
    print("\n" + heading_name)
    print('-' * len(heading_name))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        cursor.close()
        cnx.close()
