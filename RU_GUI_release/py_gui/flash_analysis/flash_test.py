import os
import sys
import shutil
import logging
import errno
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict

import config

# Flash info
BLOCKS = 8192
PAGES_IN_BLOCK = 64
PAGE_BYTESIZE = 4096
BYTES_IN_BLOCK = PAGES_IN_BLOCK*PAGE_BYTESIZE

# Script options
SAVE_TO_FILE = True

class FlashChecker(object):
    """Class for checking the flash content readback"""
    def __init__(self, path, startblock, stopblock, first_byte_bug, is_inverted, name="block_{0}.dat"):
        """Init function"""
        self.path=None
        self.name=None
        self.startblock=None
        self.stopblock=None
        self.first_byte_bug = None
        self.is_inverted = None

        self.set_path(path)
        self.setup_logging()
        self.logger = logging.getLogger("FlashChecker")
        self.set_name(name)
        self.set_blocks(startblock, stopblock)
        self.set_first_byte_bug(first_byte_bug)
        self.set_is_inverted(is_inverted)

    def set_path(self, path):
        assert os.path.isdir(path), "{0} not existing".format(path)
        self.path = path

    def set_name(self, name):
        self.name = name

    def set_blocks(self, startblock, stopblock):
        assert self.path is not None
        assert self.name is not None
        assert startblock <= stopblock
        assert stopblock < BLOCKS
        self.startblock = startblock
        self.stopblock = stopblock
        self.get_filepath(startblock)
        self.get_filepath(stopblock)

    def set_first_byte_bug(self, first_byte_bug):
        """Set attribute first_byte_bug
        """
        self.first_byte_bug = first_byte_bug

    def set_is_inverted(self, is_inverted):
        """Set attribute is_inverted
        """
        self.is_inverted = is_inverted

    def setup_logging(self):
        # Logging folder
        self.logdir = self.path + '/logs'
        try:
            if os.path.exists(self.logdir):
                shutil.rmtree(self.logdir)
            os.makedirs(self.logdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        # setup logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        log_file = os.path.join(self.logdir, "flash.log")
        log_file_errors = os.path.join(self.logdir,
                                       "flash_errors.log")

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

    def get_filepath(self, block):
        assert block in range(self.startblock, self.stopblock+1)
        path = self.path + '/' + self.name.format(block)
        assert os.path.exists(path), "path {0} not existing".format(path)
        return path

    def check_byte(self, byte, reference_byte):
        flip_1to0 = 0
        flip_0to1 = 0
        b_1count = bin(byte).count('1')
        ref_1count = bin(reference_byte).count('1')
        if b_1count < ref_1count:
            flip_1to0 = ref_1count - b_1count
        elif b_1count > ref_1count:
            flip_0to1 = b_1count - ref_1count
        #if flip_0to1 > 1 or flip_0to1 > 1:
        #    self.logger.info("byte: {0}, flip 1to0: {1}, flip_0to1: {2}:, 1s in byte {3}, 1s in ref {4}".format(byte, flip_1to0, flip_0to1, b_1count, ref_1count))
        return flip_1to0, flip_0to1

    def analyse_block(self, block):
        """"""
        filepath = self.get_filepath(block)
        with open(filepath, "rb") as f:
            byte = f.read(1)
            bytecount = 0
            byteerrors = 0
            pagenr = 0
            flip_1to0 = 0
            flip_0to1 = 0
            double_1to0 = 0
            double_0to1 = 0
            triple_plus_1to0 = 0
            triple_plus_0to1 = 0
            while byte:
                new_byte = byte
                byte = new_byte[0]
                # Do stuff with byte.
                if self.is_inverted:
                    byte = ~byte & 0xFF
                reference_value = b'\xa5'[0]
                if bytecount % PAGE_BYTESIZE == 0:
                    pagenr += 1
                    if self.first_byte_bug:
                        reference_value = b'@'[0]
                if byte != reference_value:
                    #print("{0:08b} {1:08b} ".format(my_byte, reference_value))
                    byteerrors += 1
                    f1to0, f0to1 = self.check_byte(byte, reference_value)
                    flip_1to0 += f1to0
                    if f1to0 == 2:
                        double_1to0 += f1to0
                    elif f1to0 > 2:
                        triple_plus_1to0 += f1to0
                    flip_0to1 += f0to1
                    if f0to1 == 2:
                        double_0to1 += f0to1
                    elif f0to1 > 2:
                        triple_plus_0to1 += f0to1
                    self.logger.debug("Error on byte {0}: 0to1 {1} 1to0 {2} d_0to1 {3} d_1to0 {4} t+0to1 {5} t+1to0 {6} (Byte is {7})".format(bytecount,
                                                                                                                                              flip_0to1,
                                                                                                                                              flip_1to0,
                                                                                                                                              double_0to1,
                                                                                                                                              double_1to0,
                                                                                                                                              triple_plus_0to1,
                                                                                                                                              triple_plus_1to0,
                                                                                                                                              byte))
                byte = f.read(1)
                bytecount += 1
            self.logger.info("Done analysing block {2}. byteerrors {1}.\t0to1 {3}, 1to0 {4},\td_0to1 {5} d_1to0 {6},\tt+0to1 {7} t+1to0 {8}".format(bytecount,
                                                                                                                                                    byteerrors,
                                                                                                                                                    block,
                                                                                                                                                    flip_0to1,
                                                                                                                                                    flip_1to0,
                                                                                                                                                    double_0to1,
                                                                                                                                                    double_1to0,
                                                                                                                                                    triple_plus_0to1,
                                                                                                                                                    triple_plus_1to0))
            if byteerrors == BYTES_IN_BLOCK:
                self.logger.error("Done analysing block {2}. byteerrors {1}.\t0to1 {3}, 1to0 {4},\td_0to1 {5} d_1to0 {6},\tt+0to1 {7} t+1to0 {8}".format(bytecount,
                                                                                                                                                    byteerrors,
                                                                                                                                                    block,
                                                                                                                                                    flip_0to1,
                                                                                                                                                    flip_1to0,
                                                                                                                                                    double_0to1,
                                                                                                                                                    double_1to0,
                                                                                                                                                    triple_plus_0to1,
                                                                                                                                                    triple_plus_1to0))
            assert bytecount == BYTES_IN_BLOCK, "bytecount {0}, BYTES_IN_BLOCK {1} in block {2}".format(bytecount, BYTES_IN_BLOCK, block)
        return {'byteerrors': byteerrors, 'flip_1to0': flip_1to0, 'flip_0to1': flip_0to1, 'double_1to0': double_1to0, 'double_0to1': double_0to1, 'triple_plus_1to0': triple_plus_1to0, 'triple_plus_0to1': triple_plus_0to1}

def get_xs(fluence, upsets, analysed_blocks):
    """Returns the cross section for the given fluence and number of blocks analysed
    """
    xs = upsets/(fluence*analysed_blocks*PAGES_IN_BLOCK*PAGE_BYTESIZE)
    return xs

def gen_hist(array, key, basepath):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    hist = plt.hist(array, bins=500)
    ax.set_title("Histogram of {0} per block".format(key))
    ax.set_xlabel("Number of {0} per block".format(key))
    ax.set_ylabel("Occurrences")
    if SAVE_TO_FILE:
        save_to_file(fig, key, basepath, '_hist')
    else:
        plt.show()
    return hist

def gen_plot(array, key, basepath, start_block=None):
    if start_block:
        block = list(range(start_block, start_block+len(array)))
    else:
        block = list(range(len(array)))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.semilogy(block, array)
    ax.set_xlabel("Block number")
    ax.set_ylabel("{0} per block".format(key))
    ax.set_title("{0} vs block number".format(key))
    if SAVE_TO_FILE:
        save_to_file(fig, key, basepath)
    else:
        plt.show()

def save_to_file(plt, key, basepath, name_modifier=''):
    # creates folder if it does not exist
    plotdir = basepath + '/logs/plots/'
    try:
        os.makedirs(plotdir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    # Saves plot to file
    filename = "{0}{1}{2}.pdf".format(plotdir, key, name_modifier)
    plt.savefig(filename, bbox_inches='tight')

def main(analysis):
    analysed_blocks = 0
    HIST_KEYS = ['flip_0to1']
    PLOT_KEYS = ['flip_0to1']
    keys_order = {'byteerrors': 0, 'flip_1to0': 1, 'flip_0to1': 2, 'double_1to0': 3, 'double_0to1': 4, 'triple_plus_1to0': 5, 'triple_plus_0to1': 6}
    result = {'byteerrors': 0, 'flip_1to0': 0, 'flip_0to1': 0, 'double_1to0': 0, 'double_0to1': 0, 'triple_plus_1to0': 0, 'triple_plus_0to1': 0}
    results_dict = {'byteerrors': [], 'flip_1to0': [], 'flip_0to1': [], 'double_1to0': [], 'double_0to1': [], 'triple_plus_1to0': [], 'triple_plus_0to1': []}
    results = {}
    fc = FlashChecker(path=analysis.basepath, startblock=analysis.startblock, stopblock=analysis.stopblock, first_byte_bug=analysis.first_byte_bug, is_inverted=analysis.is_inverted)
    for i in range(fc.startblock, fc.stopblock+1):
        if i not in analysis.exclude_blocks:
            analysed_blocks += 1
            results[i] = fc.analyse_block(i)
            for key in result.keys():
                result[key] += results[i][key]
    fc.logger.info(result)

    for key in results.keys():
        for res_key in results_dict.keys():
            results_dict[res_key].append(results[key][res_key])
    for key in results_dict.keys():
        if key in HIST_KEYS:
            hist = gen_hist(results_dict[key], key, analysis.basepath)
        if key in PLOT_KEYS:
            gen_plot(results_dict[key], key, analysis.basepath, analysis.startblock)
        mean = np.mean(results_dict[key])
        std = np.std(results_dict[key])
        fc.logger.info("value {0}   \tmean {1}\tstd {2}".format(key, mean, std))

    # calculates xs is fluence is available
    xs = OrderedDict()
    if analysis.fluence is not None:
        for fluence in analysis.fluence:
            upsets_0to1 = result['flip_0to1'] + result['double_0to1'] + result['triple_plus_0to1']
            upsets_1to0 = result['flip_1to0'] + result['double_1to0'] + result['triple_plus_1to0']
            upsets_tot = upsets_0to1 + upsets_1to0
            xs_avg = get_xs(fluence=fluence, upsets=upsets_tot,
                            analysed_blocks=analysed_blocks)
            xs_0to1 = get_xs(fluence=fluence, upsets=upsets_0to1,
                             analysed_blocks=analysed_blocks/2)
            xs_1to0 = get_xs(fluence=fluence, upsets=upsets_1to0,
                             analysed_blocks=analysed_blocks/2)
            xs[fluence] = {'avg': xs_avg,
                           '0to1':xs_0to1,
                           '1to0':xs_1to0}
            fc.logger.info("xs  for {0:.02e} is {1}".format(fluence, xs[fluence]))
    return result, results, xs

if __name__ == '__main__':

    if len(sys.argv) < 2 or len(sys.argv) > 3 :
        sys.exit("Usage \"python {0} key [basepath]\"".format(sys.argv[0]))
    key = sys.argv[1]
    if key not in config.analysis.keys():
        sys.exit("Key {0} not in {1}".format(key, config.analysis.keys()))
    analysis = config.analysis[key]
    if len(sys.argv) == 3:
        basepath = sys.argv[2]
        assert os.path.exists(basepath)
        analysis.set_basepath(basepath)

    main(analysis)
