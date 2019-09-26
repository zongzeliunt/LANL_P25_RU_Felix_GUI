import wx
import os
import sys

HORI = 200 #horizontal
VERT = 100 #vertical
#textbox_style = (wx.TE_MULTILINE | wx.TE_AUTO_SCROLL)
textbox_style = (wx.TE_MULTILINE | wx.HSCROLL)
#(wx.TE_MULTILINE | wx.TE_AUTO_SCROLL | wx.TE_DONTWRAP)


class stave_config(wx.Frame):
	def __init__(self, parent, title, exe_path, call_button):
		self.dirname = ''
		#over all frame
		wx.Frame.__init__(self, parent, title = title, size = (800, 600))	
		
		#over all sizer
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(self.sizer)
		
		#orig path assign, maybe not useful
		self.exe_path = exe_path
		
		#initilize call button and light it on 
		self.call_button_light_on(call_button)

 		self.include_all_RU_GUI_external_opts()
		
		#all parameters initialize
		self.parameter_list_init ()	
		
		#declare all parameter input box
		self.declare_parameter_input_box()

		#declare config exe button
		self.declare_exe_button()

		#this is destroy function, with light off call button feature
		self.Bind(wx.EVT_CLOSE, self.destroy)

	def include_all_RU_GUI_external_opts(self):
		#LANL 
		directory = self.exe_path + "/RU_GUI_external_opts"
		
		if os.path.exists(directory):
			print "external success"
			sys.path.append(directory)
			import RU_GUI_external_opts
			RU_GUI_external_opts.include_all_external_opts(self)
	


	
	def parameter_list_init(self):
		self.parameter_list = [] 
			
		self.parameter_list.append(["PULSE_VPULSEH", 170])
		self.parameter_list.append(["PULSE_VPULSEL", 100])
		self.parameter_list.append(["IBIAS", 64])
		self.parameter_list.append(["VRESETD", 147])
		self.parameter_list.append(["VCASN", 50 ])
		self.parameter_list.append(["VCASP", 86])
		self.parameter_list.append(["VCLIP", 0])
		self.parameter_list.append(["VCASN2", 57])
		self.parameter_list.append(["IDB", 29])
		self.parameter_list.append(["ITHR", 50])
		self.parameter_list.append(["ITHR_commitTransaction", "True"])


	def call_button_light_on(self, call_button):
		self.call_button = call_button
		self.call_button.SetBackgroundColour('green') 

	def destroy(self, e):
		print "stave config page close"
		self.call_button.SetBackgroundColour('blue') 
		self.Destroy()

	def declare_parameter_input_box (self):
		#text_box = wx.TextCtrl(self, -1, 'this is stave config page', size=(HORI, -1), style = textbox_style)
		#self.sizer.Add(text_box, 0, wx.ALIGN_LEFT)   

		self.parameter_value_box_list = []
		 
		for i in range(len(self.parameter_list)):
			parameter = self.parameter_list[i]
			parameter_name = parameter[0]
			parameter_value = parameter[1]

			labelbox=wx.BoxSizer(wx.HORIZONTAL)

			statictext=wx.StaticText(self,label=parameter_name)
			labelbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

			input_text = wx.TextCtrl(self, i, str(parameter_value), size=(HORI, -1), style = textbox_style)
			labelbox.Add(input_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)	
			self.sizer.Add(labelbox, 0, wx.ALIGN_LEFT)
			
			self.parameter_value_box_list.append(input_text)
			

	def declare_exe_button (self):			
		self.exe_button = wx.Button(self, 0, "Config stave", size=(200, 50))
		self.exe_button.SetBackgroundColour('white')
	
		self.sizer.Add(self.exe_button, 0, wx.ALIGN_LEFT)
		self.Bind(wx.EVT_BUTTON, self.exe_button_click, self.exe_button)

	def exe_button_click (self, event):
		for i in range (len(self.parameter_value_box_list)):
			this_parameter = self.parameter_value_box_list[i].GetValue()
			print self.parameter_list[i][0] + " :" +  this_parameter


def show_stave_config (self, e, button_num, path):
	print "show stave_config"
	print "path variable from out " + path

	exe_path =  path
	
	frame = stave_config(None, title = "Stave_config", exe_path = exe_path , call_button = self.step_button_list[button_num])
	frame.Show()
	frame.Bind(wx.EVT_CLOSE, frame.destroy)


"""
if __name__ == '__main__':
	root = wx.App()
	frame = stave_config(None, title = "Stave_config", orig_path = os.getcwd())
	frame.Show()
	root.MainLoop()
"""
