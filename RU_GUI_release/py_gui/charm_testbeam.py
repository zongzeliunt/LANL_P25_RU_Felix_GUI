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
import unittest
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

import unittest

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
import beam_shutter

jcm_server_address = "localhost"
jcm_server_port = 8001

class TestMode(Enum):
    DRY_RUN_JCM = 0
    DRY_RUN_PA3 = 1
    JCM_FAULT_INJECTION = 2
    BEAM_JCM = 3
    BEAM_PA3 = 4

def is_beam(test_mode):
    return test_mode == TestMode.BEAM_JCM or test_mode == TestMode.BEAM_PA3

def is_pa3_programming(test_mode):
    return test_mode == TestMode.BEAM_PA3 or test_mode == TestMode.DRY_RUN_PA3

TEST_MODE = TestMode.JCM_FAULT_INJECTION
USE_BEAM_SHUTTER = False

NR_FAULTS_INJECT = 100000 # tuned by setting the running time
FAULT_INJECT_DELAY = 90
FAULT_INJECT_DELAY_AFTER = 10 # wait after error corrected before injecting the next
FAULT_INJECT_CORRECTION = True

READ_uC = False
READ_PA3_VALUES = False
READ_PA3_SCRUB_COUNTER = False

END_TIME = 60 * 10
# 1000 fault injected in ~100s ~40' in Prague @1e6 flux

RESUME_RUN = False

MANUAL_SCRUBBING_CYCLE = None # Time between scrubbing

# Set to True if Events should be analyzed via event_filter while taking data
EVENT_ANALYSYS_ONLINE = False

PORT_BEAM_SHUTTER = '/dev/ttyBEAM_SHTR_CNTRL'

# Static Configuration parameters
USB_COMM_EXEC = "../../modules/usb_if/software/usb_comm_server/build/usb_comm"
SERIAL_CRU = "000001"
SERIAL_RDO = "000000"
HAMEG_PORT = "/dev/ttyHAMEG"


GITHASH_CRU = 0x0E74C47F

GITHASH_RDO = 0x01ab6ae
BS_BITFILE_CRC = 0x3292A090

#########################################################################
# Configure Readout mode:                                               #
# GPIO_ACTIVE, GTH_ACTIVE: Activate Readout of either (or both) modules #
# READOUT_SOURCE: Main Source for readout (forwarded to Gbtx)           #
# TRIGGER_FREQUENCY, SENSOR_PATTERN: Trigger configuration              #
#########################################################################
GTH_ACTIVE = True
GPIO_ACTIVE = True
READOUT_SOURCE = "GPIO"
TRIGGER_FREQUENCY = 10000
SENSOR_PATTERN = testbench.SensorMatrixPattern.EMPTY


# Don't touch if not needed (generated from main config above)
GTH_CONNECTOR = 4
READOUT_GTH_LIST = list(range(9))

GPIO_CONNECTOR  = 0
READOUT_GPIO_LIST = list(range(7))


if READOUT_SOURCE == "GTH":
    MAIN_CONNECTOR = GTH_CONNECTOR
    assert(GTH_ACTIVE)
elif READOUT_SOURCE == "GPIO":
    MAIN_CONNECTOR = GPIO_CONNECTOR
    assert(GPIO_ACTIVE)
else:
    raise NotImplementedError("Illegal value for Readout Source: {0}".format(READOUT_SOURCE))


class SensorPoweringScheme(Enum):
    HAMEG = 0
    POWERUNIT = 1

SENSOR_POWERING_SCHEME = SensorPoweringScheme.POWERUNIT
POWERUNIT_OUTPUT_CHANNEL_LIST = []
if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
    if GPIO_ACTIVE:
        POWERUNIT_OUTPUT_CHANNEL_LIST.append(0)
    if GTH_ACTIVE:
        POWERUNIT_OUTPUT_CHANNEL_LIST.append(1)

class DataPoint(object):
    """Datapoint for collecting continuous readout data"""
    def __init__(self):
        self.timestamp = None
        self.hameg_values = None
        self.cru_counters = None
        self.cru_adcs = None
        self.cru_gpio = None
        self.pa3_values = None
        self.powerunit_values = None
        self.chipdata = None
        self.dctrl_counters = None
        self.trigger_handler_mon = None
        self.gth_aligned = None
        self.gth_status = None
        self.lane_counters = OrderedDict()
        self.radmon_dctrl           = None
        self.radmon_gbtx01          = None
        self.radmon_gbtx2           = None
        self.radmon_wishbone_master = None
        self.radmon_dp_fifos        = None
        self.radmon_sysmon          = None
        self.radmon_trigger_handler = None
        self.radmon_datapath        = None
        self.radmon_mismatch_dctrl           = None
        self.radmon_mismatch_gbtx01          = None
        self.radmon_mismatch_gbtx2           = None
        self.radmon_mismatch_wishbone_master = None
        self.radmon_mismatch_sysmon          = None
        self.radmon_mismatch_trigger_handler = None
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
        self.lane_counters_gpio = OrderedDict()
        self.gbt_packer_monitor_gth = None
        self.gbt_packer_monitor_gpio = None
        self.gbt_packer_config_gth = None
        self.gbt_packer_config_gpio = None
        self.gth_config = None
        self.gpio_config = None


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

class BeamShutterDataPoint(object):
    def __init__(self):
        self.timestamp = None
        self.beam_is_on = -1

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

        self.dump_process = None
        self.read_process = None

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

        # BEAM SHUTTER
        self.beam_shutter = None
        self.beam_shutter_info = []

        # Scrubbing
        self.manual_scrubbing_info = []

        # live monitor
        self.tot_read_counter = 0

    def setup_power(self):
        self.hameg.activate_output(False)
        self.hameg.configure_channel(1,6.0,2.7)
        self.setup_sensor_power_source_on_hameg()
        self.hameg.activate_channels([1])
        self.hameg.deactivate_channels([2,3])
        self.hameg.activate_output(True)

    def setup_sensors_power_source_on_hameg(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.HAMEG:
            self.hameg.configure_channel(2,3.3,0.4)
            self.hameg.configure_channel(3,3.3,1.2)
        elif SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            self.hameg.configure_channel(2,3.3,2)
            self.hameg.configure_channel(3,5.0,0.150)
        else:
            raise NotImplementedError

    def setup_powerunit(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            self.testbench.setup_powerunit()
            self.testbench.powerunit.initialize()
            self.testbench.powerunit.power_off_all()
            self.testbench.powerunit.setup_power_IBs(dvdd=1.9, dvdd_current=1.5,
                                                     avdd=1.9, avdd_current=1.5,
                                                     bb=0,
                                                     module_list=POWERUNIT_OUTPUT_CHANNEL_LIST)

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

    def setup_beam_shutter(self):
        if USE_BEAM_SHUTTER:
            self.beam_shutter = beam_shutter.BeamShutter(PORT_BEAM_SHUTTER)
        else:
            self.beam_shutter = beam_shutter.DummyBeamShutter()

    def beam_on(self):
        if USE_BEAM_SHUTTER:
            self.logger.info("Beam ON!")
            self.beam_shutter.beam_on()
            dp = BeamShutterDataPoint()
            dp.timestamp = time.time()
            dp.beam_is_on = 1
            self.beam_shutter_info.append(dp)

    def beam_off(self):
        if USE_BEAM_SHUTTER:
            self.logger.info("Beam OFF!")
            self.beam_shutter.beam_off()
            dp = BeamShutterDataPoint()
            dp.timestamp = time.time()
            dp.beam_is_on = 0
            self.beam_shutter_info.append(dp)

    def program_RUv1(self):
        if RESUME_RUN:
            pass
        else:
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
        cfg['RESUME_RUN'] = str(RESUME_RUN)
        cfg['USE_BEAM_SHUTTER'] = USE_BEAM_SHUTTER
        cfg['NR_FAULTS_INJECT'] = NR_FAULTS_INJECT
        cfg['FAULT_INJECT_DELAY'] = FAULT_INJECT_DELAY
        cfg['FAULT_INJECT_DELAY_AFTER'] = FAULT_INJECT_DELAY_AFTER
        cfg['FAULT_INJECT_CORRECTION'] = FAULT_INJECT_CORRECTION
        cfg['MANUAL_SCRUBBING_CYCLE'] = MANUAL_SCRUBBING_CYCLE
        cfg['TRIGGER_FREQUENCY'] = TRIGGER_FREQUENCY
        cfg['MAIN_CONNECTOR'] = MAIN_CONNECTOR
        cfg['READOUT_SOURCE'] = READOUT_SOURCE
        cfg['GTH_ACTIVE'] = GTH_ACTIVE
        cfg['GPIO_ACTIVE'] = GPIO_ACTIVE
        cfg['SENSOR_PATTERN'] = SENSOR_PATTERN
        cfg['READOUT_GPIO_LIST'] = READOUT_GPIO_LIST
        cfg['READOUT_GTH_LIST'] = READOUT_GTH_LIST
        cfg['SENSOR_POWERING_SCHEME'] = str(SENSOR_POWERING_SCHEME)
        cfg['POWERUNIT_OUTPUT_CHANNEL_LIST'] = POWERUNIT_OUTPUT_CHANNEL_LIST

        with open(self.logdir + '/test_config.json','w') as cfg_file:
            cfg_file.write(json.dumps(cfg, sort_keys=True, indent=4))

    def on_test_start(self):
        if TEST_MODE == TestMode.JCM_FAULT_INJECTION:
            self.clean_readbacks_in_jcm()
            self.readback_xcku_configuration(basename='Start')
            self.start_random_fault_injection(FAULT_INJECT_DELAY,
                                              NR_FAULTS_INJECT,
                                              FAULT_INJECT_DELAY_AFTER,
                                              FAULT_INJECT_CORRECTION)
        if is_beam(TEST_MODE):
            if TEST_MODE == TestMode.BEAM_JCM:
                try:
                    self.jcm_control_client.start_blind_scrubber()
                except jcm_control_server.NoReadBackFileError as nrbe:
                    self.logger.warning("generating readback_file from current design")
                    self.jcm_control_client.start_readback()
                    time.sleep(1)
                    while not self.jcm_control_client.is_readback_finished():
                        time.sleep(0.2)
                    time.sleep(8)
                    self.jcm_control_client.start_blind_scrubber()
            elif TEST_MODE == TestMode.BEAM_PA3:
                self.testbench.cru.pa3.clear_scrubbing_counter()
                self.testbench.cru.pa3.start_blind_scrubbing()
        self.beam_on()

    def on_test_stop(self):
        self.beam_off()
        if TEST_MODE == TestMode.JCM_FAULT_INJECTION:
            self.faults_injected = self.stop_random_fault_injection()
            time.sleep(1)
            self.readback_xcku_configuration(basename='Stop')
            self.compare_xcku_readbacks(basename1='Start', basename2='Stop')
        if is_beam(TEST_MODE):
            if TEST_MODE == TestMode.BEAM_JCM:
                self.jcm_control_client.stop_blind_scrubber()
                with open(self.logdir + "/jcm_blind_scrubbing_report.log",'w') as scrub_report:
                    scrub_report.write(self.jcm_control_client.read_messages())
            elif TEST_MODE == TestMode.BEAM_PA3:
                self.testbench.cru.pa3.stop_blind_scrubbing()
        with open(self.logdir + "/beam_shutter_info.json",'w') as bs_report:
            bs_report.write(jsonpickle.encode(self.beam_shutter_info))
        with open(self.logdir + "/manual_scrubbing_times.json","w") as f:
            f.write(jsonpickle.encode(self.manual_scrubbing_info))

    def manual_single_scrub(self):
        """manual, slow scrubbing routine"""
        sc = ScrubbingCyclesDataPoint()
        self.read_values()
        sc.start_timestamp = time.time()
        self.logger.info("Manual scrubbing: Turn off continuous data")
        ch = Alpide(self.testbench.rdo,chipid=0x0F) #global broadcast
        ch.setreg_fromu_cfg_1(
            MEBMask=0,
            EnStrobeGeneration=0,
            EnBusyMonitoring=1,
            PulseMode=0,
            EnPulse2Strobe=0,
            EnRotatePulseLines=0,
            TriggerDelay=0)
        ch.trigger()
        self.testbench.cru.send_trigger(triggerType=0x100)
        time.sleep(0.1)
        self.testbench.rdo.gth.enable_data(False)
        time.sleep(0.5)
        self.logger.info("Initiate scrubbing cycle")
        if TEST_MODE == TestMode.DRY_RUN_JCM:
            self.jcm_control_client.start_blind_scrubber()
            time.sleep(0.5)
            self.jcm_control_client.stop_blind_scrubber()
            while not self.jcm_control_client.is_stopped():
                time.sleep(0.25)
            self.logger.info("Scrubbing Done")
            with open(self.logdir + "/jcm_blind_scrubbing_report.log",'a') as scrub_report:
                scrub_report.write(self.jcm_control_client.read_messages())
        elif TEST_MODE == TestMode.DRY_RUN_PA3:

            self.testbench.cru.pa3.trigger_single_scrub()
            tries = 0
            max_tries=10
            finished = False
            while not finished and tries < max_tries:
                time.sleep(1)
                finished = self.testbench.cru.pa3.is_idle()
            if finished:
                self.logger.info("Scrubbing done! reinitialize components")
            else:
                self.logger.error("Scrubbing not done within 10 seconds! reinitialize components")
        time.sleep(2)
        self.testbench.setup_sensors()
        self.testbench.setup_readout()
        ch.setreg_fromu_cfg_1(
            MEBMask=0,
            EnStrobeGeneration=1,
            EnBusyMonitoring=1,
            PulseMode=0,
            EnPulse2Strobe=0,
            EnRotatePulseLines=0,
            TriggerDelay=0)
        self.testbench.cru.send_trigger(triggerType=0x140)
        self.logger.info("Data back online and triggering")
        sc.stop_timestamp = time.time()
        self.logger.info("Manual scrubbing done in %.2f s", (sc.stop_timestamp - sc.start_timestamp))
        self.manual_scrubbing_info.append(sc)
        self.read_values()

    def start_random_fault_injection(self,delay,nr_faults,delay_after,make_correction=True):
        if TEST_MODE == TestMode.JCM_FAULT_INJECTION:
            self.jcm_control_client.start_random_fault_injection(delay,
                                                                 nr_faults,
                                                                 delay_after,
                                                                 make_correction)

    def stop_random_fault_injection(self):
        if TEST_MODE == TestMode.JCM_FAULT_INJECTION:
            self.jcm_control_client.stop_random_fault_injection()
            while not self.jcm_control_client.is_stopped():
                time.sleep(0.1)

            time.sleep(0.2)
            nr_injected, messages = self.jcm_control_client.read_fault_injection_results()

            self.logger.info("Nr Faults injected: %d", nr_injected)

            # write nr_injected to jcm_injection_report.log
            with open(self.logdir + "/jcm_injection_report.log", "w+") as injection_report_pointer:
                injection_report_pointer.write(messages)

            return nr_injected
        else:
            return None

    def clean_readbacks_in_jcm(self):
        self.jcm_control_client.remove_readback_files()

    def readback_xcku_configuration(self, basename='', max_tries=10):
        if TEST_MODE == TestMode.JCM_FAULT_INJECTION:
            self.jcm_control_client.start_readback()
            done = False
            n_tries = 0
            while done==False and n_tries < max_tries:
                n_tries += 1
                time.sleep(3)
                done, message = self.jcm_control_client.is_readback_finished()
                self.logger.info(message)
            self.jcm_control_client.rename_readback_file('readBack{0}.data'.format(basename))

    def compare_xcku_readbacks(self, basename1, basename2):
        if TEST_MODE == TestMode.JCM_FAULT_INJECTION or TEST_MODE==TestMode.JCM_DRY_RUN:
            are_equal, message = self.jcm_control_client.compare_readback(basename1, basename2)
            self.log_jcm_readback_status(are_equal)
            if are_equal:
                self.logger.info("readback files match!")
                self.logger.info(message)
            else:
                self.logger.error("readback files do not match!")
                self.logger.info(message)
            self.jcm_download_readback_files()

    def log_jcm_readback_status(self, are_equal):
        self.logger.info('copying readback files to log folder')
        filename = 'jcm_readback_status.json'
        rb = {'are_equal': are_equal}
        with open(os.path.join(self.logdir,filename),'w') as df:
            df.write(jsonpickle.encode(rb))
            df.flush()

    def jcm_download_readback_files(self):
        for basename in ['readBackStart.data', 'readBackStop.data']:
            destination_file = os.path.join(self.logdir,basename)
            os.system('sshpass -p "chrec" scp root@jcm_device:/tmp/{0} {1}'.format(basename, destination_file))

    def check_powerstate_RUv1(self):
        return self.hameg.is_channel_on(1)

    def powercycle_RUv1(self):
        self.hameg.deactivate_channel(1)
        time.sleep(0.2)
        self.hameg.activate_channel(1)

    def check_powerstate_powerunit(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            return self.hameg.is_channel_on(2), self.hameg.is_channel_on(3)

    def powercycle_powerunit(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            self.hameg.deactivate_channels([2,3])
            time.sleep(0.2)
            self.hameg.activate_channels([2])
            time.sleep(0.1)
            self.hameg.activate_channels([3])
        else:
            raise NotImplementedError

    def force_cut_sensor_power(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            self.poweroff_powerunit()
        elif SENSOR_POWERING_SCHEME == SensorPoweringScheme.HAMEG:
            self.poweroff_stave()
        else:
            raise NotImplementedError

    def poweroff_powerunit(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            self.hameg.deactivate_channels([2,3])

    def poweroff_stave(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.HAMEG:
            self.hameg.deactivate_channels([2,3])

    def powercycle_stave(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.HAMEG:
            self.hameg.deactivate_channels([2,3])
            time.sleep(0.2)
            self.hameg.activate_channels([2])
            time.sleep(0.1)
            self.hameg.activate_channels([3])
        else:
            raise NotImplementedError

    def check_power(self):
        powerOk = True
        for ch in [1,2,3]:
            voltage = self.hameg.get_voltage(ch)
            current = self.hameg.get_current(ch)
            tripped = self.hameg.get_fuse_triggered(ch)
            self.logger.info("Powercheck Channel %d: Voltage: %.2f V, Current: %.1f mA, Fuse triggered: %r", ch,voltage,current,tripped)
            if tripped:
                powerOk = False
        return powerOk

    def setup_comms(self):

        self.testbench.setup_comms(cru_ctlOnly=True)

        #nc_command = "nc 127.0.0.1 30001"
        #self.dump_process = subprocess.Popen("{0} > /dev/null".format(nc_command),shell=True,stdin=subprocess.PIPE)

    def start_datataking(self):
        #self.dump_process.stdin.close()
        #self.dump_process.kill()
        #time.sleep(0.1)

        output_data_filename = os.path.join(self.logdir,'dataout_dp2.Z')
        nc_command = "nc 127.0.0.1 30001"

        local_dir = os.path.dirname(os.path.realpath(__file__))
        event_filter_prog = os.path.join(local_dir, '../../modules/board_support_software/software/cpp/build/event_filter')
        event_filter_log = 'logs/event_filter_out.txt'
        #cmd = "{0} | {1} >> {2}".format(nc_command,event_filter_prog,event_filter_log)

        if EVENT_ANALYSYS_ONLINE:
            cmd = "{0} | ../sh/store_check_events.sh {1} {2} {3} {4}".format(nc_command,output_data_filename, self.logdir,
                                                                             event_filter_prog,event_filter_log)
        else:
            cmd = "{0} | compress | split -b 10485760 -d - {1}".format(nc_command,output_data_filename)

        self.read_process = subprocess.Popen(cmd, shell=True,preexec_fn=os.setsid,stdin=subprocess.PIPE)

    def tearDown(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            self.testbench.powerunit.power_off_all()
        elif SENSOR_POWERING_SCHEME == SensorPoweringScheme.HAMEG:
            self.hameg.deactivate_channels([2,3])
        self.testbench.cru.set_gbtx_forward_to_usb(False)

    def sensor_reads(self,dp):
        chipdata =  OrderedDict()
        for i in range(9):
            try:
                chipdata[i] = OrderedDict()
                ch = Alpide(chipid=i,board=self.testbench.rdo)
                lock = ch.getreg_dtu_pll_lock_1()[1]
                lock_counter = lock['LockCounter']
                lock_status = lock['LockStatus']
                lock_flag = lock['LockFlag']
                trigger_count = ch.read_reg(0x0009)
                strobes_count = ch.read_reg(0x000A)
                eventro_count = ch.read_reg(0x000B)
                seu_error_counter = ch.read_reg(pALPIDE.Addr.SEU_ERROR_COUNTER)
                cmu_dmu_status = ch.getreg_cmu_and_dmu_status()

                chipdata[i]['lock_counter'] = lock_counter
                chipdata[i]['lock_status'] = lock_status
                chipdata[i]['lock_flag'] = lock_flag
                chipdata[i]['trigger_count'] = trigger_count
                chipdata[i]['strobes_count'] = strobes_count
                chipdata[i]['eventro_count'] = eventro_count
                chipdata[i]['seu_count'] = seu_error_counter
                chipdata[i]['cmu_dmu_status'] = cmu_dmu_status
            except Exception as e:
                self.logger.info("Chip read failed")
                self.logger.info(e,exc_info=True)
        dp.chipdata = chipdata

    def cru_reads(self,dp):
        # CRU
        dp.cru_counters = self.testbench.cru.read_counters()
        ## ADC values
        dp.cru_adcs = self.testbench.cru.read_adcs()

        dp.cru_gpio = self.testbench.cru.sca.read_gpio()

        if READ_uC:
            dp.spi_micro_test_counters = self.testbench.cru.get_microprocessor_counters(12)

        dp.pa3_values = {}
        if READ_PA3_VALUES:
            dp.pa3_values = self.testbench.cru.pa3.dump_config()
        elif (TEST_MODE == TestMode.BEAM_PA3 or TEST_MODE == TestMode.DRY_RUN_PA3) and READ_PA3_SCRUB_COUNTER:
            dp.pa3_values['CC_SCRUB_CNT'] = self.testbench.cru.pa3.get_scrubbing_counter()
            dp.pa3_values['CC_SCRUB_CRC'] = self.testbench.cru.pa3.get_scrubbing_crc()
        else:
            dp.pa3_values['CC_SCRUB_CNT'] = -1
            dp.pa3_values['CC_SCRUB_CRC'] = -1

    def rdo_reads(self,dp):
        ##
        # RDO
        ## radiation monitor instantaneous values
        dp.radmon_mismatch_dctrl           = self.testbench.rdo.dctrl.get_mismatch()
        dp.radmon_mismatch_gbtx01, _       = self.testbench.rdo.gbtx01.get_mismatch()
        dp.radmon_mismatch_gbtx2, _        = self.testbench.rdo.gbtx2.get_mismatch()
        #dp.radmon_mismatch_wishbone_master = self.testbench.rdo.master.get_mismatch()
        dp.radmon_mismatch_sysmon          = self.testbench.rdo.sysmon.get_mismatch()
        dp.radmon_mismatch_trigger_handler = self.testbench.rdo.trigger_handler.get_mismatch()

        ## radiation monitor counters
        dp.radmon_dctrl           = self.testbench.rdo.radmon.get_counters(module=0)
        dp.radmon_gbtx01          = self.testbench.rdo.radmon.get_counters(module=1)
        dp.radmon_gbtx2           = self.testbench.rdo.radmon.get_counters(module=2)
        dp.radmon_wishbone_master = self.testbench.rdo.radmon.get_counters(module=3)
        dp.radmon_dp_fifos        = self.testbench.rdo.radmon.get_counters(module=4)
        dp.radmon_sysmon          = self.testbench.rdo.radmon.get_counters(module=5)
        dp.radmon_datapath        = self.testbench.rdo.radmon.get_counters(module=6)
        dp.radmon_trigger_handler = self.testbench.rdo.radmon.get_counters(module=7)

        ## Wishbone master errors
        wsmstr_counters = self.testbench.rdo.master_monitor.read_counters()
        dp.wsmstr_rderr = wsmstr_counters['read_error_counts']
        dp.wsmstr_wrerr = wsmstr_counters['write_error_counts']

        # Trigger Handler
        dp.trigger_handler_mon = self.testbench.rdo.trigger_handler_monitor.get_counters()

        ## dctrl
        dp.dctrl_counters = self.testbench.rdo.dctrl.get_counters()

        ## Data Monitor
        if GTH_ACTIVE:
            for i in self.testbench.rdo.gth.transceivers:
                dp.lane_counters[i] = self.testbench.rdo.datapathmon.read_counters(i)
            dp.gbt_packer_monitor_gth = self.testbench.rdo.gbt_packer_monitor_gth.read_counters()
            dp.gbt_packer_config_gth = self.testbench.rdo.gbt_packer_gth.read_config()
            dp.gth_config = self.testbench.rdo.gth.read_config()
            ## GTH status
            dp.gth_aligned = self.testbench.rdo.gth.is_aligned()
            dp.gth_status = self.testbench.rdo.gth.get_gth_status()

        if GPIO_ACTIVE:
            for i in self.testbench.rdo.gpio.transceivers:
                dp.lane_counters_gpio[i] = self.testbench.rdo.datapathmon_gpio.read_counters(i)
            dp.gbt_packer_monitor_gpio = self.testbench.rdo.gbt_packer_monitor_gpio.read_counters()
            dp.gbt_packer_config_gpio = self.testbench.rdo.gbt_packer_gpio.read_config()
            dp.gpio_config = self.testbench.rdo.gpio.read_config()

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
#        dp.mmcm_monitor_counters = []
#        dp.mmcm_monitor_lock_counters = []
#        for mmcm_monitor_i in self.testbench.rdo.mmcm_monitors:
#            dp.mmcm_monitor_counters.append(mmcm_monitor_i.get_counters(verbose=False))
#            dp.mmcm_monitor_lock_counters.append(mmcm_monitor_i.get_lock_counter(verbose=False))

        ## GBTX flow monitor
        dp.gbtx_flow_monitor_counters = self.testbench.rdo.gbtx_flow_monitor.read_counters()

        # Powerunit
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            dp.powerunit_values = self.testbench.powerunit.get_values_IBs(POWERUNIT_OUTPUT_CHANNEL_LIST)

        # Deactivate triggering during sensor readout
        self.testbench.rdo.trigger_handler.set_opcode_gating(1)
        # Sensors
        self.sensor_reads(dp)
        # Reactivates it after the readings
        self.testbench.rdo.trigger_handler.set_opcode_gating(0)


    def print_values(self, last_read, dp):
        try:
           read_str = "Read Values"
           sop_cntr = dp.gbtx_flow_monitor_counters['sop_uplink']
           eop_cntr = dp.gbtx_flow_monitor_counters['eop_uplink']
           cru_sop_cntr = dp.cru_counters['gbt_sop_counter']
           cru_eop_cntr = dp.cru_counters['gbt_eop_counter']
           dv_cntr = dp.cru_counters['gbt_data_valid_counter']

           if GTH_ACTIVE:
               chip_readout_errors = sum([counter[0]['DECODE_ERROR_COUNT'] for _, counter in dp.lane_counters.items()])
               chip_events = sum([counter[0]['EVENT_COUNT'] for _, counter in dp.lane_counters.items()])
           if GPIO_ACTIVE:
               chip_readout_errors_gpio = sum([counter[0]['DECODE_ERROR_COUNT'] for _, counter in dp.lane_counters_gpio.items()])
               chip_events_gpio = sum([counter[0]['EVENT_COUNT'] for _, counter in dp.lane_counters_gpio.items()])

           trg_cntr = dp.gbtx_flow_monitor_counters['trg_downlink']
           trigger_sent = dp.trigger_handler_mon['trigger_sent']
           trigger_gated = dp.trigger_handler_mon['trigger_gated']
           trigger_not_sent = dp.trigger_handler_mon['trigger_not_sent']
           dctrl_trigger_sent = dp.dctrl_counters['trigger_sent'] + dp.dctrl_counters['pulse_sent']
           dctrl_trigger_not_sent = dp.dctrl_counters['opcode_rejected']

           triggers_to_sensors_mismatch = trigger_sent != dctrl_trigger_sent

           sensor_trigger_received_all = [dp.chipdata[i]['trigger_count'] for i in dp.chipdata]
           sensor_trigger_received = max(sensor_trigger_received_all)
           sensor_trigger_received_disagree = len(set(sensor_trigger_received_all)) > 1

           read_str += '\n\tTriggers Sent:\t{0} (Gated: {1} Not: {2}), DCTRL: {3} (Not: {4}), Sensor: {5}'.format(trigger_sent,trigger_gated,
                                                                                                                       trigger_not_sent,dctrl_trigger_sent,
                                                                                                                       dctrl_trigger_not_sent,sensor_trigger_received)
           if triggers_to_sensors_mismatch:
               read_str += ' (Triggers to sensor do not match the value in trigger handler)'


           if sensor_trigger_received_disagree:
               read_str += ' (SENSORS DISAGREE): {0}'.format(sensor_trigger_received_all)

           if GTH_ACTIVE:
               read_str += '\n\tEvents GTH:\t{0} (DecodeErrors: {1})'.format(chip_events,chip_readout_errors)
           if GPIO_ACTIVE:
               read_str += '\n\tEvents GPIO:\t{0} (DecodeErrors: {1})'.format(chip_events_gpio,chip_readout_errors_gpio)
           read_str += '\n\tSOP:\t\t{0},\t\tEOP:\t\t{1}'.format(sop_cntr,eop_cntr)

           read_str += '\n\tCRU SOP:\t{0},\t\tCRU EOP:\t{1}'.format(cru_sop_cntr,cru_eop_cntr)

           hameg_v_ru = dp.hameg_values[0][0]
           hameg_i_ru = dp.hameg_values[0][1]
           hameg_v_2 = dp.hameg_values[1][0]
           hameg_i_2 = dp.hameg_values[1][1]
           hameg_v_3 = dp.hameg_values[2][0]
           hameg_i_3 = dp.hameg_values[2][1]

           read_str += '\n\tHameg: {0:.2f} V, {1:.2f} mA'.format(hameg_v_ru,hameg_i_ru)
           read_str += '\n\tHameg: CH2 {0:.2f} V, {1:.2f} mA CH3: {2:.2f} V, {3:.2f} mA'.format(hameg_v_2,hameg_i_2,hameg_v_3,hameg_i_3)

           if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
               for module in POWERUNIT_OUTPUT_CHANNEL_LIST:
                   powerunit_av = self.testbench.powerunit._code_to_vout(dp.powerunit_values['module_{0}_avdd_voltage'.format(module)])
                   powerunit_ai = self.testbench.powerunit._code_to_i(dp.powerunit_values['module_{0}_avdd_current'.format(module)])
                   powerunit_dv = self.testbench.powerunit._code_to_vout(dp.powerunit_values['module_{0}_dvdd_voltage'.format(module)])
                   powerunit_di = self.testbench.powerunit._code_to_i(dp.powerunit_values['module_{0}_dvdd_current'.format(module)])
                   read_str += '\n\tPowerunit module {4}: avdd {0:.2f} V, {1:.2f} mA, dvdd {2:.2f} V, {3:.2f} mA'.format(powerunit_av,powerunit_ai,powerunit_dv,powerunit_di, module)
           elif SENSOR_POWERING_SCHEME == SensorPoweringScheme.HAMEG:
               hameg_av = dp.hameg_values[1][0]
               hameg_ai = dp.hameg_values[1][1]
               hameg_dv = dp.hameg_values[2][0]
               hameg_di = dp.hameg_values[2][1]
               read_str += '\n\tHameg IB: avdd {0:.2f} V, {1:.2f} mA, dvdd {2:.2f} V, {3:.2f} mA'.format(hameg_av,hameg_ai,hameg_dv,hameg_di)

           if READ_PA3_VALUES:
               scrub_cycles = dp.pa3_values['CC_SCRUB_CNT']
               scrub_crc = dp.pa3_values['CC_SCRUB_CRC']
               read_str += '\n\tPA3: Scrub cycles: {0}, CRC: 0x{1:08X}'.format(scrub_cycles, scrub_crc)
           else:
               scrub_cycles = 0

#           MMCM_LOCK_MISMATCHES_INITIAL_VALUE = 18
#           mmcm_lock_mismatches = 0 - MMCM_LOCK_MISMATCHES_INITIAL_VALUE
#           for mmcm in dp.mmcm_monitor_lock_counters:
#               for cntr in mmcm:
#                   mmcm_lock_mismatches += cntr

#           mmcm_counter_mismatches = 0
#           for mmcm in dp.mmcm_monitor_counters:
#               compare = mmcm[0]
#               for cntr in mmcm:
#                   if cntr != compare:
#                       mmcm_counter_mismatches += 1
#           if mmcm_counter_mismatches > 0:
#               self.testbench.tg_notification("MMCM mismatch detected {0}".format(mmcm_counter_mismatches))

           swt_mismatches = 0 #dp.cru_counters['gbt_swt_mismatch_counter2'] + dp.cru_counters['gbt_swt_mismatch_counter1'] + dp.cru_counters['gbt_swt_mismatch_counter0'] + dp.cru_counters['gbt_swt_mismatch_counter3']

           read_str += '\n\tSWT mismatch {0}'.format(swt_mismatches)
           if self.tot_read_counter == 0:
               self.logger.info(read_str + "\n\tRead values done (in %.2f ms)", (time.time() - last_read)*1000)
               # print warning ic PA3 CRC is failing
               if scrub_cycles not in [0, -1]:
                   if scrub_crc != BS_BITFILE_CRC:
                       self.logger.warning('Blind scrubbing bitfile CRC mismatch 0x{0:08X} (expected 0x{1:08X})'.format(scrub_crc, BS_BITFILE_CRC))
           else:
               self.logger.info("Read values done (in %.2f ms)", (time.time() - last_read)*1000)

           self.tot_read_counter += 1
           if self.tot_read_counter == 5:
               self.tot_read_counter = 0

        except Exception as e:
            self.logger.error("Could not perform all print values")
            self.logger.info(e,exc_info=True)

    def read_values(self, recordPrefetch=False):
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

    def readback_drp(self,filename):
        try:
            start = time.time()
            rb = self.testbench.rdo.gth.readback_all_drp()
            with open(os.path.join(self.logdir,filename),'w') as df:
                df.write(jsonpickle.encode(rb))
                df.flush()
            end = time.time()
            self.logger.info("DRP readback stored to %s, duration: %.2f s", filename, end-start)
        except Exception as e:
            self.logger.error("Could not perform DRP readback. File %s may be not written", filename)
            self.logger.info(e,exc_info=True)

    def stop(self):
        if self.datafile:
            self.datafile.write(']')
            self.datafile.flush()
            os.fsync(self.datafile.fileno())
            self.datafile.close()

        self.testbench.stop()
        if self.read_process:
           self.read_process.stdin.close()

    def send_stimuli(self):
        """In main loop, send stimuli to board (run each time main loop)"""
        pass

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

        self.logger.info("Start initialization")
        self.testbench.cru.check_git_hash_and_date(expected_git_hash=GITHASH_CRU)
        self.testbench.rdo.check_git_hash_and_date(expected_git_hash=GITHASH_RDO)
        self.logger.warning("ADD PA3 version check!")
        #self.powercycle_RUv1()
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            self.testbench.powerunit.power_on_IBs(POWERUNIT_OUTPUT_CHANNEL_LIST)

        if GPIO_ACTIVE:
            self.testbench.rdo.dctrl.set_dctrl_mask(1<<GPIO_CONNECTOR)
            self.testbench.setup_sensors(enable_strobe_generation=0,
                                         LinkSpeed=0)
            self.testbench.gpio_subset(READOUT_GPIO_LIST)
            self.testbench.set_dctrl_connector(GPIO_CONNECTOR)
            self.testbench.scan_idelay_gpio(stepsize=10,waittime=0.1,set_optimum=True)
            self.testbench.setup_readout_gpio()
            self.testbench.rdo.gbt_packer_gpio.set_settings(enable_data_forward=0)
        if GTH_ACTIVE:
            self.testbench.rdo.dctrl.set_dctrl_mask(1<<GTH_CONNECTOR)
            self.testbench.setup_sensors(enable_strobe_generation=0)
            self.testbench.gth_subset(READOUT_GTH_LIST)
            self.testbench.set_dctrl_connector(GTH_CONNECTOR)
            self.testbench.setup_readout()
            self.testbench.rdo.gbt_packer_gth.set_settings(enable_data_forward=0)


        self.testbench.rdo.dctrl.set_dctrl_mask(0x1F)

        if READOUT_SOURCE == "GTH":
            self.testbench.rdo.gbt_packer_gth.set_settings(enable_data_forward=1)
        elif READOUT_SOURCE == "GPIO":
            self.testbench.rdo.gbt_packer_gpio.set_settings(enable_data_forward=1)
        else:
            msg = "Readout Source not defined: {0}".format(READOUT_SOURCE)
            self.logger.error(msg)
            raise NotImplementedError(msg)

        self.testbench.set_dctrl_connector(MAIN_CONNECTOR,force=True)

        self.testbench.setup_trigger_handler_continuous(trigger_frequency=TRIGGER_FREQUENCY, send_pulses=True)

        #self.testbench.rdo.gth.enable_data(0)

        self.readback_drp('gth_drp_start_of_run.json')
        self.logger.info("initialization done")

        self.testbench.reset_counters()
        self.start_datataking()
        self.testbench.cru.reset_counters()

        # Trigger chips

        # start of trigger
        # Use timestamp as orbit
        orbit = int(time.time()) & 0x7FFFFFFF
        self.testbench.cru.send_start_of_continuous(bc=0,orbit=orbit-1,commitTransaction=False)
        self.testbench.cru.send_heartbeat(bc=0,orbit=orbit,commitTransaction=True)
        self.logger.info("start main loop")
        # Readout sensors
        READ_INTERVAL = 1.0
        run_error = None

        START_SCRUB = 0.5*60
        SCRUBBING=0
        SCRUB_INTERVAL = 10
        STOP_SCRUB = 120.0*60

        manual_scrub_last = time.time()

        try:
            running = True
            self.start_time = time.time()
            self.read_values(recordPrefetch=True)

            self.on_test_start() # TODO Uncomment

            last_read = self.start_time
            while running:
                if (time.time()-last_read) > READ_INTERVAL:
                    last_read = time.time()
                    dp = self.read_values()
                    self.print_values(last_read,dp)

                if MANUAL_SCRUBBING_CYCLE and (time.time() - manual_scrub_last) > MANUAL_SCRUBBING_CYCLE:
                    self.manual_single_scrub()
                    manual_scrub_last = time.time()

#                if SCRUBBING == 0 and time.time() - self.start_time > START_SCRUB:
#                    SCRUBBING=1
#                    self.on_test_start()
#                if SCRUBBING == 1 and time.time() - self.start_time > STOP_SCRUB:
#                    SCRUBBING=2
#                    self.on_test_stop()
#                if SCRUBBING == 1 and time.time() - last_scrubbed > SCRUB_INTERVAL:
#                    self.logger.info("Scrub")
#                    self.on_test_start()
#                    self.on_test_stop()
#                    last_scrubbed = time.time()




                self.send_stimuli()
                running = self.check_status()
                if END_TIME and (time.time() - self.start_time) > END_TIME:
                    self.logger.info("stop run after %.2f",(time.time() - self.start_time))
                    self.testbench.tg_notification("End of run after time reached")
                    raise KeyboardInterrupt("finished after end_time reached")

        except KeyboardInterrupt as ki:
            self.logger.info("Run ended by user (Keyboard interrupt).")
            self.logger.info(ki,exc_info=True)
            run_error = ki
        except Exception as e:
            self.logger.info("Run finished Due to readout errors.")
            self.logger.info(e,exc_info=True)
            run_error = e


        try:
            self.on_test_stop()
        except Exception as e:
            self.logger.error("Exception while running on_test_stop()")
            self.logger.info(e,exc_info=True)

        # Tear down routine for test
        try:
            orbit = int(time.time()) & 0x7FFFFFFF
            self.testbench.cru.send_end_of_continuous(bc=0,orbit=orbit)
            self.readback_drp('gth_drp_end_of_run.json')
            self.read_values(recordPrefetch=True)
        except Exception as e:
            self.logger.info("Final read_values might be partial (This is ok)")

        es = self.handle_failure(run_error)
        es.faults_injected = self.faults_injected

        with open(self.testrun_exit_status_info,'w') as df:
            df.write(jsonpickle.encode(es))
            df.flush()

    def return_exit_status_over_tg(self, exitstatus):
        self.testbench.tg_notification(exitstatus.msg)
        return exitstatus

    def handle_failure(self,run_error):

        es = ExitStatus()
        es.timestamp = time.time()
        es.run_error = run_error

        exit_ids = {
            0 : "Run stopped normally",
            1 : "Run stopped by Keyboard Interrupt",
            2 : "Hameg fuse triggered",
            3 : "Can't communicate with USB",
            4 : "Can't communicate with CRU",
            5 : "Can't communicate with SCA",
            6 : "Can't communicate with RDO",
            7 : "Can't communicate with Powerunit",
            8 : "Can't communicate with Chips",
            9 : "Unknown Error"
        }

        if es is None:
            es.exit_id = 0
            es.msg = "Run stopped normally"
            return es

        if isinstance(run_error,KeyboardInterrupt):
            es.exit_id = 1
            es.msg = exit_ids[1]
            return es

        ## Find out source of error
        for hameg_ch in range(1,4):
            triggered = self.hameg.get_fuse_triggered(hameg_ch)
            if triggered:
                self.logger.info("Error source: Hameg Channel %d Fuse triggered", hameg_ch)
                es.fuse_triggered = hameg_ch
                es.exit_id = 2
                es.msg = exit_ids[2]
                self.return_exit_status_over_tg(es)

        # cleanup CRU
        try:
            self.logger.info("handle_failure, check CRU")
            self.testbench.cru.set_gbtx_forward_to_usb(0)
            success = self.testbench.cru.comm.discardall_dp1(10)
            es.discardall_dp1_success = success
            if not success:
                self.logger.info("Reading incorrect values from USB port")
                es.exit_id = 3
                es.msg = exit_ids[3]
                self.return_exit_status_over_tg(es)
                self.poweroff_RUv0()
            self.testbench.cru.check_git_hash_and_date(expected_git_hash=GITHASH_CRU)
            self.logger.info("handle_failure, check CRU OK")

        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("Communication with CRU broken")
            es.exit_id = 4
            es.msg = exit_ids[4]
            self.poweroff_RUv0()
            return self.return_exit_status_over_tg(es)
        try:
            self.logger.info("handle_failure, check SCA")
            gpio = self.testbench.cru.sca.read_gpio()
            es.sca_gpio = gpio
            self.testbench.cru.initialize()
            self.logger.info("handle_failure, check SCA OK")
        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("CRU SCA read fail")
            es.exit_id = 5
            es.msg = exit_ids[5]
            return self.return_exit_status_over_tg(es)
        try:
            self.logger.info("handle_failure, check RDO")
            self.testbench.rdo.check_git_hash_and_date(expected_git_hash=GITHASH_RDO)
            self.logger.info("handle_failure, check RDO OK")
        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("Cannot access RDO")
            self.force_cut_sensor_power()
            es.exit_id = 6
            es.msg = exit_ids[6]
            return self.return_exit_status_over_tg(es)
        try:
            if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
                pls = self.testbench.powerunit.get_power_enable_status()
                es.powerlatch_status = pls
                if pls != 0x03:
                    self.logger.info("Chip power Latch triggered")
                return es
        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("Cannot access Powerunit")
            self.force_cut_sensor_power()
            es.exit_id = 7
            es.msg = exit_ids[7]
            return self.return_exit_status_over_tg(es)
        try:
            self.logger.info("handle_failure, check Chips")
            ch = Alpide(chipid=0,board=self.testbench.rdo)
            pll_status = ch.getreg_dtu_pll_lock_1()[1]
            es.chip0_pll_status = pll_status
            if not pll_status['LockStatus']:
                self.logger.info("Chip0: Pll not locked")
                return self.return_exit_status_over_tg(es)
            self.logger.info("handle_failure, check Chips OK")
        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("Cannot communicate with chip")
            es.exit_id = 8
            es.msg = exit_ids[8]
            return self.return_exit_status_over_tg(es)

        if es.run_error is not None:
            self.logger.info("Unknown problem")
            es.exit_id = 9
            es.msg = exit_ids[9]
            return self.return_exit_status_over_tg(es)

    def log_powersupply_values(self):
        if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            channels = {1:"RDO",2:"PB_33",3:"PB_BB", 4:"CRU"}
        elif SENSOR_POWERING_SCHEME == SensorPoweringScheme.HAMEG:
            channels = {1:"RDO",2:"AVDD",3:"DVDD"}
        else:
            raise NotImplementedError
        hameg_values = [(channels[i], self.hameg.get_voltage(i),
                            self.hameg.get_current(i),
                         self.hameg.get_fuse_triggered(i))
                           for i in range(1,5)
        ]
        for ch,v,i,fuse in hameg_values:
            self.logger.info("Channel \"{0}\": V={1:.03f} V,I={2:.03f} mA, Fuse triggered: {3}".format(ch,v,i,fuse))

if __name__ == '__main__':

    testbeam_test = TestbeamTest()

    RUv1_force_powercycle = False
    RUv0_force_powercycle = False

    testbeam_test.setup_logging()

    testbeam_test.store_configuration()

    testbeam_test.setup_beam_shutter()

    if not testbeam_test.connect_jcm():
        testbeam_test.logger.error("Cannot connect to JCM. Exit")
        sys.exit(-1)

    testbeam_test.run_logger.info("Start new Run")

    testbeam_test.log_powersupply_values()

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

        testbeam_test.log_powersupply_values()
        if not testbeam_test.hameg.is_channel_on(2) or not testbeam_test.hameg.is_channel_on(3):
            if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
                testbeam_test.powercycle_powerunit()
            elif SENSOR_POWERING_SCHEME == SensorPoweringScheme.HAMEG:
                testbeam_test.powercycle_stave()
        try:
            testbeam_test.log_powersupply_values()
            testbeam_test.testbench.setup_rdo(connector_nr=MAIN_CONNECTOR)
            testbeam_test.testbench.rdo.initialize()
            if SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
                testbeam_test.setup_powerunit()
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

    testbeam_test.log_powersupply_values()

    testbeam_test.run_logger.info("Run finished.")
