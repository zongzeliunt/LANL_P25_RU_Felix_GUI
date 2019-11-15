#!/usr/bin/env python
import charm_testbeam
from charm_testbeam import *

"""Script for running the Charm testbeam"""

#################################
# Diagnostic
############################################
# import importlib
# ht_exist = importlib.util.find_spec("hanging_threads")
# if ht_exist:
#     from hanging_threads import start_monitoring
#     monitoring_thread = start_monitoring()
############################################
###########################################


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
        self.cru = charm_test_global.cru
        self.rdo = charm_test_global.rdo
        self.powerboard = charm_test_global.powerboard
        self.logger = logging.getLogger("TestHardwareConnections")

    def tearDown(self):
        #self.powerboard.PowerOffIB()
        pass

    def test_board_connection(self):
        self.cru.check_git_hash_and_date(GITHASH_CRU)
        self.rdo.check_git_hash_and_date(GITHASH_RDO)

    def test_powerboard_connection(self):
        self.powerboard.SetupPowerIB()
        self.powerboard.ReadPowerADC()
        self.powerboard.PowerOnIB()
        self.powerboard.ReadPowerADC()
        self.powerboard.PowerOffIB()
        self.powerboard.ReadPowerADC()
    def test_sensor_connection(self):
        self.powerboard.SetupPowerIB()
        self.powerboard.PowerOnIB()

        NR_READ_WRITE = 30
        NR_TRIGGERS = 10

        charm_test_global.set_enable_strobe_generation(1)
        chips = charm_test_global.setup_sensors()
        for ch in chips:
            for j in range(NR_READ_WRITE):
                ch.write_reg(0x19,0xAA + j,readback=True)
            ch.propagate_prbs(PrbsRate=0)

        self.logger.info("Chip Readback OK")
        self.rdo.wait(500)
        time.sleep(0.5)
        initialized = self.rdo.gth.initialize()
        self.assertTrue(initialized,"Reset_done not received from GTH module")
        self.logger.info("RUv1 GTH initialized")

        time.sleep(0.5)
        self.rdo.wait(250)
        locked = self.rdo.gth.is_cdr_locked()
        self.assertNotIn(False,locked,"Not all CDR circuits are locked")
        self.logger.info("RUv1 GTH CDR locked")

        self.rdo.gth.enable_prbs(enable=True,commitTransaction=True)
        self.rdo.gth.reset_prbs_counter()

        # Read counters
        self.rdo.wait(1000)
        time.sleep(0.5)

        prbs_errors = self.rdo.gth.read_prbs_counter(self)
        for cnt,link in zip(prbs_errors,self.rdo.gth.transceivers):
            self.assertEqual(0,cnt,"PRBS Error on Link {0}".format(link))

        self.logger.info("RUv1 GTH PRBS locked")

        # Setup for normal operation
        for ch in chips:
            ch.propagate_data()
            ch.setreg_mode_ctrl(ChipModeSelector=1)

        self.assertTrue(charm_test_global.setup_readout(), "GTH setup failed")
        self.rdo.wait(1000)

        for _ in range(NR_TRIGGERS):
            chips[0].trigger()
            self.rdo.wait(1000)

        # check Event counter

        events_received = False
        retries = 0

        while not events_received and retries < 10:
            self.rdo.wait(1000)
            time.sleep(1)
            event_counters = self.rdo.datapathmon.read_counter(range(9),"EVENT_COUNT")
            events_received = all([trig == NR_TRIGGERS for trig in event_counters])
            retries += 1

        # counters should be != 0
        counters = self.rdo.datapathmon.read_all_counters()
        #pprint.pprint(counters[0])
        #print(counters)

        event_counters = self.rdo.datapathmon.read_counter(range(9),"EVENT_COUNT")
        #pprint.pprint(event_counters)
        error_counters = self.rdo.datapathmon.read_counter(range(9),"DECODE_ERROR_COUNT")
        #pprint.pprint(error_counters)
        for idx,cnt in enumerate(event_counters):
            self.assertEqual(cnt,NR_TRIGGERS,"Lane {0}, Not all Events received: {1}/{2}".format(idx,cnt,NR_TRIGGERS))

@unittest.skip("skip for now...")
class TestSoftware(unittest.TestCase):
    def setUp(self):
        self.cru = charm_test_global.cru
        self.rdo = charm_test_global.rdo
        self.powerboard = charm_test_global.powerboard
        self.logger = logging.getLogger("TestSoftware")

    def test_program_rdo(self):
        self.powerboard.PowerOffIB()
        print(charm_test_global.program_rdo())

import os
def main():
    global charm_test_global
    charm_test_global = CharmTestbench()

    charm_test_global.setup_logging()

    ### Don't powercycle for now
    #charm_test_global.setup_power()

    #charm_test_global.powercycle_RUv1()
    #input("\n\nplease reprogram RUv1, press \'enter\' when done\n\n")

#    charm_test_global.powercycle_RUv1()
#    input("wait_programm")
    charm_test_global.powercycle_powerboard()


    if not charm_test_global.check_power():
        print("Power problem. shutting down")
        return -1

    charm_test_global.setup_comms(use_external_dp2=False)
    #charm_test_global.comm_cru.discardall_dp1()
    charm_test_global.setup_cru()
    charm_test_global.setup_rdo()
    charm_test_global.setup_powerboard()

    unittest.main(verbosity=2,exit=False)

    if not charm_test_global.check_power():
        print("Power problem. shutting down")

    charm_test_global.stop()

    return os.EX_OK

if __name__ == '__main__':
    ret = main()
    sys.exit(ret)
