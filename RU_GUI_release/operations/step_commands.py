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

step = ["", "", "", "", ""]
step[0] = "Program RU FPGA"
step[1] = "/home/maps/git/RUv1_Test_sync2018-08/bitstreams/"
step[2] = "vivado -mode batch -source program_3plus1.tcl"
step[3] = "Program RU FPGA"
step[4] = 0
step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Config I2C, HIC"
step[1] = "/home/maps/git/RUv1_Test_sync2018-08/software/py"
step[2] = "./testbench_hic.py rdo i2c-gbtx gbtx-config ../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv1_1.xml"
step[3] = "Config GBTx0"
step[4] = 0
step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Disable Clock"
step[1] = "/home/maps/git/RUv1_Test_sync2018-08/software/py"
step[2] = "./testbench_hic.py rdo dctrl set-dclk-mask 0"
step[3] = "Disable Clock"
step[4] = 0
step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Enable Clock"
step[1] = "/home/maps/git/RUv1_Test_sync2018-08/software/py"
step[2] = "./testbench_hic.py rdo dctrl set-dclk-mask 0x1F"
step[3] = "Enable Clock"
step[4] = 0
step_commands.append(step)

step = ["", "", "", "", ""]
step[0] = "Show Stave config page"
step[1] = "'/home/maps/git/RUv1_Test_sync2018-08/software/py_gui/'"
step[2] = "self.show_stave_config"
step[3] = "Open the Stave config sub page"
step[4] = 1 
step_commands.append(step)





