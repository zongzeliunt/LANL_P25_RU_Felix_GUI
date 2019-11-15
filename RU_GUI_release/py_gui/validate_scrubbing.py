#!/usr/bin/env python
"""Script for running the Charm testbeam"""

#################################
# Diagnostic
############################################
#import importlib
#ht_exist = importlib.util.find_spec("hanging_threads")
#if ht_exist:
#from hanging_threads import start_monitoring
#monitoring_thread = start_monitoring()
############################################
###########################################


import logging
from datetime import datetime
import time
import subprocess
import os
import sys
import argparse
from collections import OrderedDict
import sys
import select

import json
import jsonpickle
from enum import Enum

import filecmp
import shutil
import subprocess

sys.path.append('../../modules/board_support_software/software/py/')


from module_includes import *

import communication
import ru_board
import ru_transceiver
import ru_chip_power
import ws_master_monitor
import i2c
import events
from hameg import Hameg

import pALPIDE
from pALPIDE import Alpide, Opcode, Addr
from ru_board import RUv1, RUv0_CRU

import testbench

from communication import WishboneReadError, AddressMismatchError
import userdefinedexceptions

from sysmon import Sysmon

#JCM
sys.path.append('jcm/')
import jcm_control_server

jcm_server_address = "localhost"
jcm_server_port = 8001

class TestMode(Enum):
    JCM = 0
    PA3 = 1

def is_pa3_programming(test_mode):
    return test_mode == TestMode.PA3

TEST_MODE = TestMode.PA3
NR_FAULTS_INJECT = 100
FAULT_INJECT_DELAY = 10

# Static Configuration parameters
USB_COMM_EXEC = "../../modules/usb_if/software/usb_comm_server/build/usb_comm"
SERIAL_CRU = "000001"
SERIAL_RDO = "000000"
HAMEG_PORT = "/dev/ttyHAMEG0"

#GITHASH_RDO = 0x035780cb # no uController
GITHASH_RDO = 0x0a045881
GITHASH_CRU = 0x048ff336

class DataPoint(object):
    """Datapoint for collecting continuous readout data"""
    def __init__(self):
        self.timestamp = None
        self.hameg_values = None
        self.cru_counters = None
        self.cru_adcs = None
        self.cru_gpio = None
        self.pa3_values = None
        self.powerboard_values = None
        self.chipdata = None
        self.dctrl_counters = None
        self.gth_aligned = None
        self.gth_status = None
        self.lane_counters = OrderedDict()
        self.radmon_dctrl           = None
        self.radmon_gbtx01          = None
        self.radmon_gbtx2           = None
        self.radmon_wishbone_master = None
        self.radmon_dp_fifos        = None
        self.radmon_sysmon          = None
        self.radmon_mismatch_dctrl           = None
        self.radmon_mismatch_gbtx01          = None
        self.radmon_mismatch_gbtx2           = None
        self.radmon_mismatch_wishbone_master = None
        self.radmon_mismatch_sysmon          = None
        self.wsmstr_rderr = None
        self.wsmstr_wrerr = None
        self.sysmon_vccint = None
        self.sysmon_vccaux = None
        self.sysmon_vccbram = None
        self.sysmon_vcc_alpide = None
        self.sysmon_vcc_sca = None
        self.sysmon_temp = None
        self.sysmon_tmr_status = None
        self.mmcm_monitor_counters = None
        self.mmcm_monitor_lock_counters = None
        self.gbtx_flow_monitor_counters = None
        self.spi_micro_test_counters = None

class ExitStatus(object):
    def __init__(self):
        self.timestamp =None
        self.exit_id = None
        self.msg = None
        self.sca_gpio = None
        self.powerlatch_status = None
        self.chip0_pll_status = None
        self.run_error = None
        self.faults_injected = None
        self.fuse_triggered = None
        self.discardall_dp1_success = None

class ScrubbingCyclesDataPoint(object):
    def __init__(self):
        self.start_timestamp = None
        self.stop_timestamp = None

def heardKeypress():
    i,o,e = select.select([sys.stdin],[],[],0.0001)
    for s in i:
        if s == sys.stdin:
            in_val = sys.stdin.readline()
            return in_val.strip()
    return None


class TestbeamTest(object):

    def __init__(self):
        self.hameg = Hameg(HAMEG_PORT, reset=False)
        self.testbench = testbench.Testbench(use_usb_comm=True)

        self.logger = None

        self.logdir = None

        # Data files
        self.datafile = None
        self.datafilepath = None

        # PrefetchComm
        self.sequence_cru = None
        self.sequence_rdo = None

        self.logger = logging.getLogger("testbeam_testbench")

        # JCM
        self.jcm_control_client = None
        self.faults_injected = None

        # Scrubbing
        self.manual_scrubbing_info = []

        # live monitor
        self.tot_read_counter = 0

        # readback files
        self.pre_injection_file   = None
        self.after_injection_file = None
        self.after_scrubbing_file = None
        self.readback_bkp = None

    def setup_power(self):
        self.hameg.activate_output(False)
        self.hameg.configure_channel(1,5.0,3.5)
        self.hameg.activate_channels([1])
        self.hameg.deactivate_channels([2,3])
        self.hameg.activate_output(True)

    def poweron_RUv0(self,force_powercycle=False):
        is_on = True # TODO: Connect to proper hameg
        if not is_on or force_powercycle:
            testbeam_test.logger.info("Powercycle CRU")
            #testbeam_test.setup_power()
            #time.sleep(3)
            self.logger.warning("Poweron CRU is not Implemented yet: Connect to proper hameg configuration")

    def poweroff_RUv0(self):
        self.logger.warning("Poweroff CRU is not Implemented yet")

    def connect_jcm(self):
        try:
            self.jcm_control_client = jcm_control_server.JcmControlClient(jcm_server_address, jcm_server_port)
        except Exception as e:
            self.logger.info("Could not connect to JCM")
            self.logger.info(e,exc_info=True)
            return False
        return True

    def readback_jcm(self, readback_name, empty_folder=False, backup_readback=False):
        """Stores the readback files in the /tmp/read_data_<readback_name>.rdb"""
        assert isinstance(readback_name, str)
        READBACK_FOLDER = 'readback'
        pwd = os.getcwd()
        folder = pwd + '/' + READBACK_FOLDER
        if empty_folder:
            if os.path.exists(folder):
                shutil.rmtree(folder)
            os.makedirs(folder)

        file_name = 'readBack_{0}.data'.format(readback_name)
        copy_path = folder + '/' + file_name
        self.jcm_control_client.start_readback()
        time.sleep(2)
        while not self.jcm_control_client.is_readback_finished():
            time.sleep(0.5)
        # File is available (dimention > 0) around 5 seconds after Readback_Complete status!
        time.sleep(10)

        result = os.system('scp -B root@jcm_device:/tmp/readBack.data {0} 1>&2'.format(copy_path))
        self.logger.info(result)
        time.sleep(2)
        self.logger.info(os.stat(copy_path).st_size)
        assert os.path.isfile(copy_path)
        assert os.stat(copy_path).st_size != 0
        self.logger.info("readback file copied to {0}".format(copy_path))
        if backup_readback:
            self.readback_bkp = 'readBack_bkp.data'
            self.jcm_control_client.rename_readback_file(file_name=self.readback_bkp)
        return copy_path

    def analyse_readback_files(self):
        assert self.pre_injection_file   is not None
        assert self.after_injection_file is not None
        assert self.after_scrubbing_file is not None

        #diff_original_scrubbed = difflib.SequenceMatcher(None, open(self.pre_injection_file).readlines(), open(self.after_scrubbing_file).readlines())
        diff_original_scrubbed = filecmp.cmp(self.pre_injection_file, self.after_scrubbing_file)
        diff_original_injected = filecmp.cmp(self.pre_injection_file, self.after_injection_file)

        assert diff_original_scrubbed, "Original and scrubbed files differ"
        assert not diff_original_injected, "Original and injected files DO NOT differ"

        self.logger.info("\n\n\n\t\t\tScubbing validated with {0}\n\n".format(TEST_MODE.name))

    def restore_readback_file(self):
        self.jcm_control_client.rename_readback_file(restore=True, file_name=self.readback_bkp)

    def single_scrub_cycle(self):
        if TEST_MODE == TestMode.JCM:
            self.restore_readback_file()
            self.jcm_control_client.start_blind_scrubber()
            time.sleep(1)
            self.jcm_control_client.stop_blind_scrubber()
            while not self.jcm_control_client.is_stopped():
                time.sleep(0.25)
            self.logger.info("Scrubbing Done")
            with open(self.logdir + "/jcm_blind_scrubbing_report.log",'a') as scrub_report:
                scrub_report.write(self.jcm_control_client.read_messages())
        elif TEST_MODE == TestMode.PA3:
            self.testbench.cru.pa3.clear_scrubbing_counter()
            self.testbench.cru.pa3.trigger_single_scrub()
            tries = 0
            max_tries=10
            finished = False
            time.sleep(5)
            while not finished and tries < max_tries:
                time.sleep(1)
                finished = self.testbench.cru.pa3.is_idle()
                tries += 1
            counter = self.testbench.cru.pa3.get_scrubbing_counter()
            assert counter == 1, "counter {0} != 1".format(counter)
            if finished:
                self.logger.info("Scrubbing done!")
            else:
                self.logger.error("Scrubbing not done within 10 seconds! reinitialize components")

    def program_RUv1(self):
        if is_pa3_programming(TEST_MODE):
            self.logger.info("Pa3: Program RUv1")
            self.testbench.cru.set_gbtx_forward_to_usb(0)
            self.testbench.cru.pa3.reprogram_ultrascale()
            retries = 0
            MAX_RETRIES = 10
            success = False
            while not success and retries < MAX_RETRIES:
                time.sleep(1)
                success = self.testbench.cru.pa3.get_program_done()[0]
                self.logger.info("Done: %r",success)
                retries += 1
            self.testbench.cru.set_gbtx_forward_to_usb(1)
        else:
            self.jcm_control_client.start_full_configure()
            while True:
                if self.jcm_control_client.is_stopped():
                    break
                else:
                    time.sleep(0.1)
            time.sleep(0.5)  # wait for JCM to send all the messages
            success, read_messages = self.jcm_control_client.read_full_configure_results()
            self.logger.info(read_messages)

        if not success:
            self.logger.error("Could not Program RUv1. Stop")
            raise Exception("Could not Program RUv1")

    def store_configuration(self):
        cfg = OrderedDict()
        cfg['TEST_MODE'] = str(TEST_MODE)
        cfg['NR_FAULTS_INJECT'] = NR_FAULTS_INJECT
        cfg['FAULT_INJECT_DELAY'] = FAULT_INJECT_DELAY

        with open(self.logdir + '/test_config.json','w') as cfg_file:
            cfg_file.write(json.dumps(cfg, sort_keys=True, indent=4))

    def on_test_stop(self):
        if TEST_MODE == TestMode.PA3:
            self.testbench.cru.pa3.stop_blind_scrubbing()
        with open(self.logdir + "/manual_scrubbing_times.json","w") as f:
            f.write(jsonpickle.encode(self.manual_scrubbing_info))

    def check_powerstate_RUv1(self):
        return self.hameg.is_channel_on(1)

    def powercycle_RUv1(self):
        self.hameg.deactivate_channel(1)
        time.sleep(0.2)
        self.hameg.activate_channel(1)

    def powercycle_stave(self):
        self.hameg.deactivate_channels([2,3])
        time.sleep(0.2)
        self.hameg.activate_channels([2])
        time.sleep(0.1)
        self.hameg.activate_channels([3])


    def check_power(self):
        powerOk = True
        for ch in [1]:
            voltage = self.hameg.get_voltage(ch)
            current = self.hameg.get_current(ch)
            tripped = self.hameg.get_fuse_triggered(ch)
            self.logger.info("Powercheck Channel %d: Voltage: %.2f V, Current: %.1f mA, Fuse triggered: %r", ch,voltage,current,tripped)
            if tripped:
                powerOk = False
        return powerOk

    def setup_comms(self):
        self.testbench.setup_comms(ctlOnly=True)

    def tearDown(self):
        self.hameg.deactivate_channels([2,3])
        self.testbench.cru.set_gbtx_forward_to_usb(False)

    def cru_reads(self,dp):
        # CRU
        dp.cru_counters = self.testbench.cru.read_counters()
        ## ADC values
        dp.cru_adcs = self.testbench.cru.read_adcs()
        dp.cru_gpio = self.testbench.cru.sca.read_gpio()
        dp.pa3_values = {}
        dp.spi_micro_test_counters = self.testbench.cru.get_microprocessor_counters(12)
        #dp.spi_micro_test_counters = None#self.testbench.cru.get_microprocessor_counters(12)
        if TEST_MODE == TestMode.PA3:
            dp.pa3_values['CC_SCRUB_CNT'] = self.testbench.cru.pa3.get_scrubbing_counter()
        else:
            dp.pa3_values['CC_SCRUB_CNT'] = -1

    def rdo_reads(self,dp):
        ##
        # RDO
        ## radiation monitor instantaneous values
        dp.radmon_mismatch_dctrl           = self.testbench.rdo.dctrl.get_mismatch()
        dp.radmon_mismatch_gbtx01, _       = self.testbench.rdo.gbtx01.get_mismatch()
        dp.radmon_mismatch_gbtx2, _        = self.testbench.rdo.gbtx2.get_mismatch()
        #dp.radmon_mismatch_wishbone_master = self.testbench.rdo.master.get_mismatch()
        dp.radmon_mismatch_sysmon          = self.testbench.rdo.sysmon.get_mismatch()

        ## radiation monitor counters
        dp.radmon_dctrl           = self.testbench.rdo.radmon.get_counters(module=0)
        dp.radmon_gbtx01          = self.testbench.rdo.radmon.get_counters(module=1)
        dp.radmon_gbtx2           = self.testbench.rdo.radmon.get_counters(module=2)
        dp.radmon_wishbone_master = self.testbench.rdo.radmon.get_counters(module=3)
        dp.radmon_dp_fifos        = self.testbench.rdo.radmon.get_counters(module=4)
        dp.radmon_sysmon          = self.testbench.rdo.radmon.get_counters(module=5)

        ## Wishbone master errors
        wsmstr_counters = self.testbench.rdo.master_monitor.read_counters()
        dp.wsmstr_rderr = wsmstr_counters['read_error_counts']
        dp.wsmstr_wrerr = wsmstr_counters['write_error_counts']

        ## dctrl
        dp.dctrl_counters = self.testbench.rdo.dctrl.get_counters()

        ## Data Monitor
        for i in range(9):
            dp.lane_counters[i] = self.testbench.rdo.datapathmon.read_counters(i)

        ## GTH status
        dp.gth_aligned = self.testbench.rdo.gth.is_aligned()
        dp.gth_status = self.testbench.rdo.gth.get_gth_status()

        ## Sysmon status
        dp.sysmon_vccint     = self.testbench.rdo.sysmon.get_vcc_int()
        dp.sysmon_vccaux     = self.testbench.rdo.sysmon.get_vcc_aux()
        dp.sysmon_vccbram    = self.testbench.rdo.sysmon.get_vcc_bram()
        dp.sysmon_vcc_alpide = self.testbench.rdo.sysmon.get_vcc_alpide_3v3()
        dp.sysmon_vcc_sca    = self.testbench.rdo.sysmon.get_vcc_sca_1v5()
        dp.sysmon_temp       = self.testbench.rdo.sysmon.get_temperature()
        if dp.sysmon_temp > 80:
            self.logger.warning("XCKU060: High temperature (%d C)",
                                dp.sysmon_temp)

        ## MMCM counters reads
        dp.mmcm_monitor_counters = []
        dp.mmcm_monitor_lock_counters = []
        for mmcm_monitor_i in self.testbench.rdo.mmcm_monitors:
            dp.mmcm_monitor_counters.append(mmcm_monitor_i.get_counters(verbose=False))
            dp.mmcm_monitor_lock_counters.append(mmcm_monitor_i.get_lock_counter(verbose=False))

        ## GBTX flow monitor
        dp.gbtx_flow_monitor_counters = self.testbench.rdo.gbtx_flow_monitor.read_counters()

    def read_values(self, recordPrefetch=True):
        dp = DataPoint()
        # Collect Values to read
        try:

            dp.timestamp = time.time()

            if recordPrefetch:
                self.testbench.comm_cru.start_recording()
            else:
                self.testbench.comm_cru.load_sequence(self.sequence_cru)
                self.testbench.comm_cru.prefetch()

            # Hameg
            dp.hameg_values = [(self.hameg.get_voltage(i),
                             self.hameg.get_current(i))
                            for i in range(1,4)
            ]
            self.cru_reads(dp)
            self.rdo_reads(dp)

            if recordPrefetch:
                self.sequence_cru = self.testbench.comm_cru.stop_recording()

            if recordPrefetch:
                self.sequence_rdo = self.testbench.comm_rdo.stop_recording()
        except:
            self.testbench.comm_cru.stop_prefetch_mode(checkEmpty=False)
            raise
        finally:
            self.save_datapoint(dp)
            self.testbench.comm_cru.stop_prefetch_mode(checkEmpty=True)
        return dp

    def save_datapoint(self,dp):
        if self.datafile:
            self.datafile.write(',')
        else:
            self.datafile = open(self.datafilepath,'w')
            self.datafile.write('[')
        self.datafile.write(jsonpickle.encode(dp))
        self.datafile.flush()

    def stop(self):
        if self.datafile:
            self.datafile.write(']')
            self.datafile.flush()
            os.fsync(self.datafile.fileno())
            self.datafile.close()

        self.testbench.stop()

    def check_status(self):
        """Check status of run. Decide if the run should stop"""
        key = heardKeypress()
        if key is 'q':
            raise KeyboardInterrupt()
        elif key is 'r':
            self.logger.info("Reset datamon counters")
            self.testbench.rdo.datapathmon.reset_counters()
        elif key is 'p':
            input("Script pause: press any key [and press enter] to continue")
        elif key is 's':
            self.testbench.cru.pa3.stop_blind_scrubbing()
            input("Script (and pa3 scrubbing) pause: press any key [and press enter] to continue")
            self.testbench.cru.pa3.start_blind_scrubbing()
        return True

    def setup_logging(self):
        # Logging folder
        self.logdir = os.path.join(
            os.getcwd(),
            'logs/' + datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f'))
        os.makedirs(self.logdir)

        self.datafilepath = os.path.join(self.logdir,'read_values.json')
        self.testrun_exit_status_info = os.path.join(self.logdir,'exit_status.json')

        self.runlog = os.path.join(os.getcwd(),'logs/runlog.txt')

        # setup logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        log_file = os.path.join(self.logdir, "testbeam_testbeam.log")
        log_file_errors = os.path.join(self.logdir,
                                       "testbeam_testbeam_errors.log")

        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        fh2 = logging.FileHandler(log_file_errors)
        fh2.setLevel(logging.ERROR)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)


        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        fh.setFormatter(formatter)
        fh2.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(fh2)
        logger.addHandler(ch)

        self.run_logger = logging.getLogger("run_info")
        rfh = logging.FileHandler(self.runlog)
        rfh.setLevel(logging.INFO)
        rfh.setFormatter(formatter)
        self.run_logger.addHandler(rfh)

    def test_routine(self):
        # wait for Trigger
        self.logger.info(self.testbench.cru.pa3.dump_config())
        self.logger.info("Start initialization")
        self.testbench.cru.check_git_hash_and_date(expected_git_hash=GITHASH_CRU)
        self.testbench.rdo.check_git_hash_and_date(expected_git_hash=GITHASH_RDO)
        self.logger.info("initialization done")
        self.pre_injection_file = self.readback_jcm(readback_name='beforeInjection', empty_folder=True, backup_readback=True)
        self.logger.info("Read back configuration")
        self.logger.info(self.testbench.cru.pa3.dump_config())

        running = True
        self.start_time = time.time()
        self.read_values(recordPrefetch=True)
        self.jcm_control_client.start_random_fault_injection(delay=FAULT_INJECT_DELAY, n_faults=NR_FAULTS_INJECT, correction=False)
        while not self.jcm_control_client.is_stopped():
            time.sleep(0.1)
        self.after_injection_file = self.readback_jcm(readback_name='afterInjection')
        self.logger.info("Read back configuration after injection")
        self.logger.info(self.testbench.cru.pa3.dump_config())

        self.single_scrub_cycle()
        self.after_scrubbing_file = self.readback_jcm(readback_name='afterScrub')
        self.logger.info("Read back configuration after scrubbing")
        self.logger.info("Readbacks finished")
        self.logger.info(self.testbench.cru.pa3.dump_config())

        try:
            self.on_test_stop()
        except Exception as e:
            self.logger.error("Exception while running on_test_stop()")
            self.logger.info(e,exc_info=True)

        # removes them from JCM
        self.jcm_control_client.remove_readback_files()

        self.analyse_readback_files()

    def log_powersupply_values(self):
        channels = {1:"RDO"}
        hameg_values = [(channels[i], self.hameg.get_voltage(i),
                         self.hameg.get_current(i),
                         self.hameg.get_fuse_triggered(i))
                         for i in range(1,2)]
        for ch,v,i,fuse in hameg_values:
            self.logger.info("Channel \"{0}\": V={1:.03f} V,I={2:.03f} mA, Fuse triggered: {3}".format(ch,v,i,fuse))

if __name__ == '__main__':

    testbeam_test = TestbeamTest()

    RUv1_force_powercycle = False
    RUv0_force_powercycle = False

    testbeam_test.setup_logging()

    testbeam_test.store_configuration()

    if not testbeam_test.connect_jcm():
        testbeam_test.logger.error("Cannot connect to JCM. Exit")
        sys.exit(-1)

    testbeam_test.run_logger.info("Start new Run")

    testbeam_test.poweron_RUv0(force_powercycle=RUv0_force_powercycle)

    testbeam_test.log_powersupply_values()

    testbeam_test.setup_comms()

    try:
        ruv1_is_on = testbeam_test.check_powerstate_RUv1()
        testbeam_test.logger.info("RUv1 is on: {0}".format(ruv1_is_on))
        if not ruv1_is_on or RUv1_force_powercycle:
            testbeam_test.logger.info("Powercycle RUv1")
            testbeam_test.powercycle_RUv1()
            time.sleep(2)

        testbeam_test.log_powersupply_values()
        testbeam_test.testbench.setup_cru()

        testbeam_test.testbench.comm_cru.discardall_dp1()
        testbeam_test.testbench.cru.set_gbtx_forward_to_usb(0, commitTransaction=True)
        # program RUv1

        testbeam_test.testbench.cru.initialize()

        testbeam_test.testbench.cru.set_gbtx_forward_to_usb(0)
        testbeam_test.program_RUv1()


#        force_reprogram = ruv1_is_on
#        testbeam_test.check_program_rdo(force_reprogram=force_reprogram)

        testbeam_test.testbench.comm_cru.discardall_dp1()
        testbeam_test.testbench.cru.initialize()
        testbeam_test.logger.info("Discard data from dataport DP1")
        testbeam_test.testbench.comm_cru.discardall_dp1()

        try:
            testbeam_test.testbench.setup_rdo()
            testbeam_test.testbench.rdo.initialize()
            testbeam_test.log_powersupply_values()
            testbeam_test.test_routine()
        except Exception as e:
            raise e
        finally:
            testbeam_test.tearDown()
    except Exception as e:
        testbeam_test.run_logger.info("Exception in Run")
        testbeam_test.run_logger.info(e,exc_info=True)
    finally:
        testbeam_test.testbench.stop()

    testbeam_test.run_logger.info("Run finished.")
