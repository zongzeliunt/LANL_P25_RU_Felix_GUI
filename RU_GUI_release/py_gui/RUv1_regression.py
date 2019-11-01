""" Regression test list for RUv1"""

import collections
import logging
import random
import sys
import time
import traceback
import unittest

sys.path.append('../../modules/board_support_software/software/py/')
from module_includes import *

import communication
import ru_board
import ru_transceiver
import ru_datapath_monitor
import ru_eyescan
import ru_chip_power
import ru_gbt_packer
import ws_status
import i2c
import events

from pALPIDE import Alpide, Opcode, CommandRegisterOpcode, Addr
from ru_board import RUv1, RUv0_CRU
from dctrl import WsDctrlAddress
from radiation_monitor import WsRadiationMonitorAddress
from gbtx_flow_monitor import WsGbtxFlowMonitorAddress, WsGbtxFlowMonitorAddress_bit
from gbtx_controller import WsGbtxControllerAddress
from ws_master_monitor import WsMasterMonitorAddress
from ws_status import WsStatusAddress

from communication import WishboneReadError, AddressMismatchError
import pprint

import simulation_if
import trigger

SERIAL_CRU = "000001"
SERIAL_RDO = "000000"


#################################
# Diagnostic
############################################
#import importlib
#ht_exist = importlib.util.find_spec("hanging_threads")
#if ht_exist:
#    from hanging_threads import start_monitoring
#    monitoring_thread = start_monitoring()
############################################
###########################################

# TODO: Move to configuration file
if "CI" in os.environ:
    SIMULATION = True
else:
    SIMULATION = False

SIMULATE_CRU = False
if SIMULATION:
    USB_MASTER = True

    DCTRL_GTH = 0
    DCTRL_GPIO = 0
    DCTRL_CONNECTORS = [DCTRL_GTH]
    SENSOR_LIST = [1]
    GTH_LIST = list(range(9))
    GTH_CONNECTOR_LUT = {i : DCTRL_GTH for i in SENSOR_LIST}
    GPIO_CONNECTOR_LUT = {i : DCTRL_GPIO for i in SENSOR_LIST}
    GPIO_LIST = list(range(7))
    GPIO_SENSORS_PER_LANE = {i:7 for i in GPIO_LIST}
    GPIO_SENSOR_MASK = {i:0x0 for i in GPIO_LIST}
    DCTRL_CONNECTORS = [0]
    GITHASH = 0xBADCAFE
else:
    DCTRL_GTH = 4
    DCTRL_GPIO = 0
    DCTRL_CONNECTORS = [DCTRL_GTH, DCTRL_GPIO] # first connector is used for connector_lut
    SENSOR_LIST = list(range(9))
    GTH_LIST = list(range(9))
    GTH_CONNECTOR_LUT = {i : DCTRL_GTH for i in SENSOR_LIST}
    GPIO_CONNECTOR_LUT = {i : DCTRL_GPIO for i in SENSOR_LIST}
    GPIO_LIST = list(range(7))
    GPIO_SENSORS_PER_LANE = {i:1 for i in GPIO_LIST}
    GPIO_SENSOR_MASK = {0:0b1111011,
                        1:0b1110111,
                        2:0b1101111,
                        3:0b1011111,
                        4:0b0111111,
                        5:0b0000000,
                        6:0b1111110}
    GITHASH = 0x01ab6ae
    USB_MASTER = False

boardGlobal = None
boardGlobal_usb = None
cruGlobal = None

gbtx_sim_comm = None
sim_serv = None
gbt_sim = None
comm = None
serv = None

def tearDownModule():
    if SIMULATION:
        gbt_sim.close()
        comm_usb.close()
        time.sleep(5)
        sim_serv.stop()
    else:
        comm.close_connections()
    if serv:
        serv.stop()


class TestcaseBase(unittest.TestCase):

    connector = None

    def setUp(self):
        assert boardGlobal is not None, "Board not properly defined"
        self.board = boardGlobal
        self.board_usb = boardGlobal_usb
        self.cru = cruGlobal
        self.setup_connection_lut()

        self.board.gpio.enable_data(False)
        self.board.gth.enable_data(False)
        self.board.gbt_packer_gpio.set_settings(enable_data_forward=0)
        self.board.gbt_packer_gth.set_settings(enable_data_forward=0)

    def setup_connection_lut(self):
        if self.connector is not None:
            connector = self.connector
        else:
            connector = DCTRL_CONNECTORS[0]
        connection_lut = {sensor: connector for sensor in SENSOR_LIST}
        connection_lut[0x0F]=connector
        self.board.set_chip2connector_lut(connection_lut)

    def tearDown(self):
        self.board.gpio.enable_data(False)
        self.board.gth.enable_data(False)
        self.board.gbt_packer_gpio.set_settings(enable_data_forward=0)
        self.board.gbt_packer_gth.set_settings(enable_data_forward=0)

    def send_trigger(self, triggerType=0x10, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        if SIMULATION and not SIMULATE_CRU:
            gbtx_sim_comm.send_trigger(triggerType, bc, orbit)
        else:
            self.cru.send_trigger(triggerType, bc, orbit, commitTransaction)

    def send_idle(self, value=1, commitTransaction=False):
        """waits for 25 ns in sim or hw

        NOTE: commit transaction is false by default"""
        assert value > 0
        if SIMULATION and not SIMULATE_CRU:
            # an idle lasts for 1 40 MHz clock cycle
            gbtx_sim_comm.send_idle(value)
        else:
            # wait values are at steps of 160 MHz clock
            self.cru.wait(4*value, commitTransaction=commitTransaction)

    def send_start_of_triggered(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a SOT trigger"""
        triggerType = 1 << trigger.BitMap.SOT
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit,commitTransaction=commitTransaction)

    def send_end_of_triggered(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a EOT trigger"""
        triggerType = 1 << trigger.BitMap.EOT
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit,commitTransaction=commitTransaction)

    def send_start_of_continuous(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a SOC trigger"""
        triggerType = 1 << trigger.BitMap.SOC
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit,commitTransaction=commitTransaction)

    def send_end_of_continuous(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a EOC trigger"""
        triggerType = 1 << trigger.BitMap.EOC
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit,commitTransaction=commitTransaction)

    def sync(self):
        """Reads a board register to align simulator and software"""
        self.board.read(1,1)

class TestWishboneSlaves(TestcaseBase):
    """Test functions related to wishbone slaves (not directly the slave functionality)"""
    WB_MASTER_MONITOR = ru_board.RUv1.MASTER_MONITOR_MODULE
    WB_STATUS = ru_board.RUv1.STATUS_MODULE
    WB_DCTRL = ru_board.RUv1.ALPIDE_MODULE
    WB_I2C_GBT = ru_board.RUv1.I2C_GBT_MODULE
    WB_I2C_PU1 = ru_board.RUv1.I2C_PU1_MODULE
    WB_I2C_PU2 = ru_board.RUv1.I2C_PU2_MODULE
    WB_GTH_FRONTEND = ru_board.RUv1.GTH_FRONTEND_MODULE
    WB_DATAPATH_MON = ru_board.RUv1.DATAPATH_MONITOR_MODULE
    WB_GBTX0 = ru_board.RUv1.GBTX0_MODULE
    WB_GBTX2 = ru_board.RUv1.GBTX2_MODULE
    WB_WAIT = ru_board.RUv1.WAIT_MODULE
    WB_RADMON = ru_board.RUv1.RADMON_MODULE
    WB_SYSMON = ru_board.RUv1.SYSMON_MODULE
    WB_GBTX_FLOW_MONITOR = ru_board.RUv1.GBTX_FLOW_MONITOR_MODULE
    WB_TRIGGER_HANDLER = ru_board.RUv1.TRIGGER_HANDLER
    WB_TRIGGER_HANDLER_MONITOR = ru_board.RUv1.TRIGGER_HANDLER_MONITOR
    WB_GPIO_CONTROL = ru_board.RUv1.GPIO_CONTROL
    WB_DATAPATH_MON_GPIO_1 = ru_board.RUv1.DATAPATH_MONITOR_GPIO_1
    WB_DATAPATH_MON_GPIO_2 = ru_board.RUv1.DATAPATH_MONITOR_GPIO_2

    def _check_bad_results(self,bad_writes, bad_reads):
        ret = self.board.comm._read_all_bytes(log=False)
        results = communication._get_wb_reads(ret)
        err_message = "\nExpecting a read error for:\n"
        for val in results:
            err_message += "\tmodule {0:#04X} address {1:#04X}\n".format(int(val[0])>>8 & 0x7F,
                                                                               int(val[0])&0xFF)
        for val in results:
            with self.assertRaises(WishboneReadError, msg=err_message):
                self.board.comm._check_result(val, log=False)

        counters = self.board.master_monitor.read_counters()
        self.assertEqual(counters['write_error_counts'],bad_writes,"Incorrect number of Write errors")
        self.assertEqual(counters['read_error_counts'],bad_reads,"Incorrect number of Read errors")

    def _slave_test(self, registers, writeValue=0x80, restore=True):
        """Test slave addresses. Registers given in the form (module,address,READ,WRITE)"""
        expected_addr = []
        restore_idx = []
        for module, address, rd, wr in registers:
            if wr:
                if restore and rd:
                    self.board.read(module,address,commitTransaction=False)
                    restore_idx.append(len(expected_addr))
                    expected_addr.append(address)
                self.board.write(module, address, writeValue,
                                 commitTransaction=False)
            if rd:
                self.board.read(module, address, commitTransaction=False)
                expected_addr.append(address)
        self.board.flush()
        results = self.board.comm.read_results()
        result_addr = [addr & 0xFF for addr, data in results]

        self.assertEqual(expected_addr, result_addr,
                         "WB_MASTER_MONITOR address read mismatch")

        # test illegal states
        self.board.master_monitor.reset_all_counters(commitTransaction=False)
        bad_writes = 0
        bad_reads = 0
        for module, address, rd, wr in registers:
            if not wr:
                self.board.write(module, address, writeValue,
                                 commitTransaction=False)
                bad_writes += 1
            if not rd:
                self.board.read(module, address, commitTransaction=False)
                bad_reads += 1

        self.board.flush()
        self._check_bad_results(bad_writes,bad_reads)

        # restore old state
        for module, address, rd, wr in registers:
            if wr and restore and rd:
                restore_val = results[restore_idx.pop(0)][1]
                self.board.write(module,address,restore_val,commitTransaction=False)
        self.board.flush()

    def test_wsmstr(self):
        """Read/write from ws_master_monitor slave"""

        registers = [
            (self.WB_MASTER_MONITOR, WsMasterMonitorAddress.LATCH_COUNTERS, False, True),
            (self.WB_MASTER_MONITOR, WsMasterMonitorAddress.RESET_COUNTERS, False, True),
            (self.WB_MASTER_MONITOR, WsMasterMonitorAddress.READ_WBM_WRERRCNTR, True, False),
            (self.WB_MASTER_MONITOR, WsMasterMonitorAddress.READ_WBM_RDERRCNTR, True, False),
            (self.WB_MASTER_MONITOR, WsMasterMonitorAddress.READ_WBM_SEEERRCNTR, True, False)
        ]
        self._slave_test(registers)

    def test_gbtx_flow_monitor(self):
        """Read/write from gbtx_flow_monitor slave"""

        registers = [
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.LATCH_COUNTERS, True, True),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.RESET_COUNTERS, True, True),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_SWT_DOWNLINK_LSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_TRG_DOWNLINK_LSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_SWT_UPLINK_LSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_SOP_UPLINK_LSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_EOP_UPLINK_LSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_OVERFLOW_DOWNLINK_LSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_OVERFLOW_UPLINK_LSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_SWT_DOWNLINK_MSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_TRG_DOWNLINK_MSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_SWT_UPLINK_MSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_SOP_UPLINK_MSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_EOP_UPLINK_MSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_OVERFLOW_DOWNLINK_MSB, True, False),
            (self.WB_GBTX_FLOW_MONITOR, WsGbtxFlowMonitorAddress.READ_COUNTER_OVERFLOW_UPLINK_MSB, True, False),
        ]
        self._slave_test(registers)


    @unittest.skip("SYSMON do not allow to write on its own reg 0x00")
    def test_sysmon(self):
        """Read/write from wsmstr slave"""

        registers = [
            (self.WB_SYSMON, 0x00, True, False),
            (self.WB_SYSMON, 0x01, False, True),
            (self.WB_SYSMON, 0x02, True, True),
        ]
        self._slave_test(registers)

    def test_gth_frontend(self):
        "R/W test from gth"
        registers = [(self.WB_GTH_FRONTEND, i, True, True) for i in [0,2,3,5,7,8]] # skip DRP_DATA register
        registers.extend([(self.WB_GTH_FRONTEND, i, True, False)
                          for i in [1,6]])
        registers.append((self.WB_GTH_FRONTEND, 9, False, False))
        self._slave_test(registers)

    def test_gpio_frontend(self):
        "R/W test from gpio"
        registers = [(self.WB_GPIO_CONTROL,True,True) for i in
                     [0,1,4,5,6,7,8,9,10,11,12]]
        registers.extend([(self.WB_GPIO_CONTROL,True,False) for i in [2,3]])
        registers.extend([(self.WB_GPIO_CONTROL,True,False) for i in range(13,41)])
        registers.append((self.WB_GPIO_CONTROL, 41, False, False))

    def _test_datapath_monitor(self, module_id, lanes):
        nr_counters = ru_datapath_monitor.DatapathMonitor.nr_counter_regs * len(lanes)
        registers = [(module_id, i+2, True, False)
                     for i in range(nr_counters)]
        registers.append((module_id, 0, False,True))
        registers.append((module_id, 1, False,True))
        if nr_counters + 2 < 256:
            registers.append((module_id,255,False,False))
        self._slave_test(registers)

    def test_datapath_monitor(self):
        self._test_datapath_monitor(self.WB_DATAPATH_MON,self.board.datapathmon.lanes)
    def test_datapath_monitor_GPIO_1(self):
        self._test_datapath_monitor(self.WB_DATAPATH_MON_GPIO_1,self.board._datapathmon_gpio1.lanes)
    def test_datapath_monitor_GPIO_2(self):
        self._test_datapath_monitor(self.WB_DATAPATH_MON_GPIO_2,self.board._datapathmon_gpio2.lanes)

    def _test_gbt_packer_monitor(self,module_id):
        nr_counters = ru_gbt_packer.GbtPackerMonitor.nr_counter_regs
        registers = [(module_id, i+2, True, False)
                     for i in range(nr_counters)]
        registers.append(((module_id, 0, False,True)))
        registers.append(((module_id, 1, False,True)))
        registers.append((module_id,255,False,False))
        self._slave_test(registers)

    def test_gbt_packer_monitor_gth(self):
        self._test_gbt_packer_monitor(ru_board.RUv1.GBT_PACKER_MONITOR_GTH)

    def test_gbt_packer_monitor_gpio(self):
        self._test_gbt_packer_monitor(ru_board.RUv1.GBT_PACKER_MONITOR_GPIO)

    def test_wsstatus(self):
        registers = [
            (self.WB_STATUS, WsStatusAddress.GITHASH_LSB    , True, False),
            (self.WB_STATUS, WsStatusAddress.GITHASH_MSB    , True, False),
            (self.WB_STATUS, WsStatusAddress.DATE_LSB       , True, False),
            (self.WB_STATUS, WsStatusAddress.DATE_CSB       , True, False),
            (self.WB_STATUS, WsStatusAddress.DATE_MSB       , True, False),
            (self.WB_STATUS, WsStatusAddress.OS_LSB         , True, False),
            (self.WB_STATUS, WsStatusAddress.DIPSWITCH_VAL  , True, False),
            (self.WB_STATUS, WsStatusAddress.DNA_DO_READ    , False, True),
            (self.WB_STATUS, WsStatusAddress.DNA_CHUNK_0    , True, False),
            (self.WB_STATUS, WsStatusAddress.DNA_CHUNK_1    , True, False),
            (self.WB_STATUS, WsStatusAddress.DNA_CHUNK_2    , True, False),
            (self.WB_STATUS, WsStatusAddress.DNA_CHUNK_3    , True, False),
            (self.WB_STATUS, WsStatusAddress.DNA_CHUNK_4    , True, False),
            (self.WB_STATUS, WsStatusAddress.DNA_CHUNK_5    , True, False)
        ]
        self._slave_test(registers)

    def test_radiation_monitor(self):
        registers = []
        for i in range(WsRadiationMonitorAddress.NUM_REGS):
            registers.append((self.WB_RADMON, i, True, False))
        #registers.append((self.WB_RADMON, WsRadiationMonitorAddress.NUM_REGS+1, False, False))
        self._slave_test(registers)

    def test_dctrl(self):
        registers = [
            #                                                                rd     wr
            (self.WB_DCTRL, WsDctrlAddress.WRITE_CTRL                      , False, True),
            (self.WB_DCTRL, WsDctrlAddress.WRITE_ADDRESS                   , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.WRITE_DATA                      , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.PHASE_FORCE                     , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.READ_STATUS                     , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_DATA                       , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.LATCH_CTRL_CNTRS                , False, True),
            (self.WB_DCTRL, WsDctrlAddress.RST_CTRL_CNTRS                  , False, True),
            (self.WB_DCTRL, WsDctrlAddress.READ_BROADCAST_CNTR             , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_WRITE_CNTR                 , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_READ_CNTR                  , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_OPCODE_CNTR_LSB            , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_OPCODE_CNTR_MSB            , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_TRIGGER_SENT_CNTR_LSB      , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_TRIGGER_SENT_CNTR_MSB      , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_TRIGGER_NOT_SENT_CNTR      , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_PULSE_SENT_CNTR_LSB        , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_PULSE_SENT_CNTR_MSB        , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_OPCODE_REJECTED_CNTR_LSB   , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.READ_OPCODE_REJECTED_CNTR_MSB   , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.MASK_BUSY_REG                   , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.BUSY_TRANSCEIVER_MASK_LSB       , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.READ_BUSY_TRANSCEIVER_STATUS_LSB, True,  False),
            (self.WB_DCTRL, WsDctrlAddress.SET_DCTRL_INPUT                 , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_DCTRL_TX_MASK               , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.BUSY_TRANSCEIVER_MASK_MSB       , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.READ_BUSY_TRANSCEIVER_STATUS_MSB, True,  False),
            (self.WB_DCTRL, WsDctrlAddress.SET_DCLK_TX_MASK                , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.MANCHESTER_TX_EN                , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_IDELAY_VALUE0               , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_IDELAY_VALUE1               , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_IDELAY_VALUE2               , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_IDELAY_VALUE3               , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_IDELAY_VALUE4               , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.GET_IDELAY_VALUE0               , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.GET_IDELAY_VALUE1               , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.GET_IDELAY_VALUE2               , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.GET_IDELAY_VALUE3               , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.GET_IDELAY_VALUE4               , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.AUTO_PHASE_OFFSET               , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_DCLK_PARALLEL_0             , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_DCLK_PARALLEL_1             , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_DCLK_PARALLEL_2             , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_DCLK_PARALLEL_3             , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.SET_DCLK_PARALLEL_4             , True,  True),
            (self.WB_DCTRL, WsDctrlAddress.MISMATCH                        , True,  False),
            (self.WB_DCTRL, WsDctrlAddress.NUM_REG,                          False, False)
        ]
        self._slave_test(registers)
        self.chip = Alpide(self.board, chipid=SENSOR_LIST[0])
        self.chip.setreg_cmd(Command=Opcode.GRST, commitTransaction=False)
        self.chip.setreg_cmd(Command=CommandRegisterOpcode.CMUCLRERR, commitTransaction=False)
        self.board.flush()

    @unittest.skip("Bad override")
    def _test_gbtx(self, address):
        """Read/write from ws gbt_controller"""
        assert address in [self.WB_GBTX0, self.WB_GBTX2]

        registers = [
            #(self.WB_GBTX, 0x00, True , True ), #Killing the core
            (address, 0x01, True, True),
            (address, 0x02, True, True),
            (address, 0x03, True, True),
            (address, 0x04, True, True),
            (address, 0x05, True, True),
            (address, 0x06, True, True),
            (address, 0x07, True, True),
            (address, 0x08, True, True),
            (address, 0x09, True, True),
            (address, 0x0A, True, True),
            (address, 0x0B, True, True),
            (address, 0x0C, True, False),
            (address, 0x0D, True, False),
            (address, 0x0E, True, False),
            (address, 0x0F, True, False),
            (address, 0x10, True, False),
            (address, 0x11, True, False),
            (address, 0x12, True, False),
            (address, 0x13, True, False),
            (address, 0x14, True, False),
            (address, 0x15, True, False),
            (address, 0x16, False, True),  # killing the core
            (address, 0x17, True, True),
            (address, 0x18, False, True),  # killing the core
            (address, 0x19, True, False),
            (address, 0x1A, True, False)
        ]
        self._slave_test(registers)

    def test_gbtx0(self):
        self._test_gbtx(self.WB_GBTX0)

    def test_gbtx2(self):
        self._test_gbtx(self.WB_GBTX2)

    def _test_data(self, addr):
        registers = [
            (addr, 0, True, True),
            (addr, 1, True, True),
            (addr, 2, True, True),
            (addr, 3, True, False),
            (addr, 4, True, True),
            (addr, 5, True, False),
            (addr, 6, True, True),
            (addr, 7, True, False),
            (addr, 8, True, False),
            (addr, 9, True, False),
            (addr, 10, True, False),
            (addr, 11, True, False),
            (addr, 12, True, False),
            (addr, 13, True, False),
            (addr, 14, True, False),
            (addr, 15, True, False),
            (addr, 16, True, False),
            (addr, 17, True, False),
            (addr, 18, True, False),
            (addr, 19, True, False),
            (addr, 20, True, False),
            (addr, 21, True, False),
            (addr, 32, True, True),
            (addr, 33, False, False)
        ]
        self._slave_test(registers, writeValue=0x00)

    def test_trigger_handler(self):
        #                    rd     wr
        registers = [(self.WB_TRIGGER_HANDLER,i,True,True) for i in range(5)]
        registers.append((self.WB_TRIGGER_HANDLER,6,True,False))
        registers.append((self.WB_TRIGGER_HANDLER,7,False,False))
        self._slave_test(registers,writeValue = 0x00)

    def test_trigger_handler_monitor(self):
        #                                               rd     wr
        registers = [(self.WB_TRIGGER_HANDLER_MONITOR,i,True,True) for i in range(2)]
        registers += [(self.WB_TRIGGER_HANDLER_MONITOR,i,True,False) for i in range(2,13)]
        registers.append((self.WB_TRIGGER_HANDLER,13,False,False))
        self._slave_test(registers,writeValue = 0x00)

    def _test_gbt_packer(self,addr):
        registers = [(addr,i,True,True) for i in range(10)]
        registers.append((addr,10,False,False))
        self._slave_test(registers,writeValue = 0x00)

    def test_gbt_packer_gth(self):
        self._test_gbt_packer(self.board.GBT_PACKER_GTH)
    def test_gbt_packer_gpio(self):
        self._test_gbt_packer(self.board.GBT_PACKER_GPIO)


class TestWishboneMaster(TestcaseBase):
    """Test functions related to the wishbone master"""

    def test_access_nonexist(self):
        """Communicates with the last valid address of the RUv1"""
        self.board.write(63, 0x00, 0x00, commitTransaction=False)
        self.board.read(63, 0x00, commitTransaction=False)
        self.board.flush()
        with self.assertRaises(WishboneReadError):
            results = self.board.comm.read_results()

class TestWsRadiationMonitor(TestcaseBase):
    """Class to verify the behaviour of the radiation monitor wishbone slave"""

    @unittest.skip("Check")
    def test_radmon(self):
        values = self.board.radmon.get_all()
        for key in values.keys():
            if key != WsRadiationMonitorAddress.NUM_REGS-1:
                self.assertEqual(values[key], (0,0), "Read value for counter is {0} instead of (0,0) for key {1}\n values {2}".format(values[key], key, values))
            else:
                self.assertNotEqual(values[key], (0,0), "Read value for counter is {0}, and it should not. key: {1}\n values {2}".format(values[key], key, values))

class TriggerHandlerBaseTest:
    class TestTriggerHandler(TestcaseBase):
        def setUp(self):
            super().setUp()
            self.board.dctrl.disable_manchester_tx()
            self.board.dctrl.set_dctrl_mask(0)
            self.gbt_packer_wd_timeout_gth = self.board.gbt_packer_gth.get_wait_data_timeout()
            self.board.gbt_packer_gth.set_wait_data_timeout(1)
            self.gbt_packer_wd_timeout_gpio = self.board.gbt_packer_gpio.get_wait_data_timeout()
            self.board.gbt_packer_gpio.set_wait_data_timeout(1)
            self.mode = 'none'

        def tearDown(self):
            self.board.gbt_packer_gth.set_wait_data_timeout(self.gbt_packer_wd_timeout_gth)
            self.board.gbt_packer_gpio.set_wait_data_timeout(self.gbt_packer_wd_timeout_gpio)
            self.board.dctrl.set_dctrl_mask(0x1F)

        def _reset_counters_and_check(self):
            self.sync()
            self.board.dctrl.reset_counters(commitTransaction=False)
            self.board.trigger_handler_monitor.reset_counters(commitTransaction=False)
            ret = self.board.dctrl.get_counters()
            expected = 0
            for key, value in ret.items():
                self.assertEqual(value, expected, msg="Wrong counter {2} value, got {0}, expected {1} (dict {3})".format(value, expected, key, ret))
            ret = self.board.trigger_handler_monitor.get_counters()
            for key, value in ret.items():
                self.assertEqual(value, expected, msg="Wrong counter {2} value, got {0}, expected {1} (dict: {3})".format(value, expected, key, ret))

        def _test_send_trigger_in_mode(self):
            assert self.mode in ['triggered', 'continuous', 'none']
            self._reset_counters_and_check()
            if self.mode == 'none':
                expected_trigger = 0
            else:
                expected_trigger = 1
            self.send_idle(10)
            self.send_trigger(commitTransaction=False)
            self.send_idle(10)
            dctrl_counters = self.board.dctrl.get_counters()
            trigger_handler_counters = self.board.trigger_handler_monitor.get_counters()
            for value in ['opcode', 'trigger_sent']:
                self.assertEqual(dctrl_counters[value], expected_trigger, msg="Wrong counter {2} value, got {0}, expected {1}".format(dctrl_counters[value], expected_trigger, value))
            self.assertEqual(
                trigger_handler_counters['trigger_sent'], expected_trigger,
                "Not all Triggers sent: {0}/{1}".format(dctrl_counters['trigger_sent'], expected_trigger))

        def _test_mode(self, expect_triggered=0, expect_continuous=0, startup=False):
            """Checks if the is in the correct state"""
            assert expect_continuous | 1 == 1
            assert expect_triggered | 1 == 1
            if startup:
                extramsg = ' at startup'
            else:
                extramsg = ''
            expect = expect_continuous << 1 | expect_triggered
            mode, modedict = self.board.trigger_handler.get_operating_mode()
            self.assertEqual(mode, expect, msg="Mode is not correct{3}: expect {0}, got {1}. Dict: {2}".format(expect, mode, modedict, extramsg))

class TestTriggerHandlerNoMode(TriggerHandlerBaseTest.TestTriggerHandler):
    """Tests relative to the trigger handler in no mode (i.e. inactive)"""

    def test_send_trigger_reject(self):
        self._test_send_trigger_in_mode()

    def test_mode_status_continuous(self):
        """Checks if the fsm enters correctly in continuous mode"""
        self._test_mode(expect_triggered=0, expect_continuous=0, startup=True)
        self.send_start_of_continuous()
        self._test_mode(expect_triggered=0, expect_continuous=1)
        self.send_end_of_continuous()
        self._test_mode(expect_triggered=0, expect_continuous=0)

    def test_mode_status_triggered(self):
        """Checks if the fsm enters correctly in triggered mode"""
        self._test_mode(expect_triggered=0, expect_continuous=0, startup=True)
        self.send_start_of_triggered()
        self._test_mode(expect_triggered=1, expect_continuous=0)
        self.send_end_of_triggered()
        self._test_mode(expect_triggered=0, expect_continuous=0)


class TestTriggerHandlerTriggeredMode(TriggerHandlerBaseTest.TestTriggerHandler):
    """Tests relative to the trigger handler in triggered mode"""

    def setUp(self):
        super().setUp()
        self.mode = 'triggered'
        self.send_start_of_triggered()

    def tearDown(self):
        super().tearDown()
        self.send_end_of_triggered()
        self.board.trigger_handler.configure_to_send_triggers(commitTransaction=False)
        self.board.trigger_handler.set_opcode_gating(0)

    def test_send_trigger(self):
        self._test_send_trigger_in_mode()

    def test_trigger_too_close_reject(self):
        """Sends multiple triggers in triggered mode too close in time,
        with a different bc, should not generate a trigger to sensor"""
        EXPECTED_TRIGGER_NR = 1
        EXPECTED_TRIGGER_NOT_SENT_NR = 1
        self.board.dctrl.reset_counters()
        self.board.trigger_handler_monitor.reset_counters()
        self.send_idle(200)

        self.send_trigger(commitTransaction=False)
        self.send_idle(1, commitTransaction=False)
        self.send_trigger(bc=0x123, commitTransaction=False)
        self.send_idle(200)
        dctrl_counters = self.board.dctrl.get_counters()
        trigger_handler_counters = self.board.trigger_handler_monitor.get_counters()
        self.send_end_of_triggered()
        self.assertEqual(
            trigger_handler_counters['trigger_sent'], EXPECTED_TRIGGER_NR,
            "Not all Triggers sent: {0}/{1}".format(trigger_handler_counters['trigger_sent'], EXPECTED_TRIGGER_NR))
        self.assertEqual(
            dctrl_counters['trigger_sent'], EXPECTED_TRIGGER_NR,
            "Not all Triggers sent: {0}/{1}".format(dctrl_counters['trigger_sent'], EXPECTED_TRIGGER_NR))
        self.assertEqual(
            trigger_handler_counters['trigger_not_sent'], EXPECTED_TRIGGER_NOT_SENT_NR,
            "Triggers not sent not correct: {0}/{1}".format(trigger_handler_counters['trigger_not_sent'], EXPECTED_TRIGGER_NOT_SENT_NR))

    def test_send_multiple_triggers(self, trigger_nr=10):
        """Sends multiple triggers in triggered mode properly spaced"""
        assert trigger_nr > 0
        self.board.dctrl.reset_counters(commitTransaction=False)
        self.board.trigger_handler_monitor.reset_counters(commitTransaction=True)
        self.send_idle(200)
        for i in range(trigger_nr):
            self.send_trigger(commitTransaction=False)
            self.send_idle(70, commitTransaction=False)
        self.board.flush()
        self.send_idle(200)
        dctrl_counters = self.board.dctrl.get_counters()
        trigger_handler_counters = self.board.trigger_handler_monitor.get_counters()
        self.send_end_of_triggered()
        self.assertEqual(
            dctrl_counters['trigger_sent'], trigger_nr,
            "Not all Triggers sent: {0}/{1}".format(dctrl_counters['trigger_sent'], trigger_nr))
        self.assertEqual(
            trigger_handler_counters['trigger_sent'], trigger_nr,
            "Not all Triggers sent: {0}/{1}".format(trigger_handler_counters['trigger_sent'], trigger_nr))
        EXPECTED_TRIGGER_NOT_SENT_NR = 0
        self.assertEqual(
            trigger_handler_counters['trigger_not_sent'], EXPECTED_TRIGGER_NOT_SENT_NR,
            "Triggers not sent not correct: {0}/{1}".format(trigger_handler_counters['trigger_not_sent'], EXPECTED_TRIGGER_NOT_SENT_NR))

    def test_send_pulse(self):
        """Test sending a pulse"""
        self.board.trigger_handler.configure_to_send_pulses(commitTransaction=False)
        self.board.dctrl.reset_counters(commitTransaction=False)
        self.board.trigger_handler_monitor.reset_counters(commitTransaction=True)
        self.send_idle(200)
        self.send_trigger(commitTransaction=False)
        self.send_idle(200)
        dctrl_counters = self.board.dctrl.get_counters()
        trigger_handler_counters = self.board.trigger_handler_monitor.get_counters()
        expected_pulse = 1
        expected_trigger = 0
        self.assertEqual(trigger_handler_counters['trigger_sent'], expected_pulse,
                         "Not all Pulses sent: {0}/{1}".format(trigger_handler_counters['trigger_sent'], expected_pulse))
        for value in ['opcode', 'pulse_sent']:
            self.assertEqual(dctrl_counters[value], expected_pulse, msg="Wrong counter {2} value, got {0}, expected {1}".format(dctrl_counters[value], expected_pulse, value))
        self.assertEqual(dctrl_counters['trigger_sent'], expected_trigger, msg="Wrong counter expected_trigger value, got {0}, expected {1}".format(dctrl_counters['trigger_sent'], expected_trigger))

    def test_trigger_gating(self):
        """test sending a trigger when gating, expect no trigger sent
        """
        self.board.trigger_handler.set_opcode_gating(1)
        self.board.dctrl.reset_counters(commitTransaction=False)
        self.board.trigger_handler_monitor.reset_counters(commitTransaction=True)
        self.send_idle(200)
        self.send_trigger(commitTransaction=False)
        self.send_idle(200)
        dctrl_counters = self.board.dctrl.get_counters()
        trigger_handler_counters = self.board.trigger_handler_monitor.get_counters()
        expected_trigger = 0
        expected_gated_trigger = 1
        self.assertEqual(trigger_handler_counters['trigger_sent'], expected_trigger,
                         "Too many triggers sent: {0}/{1}".format(trigger_handler_counters['trigger_sent'], expected_trigger))
        self.assertEqual(trigger_handler_counters['trigger_gated'], expected_gated_trigger,
                         "Not all trigger gated: {0}/{1}".format(trigger_handler_counters['trigger_gated'], expected_gated_trigger))
        self.assertEqual(dctrl_counters['trigger_sent'], expected_trigger, msg="Wrong counter expected_trigger value, got {0}, expected {1}".format(dctrl_counters['trigger_sent'], expected_trigger))

class TestTriggerHandlerContinuousMode(TriggerHandlerBaseTest.TestTriggerHandler):
    """Tests relative to the trigger handler in continuous mode"""
    def setUp(self):
        super().setUp()
        self.send_start_of_continuous()
        self.mode = 'continuous'

    def tearDown(self):
        super().tearDown()
        self.send_end_of_continuous()

    @unittest.skip("Obsolete, to be adapted.")
    def test_send_trigger(self):
        self._test_mode(expect_triggered=0, expect_continuous=1, startup=True)
        self.board.dctrl.reset_counters(commitTransaction=False)
        self.board.trigger_handler_monitor.reset_counters(commitTransaction=False)
        self.send_idle(10)
        self.send_trigger(commitTransaction=False)
        self.send_idle(100)
        dctrl_counters = self.board.dctrl.get_counters()
        trigger_handler_counters = self.board.trigger_handler_monitor.get_counters()
        expected_trigger = 0
        expected_trigger_not_sent = 1
        self.assertEqual(trigger_handler_counters['trigger_sent'], expected_trigger,
                         "Not all Pulses sent: {0}/{1}".format(trigger_handler_counters['trigger_sent'], expected_trigger))
        self.assertEqual(trigger_handler_counters['trigger_not_sent'], expected_trigger_not_sent,
                         "Not all Pulses sent: {0}/{1}".format(trigger_handler_counters['trigger_not_sent'], expected_trigger_not_sent))
        self.assertEqual(dctrl_counters['trigger_sent'], expected_trigger, msg="Wrong counter expected_trigger value, got {0}, expected {1}".format(dctrl_counters['trigger_sent'], expected_trigger))

class TestGbtxFlowMonitor(TestcaseBase):
    """Class to verify the behaviour of the gbtx flow monitor wishbone slave"""

    def setUp(self):
        super().setUp()
        self.chips = [Alpide(self.board, chipid=i) for i in SENSOR_LIST]
        self.chips[0].reset()
        self.board.read(1,1, commitTransaction=False)
        self.board.wait(100,commitTransaction=False)
        self.board.gbtx_flow_monitor.reset_counters(commitTransaction=True)
        self.board.read_all()

    def test_swt(self):
        NR_READS = 10
        for i in range(NR_READS):
            self.board.read(1,1,commitTransaction=False)
        self.board.flush()
        self.board.read_all()

        # first latch counters
        self.board.gbtx_flow_monitor.latch_counters(commitTransaction=False)
        self.board.wait(100)

        # Synchronisation barrier
        if SIMULATION:
            time.sleep(10)
        else:
            self.cru.wait(100, commitTransaction = False)
            self.cru.read(RUv0_CRU.STATUS_MODULE,0)

        # Now read
        counters = self.board.gbtx_flow_monitor._get_counters()

        expected_swt_downlink = NR_READS + 1 +  2 # 2 for latching, 1 for firmware_wait
        self.assertEqual(counters['swt_downlink'], expected_swt_downlink,
                         "SWT counter swt downlink is not correct")

        expected_swt_uplink = NR_READS
        self.assertEqual(counters['swt_uplink'], expected_swt_uplink,
                         "SWT counter swt uplink is not correct")

    def test_trigger(self):
        NR_TRIGGERS = 10
        for i in range(NR_TRIGGERS):
            self.send_trigger(commitTransaction=False)
            if SIMULATION:
                time.sleep(5)
            else:
                self.cru.wait(1000, commitTransaction=False)
                self.cru.read(RUv0_CRU.STATUS_MODULE,0)
        self.sync()
        counters = self.board.gbtx_flow_monitor.read_counters()
        self.assertEqual(counters['trg_downlink'],
                         NR_TRIGGERS,
                         "TRG counter is not {0}: {1}".format(NR_TRIGGERS,
                                                              counters['trg_downlink']))

class TestWsStatus(TestcaseBase):
    """Class to verify the behaviour of the status wishbone slave"""

    def test_read_gitghash(self):
        #"""Reads the git hash"""
        githash = self.board.status.get_git_hash()
        if SIMULATION:
            ghash_expected = GITHASH
            self.assertEqual(githash, ghash_expected, 
                             "Returned value {0:08X} different than expected {1:08X}".format(ghash_expected,githash))

    def test_read_gitdate(self):
        #"""Reads the git date"""
        lsb = self.board.status.read(WsStatusAddress.DATE_LSB)
        csb = self.board.status.read(WsStatusAddress.DATE_CSB)
        msb = self.board.status.read(WsStatusAddress.DATE_MSB)
        date = msb << 32 | csb << 16 | lsb
        if SIMULATION:
            date_expected = 0xbad0badcafe
            self.assertEqual(date, date_expected,
                             "Returned value {0} different than expected {1}".format(date, date_expected))

    def test_os(self):
        #"""Reads the OS compilation code"""
        os = self.board.status.get_os()
        if SIMULATION:
            os_expected = 0xaffe
            self.assertEqual(os, os_expected,
                             "Returned value {0} different than expected {1}".format(os, os_expected))
        else:
            os_expected = list(range(3))
            self.assertIn(os, os_expected,
                          "Returned value {0} not in expected list {1}".format(os, os_expected))

    def test_dipswitch(self):
        #"""Reads the dipswitch value"""
        dipval = self.board.status.get_dipswitch()
        if SIMULATION:
            dip_expected = 0x2AB
            self.assertEqual(dipval, dip_expected,
                             "Returned value {0} different than expected {1}".format(dipval, dip_expected))

    def test_dna(self):
        #"""Reads the DNA code"""
        dna = self.board.status.get_dna_value()
        if SIMULATION:
            dna_expected = 0x76543210FEDCBA9876543210
            self.assertEqual(dna, dna_expected,
                             "Returned value {0} different than expected {1}".format(dna, dna_expected))


class TestDatapathMonitorModules(TestcaseBase):
    def _test_dpmon_all(self,dpmon):
        dpmon.reset_counters(False)
        counters = dpmon.read_counters()
        self.assertEqual(len(counters), len(dpmon.lanes))
        for idx,lane in enumerate(dpmon.lanes):
            for counter in dpmon.counter_mapping:
                self.assertIn(counter,counters[idx])
                self.assertEqual(0,counters[idx][counter])

    def _test_dpmon_lane(self,dpmon,lane):
        dpmon.reset_counters(False)
        counters = dpmon.read_counters(lanes=lane)
        self.assertEqual(len(counters),1)
        for counter in dpmon.counter_mapping:
            self.assertIn(counter,counters[0])
            self.assertEqual(0,counters[0][counter])

    def test_dpmon_gth_all(self):
        self._test_dpmon_all(self.board.datapathmon)

    def test_dpmon_gpio_all(self):
        self._test_dpmon_all(self.board.datapathmon_gpio)

    @unittest.skipIf(len(GTH_LIST) == 0, "No GTH Lanes active")
    def test_dpmon_gth_lane(self):
        self._test_dpmon_lane(self.board.datapathmon,self.board.datapathmon.lanes[0])

    @unittest.skipIf(len(GPIO_LIST) == 0, "No GPIO Lanes active")
    def test_dpmon_gpio_lane_first(self):
        self._test_dpmon_lane(self.board.datapathmon_gpio,self.board.datapathmon_gpio.lanes[0])

    @unittest.skipIf(len(GPIO_LIST) == 0, "No GPIO Lanes active")
    def test_dpmon_gpio_lane_last(self):
        self._test_dpmon_lane(self.board.datapathmon_gpio,self.board.datapathmon_gpio.lanes[-1])

class TestTransceiverFrontend(TestcaseBase):

    def setUp(self):
        super().setUp()
        self.chips = [Alpide(self.board, chipid=i) for i in SENSOR_LIST]
        self.board.initialize()
        self.chips[0].reset()


    def setup_chips(self, IBSerialLinkSpeed=2):
        self.__class__.setup_chips_static(self.chips, IBSerialLinkSpeed)

    @classmethod
    def setup_chips_static(cls,chips, IBSerialLinkSpeed=2):
        for ch in chips:
#            ch.initialize(disable_manchester=1,
#                          grst=False, cfg_ob_module=False)
#            ch.setreg_mode_ctrl(IBSerialLinkSpeed=IBSerialLinkSpeed)  # 1200 Mbps
#            ch.initialize_readout(PLLDAC=0x8, DriverDAC=0x8,
#                                  PreDAC=0x8, PLLDelayStages=4)
#            ch.setreg_fromu_cfg_1(EnStrobeGeneration=0, EnPulse2Strobe=0)
#            ch.setreg_fromu_pulsing_2(PulseDuration=0xFFFF)
#            ch.setreg_fromu_pulsing1(PulseDelay=0xF)
#            ch.mask_all_pixels()
#            #ch.unmask_row(0)
#            ch.reset_pll()
#            ch.setreg_mode_ctrl(ChipModeSelector=1)
#
            ch.initialize(disable_manchester=1, grst=False, cfg_ob_module=False)
            ch.setreg_dtu_dacs(PLLDAC=8, DriverDAC=8, PreDAC=8)
            for pll_off_sig in [0, 1, 0]:
                ch.setreg_dtu_cfg(VcoDelayStages=1,
                                  PllBandwidthControl=1,
                                  PllOffSignal=pll_off_sig,
                                  SerPhase=8,
                                  PLLReset=0,
                                  LoadENStatus=0)

            ch.board.write_chip_opcode(Opcode.RORST)
            ch.setreg_fromu_cfg_1(
                MEBMask=0,
                EnStrobeGeneration=0,
                EnBusyMonitoring=1,
                PulseMode=0,
                EnPulse2Strobe=0,
                EnRotatePulseLines=0,
                TriggerDelay=0)

            ch.setreg_fromu_cfg_3(FrameGap=0x800)
            ch.setreg_fromu_pulsing_2(PulseDuration=0xFF)
            ch.setreg_fromu_pulsing1(PulseDelay=0xF)

            ch.mask_all_pixels()
            ch.pulse_all_pixels_disable()
            ch.region_control_register_mask_all_double_columns(broadcast=True)

            ch.setreg_mode_ctrl(ChipModeSelector=1,
                                EnClustering=1,
                                MatrixROSpeed=1,
                                IBSerialLinkSpeed=IBSerialLinkSpeed,
                                EnSkewGlobalSignals=1,
                                EnSkewStartReadout=1,
                                EnReadoutClockGating=1,
                                EnReadoutFromCMU=0)


    def check_event_readout(self,nr_events, nr_noevent_triggers, lanes):
        with self.assertLogs(logging.getLogger("events"), level=logging.INFO) as cm:
            event_count, errors = events.check_event_readout(self.cru,nr_events, nr_events + nr_noevent_triggers,
                                                             lanes,True,None)
            self.assertEqual(0,errors, "Errors in event stream")
            warnings = []
            for rec in cm.records:
                logging.getLogger("check_event_readout").log(rec.levelno,rec.getMessage())
                warnings.append(rec.levelno > logging.INFO)
            self.assertFalse(all(warnings),"Event readout logged Warning or Error")


@unittest.skipIf(len(GPIO_LIST) == 0, "No GPIO Lanes active")
class TestTransceiverGpioFrontend(TestTransceiverFrontend):

    @classmethod
    def setUpClass(cls):
        board = boardGlobal
        board.gpio.enable_data(False)
        connector_lut = board.get_chip2connector_lut()
        board.set_chip2connector_lut(GPIO_CONNECTOR_LUT)
        chips = [Alpide(boardGlobal, chipid=i) for i in SENSOR_LIST]
        cls.setup_chips_static(chips,2)
        for ch in chips:
            ch.propagate_prbs(PrbsRate=1)
        board.gpio.enable_prbs(enable=True, commitTransaction=True)
        board.gpio.reset_prbs_counter()
        if SIMULATION:
            cls.gpio_idelays = {i : 0 for i in GPIO_LIST}
        else:
            cls.gpio_idelays = board.gpio.subset(GPIO_LIST).scan_idelays(10,0.1,True,verbose=False)
        board.set_chip2connector_lut(connector_lut)

    def setUp(self):
        super(TestTransceiverGpioFrontend, self).setUp()

        self.connector_lut = self.board.get_chip2connector_lut()
        self.board.set_chip2connector_lut(GPIO_CONNECTOR_LUT)

        self.board.gpio.enable_data(False)
        for idx in self.board.gpio.get_transceivers():
            self.board.gpio.set_lane_chip_mask(idx,GPIO_SENSOR_MASK[idx])
        self.board.gbt_packer_gpio.set_settings(enable_data_forward=1)
        self.board.gbt_packer_gth.set_settings(enable_data_forward=0)
        self.board.gbt_packer_gpio.update_masks(self.board.gpio.get_transceivers())

        for tr,idelay in self.__class__.gpio_idelays.items():
            self.board.gpio.subset([tr]).load_idelay(idelay)

    def tearDown(self):
        self.board.gpio.enable_data(False)
        for idx in self.board.gpio.get_transceivers():
            self.board.gpio.set_lane_chip_mask(idx,0x00)
        self.board.gbt_packer_gpio.set_settings(enable_data_forward=0)
        self.board.gpio.enable_data(enable=False,commitTransaction=True)
        self.board.gpio.enable_alignment(enable=False,commitTransaction=True)

        self.board.set_chip2connector_lut(self.connector_lut)

    def test_idelay(self):
        self.setup_chips(IBSerialLinkSpeed=0)
        self.board.gpio.load_idelay(0xFF)
        self.board.wait(1000)
        self.board.gpio.load_idelay(0x1FF)
        self.board.wait(1000)
        # test setting of only partial transceivers
        transceivers_temp = self.board.gpio.get_transceivers()[:]
        self.board.gpio.set_transceivers(transceivers_temp[::2])
        self.board.gpio.load_idelay(0xFF)
        self.board.wait(1000)
        self.board.gpio.set_transceivers(transceivers_temp[1::2])
        self.board.gpio.load_idelay(0x80)
        self.board.wait(1000)
        self.board.gpio.set_transceivers(transceivers_temp)
        self.board.gpio.load_idelay(0x00)
        self.board.wait(1000)
        self.board.read(1,1)

    def test_data(self):
        self.setup_chips(IBSerialLinkSpeed=0)
        for ch in self.chips:
            ch.propagate_data()

        self.board.gpio.initialize()

        self.board.gpio.align_transceivers()

        NR_TRIGGERS = 10
        NR_CHANNELS = len(GPIO_LIST)

        events_per_trigger = {i:0 for i in GPIO_LIST}
        for lane in GPIO_LIST:
            mask_bits = bin(GPIO_SENSOR_MASK[lane]).count('1')
            events_per_trigger[lane] = GPIO_SENSORS_PER_LANE[lane]

        NR_EVENTS = {lane: NR_TRIGGERS * ept for lane,ept in events_per_trigger.items()}

        self.board.datapathmon_gpio.reset_counters(commitTransaction=False)
        self.board.gbt_packer_monitor_gpio.reset_counters(commitTransaction=False)
        self.board.dctrl.rst_ctrl_cntrs(commitTransaction=False)
        self.board.wait(1000,commitTransaction=False)
        counters = self.board.datapathmon_gpio.read_counters()
        for i in range(NR_CHANNELS):
            for name,val in counters[i].items():
                self.assertEqual(val,0,"Before Trigger. Lane {0}, Counter {1}, Value not zero".format(GPIO_LIST[i],name,val))

        self.board.gpio.enable_data(True)

        self.send_start_of_triggered()
        self.trigger_min_dist = self.board.trigger_handler.get_trigger_minimum_distance()
        self.board.trigger_handler.set_trigger_minimum_distance(1)
        self.send_idle(100)
        self.sync()

        for i in range(NR_TRIGGERS):
            self.send_trigger(commitTransaction=False)
            self.send_idle(1000)
            self.board.wait(1000)
            self.sync()

        self.send_end_of_triggered()
        self.sync()
        self.board.trigger_handler.set_trigger_minimum_distance(self.trigger_min_dist)

        dctrl_counters = self.board.dctrl.get_counters()
        self.assertEqual(
            dctrl_counters['trigger_sent'], NR_TRIGGERS, "Not all Triggers sent: {0}/{1}".format(dctrl_counters['trigger_sent'], NR_TRIGGERS))

        # check Event counter

        events_received = False
        retries = 0

        while not events_received and retries < 10:
            self.board.wait(1000)
            time.sleep(1)
            event_counters = self.board.datapathmon_gpio.read_counter(counter="EVENT_COUNT")
            if not isinstance(event_counters,collections.Iterable):
                event_counters = [event_counters]
            events_received = all(
                [trig == NR_EVENTS[lane] for lane,trig in zip(GPIO_LIST,event_counters)])
            retries += 1

        counters = self.board.datapathmon_gpio.read_counters()
        gbt_counters = self.board.gbt_packer_monitor_gpio.read_counters()
        #pprint.pprint(counters)
        # print(counters)

        zero_counters = [
            "DECODE_ERROR_COUNT",
            "EVENT_ERROR_COUNT",
            "EMPTY_REGION_COUNT",
            "BUSY_COUNT",
            "BUSY_VIOLATION_COUNT",
            "DOUBLE_BUSY_ON_COUNT",
            "DOUBLE_BUSY_OFF_COUNT",
            "LANE_FIFO_FULL_COUNT",
            "LANE_FIFO_OVERFLOW_COUNT",
            "CPLL_LOCK_LOSS_COUNT",
            #"CDR_LOCK_LOSS_COUNT", #TODO MB: Investigate source of CDR lock loss. Deactivate for now
            "ALIGNED_LOSS_COUNT",
            "REALIGNED_COUNT",
            "ELASTIC_BUF_OVERFLOW_COUNT",
            "ELASTIC_BUF_UNDERFLOW_COUNT",
            "LANE_PACKAGER_LANE_TIMEOUT_COUNT",
            "GBT_PACKER_LANE_TIMEOUT_COUNT",
            "GBT_PACKER_LANE_START_VIOLATION_COUNT"
        ]
        for i in range(NR_CHANNELS):
            for cntr_name in zero_counters:
                msg = "After Trigger: Lane {0}, Counter {1} is Off. All: {2}"
                self.assertEqual(counters[i][cntr_name],0, msg.format(i,cntr_name,pprint.pformat(counters)))

           # Start/Stop counters only show upper 16 bit of 24 bit counter, cut nr_triggers
            self.assertEqual(counters[i]["LANE_PACKAGER_START_COUNT"],NR_TRIGGERS//2**8*2**8,
                             msg.format(i,"LANE_PACKAGER_START_COUNT",pprint.pformat(counters)))
            self.assertEqual(counters[i]["LANE_PACKAGER_STOP_COUNT"],NR_TRIGGERS//2**8*2**8,
                             msg.format(i,"LANE_PACKAGER_STOP_COUNT",pprint.pformat(counters)))
            self.assertEqual(counters[i]["GBT_PACKER_LANE_STOPS_COUNT"],NR_TRIGGERS//2**8*2**8,
                             msg.format(i,"GBT_PACKER_LANE_STOPS_COUNT",pprint.pformat(counters)))
            self.assertEqual(
                event_counters[i], NR_EVENTS[i], "Lane {0}, Not all Events received".format(GPIO_LIST[i]))

        self.assertEqual(gbt_counters['TRIGGER_RD'],NR_TRIGGERS+2,"GBT Packer, incorrect number of Triggers read")
        self.assertEqual(gbt_counters['SEND_SOP'],NR_TRIGGERS+2,"GBT Packer, incorrect number of SOP sent")
        self.assertEqual(gbt_counters['SEND_EOP'],NR_TRIGGERS+2,"GBT Packer, incorrect number of EOP sent")
        self.assertEqual(gbt_counters['PACKET_DONE'],NR_TRIGGERS+2,"GBT Packer, incorrect number of PACKET_DONE sent")

        self.assertEqual(gbt_counters['PACKET_TIMEOUT'],0,"GBT Packer, PACKET_TIMEOUT Non-Zero")
        self.assertEqual(gbt_counters['STATE_MISMATCH'],0,"GBT Packer, STATE_MISMATCH Non-Zero")
        self.assertEqual(gbt_counters['FIFO_FULL'],0,"GBT Packer, FIFO_FULL Non-Zero")
        self.assertEqual(gbt_counters['FIFO_OVERFLOW'],0,"GBT Packer, FIFO_OVERFLOW Non-Zero")


        self.check_event_readout(NR_TRIGGERS,2, GPIO_LIST)

        # Reset counters, check if still zero
        self.board.datapathmon_gpio.reset_counters()
        self.board.wait(1000)
        counters = self.board.datapathmon_gpio.read_all_counters()
        for i in range(NR_CHANNELS):
            for name,val in counters[i].items():
                self.assertEqual(val,0,"Lane {0}, Counter {1}, Value not zero".format(GPIO_LIST[i],name,val))

    def test_prbs400(self):
        self.setup_chips(IBSerialLinkSpeed=3)
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=1)

        time.sleep(1)
        self.board.wait(500)

        self.board.gpio.initialize()

        self.board.gpio.enable_prbs(enable=True, commitTransaction=True)
        self.board.gpio.reset_prbs_counter()

        # Read counters
        self.board.wait(1000)

        prbs_errors = self.board.gpio.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gpio.transceivers):
            self.assertEqual(0, cnt, "PRBS Error on Link {0}".format(link))

        # Set chip back to normal mode -> expect errors
        for ch in self.chips:
            ch.propagate_data(commitTransaction=False)
        self.board.wait(1000, commitTransaction=True)
        # back to PRBS sending mode
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=1, commitTransaction=True)

        prbs_errors = self.board.gpio.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gpio.transceivers):
            self.assertNotEqual(
                0, cnt, "No PRBS Error on Link {0}. Errors expected".format(link))

        # check Counter reset operation

        self.board.gpio.reset_prbs_counter(commitTransaction=True)
        self.board.wait(1000, commitTransaction=True)

        prbs_errors = self.board.gpio.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gth.transceivers):
            self.assertEqual(0, cnt, "PRBS Error on Link {0}".format(link))

@unittest.skipIf(len(GTH_LIST) == 0, "No GTH Lanes active")
class TestTransceiverGthFrontend(TestTransceiverFrontend):
    def test_eyescan(self):
        transceivers = list(self.board.gth.get_transceivers())
        self.board.gth.set_transceivers([0])
        eyescan = ru_eyescan.EyeScanGth(self.board.gth)

        eyescan.initialize()
        self.board.gth.set_transceivers(transceivers)

    def setUp(self):
        super(TestTransceiverGthFrontend, self).setUp()
        self.board.gth.enable_data(enable=False,commitTransaction=True)
        self.board.gth.enable_alignment(enable=False,commitTransaction=True)
        self.board.gbt_packer_gpio.set_settings(enable_data_forward=0)
        self.board.gbt_packer_gth.set_settings(enable_data_forward=1)
        self.connector_lut = self.board.get_chip2connector_lut()
        self.board.set_chip2connector_lut(GTH_CONNECTOR_LUT)
        self.board.gbt_packer_gth.update_masks(self.board.gth.get_transceivers())

    def tearDown(self):
        super(TestTransceiverGthFrontend, self).tearDown()
        self.board.gbt_packer_gth.set_settings(enable_data_forward=0)
        self.board.gbt_packer_gpio.set_settings(enable_data_forward=0)
        self.board.gth.enable_data(enable=False,commitTransaction=True)
        self.board.gth.enable_alignment(enable=False,commitTransaction=True)

        self.board.set_chip2connector_lut(self.connector_lut)

    def test_drp(self):
        """Test DRP interface"""
        ES_SDATA_MASK = (0x4D, 0x4C, 0x4B, 0x4A, 0x49)
        transceivers = list(self.board.gth.get_transceivers())
        data = 42
        self.setup_chips()
        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")

        for tr in transceivers:
            self.board.gth.set_transceivers([tr])
            for addr in ES_SDATA_MASK:
                self.board.gth.write_drp(addr, data + addr)
            for addr in ES_SDATA_MASK:
                rb = self.board.gth.read_drp(addr)
                self.assertEqual(
                    rb, data + addr, "DRP Write/Read mismatch on Transceiver {0}".format(tr))
        self.board.gth.set_transceivers(transceivers)

    def test_data(self):
        self.setup_chips()

        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")

        self.board.wait(500)

        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")

        aligned = self.board.gth.align_transceivers()
        self.assertTrue(aligned, "GTH module could not align to all modules: {0}".format(self.board.gth.is_aligned()))

        # discard old data
        self.assertTrue(self.cru.comm.discardall_dp2(20), "Could not discard data from dataport")

        # disable alignment
        self.board.gth.enable_alignment(False)
        self.board.gth.enable_data(True)

        NR_TRIGGERS = 10
        NR_CHANNELS = len(self.board.gth.get_transceivers())

        self.board.datapathmon.reset_counters(commitTransaction=False)
        self.board.gbt_packer_monitor_gth.reset_counters(commitTransaction=False)
        self.board.dctrl.rst_ctrl_cntrs(commitTransaction=False)
        self.board.wait(1000,commitTransaction=False)
        counters = self.board.datapathmon.read_all_counters()
        for i in range(NR_CHANNELS):
            for name,val in counters[i].items():
                self.assertEqual(val,0,"Before Trigger. Lane {0}, Counter {1}, Value not zero".format(i,name,val))

        self.board.gth.enable_data(True)

        self.send_start_of_triggered()
        self.trigger_min_dist = self.board.trigger_handler.get_trigger_minimum_distance()
        self.board.trigger_handler.set_trigger_minimum_distance(1)
        self.send_idle(100)
        self.sync()

        for i in range(NR_TRIGGERS):
            self.send_trigger(commitTransaction=False)
            self.send_idle(1000)
            self.board.wait(1000)
            self.sync()

        self.send_end_of_triggered()
        self.sync()
        self.board.trigger_handler.set_trigger_minimum_distance(self.trigger_min_dist)

        dctrl_counters = self.board.dctrl.get_counters()
        self.assertEqual(
            dctrl_counters['trigger_sent'], NR_TRIGGERS, "Not all Triggers sent: {0}/{1}".format(dctrl_counters['trigger_sent'], NR_TRIGGERS))

        # check Event counter

        events_received = False
        retries = 0

        while not events_received and retries < 10:
            self.board.wait(1000)
            time.sleep(1)
            event_counters = self.board.datapathmon.read_counter(
                range(NR_CHANNELS), "EVENT_COUNT")
            if not isinstance(event_counters,collections.Iterable):
                event_counters = [event_counters]
            events_received = all(
                [trig == NR_TRIGGERS for trig in event_counters])
            retries += 1

        counters = self.board.datapathmon.read_all_counters()
        gbt_counters = self.board.gbt_packer_monitor_gth.read_counters()
        #pprint.pprint(counters)
        # print(counters)
        zero_counters = [
            "DECODE_ERROR_COUNT",
            "EVENT_ERROR_COUNT",
            "EMPTY_REGION_COUNT",
            "BUSY_COUNT",
            "BUSY_VIOLATION_COUNT",
            "DOUBLE_BUSY_ON_COUNT",
            "DOUBLE_BUSY_OFF_COUNT",
            "LANE_FIFO_FULL_COUNT",
            "LANE_FIFO_OVERFLOW_COUNT",
            "CPLL_LOCK_LOSS_COUNT",
            #"CDR_LOCK_LOSS_COUNT", #TODO MB: Investigate source of CDR lock loss. Deactivate for now
                "ALIGNED_LOSS_COUNT",
            "REALIGNED_COUNT",
            "ELASTIC_BUF_OVERFLOW_COUNT",
            "ELASTIC_BUF_UNDERFLOW_COUNT",
            "LANE_PACKAGER_LANE_TIMEOUT_COUNT",
            "GBT_PACKER_LANE_TIMEOUT_COUNT",
            "GBT_PACKER_LANE_START_VIOLATION_COUNT"
        ]
        for i in range(NR_CHANNELS):
            for cntr_name in zero_counters:
                msg = "After Trigger: Lane {0}, Counter {1} is Off. All: {2}"
                self.assertEqual(counters[i][cntr_name],0, msg.format(i,cntr_name,pprint.pformat(counters)))

            # Start/Stop counters only show upper 16 bit of 24 bit counter, cut nr_triggers
            self.assertEqual(counters[i]["LANE_PACKAGER_START_COUNT"],NR_TRIGGERS//2**8*2**8,
                             msg.format(i,"LANE_PACKAGER_START_COUNT",pprint.pformat(counters)))
            self.assertEqual(counters[i]["LANE_PACKAGER_STOP_COUNT"],NR_TRIGGERS//2**8*2**8,
                             msg.format(i,"LANE_PACKAGER_STOP_COUNT",pprint.pformat(counters)))
            self.assertEqual(counters[i]["GBT_PACKER_LANE_STOPS_COUNT"],NR_TRIGGERS//2**8*2**8,
                             msg.format(i,"GBT_PACKER_LANE_STOPS_COUNT",pprint.pformat(counters)))
            self.assertEqual(counters[i]["EVENT_COUNT"], NR_TRIGGERS,
                             "Lane {0}, Not all Events received: {1}/{2}".format(i, counters[i]["EVENT_COUNT"], NR_TRIGGERS))

        self.assertEqual(gbt_counters['TRIGGER_RD'],NR_TRIGGERS+2,"GBT Packer, incorrect number of Triggers read")
        self.assertEqual(gbt_counters['SEND_SOP'],NR_TRIGGERS+2,"GBT Packer, incorrect number of SOP sent")
        self.assertEqual(gbt_counters['SEND_EOP'],NR_TRIGGERS+2,"GBT Packer, incorrect number of EOP sent")
        self.assertEqual(gbt_counters['PACKET_DONE'],NR_TRIGGERS+2,"GBT Packer, incorrect number of PACKET_DONE sent")

        self.assertEqual(gbt_counters['PACKET_TIMEOUT'],0,"GBT Packer, PACKET_TIMEOUT Non-Zero")
        self.assertEqual(gbt_counters['STATE_MISMATCH'],0,"GBT Packer, STATE_MISMATCH Non-Zero")
        self.assertEqual(gbt_counters['FIFO_FULL'],0,"GBT Packer, FIFO_FULL Non-Zero")
        self.assertEqual(gbt_counters['FIFO_OVERFLOW'],0,"GBT Packer, FIFO_OVERFLOW Non-Zero")

        self.check_event_readout(NR_TRIGGERS,2, list(range(NR_CHANNELS)))

        # Reset counters, check if still zero
        self.board.datapathmon.reset_counters()
        self.board.wait(1000)
        counters = self.board.datapathmon.read_all_counters()
        for i in range(NR_CHANNELS):
            for name,val in counters[i].items():
                self.assertEqual(val,0,"Lane {0}, Counter {1}, Value not zero".format(i,name,val))

    def test_comma1200(self):
        self.setup_chips()
        for ch in self.chips:
            ch.propagate_comma()

        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")

        self.board.wait(500)

        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")

        aligned = self.board.gth.align_transceivers()
        self.assertTrue(aligned, "GTH module could not align to all modules")

    @unittest.skip("Transceiver locks to deactivated stream...")
    def test_locks(self):
        self.setup_chips()
        for ch in self.chips:
            ch.propagate_comma()

        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")

        self.board.wait(500)

        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")

        aligned = self.board.gth.align_transceivers()
        self.board.gth.enable_alignment(False)

        for ch in self.chips:
            ch.reset_pll()
            ch.setreg_dtu_cfg(PllOffSignal=1)

        time.sleep(2)
        self.board.wait(65535)
        aligned = self.board.gth.is_aligned()
        self.assertNotIn(True,aligned, "GTH module aligned to deactivated stream")

        self.board.wait(1000)
        for ch in self.chips:
            ch.setreg_mode_ctrl(IBSerialLinkSpeed=1)  # 600 Mbps
            ch.setreg_dtu_cfg(PllOffSignal=0)
            ch.reset_pll()

        cdr_lock_counters = self.board.datapathmon.read_counter(
            range(9), "CDR_LOCK_LOSS_COUNT")
        self.assertNotIn(0,cdr_lock_counters,"Expected a CDR lock loss event")
        aligned_lock_counters = self.board.datapathmon.read_counter(
            range(9), "ALIGNEDLOSS_COUNT")
        self.assertNotIn(0,aligned_lock_counters,"Expected a ALIGNED lock loss event")

        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")

        aligned = self.board.gth.is_aligned()
        self.assertNotIn(False,aligned, "GTH module not aligned anymore")

    def test_prbs1200(self):
        self.setup_chips()
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=0)

        time.sleep(1)
        self.board.wait(500)

        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")

        time.sleep(2)
        self.board.wait(250)
        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")

        self.board.gth.enable_prbs(enable=True, commitTransaction=True)
        self.board.gth.reset_prbs_counter()

        # Read counters
        self.board.wait(100)

        prbs_errors = self.board.gth.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gth.transceivers):
            self.assertEqual(0, cnt, "PRBS Error on Link {0}".format(link))

        # Set chip back to normal mode -> expect errors
        for ch in self.chips:
            ch.propagate_data(commitTransaction=False)
        self.board.wait(300, commitTransaction=False)
        # back to PRBS sending mode
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=0, commitTransaction=True)

        prbs_errors = self.board.gth.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gth.transceivers):
            self.assertNotEqual(
                0, cnt, "No PRBS Error on Link {0}. Errors expected".format(link))

        # check Counter reset operation

        self.board.gth.reset_prbs_counter(commitTransaction=True)
        self.board.wait(200, commitTransaction=True)

        prbs_errors = self.board.gth.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gth.transceivers):
            self.assertEqual(0, cnt, "PRBS Error on Link {0}".format(link))

@unittest.skipIf(not USB_MASTER, "No USB Master -> Cannot test dual master")
class TestWishboneDualMaster(TestcaseBase):
    def setUp(self):
        super(TestWishboneDualMaster, self).setUp()
        self.board_usb.gbtx_flow_monitor.reset_counters(commitTransaction=True)
        self.board_usb.dctrl.rst_ctrl_cntrs()
        self.board_usb.read(1,1)

    def test_multiaccess_write(self):
        NR_WRITES = 10
#        self.board.wait(1000,commitTransaction=False)
        for i in range(NR_WRITES):
            self.board.dctrl.write_chip_opcode(Opcode.RORST, commitTransaction=False)
            self.board.read(1,1,commitTransaction=False)
            self.board_usb.dctrl.write_chip_opcode(Opcode.RORST, commitTransaction=False)
            self.board_usb.read(1,1,commitTransaction=False)

        self.board.flush()
        self.board_usb.flush()
        result_cru = self.board.comm.diagnose_read_results()
        result_usb = self.board_usb.comm.diagnose_read_results()

        rderrors_cru = 0
        rderrors_usb = 0

        for err,addr,data in result_cru:
            if err:
                rderrors_cru += 1
            self.assertEqual(addr,0x0101,"Read from CRU: Address incorrect")
        for err,addr,data in result_usb:
            if err:
                rderrors_usb += 1
            self.assertEqual(addr,0x0101,"Read from USB: Address incorrect")

        #self.assertEqual(rderrors_cru + rderrors_usb,0,
        if rderrors_cru + rderrors_usb > 0:
            print(
                         "{2} + {3} Read Errors on CRU or USB registered. Data_CRU: {0}, Data_USB: {1}"
                .format(result_cru,result_usb, rderrors_cru, rderrors_usb)
            )
        # check that both interfaces still work, and that all writes were received
        self.assertEqual(self.board.dctrl.get_counters()['opcode'],2*NR_WRITES,
                         "Write Execution Mismatch. (Not all chip opcodes performed)")
        self.assertEqual(self.board_usb.dctrl.get_counters()['opcode'],2*NR_WRITES,
                         "Write Execution Mismatch. (Not all chip opcodes performed)")


    def test_interleaved_reads(self):
        testlist = [(self.board.DATAPATH_MONITOR_MODULE,i) for i in range(3,25)] + [(1,1), (1,0)]

        self.board.wait(1000,commitTransaction=False) # sync
        for mod,addr in testlist:
            self.board.read(mod,addr,commitTransaction=False)
        for mod,addr in reversed(testlist):
            self.board_usb.read(mod,addr,commitTransaction=False)

        self.board.flush()
        self.board_usb.flush()

        result_usb = list(reversed(self.board_usb.comm.read_results()))
        result_cru = self.board.comm.read_results()

        self.assertEqual(result_usb,result_cru, "Same Read sequence leads to different results for both wishbone masters")

    def test_timeouts(self):
        githash_ref = self.board.read(1,1)

        # cause timeouts on both interfaces
        self.board.write(100,1,0)
        self.board_usb.write(100,1,0)

        with self.assertRaises(WishboneReadError, msg="Error for illegal read not raised"):
            self.board.read(100,1)
        with self.assertRaises(WishboneReadError, msg="Error for illegal read not raised"):
            self.board_usb.read(100,1)
        # check that read still works
        gh_cru = self.board.read(1,1)
        gh_usb = self.board_usb.read(1,1)

        self.assertEqual(gh_cru,githash_ref,"CRU comm githash mismatch")
        self.assertEqual(gh_usb,githash_ref,"USB comm githash mismatch")

class TestSysmon(TestcaseBase):
    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getTemperature(self):
        rv = self.board.sysmon.get_temperature()
        self.assertTrue(15.0 < rv < 95.0, "Read value is {0}".format(rv))

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVccInt(self):
        rv = self.board.sysmon.get_vcc_int()
        self.assertTrue(0.855 < rv < 1.045, "Read value is {0}".format(rv))

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVccAux(self):
        rv = self.board.sysmon.get_vcc_aux()
        self.assertTrue(1.62 < rv < 1.98, "Read value is {0}".format(rv))

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVccBram(self):
        rv = self.board.sysmon.get_vcc_bram()
        self.assertTrue(0.855 < rv < 1.045, "Read value is {0}".format(rv))

    def test_getOtStatus(self):
        rv = self.board.sysmon.get_ot_status()
        self.assertFalse(rv)

    def test_getTmrMismatch(self):
        rv = self.board.sysmon.get_tmr_mismatch()
        self.assertFalse(rv)

    def test_enableOtProtection(self):
        # Get the current status of register 0x41
        self.board.sysmon.set_drp_address(0x41)
        data1 = self.board.sysmon.get_drp_data()

        # Run tested method
        self.board.sysmon.enable_ot_protection()

        # Get the current status of register 0x41
        self.board.sysmon.set_drp_address(0x41)
        data2 = self.board.sysmon.get_drp_data()

        # Data must be equal except the last bit, the last bit must be 0
        self.assertEqual(data1 & ~0x01, data2 & ~0x01)
        self.assertEqual(data2 & 0x01, 0x00)

    def test_disableOtProtection(self):
        # Get the current status of register 0x41
        self.board.sysmon.set_drp_address(0x41)
        data1 = self.board.sysmon.get_drp_data()

        # Run tested method
        self.board.sysmon.disable_ot_protection()

        # Get the current status of register 0x41
        self.board.sysmon.set_drp_address(0x41)
        data2 = self.board.sysmon.get_drp_data()

        # Data must be equal except the last bit, the last bit must be 1
        self.assertEqual(data1 & ~0x01, data2 & ~0x01)
        self.assertEqual(data2 & 0x01, 0x01)

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVcc_ALPIDE_3v3(self):
        rv = self.board.sysmon.get_vcc_alpide_3v3()
        self.assertTrue(2.97 < rv < 3.63, "Read value is {0}".format(rv))

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVcc_SCA_1v5(self):
        rv = self.board.sysmon.get_vcc_sca_1v5()
        self.assertTrue(1.35 < rv < 1.65, "Read value is {0}".format(rv))


@unittest.skipIf(not SIMULATION, "Check for correct I2C addresses in hardware")
class TestI2C(TestcaseBase):

    def setUp(self):
        super().setUp()

    def test_i2c_gbtx(self):
        self.board.i2c_gbtx.write_data(0, 0x1234, 0x0056, False) # write to GBTx0 address 0x1234
        self.board.i2c_gbtx._write_data(0x00BC, False) # write to GBTx0 address 0x1235
        self.board.i2c_gbtx._write_data(0x0042, False) # write to GBTx0 address 0x1235
        self.board.i2c_gbtx.write_data(1, 0xabcd, 0x00ef, False) # write to GBTx1 address 0xabcd
        self.board.i2c_gbtx.write_data(2, 0x5678, 0x00ab, False) # write to GBTx2 address 0x5678

        rb = self.board.i2c_gbtx.read_data(0, 0x1236) # read from GBTx0 address 0x1236
        self.assertEqual(rb, 0x42, "I2C readback failed: expected 0x0042 got {0:#06x}".format(rb))
        rb = self.board.i2c_gbtx.read_data(0, 0x1234) # read from GBTx0 address 0x1234
        self.assertEqual(rb, 0x56, "I2C readback failed: expected 0x0056 got {0:#06x}".format(rb))
        rb = self.board.i2c_gbtx._read_data() # read from GBTx0 address 0x1235
        self.assertEqual(rb, 0xBC, "I2C readback failed: expected 0x00bc got {0:#06x}".format(rb))

        rb = self.board.i2c_gbtx.read_data(1, 0xabcd) # read from GBTx1 address 0xabcd
        self.assertEqual(rb, 0xef, "I2C readback failed: expected 0x00ef got {0:#06x}".format(rb))

        rb = self.board.i2c_gbtx.read_data(2, 0x5678) # read from GBTx2 address 0x5678
        self.assertEqual(rb, 0xab, "I2C readback failed: expected 0x00ab got {0:#06x}".format(rb))

    def test_i2c_pu1(self):
        self.i2cmod_pu1 = i2c.I2CModule(
            TestWishboneSlaves.WB_I2C_PU1,self.board)

        # write and read main I2C bus (slave with 0 address 1 data byte)
        self.i2cmod_pu1.write(0x16, 0x1234)
        rb = self.i2cmod_pu1.read(0x16)
        self.assertEqual(rb, 0x34, "I2C readback failed: expected 0x0034 got {0:#06x}".format(rb))

        # write and read aux I2C bus (slave with 0 address 1 data byte)
        self.i2cmod_pu1.write(0x20, 0x5678)
        rb = self.i2cmod_pu1.read(0x20)
        self.assertEqual(rb, 0x78, "I2C readback failed: expected 0x0034 got {0:#06x}".format(rb))

        # write and read main I2C bus (slave with 1 byte write, 2 byte read)
        self.i2cmod_pu1.write(0x10, 0xa9)
        rb = self.i2cmod_pu1.read(0x10)
        # expect the last byte written to be in both MSB and LSB (simple I2C slave with just 1 byte memory)
        self.assertEqual(rb, 0xa9a9, "I2C readback failed: expected 0xa9a9 got {0:#06x}".format(rb))

    def test_i2c_pu2(self):
        self.i2cmod_pu2 = i2c.I2CModule(
            TestWishboneSlaves.WB_I2C_PU2,self.board)

        # write and read main I2C bus (slave with 0 address 1 data byte)
        self.i2cmod_pu2.write(0x16, 0x1234)
        rb = self.i2cmod_pu2.read(0x16)
        self.assertEqual(rb, 0x34, "I2C readback failed: expected 0x0034 got {0:#06x}".format(rb))

        # write and read aux I2C bus (slave with 0 address 1 data byte)
        self.i2cmod_pu2.write(0x20, 0x5678)
        rb = self.i2cmod_pu2.read(0x20)
        self.assertEqual(rb, 0x78, "I2C readback failed: expected 0x0034 got {0:#06x}".format(rb))
        # write and read main I2C bus (slave with 1 byte write, 2 byte read)
        self.i2cmod_pu2.write(0x10, 0xa9)
        rb = self.i2cmod_pu2.read(0x10)
        # expect the last byte written to be in both MSB and LSB (simple I2C slave with just 1 byte memory)
        self.assertEqual(rb, 0xa9a9, "I2C readback failed: expected 0xa9a9 got {0:#06x}".format(rb))


class DctrlBaseTest:

    class TestDctrl(TestcaseBase):

        def configure_test(self, connector, chipid):
            self.connector = connector
            self.chipid = chipid

        def setUp(self):
            super().setUp()
            self.board.dctrl.disable_manchester_tx()
            self.ch = Alpide(self.board, chipid=self.chipid)
            self.ch.reset()

        def tearDown(self):
            self.board.dctrl.disable_manchester_tx()
            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=True,
                                           EnableDDR=1)
            self.connector = None
            self.setup_connection_lut()

        def _test_chip_read_write(self):
            self.ch.write_reg(0x19, 0x4242, commitTransaction=True,
                              readback=True, log=False, verbose=False)
            self.ch.write_reg(0x19, 0xDEAD, commitTransaction=True,
                              readback=True, log=False, verbose=False)
            self.ch.write_reg(0x19, 0xAAAA, commitTransaction=True,
                              readback=True, log=False, verbose=False)
            self.ch.write_reg(0x19, 0x5555, commitTransaction=True,
                              readback=True, log=False, verbose=False)

        def _test_manchester_settings(self, manchesterTx=True, manchesterRx=True):
            if manchesterTx:
                self.board.dctrl.enable_manchester_tx()
            else:
                self.board.dctrl.disable_manchester_tx()

            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=not manchesterRx,
                                           EnableDDR=1
                                           )

            self.board.wait(10)

            self._test_chip_read_write()
            self.board.dctrl.disable_manchester_tx()
            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=True,
                                           EnableDDR=1
                                           )

        def _test_reads(self, manchester_rx=True, test_number=30, assert_manchester=False):

            value0 = 0xAA
            value1 = 0x55

            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=not manchester_rx,
                                           EnableDDR=1, commitTransaction=False
                                           )
            self.board.wait(10, commitTransaction=False)
            self.ch.setreg_dtu_test_2(DIN0=value0, DIN1=value1, commitTransaction=False)
            self.board.wait(10, commitTransaction=False)
            for i in range(test_number):
                ret = self.ch.getreg_dtu_test_2()[1]
                manchester_detected = self.board.dctrl.get_manchester_rx_detected()
                self.assertEqual(value0, ret['DIN0'], msg="readback differs set {0:#04X} get {1:#04X} on iteration {2}".format(value0,
                                                                                                                               ret['DIN0'],
                                                                                                                               i))
                self.assertEqual(value1, ret['DIN1'], msg="readback differs set {0:#04X} get {1:#04X} on iteration {2}".format(value1,
                                                                                                                               ret['DIN1'],
                                                                                                                               i))
                if assert_manchester:
                    self.assertEqual(manchester_detected, manchester_rx, msg="Manchester not detected correctly (get {0}, set {1} on iteration {2})".format(manchester_detected, manchester_rx, i))
            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=True,
                                           EnableDDR=1
                                           )

        def test_dctrl_dac_range(self):
            self.ch.setreg_dac_settings_cmu_io_buffers(
                DCTRLDriver=0x2, DCTRLReceiver=0xA)
            self._test_chip_read_write()
            self.ch.setreg_dac_settings_cmu_io_buffers(
                DCTRLDriver=0x8, DCTRLReceiver=0xA)
            self._test_chip_read_write()
            self.ch.setreg_dac_settings_cmu_io_buffers(
                DCTRLDriver=0xF, DCTRLReceiver=0xA)
            self._test_chip_read_write()

        def test_manchester_tx_on_rx_on(self):
            self._test_manchester_settings(True, True)

        def test_manchester_tx_on_rx_off(self):
            self._test_manchester_settings(True, False)

        def test_manchester_tx_off_rx_on(self):
            self._test_manchester_settings(False, True)

        def test_manchester_tx_off_rx_off(self):
            self._test_manchester_settings(False, False)

        def test_idelay(self):
            idelays = self.board.dctrl._get_idelay(index=self.connector)
            for i in range(10):
                idelay = random.randrange(1<<10 -1)
                self.board.dctrl._set_idelay(idelay=idelay, index=self.connector)
                self.board.wait(10)
                self._test_chip_read_write()
            self.board.dctrl._set_idelay(idelay=idelay, index=self.connector)

        def _test_idelays_readback(self, index):
            idelay = random.randrange(1<<10 -1)
            self.board.dctrl._set_idelay(idelay=idelay, index=index)
            read_idelay = self.board.dctrl._get_idelay(index=index)
            self.assertEqual(idelay, read_idelay, msg="idelays differ set {0:#04X} get {1:#04X} on {2}".format(idelay,
                                                                                                               read_idelay,
                                                                                                               index))

        def test_idelays_readback(self):
            idelays = self.board.dctrl.get_idelays()
            for i in range(5):
                self._test_idelays_readback(index=i)
            self.board.dctrl.set_idelays(idelays=idelays)

        def test_multiple_reads_rx_manchester(self):
            self._test_reads(manchester_rx=True)

        def test_multiple_reads_rx_no_manchester(self):
            self._test_reads(manchester_rx=False)

        def test_dclk_phases(self):
            for phase in range(0,360,45):
                for index in range(5):
                    self.board.dctrl.set_dclk_parallel(index=index, phase=phase, commitTransaction=False)
                self.board.dctrl.flush()
                for index in range(5):
                    ret = self.board.dctrl.get_dclk_parallel(index=index)
                    self.assertEqual(ret, phase, msg="phase_set mismatch {0} instead of {1} on index {2}".format(ret,
                                                                                                                 phase,
                                                                                                                 index))
            for index in range(5):
                self.board.dctrl.set_dclk_parallel(index=index, phase=180)
            self.ch.reset()

        def test_CMU_error_status(self):
            self.ch.getreg_dtu_pll_lock_2()
            dataread, ret = self.ch.getreg_cmu_and_dmu_status()
            self.assertEqual(ret["CMUErrorsCounter"], 0, msg="CMU errors are {0:#04X} instead of 0 {1:#06X}".format(ret["CMUErrorsCounter"], dataread))
            self.assertEqual(ret["CMUTimeOutCounter"], 0, msg="CMU Timeout errors are {0:#04X} instead of 0 {1:#06X}".format(ret["CMUTimeOutCounter"], dataread))
            self.assertEqual(ret["CMUOpCounter"], 0, msg="CMU Unknown Opcode errors are {0:#04X} instead of 0 {1:#06X}".format(ret["CMUOpCounter"], dataread))

        def test_counters(self):
            self.ch.getreg_dtu_pll_lock_2()
            self.board.dctrl.rst_ctrl_cntrs()
            ret = self.board.dctrl.get_counters()
            expected = {'broadcast':0, 'write':0, 'read': 0, 'opcode':0, 'trigger_sent':0, 'trigger_not_sent':0, 'pulse_sent':0, 'opcode_rejected':0}
            self.assertEqual(ret, expected, msg="Wrong counter value, got {0}, expected {1}".format(ret, expected))
            self.ch.getreg_dtu_pll_lock_2()
            ret = self.board.dctrl.get_counters()
            expected['read'] = 1
            self.assertEqual(ret, expected, msg="Wrong counter value, got {0}, expected {1}".format(ret, expected))

        def test_readback_wait_cycles(self):
            """Test readback of initial wait register"""
            value = self.board.dctrl.get_wait_cycles()
            test_value = 5
            self.board.dctrl.set_wait_cycles(test_value)
            rd_value = self.board.dctrl.get_wait_cycles()
            self.assertEqual(rd_value, test_value, msg="Wrong counter value, got {0}, expected {1}".format(rd_value, test_value))
            self.board.dctrl.set_wait_cycles(value)

@unittest.skipIf(0 not in DCTRL_CONNECTORS, "No Chip Connected")
class TestDctrl0(DctrlBaseTest.TestDctrl):

    def setUp(self):
        self.configure_test(connector=0, chipid=SENSOR_LIST[0])
        super().setUp()

@unittest.skipIf(1 not in DCTRL_CONNECTORS, "No Chip Connected")
class TestDctrl1(DctrlBaseTest.TestDctrl):

    def setUp(self):
        self.configure_test(connector=1, chipid=SENSOR_LIST[0])
        super().setUp()

@unittest.skipIf(2 not in DCTRL_CONNECTORS, "No Chip Connected")
class TestDctrl2(DctrlBaseTest.TestDctrl):

    def setUp(self):
        self.configure_test(connector=2, chipid=SENSOR_LIST[0])
        super().setUp()

@unittest.skipIf(3 not in DCTRL_CONNECTORS, "No Chip Connected")
class TestDctrl3(DctrlBaseTest.TestDctrl):

    def setUp(self):
        self.configure_test(connector=3, chipid=SENSOR_LIST[0])
        super().setUp()

@unittest.skipIf(4 not in DCTRL_CONNECTORS, "No Chip Connected")
class TestDctrl4(DctrlBaseTest.TestDctrl):

    def setUp(self):
        self.configure_test(connector=4, chipid=SENSOR_LIST[0])
        super().setUp()

@unittest.skip("deactivate")
class TestPythonScripts(TestcaseBase):

    def _function_call_routine(self):
        self.board.check_git_hash_and_date(expected_git_hash=GITHASH)
        self.board.wait(100)
        counters = self.board.datapathmon.read_all_counters()

    def _function_read_counters(self):
        counters_datamon = self.board.datapathmon.read_all_counters()
        counters_dctrl = self.board.dctrl.get_counters()
        counters_cru = self.cru.read_counters()

        ch = Alpide(self.board,chipid=SENSOR_LIST[0]) #global broadcast
        seu_error_counter = ch.read_reg(Addr.SEU_ERROR_COUNTER)
        lock = ch.getreg_dtu_pll_lock_1()[1]
        lock_counter = lock['LockCounter']
        lock_status = lock['LockStatus']
        lock_flag = lock['LockFlag']

        powerboard = PowerBoard(self.board.comm,logging.getLogger("Powerboard"))
        latch_status = powerboard.ReadPowerLatchStatus(1)
        bias_latch_status = powerboard.ReadBiasLatchStatus(1)
        adc_power = powerboard.ReadPowerADC()
        adc_bias = powerboard.ReadBiasADC()

    def test_githash(self):
        NR_TESTS = 1000
        keys = {
            self.board.read(65,0,commitTransaction=True):"CRU 1 0" ,
            self.board.read(65,1,commitTransaction=True):"CRU 1 1" ,
            self.board.read(1,0,commitTransaction=True):"RDO 1 0" ,
            self.board.read(1,1,commitTransaction=True):"RDO 1 1",
            self.board.read(3,0,commitTransaction=True):"RDO 3 0"
        }
        for i in range(NR_TESTS):
            self.board.read(65,0,commitTransaction=False)
            #self.board.read(3,0,commitTransaction=False)
            self.board.read(1,0,commitTransaction=False)
            self.board.read(65,1,commitTransaction=False)
            self.board.read(1,1,commitTransaction=False)
        self.board.flush()
        results = self.board.read_all()
        result_set = {}
        for r in results:
            if r not in result_set:
                result_set[r] = 0
            result_set[r] += 1
        print(["{0}: {1}".format(keys[k],v) for k,v in result_set.items()])
        for k,x in result_set.items():
            self.assertEqual(NR_TESTS,x,"Address {0}, counter not {1}".format(k,NR_TESTS))


    def _function_readout_setup(self):
        #setup all chips
        ch = Alpide(self.board,chipid=0x0F) #global broadcast
        ch.reset()
        self.board.gth.initialize(check_reset_done=False)
        ch.initialize(disable_manchester=1,grst=False,cfg_ob_module=False)
        ch.setreg_dtu_dacs(PLLDAC=8,DriverDAC=8,PreDAC=8)
        for pll_off_sig in [0,1,0]:
            ch.setreg_dtu_cfg(VcoDelayStages=1,
                              PllBandwidthControl = 1,
                              PllOffSignal=pll_off_sig,
                              SerPhase=8,
                              PLLReset=0,
                              LoadENStatus=0)

        ch.board.write_chip_opcode(Opcode.RORST)

        ch.setreg_fromu_cfg_1(
                           MEBMask=0,
                           EnStrobeGeneration=0,
                           EnBusyMonitoring=1,
                           PulseMode=0,
                           EnPulse2Strobe=0,
                           EnRotatePulseLines=0,
                           TriggerDelay=0)

        ch.setreg_fromu_pulsing_2(PulseDuration=0xFF)
        ch.setreg_fromu_pulsing1(PulseDelay=0xF)

        ch.mask_all_pixels()
        ch.region_control_register_mask_all_double_columns(broadcast=True)

        ch.setreg_mode_ctrl(ChipModeSelector=1,
                            EnClustering=1,
                            MatrixROSpeed=1,
                            IBSerialLinkSpeed=3,
                            EnSkewGlobalSignals=1,
                            EnSkewStartReadout=1,
                            EnReadoutClockGating=1,
                            EnReadoutFromCMU=0)

        self.board.wait(1000)
        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")
        self.board.wait(100)
        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")
        self.board.gth.align_transceivers(check_aligned=False)
        self.board.wait(255)
        aligned = self.board.gth.is_aligned()
        self.assertTrue(aligned, "GTH module could not align to all modules")
        self.board.datapathmon.reset_counters()
        counters = self.board.datapathmon.read_all_counters()
        for idx,c in enumerate(counters):
            for cntr,val in c.items():
                self.assertEqual(0,val,"Counter {0} non-zero after reset".format(idx))
        self.board.gth.enable_data()


    def _test_prefetch_function(self,func):
        self.board.comm.start_recording()
        func()
        sequence = self.board.comm.stop_recording()
        print("Length of prefetch sequence: {0}".format(len(sequence)))
        self.board.comm.prefetch()
        func()
        self.assertTrue(self.board.comm.prefetch_mode,"Prefetch mode False, should be True")
        with self.assertLogs(self.board.comm.logger,logging.ERROR):
            self.board.check_git_hash_and_date(expected_git_hash=GITHASH)
            self.assertFalse(self.board.comm.prefetch_mode,"Prefetch mode True, should be False")

    def test_prefetch_githash(self):
        self._test_prefetch_function(self.test_githash)

    def test_prefetch_counters(self):
        self._test_prefetch_function(self._function_read_counters)

    def test_prefetch_basic_communication(self):
        self._test_prefetch_function(self._function_call_routine)
    def test_prefetch_sensor_datareadout(self):
        self._test_prefetch_function(self._function_readout_setup)

@unittest.skip("add sca in regression")
class TestScaReset(TestcaseBase):
    def setUp(self):
        super(TestScaReset, self).setUp()
        self.board.wait(1000,commitTransaction=False) # sync

    def test_reset(self):
        """Asserts reset via SCA, it tries to read, expect fail, deassert reset, expect correct read"""
        read_lists = [(1,0), (1,1)]

        # reset is active
        self.sca.set_xcku_reset(1)
        for mod,addr in testlist:
            with self.assertRaises(WishboneReadError, msg="Error for read during reset not raised"):
                self.board.read(mod,addr)

        # reset is deactivated
        self.sca.set_xkcu_reset(0)
        for mod,addr in testlist:
            self.board.read(mod,addr)

@unittest.skip("WB2Fifo not used in current design")
class TestWb2Fifo(TestcaseBase):

    def setUp(self):
        super(TestWb2Fifo, self).setUp()


    def test_pagewrite(self):
        wr_counter = self.board.wb2fifo.read_write_counter()
        overflow_counter = self.board.wb2fifo.read_overflow_counter()
        status = self.board.wb2fifo.read_fifo_status()

        print("Write counter: {0:d}, overflow counter: {1:d}, status: {2:04x}".format(wr_counter,overflow_counter,status))
        self.board.wb2fifo.write_bitfile("./load_bitfile.py")
        wr_counter = self.board.wb2fifo.read_write_counter()
        overflow_counter = self.board.wb2fifo.read_overflow_counter()
        status = self.board.wb2fifo.read_fifo_status()

        print("Write counter: {0:d}, overflow counter: {1:d}, status: {2:04x}".format(wr_counter,overflow_counter,status))

    def test_performance(self):
        bytes_to_transmit = 24125021 #bitfile size
        chunks = 256*100
        chunks_per_part = 10
        data_part_size = chunks*chunks_per_part*3
        repetitions = int(bytes_to_transmit/data_part_size + 0.5)
        data = bytearray(data_part_size)
        total_bytes = data_part_size*repetitions


        print("Transmit {0} bytes".format(total_bytes))

        wr_counter = self.board.wb2fifo.read_write_counter()

        starttime = time.time()

        for i in range(repetitions):
            self.board.wb2fifo.bulk_write(data,chunks)

        wr_counter2 = self.board.wb2fifo.read_write_counter()
        endtime = time.time()

        duration = endtime - starttime
        print("Transmission time: {0}".format(duration))

        rate = total_bytes / duration
        rate_mb = rate / (1024*1024)
        print("Transmission rate: {0} Mib/s".format(rate_mb))

        written = wr_counter2-wr_counter
        self.assertEqual(written,total_bytes/3,"Mismatch in words written and words send to USB")

    def test_validate_counter(self):
        cnt_max = 2048
        writes, errors = self.board.wb2fifo.counter_test(cnt_max)

        self.assertEqual(0,errors,"Errors encountered while running counter test")
        self.assertEqual(cnt_max,writes,"Number of writes mismatch")

    def test_counter_read(self):
        wr_counter = self.board.wb2fifo.read_write_counter()
        self.board.wb2fifo.read_read_counter()
        self.board.wb2fifo.read_overflow_counter()
        self.board.wb2fifo.read_validate_read_counter()

        self.board.wb2fifo.write(0,0)
        wr_counter2 = self.board.wb2fifo.read_write_counter()

        self.assertEqual(wr_counter+1,wr_counter2,"Write counter mismatch, did not track write operation")

    def test_bulk_write(self):
        wr_counter = self.board.wb2fifo.read_write_counter()

        nr_words = 2500
        data = bytearray(nr_words*3)
        self.board.wb2fifo.bulk_write(data)

        wr_counter2 = self.board.wb2fifo.read_write_counter()

        written = wr_counter2-wr_counter
        self.assertEqual(written,nr_words,"Write counter mismatch, expected {0} writes, registered {1}".format(nr_words,written))

@unittest.skip("Dummytest for exit code verification")
class TestSimExitHandling(TestcaseBase):
    def setUp(self):
        super().setUp()

    def test_1_pass(self):
        githash_ref = self.board.read(1,1)

    @unittest.skip("Failure disabled")
    def test_2_fail(self):
        self.assertEqual(0,1,"Failure provoked")

@unittest.skipIf(SIMULATION and not SIMULATE_CRU,"Needs CRU functionality to test")
class TestCRUSWTRaceCondition(TestcaseBase):
    def setUp(self):
        super().setUp()
        self.logger = logging.getLogger("TestRaceCondition")

    def tearDown(self):
        super().tearDown()

    def _test_register(self,module,address,mask):
        if SIMULATION:
            NR_TESTS = 10
        else:
            NR_TESTS = 100
        error_counts = 0
        base_value = self.board.read(module,address)
        base_value_test = ~base_value&mask
        self.board.gbtx_flow_monitor.reset_counters()
        self.send_idle(50)
        self.cru.reset_counters()
        for i in range(NR_TESTS):
            self.board.write(module,address,base_value_test)
            self.send_end_of_triggered()
            self.cru.wait(20)
            value_rb = self.board.read(module,address)
            self.board.write(module,address,base_value)
            if value_rb != base_value_test:
                error_counts += 1
                self.logger.info("Iteration {0}. Mismatch. {1}/{2}".format(i,value_rb,base_value_test))
            #self.sync()

        cru_counter = self.cru.read_counters()['gbt_wr_swt_counter']
        self.board.gbtx_flow_monitor.latch_counters(commitTransaction=False)
        self.send_idle(50)
        gbtx_counters = self.board.gbtx_flow_monitor._get_counters()

        swt_counter = gbtx_counters['swt_downlink']


        self.logger.info("SWT Counter value: {0}".format(swt_counter))
        self.logger.info("Cru counter: {0}".format(cru_counter))

        self.assertEqual(cru_counter,3*NR_TESTS,"CRU SWT wr counter mismatch (3* Number of Tests)")
        self.assertEqual(swt_counter,3*NR_TESTS+2,"SWT counter mismatch (should be 3* Number of Tests + 2 (counter latching))")


        self.assertEqual(error_counts,0,"Value rb failed")


    def test_set_dctrl_mask(self):
        self._test_register(self.board.ALPIDE_MODULE,WsDctrlAddress.SET_DCTRL_TX_MASK,0x1F)
    def test_set_dclk_mask(self):
        self._test_register(self.board.ALPIDE_MODULE,WsDctrlAddress.SET_DCLK_TX_MASK,0x1F)
    def test_gbtx2_idelay(self):
        self._test_register(self.board.GBTX2_MODULE,WsGbtxControllerAddress.SET_IDELAY_VALUE0,0x1FF)


if __name__ == '__main__':

    timeout = 1

    # setup logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    log_file = "Ruv1_regression.log"
    log_file_errors = "Ruv1_regression_errors.log"

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    fh2 = logging.FileHandler(log_file_errors)
    fh2.setLevel(logging.ERROR)

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)


    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    formatter_ch = logging.Formatter(
        "%(name)s - %(levelname)s - %(message)s")


    fh.setFormatter(formatter)
    fh2.setFormatter(formatter)
    ch.setFormatter(formatter_ch)

    logger.addHandler(fh)
    logger.addHandler(fh2)
    logger.addHandler(ch)

    if SIMULATION:
        sim_serv = simulation_if.SimulationServer()
        if SIMULATE_CRU:
            gbt_sim = simulation_if.GbtCruGbtxBridge(server=sim_serv.server)
            comm = simulation_if.UsbCommSim(server=sim_serv.server)
        else:
            gbt_sim = simulation_if.GbtxSim(server=sim_serv.server)
            comm = simulation_if.Wb2GbtxComm(gbtx_sim=gbt_sim)
            gbtx_sim_comm = comm
        if USB_MASTER:
            comm_usb = simulation_if.UsbCommSim(server=sim_serv.server)
        else:
            comm_usb=comm
        sim_serv.start()

        time.sleep(0.2)
    else:
        serv = communication.UsbCommServer(
            "../../modules/usb_if/software/usb_comm_server/build/usb_comm",
            serial=SERIAL_CRU)
        serv.start()
        time.sleep(0.5)
        comm = communication.NetUsbComm(Timeout=timeout)
        if USB_MASTER:
            comm_usb = communication.PyUsbComm(serialNr=SERIAL_RDO)
        else:
            comm_usb = comm

    comm_prefetch = communication.PrefetchCommunication(comm)
    comm_prefetch.enable_rderr_exception()

    comm_usb_prefetch = communication.PrefetchCommunication(comm_usb)
    comm_usb_prefetch.enable_rderr_exception()

    cruGlobal = ru_board.RUv0_CRU(comm_prefetch)
    boardGlobal = ru_board.RUv1(comm_prefetch)
    if SIMULATE_CRU:
        cruGlobal.write(cruGlobal.GBT_FPGA_MODULE,2,0)
        cruGlobal.write(cruGlobal.GBT_FPGA_MODULE,0,1)
        cruGlobal.write(cruGlobal.GBT_FPGA_MODULE,0,0x60)
    if USB_MASTER:
        boardGlobal_usb = ru_board.RUv1(comm_usb_prefetch)

    connection_lut = {sensor: DCTRL_CONNECTORS[0] for sensor in SENSOR_LIST}
    connection_lut[0x0F]=DCTRL_CONNECTORS[0]
    boardGlobal.set_chip2connector_lut(connection_lut)

    # general setup
    boardGlobal.gth.set_transceivers(GTH_LIST)
    boardGlobal.datapathmon.set_lanes(GTH_LIST)
    boardGlobal.gpio.set_transceivers(GPIO_LIST)
    boardGlobal.datapathmon_gpio.set_lanes(GPIO_LIST)

    try:
        logger.info("Start Test")
        unittest.main(verbosity=2, exit=True)
    except KeyboardInterrupt:
        traceback.print_exc(file=sys.stdout)
        os._exit(1)
