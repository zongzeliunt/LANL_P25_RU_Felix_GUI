#!/usr/bin/env python
import charm_testbeam
from charm_testbeam import *

"""Script for initializing (and testing) the lab setup

Setup is composed of a

RUv0 acting as CRU emulator,
RUv1
IB stave

The hameg power supply is connected:
Ch1 => RUv1
CH2 => IB stave AVdd (regulator)
CH3 => IB stave DVdd (regulator)
"""

import logging
import time
import unittest
import sys

sys.path.append('../../modules/board_support_software/software/py/')


from module_includes import *

import communication
import ru_board
import ru_transceiver
import ru_chip_power
import i2c
import events
from hameg import Hameg


import unittest


from pALPIDE import *
from ru_board import RUv1, RUv0_CRU

from communication import WishboneReadError, AddressMismatchError
import userdefinedexceptions

class TestHardwareConnections(unittest.TestCase):
    """Test to run for verifying proper connections between all devices"""
    def setUp(self):
        self.cru = charm_test_global.testbench.cru
        self.rdo = charm_test_global.testbench.rdo
        self.logger = logging.getLogger("TestHardwareConnections")

    def tearDown(self):
        pass

    def test_board_connection(self):
        self.cru.check_git_hash_and_date(GITHASH_CRU)
        self.rdo.check_git_hash_and_date(GITHASH_RDO)

    def single_sensor_dctr(self, sensor=0):
        NR_READ_WRITE = 30
        tb = charm_test_global.testbench
        tb.setup_sensors(enable_strobe_generation=0)
        tb.test_chips(nrfirst=sensor, nrlast=sensor, nrtests=NR_READ_WRITE)

    def test_single_sensor_dctrl0(self):
        self.single_sensor_dctr(sensor=0)
    def test_single_sensor_dctrl1(self):
        self.single_sensor_dctr(sensor=1)
    def test_single_sensor_dctrl2(self):
        self.single_sensor_dctr(sensor=2)
    def test_single_sensor_dctrl3(self):
        self.single_sensor_dctr(sensor=3)
    def test_single_sensor_dctrl4(self):
        self.single_sensor_dctr(sensor=4)
    def test_single_sensor_dctrl5(self):
        self.single_sensor_dctr(sensor=5)
    def test_single_sensor_dctrl6(self):
        self.single_sensor_dctr(sensor=6)
    def test_single_sensor_dctrl7(self):
        self.single_sensor_dctr(sensor=7)
    def test_single_sensor_dctrl8(self):
        self.single_sensor_dctr(sensor=8)

    def test_sensor_connection(self):
        NR_TRIGGERS = 10

        tb = charm_test_global.testbench
        tb.setup_sensors(enable_strobe_generation=0)
        tb.test_chips(nrtests=0)
        tb.setup_readout()

        tb.test_prbs(runtime=3)
        tb.test_readout()

def main():
    global charm_test_global
    charm_test_global = TestbeamTest()

    RUv1_force_powercycle = True
    RUv0_force_powercycle = True
    sensors_force_powercyle = True

    charm_test_global.setup_logging()
    charm_test_global.log_powersupply_values()

    charm_test_global.testbench.setup_comms(ctlOnly=False)
    charm_test_global.testbench.setup_boards()

    charm_test_global.testbench.cru.set_gbtx_forward_to_usb(0, commitTransaction=True)

    ruv1_is_on = charm_test_global.hameg.is_channel_on(1)
    charm_test_global.logger.info("RUv1 is on: {0}".format(ruv1_is_on))
    if not ruv1_is_on or RUv1_force_powercycle:
        charm_test_global.logger.info("Powercycle RUv1")
        charm_test_global.powercycle_RUv1()
        time.sleep(2)

    charm_test_global.log_powersupply_values()
    charm_test_global.testbench.comm_cru.discardall_dp1()

    input("Program RUv1, press enter when done")

    charm_test_global.testbench.cru.initialize()
    charm_test_global.testbench.cru.set_gbtx_forward_to_usb(1, commitTransaction=True)
    charm_test_global.testbench.rdo.initialize()

    charm_test_global.log_powersupply_values()
    if not charm_test_global.hameg.is_channel_on(2) or not charm_test_global.hameg.is_channel_on(3) or sensors_force_powercyle:
        charm_test_global.setup_stave_power()
        charm_test_global.powercycle_stave()

    charm_test_global.log_powersupply_values()

    unittest.main(verbosity=2,exit=False)

    charm_test_global.testbench.stop()

    return os.EX_OK

if __name__ == '__main__':
    ret = main()
    sys.exit(ret)
