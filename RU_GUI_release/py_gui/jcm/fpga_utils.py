#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Krzysztof Marek Sielewicz <krzysztof.sielewicz@cern.ch>
FPGA utilities
"""

import time
import sys
import subprocess
import os
import config
import struct
import fire


MASK_FILE_DATA_OFFSET = 8
RBD_FILE_K7_325T_LINES = 2860421
RBD_FILE_KU_060_LINES = 6030823
VIVADO_PATH_LNX = config.VIVADOLAB_PATH
TCL_SCRIPTS_PATH_LNX = 'tcl_scripts/'


def readback_fpga(readback_bitfile_path):
    """This function reads the bitfile back from the FPGA
    over Vivado"""

    time_start = time.time()
    print("Reading back the FPGA bitfile...\n")
    print("Readback bitfile path: %s\n" % readback_bitfile_path)
    if os.path.exists(readback_bitfile_path):
        print("Specified readback bitfile already exists!")
    else:
        print(subprocess.call([VIVADO_PATH_LNX,
                               "-mode",
                               "batch",
                               "-source",
                               TCL_SCRIPTS_PATH_LNX + "readback.tcl",
                               "-tclargs",
                               readback_bitfile_path]))
    time_end = time.time()
    print("The FPGA was read back in %ds!\n" % (int(time_end - time_start)))


def configure_fpga(bitfile_path):
    """This function configures the FPGA over Vivado"""

    time_start = time.time()
    print("Programming the FPGA...\n")
    print("Bitfile path: %s\n" % bitfile_path)
    print(subprocess.call([VIVADO_PATH_LNX,
                           "-mode",
                           "batch",
                           "-source",
                           TCL_SCRIPTS_PATH_LNX + "prog.tcl",
                           "-tclargs",
                           bitfile_path]))
    time_end = time.time()
    print("The FPGA was programmed in %ds!\n" % (int(time_end - time_start)))


def compare_rbd_bitfiles(golden_rbd_path,
                         readback_rbd_path,
                         msd_path):
    """Function that compares readback images"""
    errors_cram = 0
    golden_rbd = open(golden_rbd_path)
    readback_rbd = open(readback_rbd_path)
    msd = open(msd_path)

    for i in range(0, 8):
        golden_rbd_line = golden_rbd.readline()
        msd_line = msd.readline()

    time_start = time.time()
    for n in range(0, RBD_FILE_KU_060_LINES):
        golden_rbd_line = golden_rbd.readline()
        msd_line = msd.readline()
        readback_rbd_line = readback_rbd.readline()

        for i in range(0, 32):
            if(readback_rbd_line[i] != golden_rbd_line[i]
               and msd_line[i] == '0'):
                errors_cram += 1

    time_end = time.time()
    print("Error report (%ds):\nerrors_cram: %d" \
          % (int(time_end - time_start), errors_cram))
    return errors_cram


def compare_readbacks(golden_path,
                      readback_path):
    """Function that compares readback images"""

    errors_cram = 0
    seu_01 = 0
    seu_10 = 0
    mbu_pos = 0
    mbu_neg = 0
    mbu_delta = []

    golden = open(golden_path, "rb")
    readback = open(readback_path, "rb")

    golden_array = golden.read()
    readback_array = readback.read()
    print(len(golden_array))
    print(len(readback_array))

    for i in range(0, len(golden_array)):
        if golden_array[i] != readback_array[i]:
            gold_byte, = struct.unpack("B", golden_array[i])
            gold_byte_ones = bin(gold_byte).count("1")
            readback_byte, = struct.unpack("B", readback_array[i])
            readback_byte_ones = bin(readback_byte).count("1")

            delta = gold_byte_ones - readback_byte_ones

            if delta == -1:
                seu_01 += 1
            elif delta == 1:
                seu_10 += 1
            elif delta > 1:
                mbu_pos += 1
                mbu_delta.append(delta)
                print("\n\n\n\n\n DUPA \n\n\n\n\n")
            elif delta < -1:
                mbu_neg += 1
                mbu_delta.append(delta)
                print("\n\n\n\n\n DUPA \n\n\n\n\n")

            print(gold_byte,
                  readback_byte,
                  delta)

            errors_cram += 1

    print("\n\nseu_01: {0}\nseu_10: {1}\nmbu_01: {2}\nmbu_10: {3}".format(seu_01, seu_10, mbu_neg, mbu_pos))
    print(mbu_delta)
    golden.close()
    readback.close()

    return errors_cram

def main():
    """ main function """

    os.system('clear')

    if len(sys.argv) > 1:
        path_1 = sys.argv[1]
        #path_2 = sys.argv[2]
        # path_3 = sys.argv[3]
    else:
        print("Not enough parameters given!")
        return 0

    readback_fpga(path1)
    # configure_fpga(path1)
    # compare_rbd_bitfiles(path_1, path_2, path_3)
    #print("errors in total = {0}\n".format(compare_readbacks(path_1, path_2)))

def main_fire():
    fire.Fire()

if __name__ == "__main__":
    #main()
    main_fire()
