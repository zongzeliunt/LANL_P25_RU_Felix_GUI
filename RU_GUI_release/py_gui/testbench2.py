#!/usr/bin/env python3
"""Generic Testbench for testing different routines and interactive access to RU modules"""
import argparse
import collections
import enum
import errno
import fire
import logging
import os
import pprint
import subprocess
import sys
import time
import unittest

from collections import OrderedDict
from datetime import datetime

import imageio
import numpy

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)
from module_includes import *

import communication
import ru_board
import ru_transceiver
import ru_chip_power
import i2c
import events
from hameg import Hameg

import pALPIDE
from pALPIDE import Alpide, Opcode, Addr
from ru_board import RUv1, RUv0_CRU

from communication import WishboneReadError, AddressMismatchError
import userdefinedexceptions

from sysmon import Sysmon

from curses import wrapper
import curses

from contextlib import contextmanager

#from testbench_base import *

# MVTX test beam config parameters

DIPSWITCH = 512 # binary value of the S8 dipswitch - 0 if program-on-powercycle is disabled

NUM_GTH = 9

TBNAME = "testbench2"

CHIP_MAP = []

GTH_SUBSET = [0,1,2,3,4,5,6,7,8] #single stave, 9-lane firmware
for i in [7,0,1,2,3,4,5,6,8]: CHIP_MAP.append((4,i)) #GT connector on ALICE board

SETUP_PULSE = False #configure pixels for masking if true; otherwise, use the masklist from text file

PULSE_DELAY = 20 #in units of 25ns clocks: 20 = 500 ns is the MOSAIC default

PULSE_VPULSEH = 170 #in DAC units: analog pulse strength is proportional to (VPULSEH-VPULSEL)
PULSE_VPULSEL = 100

PULSE_ANOTD = 1 #1 for analog pulsing, 0 for digital pulsing

# Static configuration parameters

USE_USB_COMM = False
USB_COMM_EXEC = os.path.join(
    script_path, "../../modules/usb_if/software/usb_comm_server/build/usb_comm")
SERIAL_CRU = "000001"
SERIAL_RDO = "000000"

# Flag this module to run standalone. If yes, performe advanced setup
STANDALONE_RUN = False
USE_RDO_USB = True
USE_CRU = False

GPIO_LIST = [0,1,2,3,4,5,6]

GPIO_SENSOR_MASK = {0:0b1111011,
                    1:0b1110111,
                    2:0b1101111,
                    3:0b1011111,
                    4:0b0111111,
                    5:0b0000000,
                    6:0b1111110}

exec(open("testbench_base.py").read())
