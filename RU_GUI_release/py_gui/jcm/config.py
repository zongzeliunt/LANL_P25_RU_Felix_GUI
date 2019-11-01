"""
Matteo Lupi <matteo.lupi@cern.ch>
Configuration file to set platform dependent options
"""

import os
import sys
import getpass
USR = getpass.getuser()
MODULE_PATH = os.path.dirname(sys.modules[__name__].__file__)

if USR in ['ksielewi', 'root', 'testbeam']:
    VIVADOLAB_PATH = '/opt/Xilinx/Vivado_Lab/2017.1/bin/vivado_lab'
    SEM_IP_PORT = '/dev/ttySEM_IP_UART'
    POWERSUPPLY_PORT = '/dev/ttyHAMEG0'
    BEAM_SHUTTER_PORT = '/dev/BEAM_SHUTTER'
    TESTBEAM_MODE = 0
    MAX_REPEAT = 25
elif USR == 'itsru':
    VIVADOLAB_PATH = '/opt/Xilinx/Vivado_Lab/2016.2/bin/vivado_lab'
    SEM_IP_PORT = '/dev/ttySEM_IP_UART'
    POWERSUPPLY_PORT = '/dev/ttyHAMEG0'
    BEAM_SHUTTER_PORT = '/dev/ttyBEAM_SHTR_CNTRL'
    TESTBEAM_MODE = 1
    MAX_REPEAT = 25
elif USR == 'mbonora':
    VIVADOLAB_PATH = '/opt/Xilinx/Vivado_Lab/2016.4/bin/vivado_lab'
    SEM_IP_PORT = '/dev/ttySEM_IP_CTRL'
    POWERSUPPLY_PORT = '/dev/ttyHAMEG1'
    BEAM_SHUTTER_PORT = '/dev/BEAM_SHUTTER'
    TESTBEAM_MODE = 0
    MAX_REPEAT = 25
else:
    print("User not defined in config.py")
    raise RuntimeError
