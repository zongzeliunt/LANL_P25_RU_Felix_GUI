#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import os
import sys
import jcm_control_server
import fire

jcm_control_client = None

def start_jcm():
    """Connect to JCM and do some stuff"""

    server_address = "localhost"
    server_port = 8001
    return jcm_control_server.JcmControlClient(server_address, server_port)

def run_jcm():
    # programming
    jcm_control_client.start_full_configure()
    while True:
        if jcm_control_client.is_stopped():
            break
    time.sleep(1)  # wait for JCM to send all the messages
    read_messages = jcm_control_client.read_messages()
    if len(read_messages) > 0:
        print(read_messages[:-1])

    # wait before end of programming and fault injection
    print("\nWaiting 10s...")
    time.sleep(10)

    # fault injection
    jcm_control_client.start_random_fault_injection(50, 1000, True)

    # random stop
    time.sleep(30)
    jcm_control_client.stop_random_fault_injection()

    while True:
        if jcm_control_client.is_stopped():
            break

    time.sleep(1)  # wait for JCM to send all the messages
    read_messages = jcm_control_client.read_messages()
    successful_injected_faults = int(read_messages.split(" ")[-1])
    print("successful_injected_faults = %d" %successful_injected_faults)


def main():
    """Main function"""


    return fire.Fire(start_jcm())


if __name__ == '__main__':
    sys.exit(main())
