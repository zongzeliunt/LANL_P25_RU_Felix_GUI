#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""JCM Control Server
Krzysztof Marek Sielewicz <krzysztof.sielewicz@cern.ch>
Matthias Bonora <matthias.bonora@cern.ch>
Matteo Lupi <matteo.lupi@cern.ch>
"""

from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import subprocess
from queue import Queue, Empty  # python 3.x
from threading import Thread
import signal
import sys
import time
import datetime
import os
import logging

ON_POSIX = 'posix' in sys.builtin_module_names

def enqueue_output(out, err, input_queue):
    """Print data from the input_queue"""
    logger = logging.getLogger()
    # print('Starting enqueue_output')
    for line in iter(out.readline, b''):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        input_queue.put(timestamp + "; " + line.decode("ascii"))
        logger.info(line.decode("ascii")[:-1])
    for line in iter(err.readline, b''):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        input_queue.put(timestamp + "; " + line.decode("ascii"))
        logger.info(line.decode("ascii")[:-1])

class NoReadBackFileError(Exception):
    """basic class to define the lack of a readback file in the JCM error exception"""

    def __init__(self, message):
        super(NoReadBackFileError, self).__init__()
        self.logger = logging.getLogger("JCM control server Exception")
        self.message=message
        self.log_info()

    def __srt__(self):
        return repr(self.message)

    def log_info(self):
        """returns the args of the exception"""
        self.logger.error("\n\n{0}\n\n".format(self.message))


class JCM(object):
    """Class JCM - executed on JCM"""

    def __init__(self):
        self.message_queue = None
        self.process = None
        self.message_thread = None

        self.logger = None
        self.setup_logging()

        self.logger.info("JCM server started successfully")

    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)


        formatter = logging.Formatter("%(asctime)s; %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        self.logger = logger

    def start_calibrate_device(self):
        """Start JTAG calibration"""

        path = './jcm_calibrate_device.elf'
        self.logger.info('Starting start_calibrate_device.')

        self.logger.info('Command: %s', path)
        self.process = subprocess.Popen(path,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        close_fds=ON_POSIX)
        self.message_queue = Queue()
        self.message_thread = Thread(target=enqueue_output,
                                     args=(self.process.stdout,
                                           self.process.stderr,
                                           self.message_queue))
        self.message_thread.start()

    def start_full_configure(self, bitfile=None):
        """Start full FPGA configuration"""

        path = './jcm_full_configure.elf'
        if bitfile:
            path += ' -bf {0}'.format(bitfile)
        self.logger.info('Starting start_full_configure.')

        self.logger.info('Command: %s', path)
        self.process = subprocess.Popen(path,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        close_fds=ON_POSIX)
        self.message_queue = Queue()
        self.message_thread = Thread(target=enqueue_output,
                                     args=(self.process.stdout,
                                           self.process.stderr,
                                           self.message_queue))
        self.message_thread.start()

    def is_stopped(self):
        """Check if self.process is stopped or still running"""

        stopped = False
        if self.process:
            poll = self.process.poll()
            if poll is not None:
                stopped = True
                if poll < 0:
                    self.logger.info("You talking to me?", -poll)
        return stopped

    def start_readback(self):
        """Readback configuration of FPGA"""

        path = './jcm_full_readback.elf'
        self.logger.info('Starting readback')

        self.logger.info('Command: %s', path)
        self.process = subprocess.Popen(path,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        close_fds=ON_POSIX)
        self.message_queue = Queue()
        self.message_thread = Thread(target=enqueue_output,
                                     args=(self.process.stdout,
                                           self.process.stderr,
                                           self.message_queue))
        self.message_thread.start()


    def rename_readback_file(self, file_name=None, restore=False):
        """Renames the readback file on the JCM device
        if restore is False, it renames the standard readBack.data to file_name in the /tmp folder,
        if restore is True, it renames the file_name in /tmp to the standard readBack.data file
        """
        directory = '/tmp/'
        original_file_name = 'readBack.data'
        if restore:
            path = 'mv {0}{1} {0}{2}'.format(directory, file_name, original_file_name)
        elif file_name is not None:
            path = 'mv {0}{1} {0}{2}'.format(directory, original_file_name, file_name)
        else:
            raise RuntimeError("Incorrect parameters for function")
        self.logger.info('Moving readback file')

        self.logger.info('Command: %s', path)
        self.process = subprocess.Popen(path,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        close_fds=ON_POSIX)
        self.message_queue = Queue()
        self.message_thread = Thread(target=enqueue_output,
                                     args=(self.process.stdout,
                                           self.process.stderr,
                                           self.message_queue))
        self.message_thread.start()

    def remove_readback_files(self):
        "Removes the readback file on the JCM device"
        self.logger.info('Removing readback files')
        directory = '/tmp/'
        original_file_name = '*.data'
        path = 'rm {0}{1}'.format(directory, original_file_name)
        self.logger.info('Removing readback file')

        self.logger.info('Command: %s', path)
        self.process = subprocess.Popen(path,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        close_fds=ON_POSIX)
        self.message_queue = Queue()
        self.message_thread = Thread(target=enqueue_output,
                                     args=(self.process.stdout,
                                           self.process.stderr,
                                           self.message_queue))
        self.message_thread.start()

    def compare_readback(self, basename1, basename2):
        "Compares the readback file on the JCM device"
        self.logger.info('Comparing readback file')
        directory = '/tmp/'
        original_file_name = 'readBack{0}.data'
        file1 = original_file_name.format(basename1)
        file2 = original_file_name.format(basename2)
        for f in [file1, file2]:
            if not os.path.isfile(directory+f):
                self.logger.error("file {0}{1} not existing".format(directory, f))
        self.logger.info('Comparing readBack files {0}{1} and {0}{2}'.format(directory, file1, file2))
        path = 'diff {0}{1} {0}{2}'.format(directory, file1, file2)

        self.logger.info('Command: %s', path)
        self.process = subprocess.Popen(path,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        close_fds=ON_POSIX)
        self.message_queue = Queue()
        self.message_thread = Thread(target=enqueue_output,
                                     args=(self.process.stdout,
                                           self.process.stderr,
                                           self.message_queue))
        self.message_thread.start()


    def start_blind_scrubber(self):
        """Start blind scrubbing"""

        self.logger.info("Starting start_blind_scrubber")
        path = "./jcm_blind_scrub.elf"
        self.logger.info(path)
        self.process = subprocess.Popen(path,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        close_fds=ON_POSIX)
        self.message_queue = Queue()
        self.message_thread = Thread(target=enqueue_output,
                                     args=(self.process.stdout,
                                           self.process.stderr,
                                           self.message_queue))
        self.message_thread.start()

    def stop_blind_scrubber(self):
        """Send stop signal to jcm_blind_scrubber"""

        self.process.stdin.write(b'\n')
        time.sleep(0.1)
        self.process.stdin.write(b'0\n')
        time.sleep(0.1)
        self.process.stdin.flush()

    def start_random_fault_injection(self,
                                     delay,
                                     n_faults,
                                     delay_after,
                                     correction):
        """Start random fault injection of n_faults,
        * @param delay        The delay in milliseconds between injection and repair.
        * @param delay_after  The delay in milliseconds between repais and next injection (or between to injections if not repair).
        """

        self.logger.info("Starting random fault injection")

        if correction:
            path = './jcm_random_fault_injection.elf -d %d -c -i %d -da %d' %(delay,
                                                                              n_faults,
                                                                              delay_after)
        else:
            path = './jcm_random_fault_injection.elf -d %d -i %d -da %d' %(delay,
                                                                           n_faults,
                                                                           delay_after)
        self.logger.info(path)
        self.process = subprocess.Popen(path,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        close_fds=ON_POSIX)
        self.message_queue = Queue()
        self.message_thread = Thread(target=enqueue_output,
                                     args=(self.process.stdout,
                                           self.process.stderr,
                                           self.message_queue))
        self.message_thread.start()

    def stop_random_fault_injection(self):
        """Send stop signal to jcm_random_fault_injection"""

        self.process.stdin.write(b'\n')
        time.sleep(0.1)
        self.process.stdin.write(b'0\n')
        time.sleep(0.1)
        self.process.stdin.flush()

    def read_messages(self):
        """Read data from message_queue and return as msg"""

        msg = ""
        try:
            while True:
                line = self.message_queue.get_nowait()
                # msg += line.decode("utf-8")
                msg += line
        except Empty:
            pass  # finished
        return msg

    def test_function(self):
        """Test functions"""

        self.logger.info('This is a test function')
        time.sleep(5)


class JcmControlServer(object):
    """RPC server, running on JCM"""

    def __init__(self, address, port):
        """Initialize server with given interface address and port"""

        self._address = address
        self._port = port
        self._server = SimpleXMLRPCServer((self._address, self._port),
                                          logRequests=False,
                                          allow_none=True)
        # Register JCM class, all functions will be available in the client
        self._server.register_instance(JCM())
        # self.logger.info('Server on the JCM started successfully!')

    def start(self):
        "Start server"
        self._server.serve_forever(0.5)

    def close(self):
        "Close server"
        self._server.server_close()


class JcmControlClient(object):
    """Remote JCM client, running on a beam test notebook"""

    def __init__(self, address, port):
        self._proxy = xmlrpc.client.ServerProxy("http://{0}:{1}".format(address, port),allow_none=True)
        self.logger = logging.getLogger("JcmControlClient")

    def start_calibrate_device(self):
        """Start device calibration"""

        self.logger.info('Starting start_device_calibration')
        self._proxy.start_calibrate_device()

    def start_full_configure(self, bitfile=None):
        """Start full configuration"""

        self.logger.info('Starting start_full_configure')
        self._proxy.start_full_configure(bitfile)

    def is_stopped(self):
        """Check if self.process is stopped or still running"""

        return self._proxy.is_stopped()

    def read_calibrate_device_results(self):
        """Read calibrate device results"""

        read_messages = self.read_messages()
        success = True
        if read_messages:
            read_messages = read_messages[:-1]
            if "Calibration failed!" in read_messages[:-1].strip():
                success = False
        return success, read_messages

    def read_full_configure_results(self):
        """Read full configure results"""

        read_messages = self.read_messages()
        success = True
        if read_messages:
            read_messages = read_messages[:-1]
            if "Configuration unsuccessful, check cables" in read_messages[:-1].strip():
                success = False
        return success, read_messages

    def start_readback(self):
        """Start readback of configuration"""

        self.logger.info('Starting readback')
        self._proxy.start_readback()

    def is_readback_finished(self):
        """Read readback results"""
        read_messages = self.read_messages()
        success = False
        if read_messages:
            read_messages = read_messages[:-1]
            if "Readback Complete" in read_messages[:-1].strip():
                success = True
        return success, read_messages

    def rename_readback_file(self, file_name=None, restore=False):
        "Renames the readback file on the JCM device"
        self.logger.info('Moving readback file')
        self._proxy.rename_readback_file(file_name, restore)
        while not self.is_stopped():
            time.sleep(0.2)
            self.logger.info("Waiting for rename to finish")
        self.logger.info("Finished renaming")

    def remove_readback_files(self):
        "Removes the readback file on the JCM device"
        self.logger.info('Removing readback files')
        self._proxy.remove_readback_files()
        while not self.is_stopped():
            time.sleep(0.2)
            self.logger.info("Waiting for remove to finish")
        self.logger.info("readBack*.data removed")

    def compare_readback(self, basename1, basename2):
        "Removes the readback file on the JCM device"
        self.logger.info('Comparing readback files')
        self._proxy.compare_readback(basename1, basename2)
        while not self.is_stopped():
            time.sleep(0.2)
            self.logger.info("Waiting for compare to finish")
        read_messages = self.read_messages()
        if read_messages:
            are_equal =False
            if 'differ' in read_messages[:-1].strip():
                self.logger.info(read_messages[:-1].strip())
        else:
            are_equal = True
        return are_equal, read_messages

    def start_blind_scrubber(self):
        """Start blind scrubber"""

        self.logger.info("Starting start_blind_scrubber")
        self._proxy.start_blind_scrubber()
        time.sleep(1)
        success, messages = self.read_start_blind_scrubber_results()
        assert success, messages

    def read_start_blind_scrubber_results(self):
        """Read All messages from start_blind_scrubber.
        return tuple (success, messages)
        """
        success = True
        read_messages = self.read_messages()
        if read_messages:
            read_messages = read_messages[:-1]
            if ": iostream error" in read_messages.strip():
                raise NoReadBackFileError(read_messages)
        return (success, read_messages)

    def stop_blind_scrubber(self):
        """Send stop signal to jcm_blind_nscrubber"""

        self.logger.info("Stopping jcm_blind_scrubber")
        self._proxy.stop_blind_scrubber()

    def start_random_fault_injection(self,delay,n_faults,delay_after=0,correction=True):
        """Start random fault injection of n_faults"""

        self.logger.info("Starting random fault injection")
        self._proxy.start_random_fault_injection(delay,n_faults,delay_after,correction)

    def stop_random_fault_injection(self):
        """Send stop signal to jcm_random_fault_injection"""

        self.logger.info("Stopping random fault injection")
        self._proxy.stop_random_fault_injection()

    def read_fault_injection_results(self):
        """Read All messages from fault injection
        return tuple (successful_injected_faults,messages)
        """
        read_messages = self.read_messages()
        successful_injected_faults = int(read_messages.split(" ")[-1])
        return (successful_injected_faults, read_messages)

    def read_messages(self):
        """Read messages"""

        return self._proxy.read_messages()

    def test_function(self):
        """Test function"""

        return self._proxy.test_function()

def main():
    """Main function that executes JCM control server"""

    os.system('clear')
    server_address = "localhost"
    server_port = 8001
    jcm_control_server = JcmControlServer(server_address, server_port)

    def signal_handler(signum, frame):
        """ signal_handler - handling signals """

        print('Signal handler called with signal %d', signum)
        print('Exiting jcm_control_server.py')
        jcm_control_server.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    jcm_control_server.start()


if __name__ == "__main__":
    sys.exit(main())
