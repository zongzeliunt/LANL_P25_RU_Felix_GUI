#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
krzysztof.sielewicz@cern.ch
beam_shutter.py - BeamShutter class
"""

import serial
import logging

import fire
import os

PORT_BEAM_SHUTTER = '/dev/ttyBEAM_SHTR_CNTRL'


class BeamShutter(object):
    """ Beam Shutter class"""

    def __init__(self, port):
        """ Init function """
        self.logger = logging.getLogger("BeamShutter")
        self.port_opened = False
        try:
            self.beam_shutter_serial_port = serial.Serial(port,
                                                          baudrate=115200,
                                                          timeout=0.1,
                                                          write_timeout=1)
            self.port_opened = True
        except serial.SerialException:
            self.logger.error("Cannot open Beam Shutter Controller port!")
            raise


    def beam_off(self):
        """ Close the beam shutter """
        if not self.port_opened:
            raise Exception("Serial port for BeamShutter not opened")

        self.beam_shutter_serial_port.write('*B1OS1H\r'.encode('utf-8'))
        msg = self.beam_shutter_serial_port.read(6)
        self.logger.info("Beam OFF. Message: %s",msg)

    def beam_on(self):
        """ Open the beam shutter """
        if not self.port_opened:
            raise Exception("Serial port for BeamShutter not opened")

        self.beam_shutter_serial_port.write('*B1OS1L\r'.encode('utf-8'))
        msg = self.beam_shutter_serial_port.read(6)
        self.logger.info("Beam ON. Message: %s",msg)

    def beam_shutter_2_off(self):
        """ Open the beam shutter """
        if not self.port_opened:
            raise Exception("Serial port for BeamShutter not opened")

        self.beam_shutter_serial_port.write('*B1OS2H\r'.encode('utf-8'))
        msg = self.beam_shutter_serial_port.read(6)
        self.logger.info("Beam shutter 2. Message: %s",msg)

    def beam_shutter_2_on(self):
        """ Open the beam shutter """
        if not self.port_opened:
            raise Exception("Serial port for BeamShutter not opened")

        self.beam_shutter_serial_port.write('*B1OS2L\r'.encode('utf-8'))
        msg = self.beam_shutter_serial_port.read(6)
        self.logger.info("Beam shutter 2. Message: %s",msg)

class DummyBeamShutter(object):
    def __init__(self):
        self.logger = logging.getLogger("BeamShutter")
        self.logger.info("Using dummy beam shutter")
    def beam_off(self):
        """ Close the beam shutter """
        pass

    def beam_on(self):
        """ Open the beam shutter """
        pass


if __name__ == "__main__":
    tb = BeamShutter(port=PORT_BEAM_SHUTTER)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_file = os.path.join('logs', "beam_shutter.log")
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    try:
        fire.Fire(tb)
    except:
        raise
    finally:
        pass
