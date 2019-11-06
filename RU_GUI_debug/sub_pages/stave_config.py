import wx
import os
import sys
import json
import subprocess

HORI = 200 #horizontal
VERT = 100 #vertical
#textbox_style = (wx.TE_MULTILINE | wx.TE_AUTO_SCROLL)
textbox_style = (wx.TE_MULTILINE | wx.HSCROLL)
#(wx.TE_MULTILINE | wx.TE_AUTO_SCROLL | wx.TE_DONTWRAP)

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

class stave_config(wx.Frame):
	def __init__(self, parent, title, exe_path, call_button = ""):
		self.dirname = ''
		#over all frame
		wx.Frame.__init__(self, parent, title = title, size = (1000, 800))	
		
		self.parameter_list = [] 
		#over all sizer
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(self.sizer)
		
		#orig path assign, maybe not useful
		self.exe_path = exe_path
		
		self.call_button_light_on(call_button)
	
	#all parameters initialize, this function is declared in RU_GUI_external_opts
		self.parameter_list_init(0)
		
		self.declare_parameter_input_box()
	
		self.add_stdoutbox()

		self.declare_exe_button()

		#this is destroy function, with light off call button feature
		self.Bind(wx.EVT_CLOSE, self.destroy)

	def declare_parameter_input_box (self):
	#{{{
		#declare all parameter input box
		self.parameter_value_inputbox_list = []
		self.parameter_value_readbox_list = []
		 
		labelbox=wx.BoxSizer(wx.HORIZONTAL)
		statictext=wx.StaticText(self,size=(HORI, -1))
		labelbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		statictext=wx.StaticText(self, label = "input", size=(HORI, -1))
		labelbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		statictext=wx.StaticText(self, label = "output", size=(HORI, -1))
		labelbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		self.sizer.Add(labelbox, 0, wx.ALIGN_LEFT)
		
		for i in range(len(self.parameter_list)):
			parameter = self.parameter_list[i]
			parameter_name = parameter[0]
			parameter_value = parameter[1]

			labelbox=wx.BoxSizer(wx.HORIZONTAL)

			statictext=wx.StaticText(self,label=parameter_name, size=(HORI, -1))
			labelbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

			input_text = wx.TextCtrl(self, i, str(parameter_value), size=(HORI, -1), style = textbox_style)
			labelbox.Add(input_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)	
			
			read_text = wx.TextCtrl(self, i, str(parameter_value), size=(HORI, -1), style = textbox_style)
			labelbox.Add(read_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
	
			self.sizer.Add(labelbox, 0, wx.ALIGN_LEFT)
			
			self.parameter_value_inputbox_list.append(input_text)
			self.parameter_value_readbox_list.append(read_text)
	#}}}

	def add_stdoutbox (self):
	#{{{
		stdoutbox=wx.BoxSizer(wx.HORIZONTAL)

		statictext=wx.StaticText(self,label='Linux Stdout:')
		stdoutbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		self.stdout_text = wx.TextCtrl(self, -1, 'stdout', size=(600, VERT), style=textbox_style)
		#stdoutbox.Add(self.stdout_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)	
		stdoutbox.Add(self.stdout_text, 1, flag=wx.LEFT |wx.FIXED_MINSIZE,border=5)	
		self.sizer.Add(stdoutbox, 0, wx.ALIGN_LEFT)	
	#}}}

	def declare_exe_button (self):	
	#{{{		
		#declare config exe button
		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.write_file_button = wx.Button(self, 0, "Write stave config file", size=(200, 50))
		self.write_file_button.SetBackgroundColour('white')

		button_sizer.Add(self.write_file_button, 0, wx.ALIGN_LEFT)
		
		self.exe_button = wx.Button(self, 1, "Config stave", size=(200, 50))
		self.exe_button.SetBackgroundColour('white')

		button_sizer.Add(self.exe_button, 1, wx.ALIGN_LEFT)

		self.write_default_file_button = wx.Button(self, 2, "Write default value to file", size=(200, 50))
		self.write_default_file_button.SetBackgroundColour('white')

		button_sizer.Add(self.write_default_file_button, 2, wx.ALIGN_LEFT)

		self.read_button = wx.Button(self, 3, "Read parameter from stave", size=(200, 50))
		self.read_button.SetBackgroundColour('white')
		button_sizer.Add(self.read_button, 3, wx.ALIGN_LEFT)
		
		self.sizer.Add(button_sizer, 0, wx.ALIGN_LEFT)
		self.Bind(wx.EVT_BUTTON, self.write_file_button_click, self.write_file_button)
		self.Bind(wx.EVT_BUTTON, self.write_default_file_button_click, self.write_default_file_button)
		self.Bind(wx.EVT_BUTTON, self.exe_button_click, self.exe_button)
		self.Bind(wx.EVT_BUTTON, self.read_button_click, self.read_button)
	#}}}

	def read_button_click (self, event):
	#{{{

		path = self.exe_path
		command = "./testbench1.py setup_sensors;"

		cmd = "cd " + path + "; " + command

		#ARES in real system this command must execute
		#sp = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		

		result_dict = {}
		file_name = self.exe_path + "/read_parameter.json"

		fl = open(file_name, "r")
		result_dict = json.load(fl)
		fl.close()     

		self.parameter_value_readbox_list[0].SetValue(str(result_dict["PULSE_VPULSEH"]))
		self.parameter_value_readbox_list[1].SetValue(str(result_dict["PULSE_VPULSEL"]))
		self.parameter_value_readbox_list[2].SetValue(str(result_dict["IBIAS"]))
		self.parameter_value_readbox_list[3].SetValue(str(result_dict["VRESETD"]))
		self.parameter_value_readbox_list[4].SetValue(str(result_dict["VCASN"]))
		self.parameter_value_readbox_list[5].SetValue(str(result_dict["VCASP"]))
		self.parameter_value_readbox_list[6].SetValue(str(result_dict["VCLIP"]))
		self.parameter_value_readbox_list[7].SetValue(str(result_dict["VCASN2"]))
		self.parameter_value_readbox_list[8].SetValue(str(result_dict["IDB"]))
		self.parameter_value_readbox_list[9].SetValue(str(result_dict["ITHR"]))
		self.parameter_value_readbox_list[10].SetValue(str(result_dict["ITHR_commitTransaction"]))


	#}}}

	def exe_button_click (self, event):
	#{{{
		path = self.exe_path
		command = "./testbench1.py setup_sensors;"

		cmd = "cd " + path + "; " + command
		
		sp = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		stdout_list = sp.stdout.readlines()
		stderr_list = sp.stderr.readlines()

		stdout_tmp = ""	
		for line in stdout_list:
			stdout_tmp += line
		for line in stderr_list:
			stdout_tmp += line
		
		self.stdout_text.SetValue(stdout_tmp)
	#}}}
	
	def write_default_file_button_click (self, event):
	#{{{
		self.parameter_list_init(1)
		for i in range (len(self.parameter_list)):
			this_parameter = self.parameter_list[i]
			self.parameter_value_inputbox_list[i].SetValue(str(this_parameter[1]))

		self.parameter_dict_write_to_json_file()
		self.write_default_file_button.SetBackgroundColour('green')
	#}}}
	
	def write_file_button_click (self, event):
	#{{{
		#parameter list is only for sequence order
		#operations are still doing on parameter dict

		for i in range (len(self.parameter_value_inputbox_list)):
			this_parameter = self.parameter_value_inputbox_list[i].GetValue()
			#print self.parameter_list[i][0] + " :" +  this_parameter
			parameter_name = self.parameter_list[i][0]
			self.parameter_dict[parameter_name] = this_parameter
		#all parameter in dict are updated
		#can write to json file and call stave config function
		self.parameter_dict_write_to_json_file()
		self.write_file_button.SetBackgroundColour('green')
	#}}}

	def parameter_dict_write_to_json_file (self):
	#{{{
		file_name = self.exe_path + "/parameter.json"
	 
		fl = open(file_name, "w")
		json.dump(self.parameter_dict,fl)
		fl.close()     
	#}}}

	def parameter_dict_read_from_json_file (self):
	#{{{
		result_dict = {}
		file_name = self.exe_path + "/parameter.json"
	 
		try:
			fl = open(file_name, "r")
			result_dict = json.load(fl)
			for arg in result_dict:
				if not arg == "ITHR_commitTransaction":
					result_dict[arg] = int(result_dict[arg])

			fl.close()     
		except:
			#default values
			result_dict	= default_parameter_dict 
		return result_dict
	#}}}

	def parameter_list_init(self, mode):
	#{{{
		self.parameter_dict = {}
		if mode == 0:
			#read parameter from json file
			self.parameter_dict = self.parameter_dict_read_from_json_file()
		else:
			#get parameter from default dict
			self.parameter_dict = default_parameter_dict

		#this list is just used to make parameter dict have sequence order
		
		self.parameter_list = [[] for i in range(len(self.parameter_dict))]

		self.parameter_list[0] = ["PULSE_VPULSEH", 			self.parameter_dict["PULSE_VPULSEH"]]
		self.parameter_list[1] = ["PULSE_VPULSEL", 			self.parameter_dict["PULSE_VPULSEL"]]
		self.parameter_list[2] = ["IBIAS", 					self.parameter_dict["IBIAS"]]
		self.parameter_list[3] = ["VRESETD", 					self.parameter_dict["VRESETD"]]
		self.parameter_list[4] = ["VCASN",  					self.parameter_dict["VCASN"]]
		self.parameter_list[5] = ["VCASP", 					self.parameter_dict["VCASP"]]
		self.parameter_list[6] = ["VCLIP", 					self.parameter_dict["VCLIP"]]
		self.parameter_list[7] = ["VCASN2", 					self.parameter_dict["VCASN2"]]
		self.parameter_list[8] = ["IDB", 						self.parameter_dict["IDB"]]
		self.parameter_list[9] = ["ITHR", 					self.parameter_dict["ITHR"]]
		self.parameter_list[10] = ["ITHR_commitTransaction", 	self.parameter_dict["ITHR_commitTransaction"]]
	#}}}
	
	#{{{
	def call_button_light_on(self, call_button):
		#the call_button is the upper page's button, calling this sub page
		#initilize call button and light it on 
		#we need to change call button color when close the frame
		self.call_button = call_button
		if not self.call_button == "":
			self.call_button.SetBackgroundColour('green') 

	def destroy(self, e):
		if not self.call_button == "":
			self.call_button.SetBackgroundColour('blue') 
		self.Destroy()
	#}}}

def show_stave_config (self, e, button_num, path):
	frame = stave_config(None, title = "Stave_config", exe_path = path , call_button = self.step_button_list[button_num])
	frame.Show()
	frame.Bind(wx.EVT_CLOSE, frame.destroy)


"""
if __name__ == '__main__':
	root = wx.App()
	frame = stave_config(None, title = "Stave_config", exe_path = os.getcwd())
	frame.Show()
	root.MainLoop()
"""
