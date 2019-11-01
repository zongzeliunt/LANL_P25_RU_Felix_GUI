step_commands = [] 

#0: title (buttom name)
#1: path
#2: command
#3: explain
#4: mode


#template
#step = ["", "", "", "", ""]
#step[0] = ""
#step[1] = ""
#step[2] = ""
#step[3] = ""
#step[4] = ""
#step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Program Felix"
step[1] = "~/git/felix-firmware-sync2018-08/bitstreams"
step[2] = "vivado -mode batch -source program.tcl"
step[3] = "Program Felix FPGA"
step[4] = 0
step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Setup DAQ"
step[1] = "~/meeg/felix/daq/felix_rcdaq/build"
step[2] = "flx-init -X ~/gtm/clockscripts/Si5345-RevB-40_08MHz.slabtimeproj_1_10_17-Registers_2_10_output_default.h"
step[3] = "Setup DAQ"
step[4] = "0"
step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Run DAQ"
step[1] = " ~/meeg/felix/daq/felix_rcdaq"
step[2] = "./setup_felix_rcdaq_felixTrigger.sh ; daq_set_runtype calib"
step[3] = "Run DAQ"
step[4] = "0"
step_commands.append(step)


#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#debug

step_commands_1 = []

step = ["", "", "", "", ""]
step[0] = "PS control page"
step[1] = "'./sub_pages'"
step[2] = "self.show_power_control"
step[3] = "power supply control"
step[4] = 1
step_commands_1.append(step)

"""
step = ["", "", "", "", ""]
step[0] = "Test step 0"
step[1] = "/home/ares/LANL_work/LANL_P25_RU_Felix_GUI/test_folder/"
step[2] = "sh test.sh"
step[3] = "test step 0"
step[4] = 0
step_commands_1.append(step)
"""

step = ["", "", "", "", ""]
step[0] = "Test step 1"
step[1] = "/home/ares/LANL_work/LANL_P25_RU_Felix_GUI/test_folder/level_1"
step[2] = "sh test.sh"
step[3] = "test step 1"
step[4] = 0
step_commands_1.append(step)

step = ["", "", "", "", ""]
step[0] = "Test step 2"
step[1] = "/home/ares/LANL_work/LANL_P25_RU_Felix_GUI/test_folder/level_2"
step[2] = "sh test.sh"
step[3] = "test step 2"
step[4] = 0
step_commands_1.append(step)

step = ["", "", "", "", ""]
step[0] = "Show Stave config page"
step[1] = "'./sub_pages'"
#for real system, change this path to the orig software path
step[2] = "self.show_stave_config"
step[3] = "test pop page, call internal function"
step[4] = 1 
step_commands_1.append(step)

