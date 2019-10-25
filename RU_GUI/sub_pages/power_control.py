import wx
import os
import sys
import json


HORI = 200 #horizontal
VERT = 100 #vertical
textbox_style = (wx.TE_MULTILINE | wx.HSCROLL)


class power_control(wx.Frame):
	def __init__(self, parent, title, exe_path, call_button = ""):
		self.dirname = ''
		#over all frame
		wx.Frame.__init__(self, parent, title = title, size = (1000, 800))	
		
		


		#over all sizer
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(self.sizer)
		
		#orig path assign, maybe not useful
		self.exe_path = exe_path
		
		lib_path = 	self.exe_path + '/power_supply_control_lib'
		sys.path.append(lib_path)
		import e3636a_monitor_lib_version as e3636a
		


		self.call_button_light_on(call_button)

		self.declare_PS_0_box()

		self.Bind(wx.EVT_CLOSE, self.destroy)
	



	def declare_PS_0_box(self):
		
		#three buttons
		buttonbox=wx.BoxSizer(wx.HORIZONTAL)
		statictext=wx.StaticText(self, label = "PS_0", size=(HORI, -1))
		buttonbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.PS_0_start = wx.Button(self, 0, "PS 0 START", size=(HORI, 50))
		buttonbox.Add(self.PS_0_start, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		self.PS_0_off = wx.Button(self, 0, "PS 0 OFF", size=(HORI, 50))
		buttonbox.Add(self.PS_0_off, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		self.PS_0_recall = wx.Button(self, 0, "PS 0 Recall", size=(HORI, 50))
		buttonbox.Add(self.PS_0_recall, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.sizer.Add(buttonbox, 0, wx.ALIGN_LEFT)
	
		#status box	
		PS_0_status_box=wx.BoxSizer(wx.HORIZONTAL)

		statictext=wx.StaticText(self,label='PS 0 status box:', size=(HORI, VERT))
		PS_0_status_box.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		self.PS_0_status_text = wx.TextCtrl(self, -1, 'PS 0 status', size=(HORI * 1.5, VERT), style=textbox_style)
		PS_0_status_box.Add(self.PS_0_status_text, 1, flag=wx.LEFT |wx.FIXED_MINSIZE,border=5)	
		self.PS_0_operate_text = wx.TextCtrl(self, -1, 'PS 0 operate', size=(HORI * 1.5, VERT), style=textbox_style)
		PS_0_status_box.Add(self.PS_0_operate_text, 1, flag=wx.LEFT |wx.FIXED_MINSIZE,border=5)	
		
		self.sizer.Add(PS_0_status_box, 0, wx.ALIGN_LEFT)	
		








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

def show_power_control (self, e, button_num, path):
	frame = power_control(None, title = "Power_supply_control", exe_path = path , call_button = self.step_button_list[button_num])
	frame.Show()
	frame.Bind(wx.EVT_CLOSE, frame.destroy)


if __name__ == '__main__':
	root = wx.App()
	frame = power_control(None, title = "Power_supply_control", exe_path = os.getcwd())
	frame.Show()
	root.MainLoop()
