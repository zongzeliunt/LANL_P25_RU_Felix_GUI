import os
import sys
import shutil
import logging
import errno
import numpy as np
import matplotlib.pyplot as plt
from enum import IntEnum

import config

# Flash Info
XS_PRAGUE_1to0 = 4.92e-21
XS_PRAGUE_0to1 = 2.62e-16
XS_OXFORD = 3.41e-20

class XsType(IntEnum):
    PRAGUE = 0
    OXFORD = 1

class BitFileAnalyser(object):
    def __init__(self, name=".bit"):
        """Init function"""
        self.path=None
        self.ones_percent=None
        self.zeros_percent=None

        self.set_name(name)
        self.setup_logging()
        self.logger = logging.getLogger("BitFileAnalyser")

    def set_name(self, name):
        assert os.path.exists(name), "{0} not existing".format(name)
        self.name = name

    def setup_logging(self):
        # Logging folder
        self.logdir = os.path.join(os.getcwd() + '/logs')
        try:
            os.makedirs(self.logdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        # setup logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        log_file = os.path.join(self.logdir, "bitfile.log")
        log_file_errors = os.path.join(self.logdir,
                                       "bitfile_errors.log")

        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)

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

    def get_xs_bitfile(self, xs_type, inverted=False):
        if xs_type is XsType.PRAGUE:
            if not inverted:
                message = "Composite cross section with "
                xs = XS_PRAGUE_0to1*self.zeros_percent + XS_PRAGUE_1to0*self.ones_percent
                message += "not inverted bitfile {0:.2e} [bit^-1] (prague xs)".format(xs)
            else:
                message = "Composite cross section with "
                xs = XS_PRAGUE_0to1*self.ones_percent + XS_PRAGUE_1to0*self.zeros_percent
                message += "inverted bitfile {0:.2e} [bit^-1] (prague xs)".format(xs)
        elif xs_type is XsType.OXFORD:
            message = "Cross section with "
            xs = XS_OXFORD
            message += "{0:.2e} (oxford xs)".format(xs)
        self.logger.info(message)

    def analyse_bitfile(self):
        """"""
        with open(self.name, "rb") as f:
            byte = f.read(1)
            bytecount = 0
            ones = 0
            zeros = 0
            self.logger.info("Start analysing {0}".format(self.name))
            while byte:
                # Do stuff with byte.
                bytecount += 1
                if bytecount % 1e6 == 0:
                    self.logger.info("{0} MB analysed".format(bytecount/1e6))
                one = bin(ord(byte)).count('1')
                ones += one
                zeros += 8-one
                byte = f.read(1)
            assert bytecount*8 == ones + zeros
            self.ones_percent = ones/(bytecount*8)
            self.zeros_percent = zeros/(bytecount*8)
            self.logger.info("Total {0} bits".format(bytecount*8))
            self.logger.info("Ones {0}, {1:%} total".format(ones, self.ones_percent))
            self.logger.info("Zeros {0}, {1:%} total".format(zeros, self.zeros_percent))
def main():
    if len(sys.argv) != 2:
        sys.exit("Usage \"python {0} bitfile.bit\"".format(sys.argv[0]))
    bfs = BitFileAnalyser(name=sys.argv[1])
    bfs.analyse_bitfile()
    bfs.get_xs_bitfile(xs_type=XsType.OXFORD)
    bfs.get_xs_bitfile(xs_type=XsType.PRAGUE)
    bfs.get_xs_bitfile(xs_type=XsType.PRAGUE, inverted=True)

if __name__ == '__main__':
    main()
