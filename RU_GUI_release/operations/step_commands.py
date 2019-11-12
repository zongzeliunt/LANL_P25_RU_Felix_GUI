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
step[0] = "PS control page"
step[1] = "'./sub_pages'"
step[2] = "self.show_power_control"
step[3] = "Open power supply control sub page"
step[4] = 1
step_commands.append(step)

"""
step = ["", "", "", "", ""]
step[0] = "Open power terminals"
step[1] = "/home/maps/git/misc_software/usbserial_testbeam/"
step[2] = "./open_terminals.sh"
step[3] = "Open power supply terminals"
step[4] = 0
step_commands.append(step)
"""

step = ["", "", "", "", ""]
step[0] = "Program RU FPGA"
step[1] = "/home/maps/git/RUv1_Test_sync2018-08/bitstreams/"
step[2] = "vivado -mode batch -source program_3plus1.tcl"
step[3] = "Program RU FPGA"
step[4] = 0
step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Config GBTx0"
step[1] = "/home/maps/git/RUv1_Test_sync2018-08/software/py"
step[2] = "./testbench1.py rdo i2c-gbtx gbtx-config ../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv1_1.xml"
step[3] = "Config GBTx0"
step[4] = 0
step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Config GBTx1"
step[1] = "/home/maps/git/RUv1_Test_sync2018-08/software/py/"
step[2] = "./testbench2.py rdo i2c-gbtx gbtx-config ../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv1_1.xml"
step[3] = "Config GBTx1"
step[4] = 0
step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Show Stave config page"
step[1] = "'/home/maps/git/RUv1_Test_sync2018-08/software/py_gui/'"
step[2] = "self.show_stave_config"
step[3] = "Open the Stave config sub page"
step[4] = 1 
step_commands.append(step)





