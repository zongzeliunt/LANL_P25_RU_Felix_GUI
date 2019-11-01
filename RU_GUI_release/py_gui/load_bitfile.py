import logging
import time
import unittest
import sys
import platform

sys.path.append('../../modules/board_support_software/software/py/')
from module_includes import *

import ru_wb2fifo

from communication import *

VID = 0x04b4
PID = 0x0008
SLV_ADDR = 4
# windows = 0, Linux = 2
if (platform.system() == 'Windows'):
    ITFID = 0
else:
    ITFID = 2
WB2FIFO_MODULE = 36

if(len(sys.argv) < 2):
    exit("usage: load_bitfile.py <bitfile> [<serial_number>]")


if(len(sys.argv) == 3):
    comm = PyUsbComm(VID=VID,PID=PID,IF=ITFID,serialNr=sys.argv[2])
else:
    comm = PyUsbComm(VID=VID,PID=PID,IF=ITFID)

lbf = ru_wb2fifo.WishboneToFifo(comm=comm,moduleid=WB2FIFO_MODULE)

ret = lbf.write_bitfile(sys.argv[1], timeout_count = 10)
if(ret <= 0):
    print ("writing incomplete, bytes written = ", -ret)
else:
    print ("total bytes written = ", ret)


