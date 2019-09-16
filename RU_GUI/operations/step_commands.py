step_commands = {}
step_0 = ["", "", ""]
step_0[0] = "/home/maps/git/misc_software/usbserial_testbeam/"
step_0[1] = "./open_terminals.sh"
step_0[1] = "Open power supply terminals"
step_commands["Step 0: open teminals"] = step_0

step_1 = ["", "", ""]
step_1[0] = "/home/maps/software/Xilinx/Vivado/2017.4/"
step_1[1] = "source settings64.sh"
step_1[2] = "Source Vivado setting"
step_commands["Step 1: source Vivado setting"] = step_1

step_2 = ["", "", ""]
step_2[0] = "/home/maps/git/RUv1_Test_sync2018-08/bitstreams/"
step_2[1] = "vivado -mode batch -source program_3plus1.tcl"
step_2[2] = "Program RU FPGA"
step_commands["Step 2: program RU FPGA"] = step_2

step_3 = ["", "", ""]
step_3[0] = "/home/maps/git/RUv1_Test_sync2018-08/software/py/"
step_3[1] = "source scl_source enable rh-python36"
step_3[2] = "Config python"
step_commands["Step 3: Config python"] = step_3

step_4 = ["", "", ""]
step_4[0] = "/home/maps/git/RUv1_Test_sync2018-08/software/py/"
step_4[1] = "./testbench1.py rdo i2c-gbtx gbtx-config ../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv1_1.xml"
step_4[2] = "Config GBTx0"
step_commands["Step 4: Config GBTx0"] = step_4

step_5 = ["", "", ""]
step_5[0] = "/home/maps/git/RUv1_Test_sync2018-08/software/py/"
step_5[1] = "./testbench2.py rdo i2c-gbtx gbtx-config ../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv1_1.xml"
step_5[2] = "Config GBTx0"
step_commands["Step 5: Config GBTx1"] = step_5

"""
#step_0[0]: path
#step_0[1]: command
#step_0[2]: explain
step_0 = ["", "", ""]
step_0[0] = "/home/ares/UNT_work/github_copy/Python_experiments/python_GUI/my_GUI/"
step_0[1] = "./test.sh"
step_0[2] = "test step 0"
step_commands["Step 0: open teminals"] = step_0

"""





"""
step_commands["step_0"] = ["print 'abc'", " use to print abc"]
step_commands["step_1"] = ["print '123'", "use to print 123"]
step_commands["step_2"] = ["print 'fgh'", "use to print fgh"]
"""

