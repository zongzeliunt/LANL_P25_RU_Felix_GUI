"""File configuring different analysis for different flash readout
"""

import pathlib

class Analysis(object):
    """Class describing the attributes of the analysis
    """
    def __init__(self,
                 basepath=str(pathlib.Path.home()),
                 startblock = 0, stopblock = 8191,
                 RUv1_version = 1, RUv1_progressive = 6,
                 is_inverted=False,
                 first_byte_bug=False,  exclude_blocks = [],
                 fluence=[]):
        "Init for the Analysis class"
        self.basepath = None

        self.RUv1_version = RUv1_version
        self.RUv1_progressive = RUv1_progressive
        self.startblock=startblock
        self.stopblock=stopblock
        self.first_byte_bug = first_byte_bug
        self.exclude_blocks = exclude_blocks
        self.is_inverted = is_inverted
        self.set_basepath(basepath)
        self.fluence = fluence

    def set_basepath(self, basepath):
        """Set path for analysis
        """
        self.basepath = basepath + '/FLASH_RUv1_{0}_N{1}'.format(self.RUv1_version, self.RUv1_progressive)

analysis = {'v0n6' : Analysis(startblock = 400, # after prague_beam_test
                              stopblock = 4500,
                              RUv1_version = 0,
                              RUv1_progressive = 6,
                              first_byte_bug=True,
                              exclude_blocks = [1893, 3344, 3889],
                              fluence = [4.24e11]),
            'v0n6o' : Analysis(startblock = 400, # read back on 06.04.18 (before overwriting it)
                              stopblock = 4500,
                              RUv1_version = 0,
                              RUv1_progressive = '6_0418',
                              exclude_blocks = [1893, 3344, 3889],
                              fluence = [4.24e11]),
            'v0n6r' : Analysis(startblock = 0, # read back after re-writing
                              stopblock = 8191,
                              RUv1_version = 0,
                              RUv1_progressive = '6_rewritten',
                              is_inverted = True, # (pattern written in 0x5a, instead of 0xa5)
                              exclude_blocks = [1893, 3344, 3889]),
            'v1n4' : Analysis(startblock = 1, # pre oxford bean test
                              stopblock = 8191,
                              RUv1_version = 1,
                              RUv1_progressive = 4,
                              exclude_blocks = [169, 266, 268, 269, 681, 1898, 4357] + list(range(300,500))),
            'v1n6' : Analysis(startblock = 1,  # pre oxford bean test
                              stopblock = 8191,
                              RUv1_version = 1,
                              RUv1_progressive = 6,
                              exclude_blocks = [2636, 2832, 6123] + list(range(100,300))),
            'v1n6a' : Analysis(startblock = 1, # after oxford bean test
                               stopblock = 8191,
                               RUv1_version = 1,
                               RUv1_progressive = '6after',
                               is_inverted = True,
                               exclude_blocks = [2636, 2832, 6123] + list(range(100,300)) + list(range(300,393)) + list(range(400,471)),
                               fluence = [6.5e10, 2e11, 5e11])
            }
