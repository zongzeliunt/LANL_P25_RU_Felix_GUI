#NOTE:
#This note is for future software developer to add new features, if you are not RU system developer please don't change anything. Otherwise you could make the RU GUI not working.
#For any question please contact Zongze Li by: zongzeli2@my.unt.edu


#Copy this whole RU_GUI_external_opts path to the path which you want to execute ./testbench1.py. 
#According to cheatsheet the path is 
#	~/git/RUv1_Test_sync2018-08/software/py/
 
#First, we need to add this initialize function call at testbench_base.py's Testbench's __init__ function to make sure the include_all_RU_GUI_external_opts function can be called when initialize a Testbench class type object:
"""
 		self.include_all_RU_GUI_external_opts()
"""

#And copy this internal function to somewhere inside class Testbench:
"""
	def include_all_RU_GUI_external_opts(self):
		#LANL 
		directory = "RU_GUI_external_opts"
		if os.path.exists(directory):
			sys.path.append(directory)
			import RU_GUI_external_opts
			RU_GUI_external_opts.include_all_external_opts(self)
"""
	#Please notice package "os" and "sys" are imported in testbench1.py, but if you want to execuate testbench_base.py alone you need to import them at testbench_base.py


#EXPLAIN
	#1) This is the way of minimum affect the original code. All GUI related functions are in this RU_GUI_external_opts file. We don't need to modify testbench_base.py too much. Which can be easy to merge future update.
	#2) However, we still need the class Testbench to include our functions as its class' internal function. 
	#3) When add new function, if want to call by testbench_base.py or testbench1.py, please list it in include_all_external_opts(self).
	#4) The way to write the command in the GUI's stave_config sub page's execute command button like this:
		#originally in cheatsheet, the command is ./testbench1.py setup_sensors
		#We still need to execuate testbench1.py first, not call RU_GUI_setup_sensors. We need the class testbench to initialize those senseors, then we use our function to write the parameters to the senseors.



import json

default_parameter_dict = {}
default_parameter_dict["PULSE_VPULSEH"] 			= 170
default_parameter_dict["PULSE_VPULSEL"] 			= 100
default_parameter_dict["IBIAS"] 					= 64
default_parameter_dict["VRESETD"] 					= 147
default_parameter_dict["VCASN"] 					= 50 
default_parameter_dict["VCASP"] 					= 86
default_parameter_dict["VCLIP"] 					= 0
default_parameter_dict["VCASN2"] 					= 57
default_parameter_dict["IDB"]						= 29
default_parameter_dict["ITHR"] 						= 50
default_parameter_dict["ITHR_commitTransaction"] 	= "True"


def include_all_external_opts(self):
	print "include all external"
	#self.RU_GUI_setup_sensors = RU_GUI_setup_sensors
	self.RU_GUI_setup_sensors_debug = RU_GUI_setup_sensors_debug


def parameter_dict_read_from_json_file ():
#{{{
	result_dict = {} 
	file_name = "./RU_GUI_external_opts/parameter.json"
 
	try:
		fl = open(file_name, "r")
		result_dict = json.load(fl)
		fl.close()     
	except:
		#default values
		result_dict	= default_parameter_dict 
	return result_dict
#}}}


def RU_GUI_setup_sensors(self,enable_strobe_generation=0,LinkSpeed=3,disable_manchester=1, pattern=SensorMatrixPattern.EMPTY):
	maskdict = self.read_maskfile("masklist_"+TBNAME+".txt")
	#do GRST at the beginning, since it's global
	self.rdo.dctrl.set_dctrl_mask(0x1F) #restore broadcast to all connectors
	ch_broadcast = Alpide(self.rdo, chipid=0x0F)
	ch_broadcast.reset()
	for connector,chipid in CHIP_MAP:
		self.rdo.dctrl.set_dctrl_mask(1<<connector)
		self.rdo.dctrl.set_input(connector,force=True)
		ch = Alpide(self.rdo, chipid=chipid)
		self.rdo.gth.initialize(check_reset_done=False)
		ch.initialize(disable_manchester=disable_manchester, grst=False, cfg_ob_module=False)
		ch.setreg_dtu_dacs(PLLDAC=8, DriverDAC=0x8, PreDAC=0x8)




		#this part is different from original
		parameter_dict = parameter_dict_read_from_json_file()
		ch.setreg_VPULSEH	(VPULSEH	=parameter_dict["PULSE_VPULSEH"])
		ch.setreg_VPULSEL	(VPULSEL	=parameter_dict["PULSE_VPULSEL"])
		ch.setreg_IBIAS		(IBIAS		=parameter_dict["IBIAS"])
		ch.setreg_VRESETD	(VRESETD	=parameter_dict["VRESETD"])
		ch.setreg_VCASN		(VCASN		=parameter_dict["VCASN"])
		ch.setreg_VCASP		(VCASP		=parameter_dict["VCASP"])
		ch.setreg_VCLIP		(VCLIP		=parameter_dict["VCLIP"])
		ch.setreg_VCASN2	(VCASN2		=parameter_dict["VCASN2"])
		ch.setreg_IDB		(IDB		=parameter_dict["IDB"])
		ch.setreg_ITHR		(ITHR		=parameter_dict["ITHR"],\
							commitTransaction=parameter_dict["commitTransaction"])
		#end


		for pll_off_sig in [0, 1, 0]:
			ch.setreg_dtu_cfg(VcoDelayStages=1,
							  PllBandwidthControl=1,
							  PllOffSignal=pll_off_sig,
							  SerPhase=8,
							  PLLReset=0,
							  LoadENStatus=0)

		ch.setreg_fromu_cfg_1(
			MEBMask=0,
			EnStrobeGeneration=enable_strobe_generation,
			EnBusyMonitoring=1,
			PulseMode=PULSE_ANOTD,
			EnPulse2Strobe=1,
			EnRotatePulseLines=0,
			TriggerDelay=0)

		# Duration of a Strobe Frame (Trigger)
		#ch.setreg_fromu_cfg_2(FrameDuration=0x3) # (3+1)*25ns
		ch.setreg_fromu_cfg_2(FrameDuration=80) # from MOSAIC. default for testbeam
		# Gap between Strobes (internal Trigger, when EnStrobeGeneration=1)
		ch.setreg_fromu_cfg_3(FrameGap=0x9) # (9+1)*25ns
		# Duration of PULSE window
		#ch.setreg_fromu_pulsing_2(PulseDuration=0x8) # 8*25ns
		ch.setreg_fromu_pulsing_2(PulseDuration=500) # copied from MOSAIC test_threshold - for analog pulsing this value must be large, since the (capacitively coupled) charge injection happens at edges of the pulse and you don't want to see the falling edge
		# Delay between Start of PULSE and start of STROBE (when EnPulse2Strobe=1)
		#ch.setreg_fromu_pulsing1(PulseDelay=0x1) # (1+1)*25ns
		ch.setreg_fromu_pulsing1(PulseDelay=PULSE_DELAY)

		#self.setup_sensor_matrix(ch,pattern=pattern)
		self.setup_sensor_matrix_list(ch,(connector,chipid),maskdict) #mask all pixels listed in the text file

		# ChipModeSelector determines the trigger mode:
		# 0=disabled, 1=triggered, 2=continuous
		ch.setreg_mode_ctrl(ChipModeSelector=1,
							EnClustering=1, #enable clustering
							#EnClustering=0, #disable clustering (simpler data format)
							MatrixROSpeed=1,
							IBSerialLinkSpeed=LinkSpeed,
							EnSkewGlobalSignals=1,
							EnSkewStartReadout=1,
							EnReadoutClockGating=1,
							EnReadoutFromCMU=0)
		self.rdo.dctrl.flush()
	self.rdo.dctrl.set_dctrl_mask(0x1F) #restore broadcast to all connectors
	#do RORST at the end, since it's global
	ch_broadcast.board.write_chip_opcode(Opcode.RORST)

def RU_GUI_setup_sensors_debug():
	print "ARES!!!!!!!!! RU GUI setup sensor debug"
	parameter_dict = parameter_dict_read_from_json_file()
	print parameter_dict 

