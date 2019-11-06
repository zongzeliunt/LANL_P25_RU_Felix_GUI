#DEBUG
import serial
import sys, time


WAIT = 0.2
def redraw_settings(ser):
	outstr = ""
	ser.write("*IDN?\r\n".encode())
	response = ser.readline()
	outstr += response.decode().strip() + "\n"
	
	time.sleep(WAIT)
	
	ser.write("INST:NSEL 1\r\n".encode())
	outstr += print_settings(ser) + "\n"
	time.sleep(WAIT)
	
	ser.write("INST:NSEL 2\r\n".encode())
	outstr += print_settings(ser) + "\n"
	time.sleep(WAIT)
	return outstr

def get_status (ser):
	outstr = ""
	ser.write("INST:NSEL 1\r\n".encode())
	outstr += print_status(ser) + "\n"
	time.sleep(WAIT)

	ser.write("INST:NSEL 2\r\n".encode())
	outstr += print_status(ser) + "\n"
	time.sleep(WAIT)
	return outstr


def power_on(ser):
    ser.write("OUTPUT ON\r\n".encode())
    
def power_off(ser):
    ser.write("OUTPUT OFF\r\n".encode())

def recall_settings(ser):
    ser.write("*RCL 1\r\n".encode())

def print_settings(ser,end="\n"):
#{{{
	#no need to change
    outstr = ""
    ser.write("INST:SEL?\r\n".encode()); response = ser.readline()
    channel = response.decode().strip()
    outstr += "channel {0}: ".format(channel)

    ser.write("VOLT?\r\n".encode()); response = ser.readline()
    volt_set = float(response)
    ser.write("CURR?\r\n".encode()); response = ser.readline()
    curr_set = float(response)
    outstr += "setpoints {0:.3f} V {1:.3f} A, ".format(volt_set, curr_set)

    ser.write("VOLT:PROT:STATE?\r\n".encode()); response = ser.readline()
    ovp_enabled = "ENABLED" if int(response)==1 else "DISABLED"
    ser.write("VOLT:PROT:LEVEL?\r\n".encode()); response = ser.readline()
    ovp_setpoint = float(response)
    outstr += "OVP {0} @ {1} V".format(ovp_enabled, ovp_setpoint)

    return outstr
#}}}

def print_status(ser,end="\n"):
#{{{
	#no need to change

    outstr = ""
    ser.write("INST:SEL?\r\n".encode()); response = ser.readline()
    channel = response.decode().strip()
    outstr += "channel {0}: ".format(channel)

    ser.write("OUTPUT?\r\n".encode()); response = ser.readline()
    output_enabled = "ON" if int(response)==1 else "OFF"
    outstr += "output {0}, ".format(output_enabled)

    ser.write("MEAS:VOLT?\r\n".encode()); response = ser.readline()
    volt_readback = float(response)
    ser.write("MEAS:CURR?\r\n".encode()); response = ser.readline()
    curr_readback = float(response)
    outstr += "readbacks {0:.6f} V {1:.6f} A, ".format(volt_readback, curr_readback)

    ser.write("VOLT:PROT:TRIP?\r\n".encode()); response = ser.readline()
    ovp_tripped = "TRIPPED" if int(response)==1 else "OK"
    outstr += "OVP {0}".format(ovp_tripped)

    return outstr
#}}}

#DEBUG
def e3646a_serial_connect(PS_0_USB_ID):
	ser = serial.Serial(PS_0_USB_ID, 9600, timeout=1, dsrdtr=True)
	ser.flush()
	ser.write("SYST:REM\r\n".encode())
	return ser


def e3646a_serial_connect_debug(USB_ID):
	print ("this is from e3646a lib")
	debug_ser = USB_ID + "_debug_ser"
	return debug_ser
#{{{
"""

def main(stdscr):
    stdscr.clear()
    stdscr.nodelay(True)
    initwindow = stdscr.subwin(3,80,0,0)
    monitorwindow = stdscr.subwin(2,80,3,0)

    ser = serial.Serial(sys.argv[1], 9600, timeout=1, dsrdtr=True)
    ser.flush()
    ser.write("SYST:REM\r\n".encode())
    time.sleep(WAIT)

    redraw_settings(ser,initwindow)

    while True:
        c = stdscr.getch()
        if c == ord('q'):
            break
        elif c == ord('R'):
            recall_settings(ser)
            monitorwindow.erase()
            initwindow.erase()
            redraw_settings(ser,initwindow)
        elif c == ord('N'):
            power_on(ser)
            monitorwindow.erase()
        elif c == ord('F'):
            power_off(ser)
            monitorwindow.erase()


        ser.write("INST:NSEL 1\r\n".encode())
        time.sleep(WAIT)
        monitorwindow.addstr(0,0,print_status(ser))
        monitorwindow.refresh()
        ser.write("INST:NSEL 2\r\n".encode())
        time.sleep(WAIT)
        monitorwindow.addstr(1,0,print_status(ser))
        monitorwindow.refresh()
"""
#}}}
