#!/usr/bin/python
# -*- coding: utf-8 -*-

# tbproc.py
# tbproc - test beam helper functions
# krzysztof.sielewicz@cern.ch

from Tkinter import *
import time
import subprocess
import os
import config

MASK_FILE_DATA_OFFSET = 8
RBD_FILE_LINES = 2860421
VIVADO_PATH_LNX = config.VIVADOLAB_PATH
TCL_SCRIPTS_PATH_LNX = 'tcl_scripts/'


def bitfile_readback(readback_bitfile_path):
    print (subprocess.call([VIVADO_PATH_LNX,
                            "-mode",
                            "batch",
                            "-source",
                            TCL_SCRIPTS_PATH_LNX + "readback.tcl",
                            "-tclargs",
                            readback_bitfile_path]))


# compare_cram_tbp - compare CRAM readback file test-beam procedure
def compare_cram_tbp(txtPntr,
                     eDrtnPntr,
                     eFlxPntr,
                     prgsBrPntr,
                     textStatusPntr,
                     progFPGAState,
                     rdbckFPGAState,
                     rdbckFl,
                     rdbckCmpFlsState,
                     enblErrCntrs,
                     enblCnslLog):
    global crcErr, bfrErr, sedOkErr, sedNgErr, dedErr

    pathFlRbd = RBD_FPGA_FILE_PATH_LNX + rdbckFl.get()
    print pathFlRbd
    if (os.path.isfile(pathFlRbd) and rdbckFPGAState.get()):
        txtPntr.insert(END, 'Cannot perform the test because the specified readback file already exists'
                            'and readback the FPGA option is enabled!\n', 'color_red')
    else:
        tDrtn = int(eDrtnPntr.get())
        txtPntr.insert(END, '### CRAM Readback test ### \n', 'color_green')
        txtPntr.insert(END, 'Test duration: %d s\n' % (tDrtn), 'color_green')
        txtPntr.insert(END, 'Particle flux: %s p/(cm^2)*s\n' % (eFlxPntr.get()), 'color_green')

        # programming the FPGA
        if(progFPGAState.get()):
            progFPGA(textStatusPntr, txtPntr, VIVADO_PATH_LNX, TCL_SCRIPTS_PATH_LNX, BIT_FPGA_GOLDEN_FILE_PATH_LNX)

        # waiting
        print 'Start waiting'
        txtPntr.insert(END, 'Starting the waiting, duration = %ds\n' % (tDrtn), 'color_green')
        textStatusPntr.set('Waiting in progress...')
        prgsBrPntr["value"] = 0
        for i in range(0, tDrtn):
            time.sleep(1)
            progress = int((i * 100) / tDrtn) + 1
            prgsBrPntr["value"] = progress
            textStatusPntr.set('Waiting in progress... %ds passed [%d / 100%%]' % (i, progress))
        print 'Waiting done'
        prgsBrPntr["value"] = 0
        txtPntr.insert(END, 'The waiting finished.\n', 'color_green')

        # reading back the FPGA
        if(rdbckFPGAState.get()):
            enblErrCntrs[0] = False  # disable error counting
            tmStrt = time.time()
            textStatusPntr.set('Reading back the FPGA...')
            txtPntr.insert(END, 'Reading back the FPGA...\n', 'color_green')
            txtPntr.insert(END, 'Readback BITFILE: %s\n' % (pathFlRbd), 'color_green')
            enblCnslLog[0] = False  # disable console logging
            print subprocess.call([VIVADO_PATH_LNX,
                                   "-mode",
                                   "batch",
                                   "-source",
                                   TCL_SCRIPTS_PATH_LNX + "readback.tcl",
                                   "-tclargs",
                                   pathFlRbd])
            enblCnslLog[0] = True  # enable console logging
            tmEnd = time.time()
            tmDelta = tmEnd - tmStrt
            txtPntr.insert(END, 'The FPGA was readback in %ds!\n' % (int(tmDelta)), 'color_green')
            txtPntr.see(END)  # auto scroll
            enblErrCntrs[0] = True  # enable error counting

        # comparing the files
        if(rdbckCmpFlsState.get()):
            txtPntr.insert(END, 'Comparing the files...\n', 'color_green')
            txtPntr.see(END)  # auto scroll
            # calculating the cross-section from here
            # CRAM errors
            [errCntCRAM, errCntBRAM] = compare_cram_rbd_fls(prgsBrPntr, txtPntr, textStatusPntr, pathFlRbd)
            fluence = float(eFlxPntr.get()) * tDrtn  # fluence = flux * time
            if(fluence == 0):
                txtPntr.insert(END, 'Wrong time or fluence!\n', 'color_red')
            else:
                nBitsCRAM = 75144416
                cross_section = errCntCRAM / (fluence * nBitsCRAM)
                # print cross_section
                txtPntr.insert(END, 'The calculated CRAM cross section is %.4e!\n' % (cross_section), 'color_green')

def progFPGA(textStatusPntr, txtPntr, vivadoPathLnx, tclScriptsPathLnx, fpgaBitstreamPath):
    tmStrt = time.time()
    print 'Starting programming the FPGA'
    textStatusPntr.set('Programming the FPGA...')
    txtPntr.insert(END, 'Programming the FPGA...\n', 'color_green')
    txtPntr.insert(END, 'BITFILE: %s\n' % (fpgaBitstreamPath), 'color_green')
    print subprocess.call([vivadoPathLnx, "-mode", "batch", "-source", tclScriptsPathLnx + "prog.tcl", "-tclargs",
                           fpgaBitstreamPath])
    tmEnd = time.time()
    tmDelta = tmEnd - tmStrt
    txtPntr.insert(END, 'The FPGA was programmed in %ds!\n' % (int(tmDelta)), 'color_green')
    txtPntr.see(END)  # auto scroll
    textStatusPntr.set('FPGA programmed!')

def progFPGA_Vivado(log_file, vivadoPathLnx, tclScriptsPathLnx, fpgaBitstreamPath):
    tmStrt = time.time()
    log_file.write('Programming the FPGA...\n')
    log_file.write('BITFILE: %s\n' % (fpgaBitstreamPath))
    print subprocess.call([vivadoPathLnx, "-mode", "batch", "-source", tclScriptsPathLnx + "prog.tcl", "-tclargs",
                           fpgaBitstreamPath])
    tmEnd = time.time()
    tmDelta = tmEnd - tmStrt
    log_file.write('The FPGA was programmed in %ds!\n' % (int(tmDelta)))

def compare_cram_rbd_fls(prgsBrPntr, txtPntr, textStatusPntr, pathFlRbd):
    errCntCRAM = 0
    errCntBRAM = 0
    # prgsBrPntr["value"] = 0
    fpgaBtstrm = open(pathFlRbd, 'r')
    goldenBtstrm = open(RBD_FPGA_GOLDEN_FILE_PATH_LNX, 'r')
    msdBtstrm = open(MSD_FPGA_GOLDEN_FILE_PATH_LNX, 'r')

    for i in range(0, 8):
        goldenBtstrmLine = goldenBtstrm.readline()
        msdBtstrmLine = msdBtstrm.readline()

    tmStrt = time.time()
    textStatusPntr.set('Comparing in progress...')

    for n in range(0, RBD_FILE_LINES):
        # progress = int((n*100)/RBD_FILE_LINES) + 1
        # prgsBrPntr["value"] = progress
        # textStatusPntr.set('Comparing in progress... [%d / 100%%]' %(progress))
        fpgaBtstrmLine = fpgaBtstrm.readline()
        goldenBtstrmLine = goldenBtstrm.readline()
        msdBtstrmLine = msdBtstrm.readline()

        for i in range(0, 32):
            if(fpgaBtstrmLine[i] != goldenBtstrmLine[i]):
                if(msdBtstrmLine[i] == '0'):
                    # print 'A CRAM error was found at:', n, i
                    errCntCRAM += 1
                else:
                    # print 'A BRAM error was found at:', n, i
                    errCntBRAM += 1

    print 'errCntCRAM =', errCntCRAM
    print 'errCntBRAM =', errCntBRAM
    tmEnd = time.time()
    txtPntr.insert(END,
                   'Error report (%ds):\nerrCntCRAM = %d\nerrCntBRAM = %d\n' % (int(tmEnd - tmStrt),
                                                                                errCntCRAM, errCntBRAM), 'color_red')
    return [errCntCRAM, errCntBRAM]

def compare_cram_rbd_fls_ex():
    errCntCRAM = 0
    errCntBRAM = 0
    fpgaBtstrm = open('E:/TB_REZ_13140316/tb_firmware/32bit_pll_96_50MHz_asynchreg/FPGA_RBD_4.rbd', 'r')
    goldenBtstrm = open('E:/TB_REZ_13140316/tb_firmware/32bit_pll_96_50MHz_asynchreg/RUv0a_top.rbd', 'r')
    msdBtstrm = open('E:/TB_REZ_13140316/tb_firmware/32bit_pll_96_50MHz_asynchreg/RUv0a_top.msd', 'r')

    for i in range(0, 8):
        goldenBtstrmLine = goldenBtstrm.readline()
        msdBtstrmLine = msdBtstrm.readline()

    tmStrt = time.time()
    for n in range(0, RBD_FILE_LINES):
        fpgaBtstrmLine = fpgaBtstrm.readline()
        goldenBtstrmLine = goldenBtstrm.readline()
        msdBtstrmLine = msdBtstrm.readline()

        for i in range(0, 32):
            if(fpgaBtstrmLine[i] != goldenBtstrmLine[i]):
                if(msdBtstrmLine[i] == '0'):
                    errCntCRAM += 1
                else:
                    errCntBRAM += 1

    tmEnd = time.time()
    print 'Error report (%ds):\nerrCntCRAM = %d\nerrCntBRAM = %d\n' % (int(tmEnd - tmStrt), errCntCRAM, errCntBRAM)
    return [errCntCRAM, errCntBRAM]
