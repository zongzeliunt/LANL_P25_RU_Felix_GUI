#!/usr/bin/python
# -*- coding: utf-8 -*-

# bfproc.py
# bfproc - bitfile processing helper functions
# krzysztof.sielewicz@cern.ch

from Tkinter import *
import mmap
import os
import subprocess
import time
import Queue as queue

# defines
pathImpact = 'C:\\EDA\\Xilinx\\14.7\\ISE_DS\\ISE\\bin\\nt64\\'
pathBatScr = 'C:\\EDA\\Xilinx\\14.7\\ISE_DS\\ISE\\bin\\nt64\\'

CNF_FRM_SIZE = 101 * 4  # 101 * 32b = 101 * 4B
CONF_FRMS = 22546
CONF_CRAM_FRMS = 22542
HEADER = '00090FF00FF00FF00FF000000161003573656D5F305F73656D5F6578616D706C653B5573657249443D305846464646464646463B56657273696F6E3D323031352E322E310062000D376B333235746666673930300063000B323031352F31302F31350064000931363A35333A3136006500000800FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF000000BB11220044FFFFFFFFFFFFFFFFAA9955662000000030018001036510932000000030002001'
HEADER_CRAM = '00090ff00ff00ff00ff000000161002b52557630615f746f703b5573657249443d305846464646464646463b56657273696f6e3d323031352e330062000d376b333235746666673930300063000b323031362f30332f31350064000931323a31343a3137006500ae9d9cffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff000000bb11220044ffffffffffffffffAA9955662000000030018001036510932000000030002001'
INIT_CRAM_WR_CMDS = "3000800100000001200000003000400050"
INIT_WR_CMDS = "3000800100000001300040CA"
PAD_FRM = "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
FOOTER = "20000000300080010000000D20000000200000002000000020000000200000002000000020000000200000002000000020000000200000002000000020000000200000002000000020000000"


def generate_partial_bitfiles(bitfile_path):
    """ generate partial bitfiles """

    partial_bitfile_directory = os.path.dirname(os.path.realpath(bitfile_path)) + "/partial_bitfiles/"
    # make partial_bitfiles directory
    if not os.path.exists(os.path.dirname(partial_bitfile_directory)):
        os.makedirs(os.path.dirname(partial_bitfile_directory))

    print "I will generate %d partial bitfiles in\n%s\n" % (CONF_CRAM_FRMS, partial_bitfile_directory)
    with open(bitfile_path, 'r+') as bitfile_handler:
        # mmap the bitfile to the memory
        bitfile_mmap = mmap.mmap(bitfile_handler.fileno(), 0)
    delta = bitfile_mmap.find('\x00\x00\x00\x01')  # find write conf reg
    bitfile_mmap.seek(delta + 16)
    # process the header
    header = string_to_byte_array('HEADER', HEADER)
    # process the INIT_WR_CMDS
    init_write_commands = string_to_byte_array('INIT_WR_CMDS', INIT_WR_CMDS)
    # process PAD frame
    pad_frame = string_to_byte_array('PAD_FRM', PAD_FRM)
    # process FOOTER
    footer = string_to_byte_array('FOOTER', FOOTER)
    # print 'Bitfile offset = ', bitfile_mmap.tell()

    for i in range(0, CONF_FRMS):
        configuration_frame_data = bitfile_mmap.read(CNF_FRM_SIZE)
        frame_address = bytearray([0, 0, 0, 0])
        write_partial_bitfile(header,
                              frame_address,
                              init_write_commands,
                              configuration_frame_data,
                              pad_frame,
                              footer,
                              i,
                              partial_bitfile_directory)


def string_to_byte_array(string_to_print, string_to_convert):
    """ take a string where signs represent HEX values and return an array of bytes """

    string_of_bytes = []
    data_integer = []
    for i in range(0, len(string_to_convert), 2):
        string_of_bytes.append(string_to_convert[i:i + 2])
    for i in range(0, len(string_of_bytes)):
        data_integer.append(int(string_of_bytes[i], 16))
    print '%s length = %d' % (string_to_print, len(data_integer))
    return bytearray(data_integer)


def write_partial_bitfile(header,
                          frame_addres,
                          init_write_commands,
                          configuration_frame_data,
                          pad_frame,
                          footer,
                          frame_id,
                          partial_bitfile_directory):
    """ write partial bitfile """

    # name of the bitlife is LA XXXXXXXX (linear address in HEX)
    partial_bitfile_path = partial_bitfile_directory + ('%0.8X' % frame_id) + '.bit'
    # make partial_bitfiles directory
    with open(partial_bitfile_path, "w+") as partial_bitfile_handler:
        # write header
        partial_bitfile_handler.write(header)
        # write frame address
        partial_bitfile_handler.write(frame_addres)
        # write init_write_commands
        partial_bitfile_handler.write(init_write_commands)
        # write configuration data
        partial_bitfile_handler.write(configuration_frame_data)
        # write pad frame
        partial_bitfile_handler.write(pad_frame)
        # write footer
        partial_bitfile_handler.write(footer)


def write_physical_address(path_bitfile_directory, linear_address, physical_address):
    """ Write physical address to the partial bitfile """

    # print 'Modyfying the partial bitfile: %0.8X.bit' % linear_addres
    # print 'PA hex = %0.8X' % physical_address
    # print 'LA hex = %0.8X' % linear_address

    partial_bitfile_path = path_bitfile_directory + '/partial_bitfiles/' + ('%0.8X' % linear_address) + '.bit'
    partial_bitfile_handler = open(partial_bitfile_path, 'r+')
    partial_bitfile_handler.seek(188)  # go to position after command [0x30 00 20 01]
    partial_bitfile_handler.write(string_to_byte_array('Partial bitfile\'s physical address',
                                          ('%0.8X' % physical_address)))
    partial_bitfile_handler.close()


# write physical address to the partial bitfile
def wrtPA(flPthDir, linAddr, phyAddr):
    #print 'Modyfying the partial bitfile: %0.8X.bit' % linAddr
    #print 'PA hex = %0.8X' % phyAddr
    #print 'LA hex = %0.8X' % linAddr
    filename = flPthDir + 'prtBitFls/' + ('%0.8X' % linAddr) + '.bit'
    fprtbtstrm = open(filename, 'r+')
    fprtbtstrm.seek(188)  # go to position after command [0x30 00 20 01]
    fprtbtstrm.write(prcsStr('Partial bitfile physical address', ('%0.8X' % phyAddr)))
    fprtbtstrm.close()


# generate partial bitfiles
def genPrtBtFls(flpth, txtPntr, prgsBrPntr):
    with open(flpth, 'r+') as file:
        mm = mmap.mmap(file.fileno(), 0)
    delta = mm.find('\x00\x00\x00\x01')  # find write conf reg
    mm.seek(delta + 16)
    header = prcsStr('HEADER', HEADER)  # process the header
    initWrCmds = prcsStr('INIT_WR_CMDS', INIT_WR_CMDS)  # process the INIT_WR_CMDS
    pad_frm = prcsStr('PAD_FRM', PAD_FRM)
    footer = prcsStr('FOOTER', FOOTER)  # process the FOOTER
    # print 'Bitfile offset = ', mm.tell()
    prgsBrPntr["value"] = 0
    prtBitFlDir = rtrnFlDir(flpth)
    for n in range(0, CONF_FRMS):
        cnfFrmDt = mm.read(CNF_FRM_SIZE)
        FrmAddr = prcFrmAddr()
        wrtPrtbtf(header, FrmAddr, initWrCmds, cnfFrmDt, pad_frm, footer, n, prtBitFlDir)
        prgsBrPntr["value"] = int((n * 100) / CONF_FRMS) + 1
    txtPntr.insert(END, '%d partial bitfiles saved\n' % (n + 1), 'color_green')


# write partial bitfile
def wrtPrtbtf(header, FrmAddr, initWrCmds, cnfdt, pad_frm, footer, frmInd, prtBitFlDir):
    # name of the bitlife is LA XXXXXXXX (linear address in HEX)
    filename = prtBitFlDir + 'prtBitFls/' + ('%0.8X' % frmInd) + '.bit'
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    with open(filename, "w+") as f:
        f.write(header)     # write header
        f.write(FrmAddr)    # write FrmAddr
        f.write(initWrCmds) # write init
        f.write(cnfdt)      # write configuration data
        f.write(pad_frm)    # write pad frame
        f.write(footer)     # write footer

# generate partial CRAM bitfile
def genPrtCRAMbtfl(btflPth):
    tmStrt = time.time()
    print 'genPrtCRAMbtfl, CRAM frames: %d' %CONF_CRAM_FRMS
    print btflPth
    with open(btflPth, 'r+') as file:
        btfl = mmap.mmap(file.fileno(), 0)
    delta = btfl.find('\x00\x00\x00\x01')  # find write conf reg
    btfl.seek(delta + 16)

    # process the header
    header = prcsStr('HEADER_CRAM', HEADER_CRAM)
    # process the INIT_WR_CMDS
    initWrCmds = prcsStr('INIT_CRAM_WR_CMDS', INIT_CRAM_WR_CMDS + '%0.6X' %((CONF_CRAM_FRMS + 1) * 101))
    # process the PAD_FRAME
    pad_frm = prcsStr('PAD_FRM', PAD_FRM)
    # process the FOOTER
    footer = prcsStr('FOOTER', FOOTER)

    # print 'Bitfile offset = ', mm.tell()
    prtCRAMbtflPth = rtrnFlDir(btflPth) + 'prtlCRAMbtfl.bit'

    with open(prtCRAMbtflPth, "w+") as prtCRAMbtfl:
        prtCRAMbtfl.write(header)       # write header
        frmAddr = prcFrmAddr()          # FAR register (FRAME ADDRESS)
        prtCRAMbtfl.write(frmAddr)      # write FrmAddr
        prtCRAMbtfl.write(initWrCmds)   # write init

        for n in range(0, CONF_CRAM_FRMS):
            cnfFrmDt = btfl.read(CNF_FRM_SIZE)
            prtCRAMbtfl.write(cnfFrmDt) # write configuration data
        prtCRAMbtfl.write(pad_frm)      # write pad frame
        prtCRAMbtfl.write(footer)       # write footer
    tmEnd = time.time()
    print 'genPrtCRAMbtfl executed in %d' % (int(tmEnd - tmStrt))

# return the directory where the flpth is located
def rtrnFlDir(flpth):
    dirPth = '/'
    dirPthLst = flpth.split('/')
    for i in range(1, len(dirPthLst) - 1):
        dirPth += dirPthLst[i] + '/'
    return dirPth


# process string, take a string where signs represent HEX values and return an array of bytes
def prcsStr(str2prnt, str):
    strBytes = []
    dataInt = []
    for i in range(0, len(str), 2):
        strBytes.append(str[i:i + 2])
    for i in range(0, len(strBytes)):
        dataInt.append(int(strBytes[i], 16))
    print '%s length = %d' % (str2prnt, len(dataInt))
    return bytearray(dataInt)


# process frame address
def prcFrmAddr():
    data = [0, 0, 0, 0]
    return bytearray(data)


# program the FPGA using IMPACT
def progFpgaImpact(textStatusPntr, txtPntr, fpgaBitstreamPath, printLog):
    tmStrt = time.time()
    print '\n\n### Starting programming the FPGA ###\n\n'
    if printLog:
        textStatusPntr.set('Programming the FPGA...')
        txtPntr.insert(END, 'Programming the FPGA...\n', 'color_green')
        txtPntr.insert(END, 'BITFILE: %s\n' % (fpgaBitstreamPath), 'color_green')
    print subprocess.call(["./tcl_scripts/loadbit.sh", fpgaBitstreamPath])
    tmEnd = time.time()
    prgTime = int(tmEnd - tmStrt)

    if printLog:
        txtPntr.insert(END, 'The FPGA was programmed in %ds!\n' % (prgTime), 'color_green')
        txtPntr.see(END)  # auto scroll
    print 'The FPGA was programmed in %ds!\n' %prgTime
    textStatusPntr.set('FPGA programmed!')

# program the FPGA using IMPACT, no-gui
def progFpgaImpact_nogui(fpgaBitstreamPath):
    tmStrt = time.time()
    print '\n\n### Starting programming the FPGA ###\n\n'
    # if printLog:
    #     # textStatusPntr.set('Programming the FPGA...')
    #     txtPntr.insert(END, 'Programming the FPGA...\n', 'color_green')
    #     txtPntr.insert(END, 'BITFILE: %s\n' % (fpgaBitstreamPath), 'color_green')
    print subprocess.call(["./tcl_scripts/loadbit.sh", fpgaBitstreamPath])
    tmEnd = time.time()
    prgTime = int(tmEnd - tmStrt)
    print 'The FPGA was programmed in %ds!\n' % (prgTime)

    # if printLog:
    #     txtPntr.insert(END, 'The FPGA was programmed in %ds!\n' % (prgTime), 'color_green')
    #     txtPntr.see(END)  # auto scroll
    # print 'The FPGA was programmed in %ds!\n' %prgTime
    # textStatusPntr.set('FPGA programmed!')

# thread to carry out the JTAG scrubbing
def jtagScrubberThrd(cramBtPth, queueJtagScrbrThrdTrmt, queueJtagScrbrThrdCntr):

    jtagScrbrThrdTrmt = 1
    jtagScrbrThrdCntr = 0
    print 'jtagScrubberThrd On'

    while jtagScrbrThrdTrmt:
        try:
            jtagScrbrThrdTrmt = queueJtagScrbrThrdTrmt.get_nowait()
        except queue.Empty:
            #print subprocess.call(["./tcl_scripts/loadbit.sh", cramBtPth])
            subprocess.call(["./tcl_scripts/loadbit.sh", cramBtPth])
            jtagScrbrThrdCntr += 1

            try:
                queueJtagScrbrThrdCntr.put_nowait(jtagScrbrThrdCntr)
            except queue.Full:
                pass

    print 'jtagScrubberThrd Off'


def main():
    """ main function """

    os.system('clear')

    if len(sys.argv) > 1:
        bitfile_path = sys.argv[1]
    else:
        print "Not enough parameters given!"
        return 0

    generate_partial_bitfiles(bitfile_path)

if __name__ == "__main__":
    main()
