#!/usr/bin/env python
# --------------------------------------
#
# sense_thp.py
#
# Read sensor data from SenseHat sensor
# (Raspberry Pi) and output to console.
#
#
# Author: Michael Emery (12154337)
#         Massey University
#
# Copyright (c) 2017 Foofactory
#
# --------------------------------------

from sense_hat import SenseHat

sense = SenseHat()

def main():

    sense.clear()
    while True:
        temperature = sense.get_temperature()
        humidity = sense.get_humidity()
        pressure = sense.get_pressure()
        print("Temperature : {}".format(temperature))
        print("Humidity    : {}".format(humidity))
        print("Pressure    : {}".format(pressure))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        sense.clear()
