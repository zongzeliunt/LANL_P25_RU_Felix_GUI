import wx
import os
import sys
import json
import time

HORI = 200 #horizontal
VERT = 100 #vertical
textbox_style = (wx.TE_MULTILINE | wx.HSCROLL)

WAIT = 1000

#WAIT = 200
 

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
	
		self.call_button_light_on(call_button)

		sys.path.append(lib_path)

		#PS_0
		#==============================================================================
		#operate library
		import e3646a_monitor_lib_version as e3646a
		self.e3646a = e3646a

		PS_0_USB_ID = "/dev/ttyUSB_id4"

		self.declare_PS_0_buttom_box()
		self.declare_PS_0_status_box()
		self.PS_0_buttom_event_bind()
		
		#DEBUG
		#self.PS_0_ser = e3646a.e3646a_serial_connect(PS_0_USB_ID)
		self.PS_0_ser = e3646a.e3646a_serial_connect_debug(PS_0_USB_ID)

		self.PS_0_timer = wx.Timer(self)
		self.PS_0_timer.Start(WAIT)
		
		#DEBUG
		self.Bind(wx.EVT_TIMER, self.PS_0_opt_process_debug, self.PS_0_timer)
		#self.Bind(wx.EVT_TIMER, self.PS_0_opt_process, self.PS_0_timer)

		self.PS_0_last_opt = "r1"
			#initial status is recall_1, need to call redraw_settings
			#w: wait, o: on, f: off, r0: recall_0, r1: recall_1


		#PS_1
		#==============================================================================
		#operate library
		import e3633a_monitor_lib_version as e3633a
		self.e3633a = e3633a

		PS_1_USB_ID = "/dev/ttyUSB_id5"
		self.declare_PS_1_buttom_box()
		self.declare_PS_1_status_box()
		self.PS_1_buttom_event_bind()
		
		#DEBUG
		#self.PS_1_ser = e3633a.e3633a_serial_connect(PS_1_USB_ID)
		self.PS_1_ser = e3633a.e3633a_serial_connect_debug(PS_1_USB_ID)
		
		self.PS_1_timer = wx.Timer(self)
		self.PS_1_timer.Start(WAIT)  
		
		#DEBUG
		self.Bind(wx.EVT_TIMER, self.PS_1_opt_process_debug, self.PS_1_timer)
		#self.Bind(wx.EVT_TIMER, self.PS_1_opt_process, self.PS_1_timer)

		self.PS_1_last_opt = "r1"
	
		#PS_2
		#==============================================================================
		#operate library

		PS_2_USB_ID = "/dev/ttyUSB_id6"
		self.declare_PS_2_buttom_box()
		self.declare_PS_2_status_box()
		self.PS_2_buttom_event_bind()
		
		#DEBUG
		#self.PS_2_ser = e3633a.e3633a_serial_connect(PS_2_USB_ID)
		self.PS_2_ser = e3633a.e3633a_serial_connect_debug(PS_2_USB_ID)
		
		self.PS_2_timer = wx.Timer(self)
		self.PS_2_timer.Start(WAIT)  
		
		#DEBUG
		self.Bind(wx.EVT_TIMER, self.PS_2_opt_process_debug, self.PS_2_timer)
		#self.Bind(wx.EVT_TIMER, self.PS_2_opt_process, self.PS_2_timer)

		self.PS_2_last_opt = "r1"


		self.Bind(wx.EVT_CLOSE, self.destroy)

	def declare_PS_0_buttom_box(self):
		#{{{
		#three buttons
		buttombox=wx.BoxSizer(wx.HORIZONTAL)
		buttomtext=wx.StaticText(self, label = "PS_0", size=(HORI, -1))
		buttombox.Add(buttomtext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.PS_0_on_buttom = wx.Button(self, 0, "PS_0 ON", size=(HORI, 50))
		self.PS_0_on_buttom.SetBackgroundColour('white')
		buttombox.Add(self.PS_0_on_buttom, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		self.PS_0_off_buttom = wx.Button(self, 1, "PS_0 OFF", size=(HORI, 50))
		self.PS_0_off_buttom.SetBackgroundColour('white')
		buttombox.Add(self.PS_0_off_buttom, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.PS_0_recall_buttom = wx.Button(self, 2, "PS_0 Recall", size=(HORI, 50))
		self.PS_0_recall_buttom.SetBackgroundColour('white')
		buttombox.Add(self.PS_0_recall_buttom, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.sizer.Add(buttombox, 0, wx.ALIGN_LEFT)
		#}}}
	
	def declare_PS_0_status_box(self):
		#{{{
		#status box	
		PS_0_status_box=wx.BoxSizer(wx.HORIZONTAL)

		statustext=wx.StaticText(self,label='PS_0 status box:', size=(HORI * 0.5, VERT))
		PS_0_status_box.Add(statustext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		self.PS_0_status_text = wx.TextCtrl(self, 0, 'PS_0 status', size=(HORI * 2.5, VERT), style=textbox_style)
		PS_0_status_box.Add(self.PS_0_status_text, 1, flag=wx.LEFT |wx.FIXED_MINSIZE,border=5)	
		self.PS_0_operate_text = wx.TextCtrl(self, 1, 'PS_0 operate', size=(HORI , VERT), style=textbox_style)
		PS_0_status_box.Add(self.PS_0_operate_text, 1, flag=wx.LEFT |wx.FIXED_MINSIZE,border=5)	
		
		self.sizer.Add(PS_0_status_box, 0, wx.ALIGN_LEFT)	
		#}}}
		
	def PS_0_buttom_event_bind(self):
	#{{{
		self.Bind(wx.EVT_BUTTON, self.PS_0_on, self.PS_0_on_buttom)
		self.Bind(wx.EVT_BUTTON, self.PS_0_off, self.PS_0_off_buttom)
		self.Bind(wx.EVT_BUTTON, self.PS_0_recall, self.PS_0_recall_buttom)


	def PS_0_on (self, e):
		self.PS_0_on_buttom.SetBackgroundColour('green')
		self.PS_0_off_buttom.SetBackgroundColour('white')
		self.PS_0_recall_buttom.SetBackgroundColour('white')
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_0_operate_text.SetValue(now_time + " PS_0 on")
		self.PS_0_last_opt = "o"
		
	def PS_0_off (self, e):
		self.PS_0_off_buttom.SetBackgroundColour('green')
		self.PS_0_on_buttom.SetBackgroundColour('white')
		self.PS_0_recall_buttom.SetBackgroundColour('white')
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_0_operate_text.SetValue(now_time + " PS_0 off")
		self.PS_0_last_opt = "f"

	def PS_0_recall (self, e):
		self.PS_0_recall_buttom.SetBackgroundColour('green')
		self.PS_0_off_buttom.SetBackgroundColour('white')
		self.PS_0_on_buttom.SetBackgroundColour('white')
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_0_operate_text.SetValue(now_time + " PS_0 recall")
		self.PS_0_last_opt = "r0"
	#}}}

	def PS_0_opt_process(self, e):
		#{{{
		#all operations must be done in the gap of WAIT!
		#my WAIT is 1000 or 1s, if sleep more than that could have error!

		#w: wait, o: on, f: off, r0: recall_0, r1: recall_1

		last_opt = self.PS_0_last_opt

		if last_opt == "w":
			status = self.e3646a.get_status(self.PS_0_ser)
			#get status wait 0.4 s
			self.PS_0_status_text.SetValue(status)
			self.PS_0_last_opt = "w"
		elif last_opt == "o":
			self.e3646a.power_on(self.PS_0_ser)
			self.PS_0_last_opt = "w"
		elif last_opt == "f":
			self.e3646a.power_off(self.PS_0_ser)
			self.PS_0_last_opt = "w"
		elif last_opt == "r0":
			self.e3646a.recall_settings(self.PS_0_ser)
			self.PS_0_last_opt = "r1"
		elif last_opt == "r1":
			status = self.e3646a.redraw_settings(self.PS_0_ser)
			self.PS_0_status_text.SetValue(status)
			self.PS_0_last_opt = "w"
		else:
			self.PS_0_last_opt = "w"
		#}}}

	def PS_0_opt_process_debug(self, e):
		#Example: https://blog.csdn.net/rumswell/article/details/6564181
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_0_status_text.SetValue(now_time + " " + self.PS_0_last_opt)

		#this is the gap all operations must be done!:
		#	WAIT / 1000 - 0.1
		#
		#time.sleep(WAIT / 1000 - 0.1)
	


	def declare_PS_1_buttom_box(self):
		#{{{
		#three buttons
		buttombox=wx.BoxSizer(wx.HORIZONTAL)
		buttomtext=wx.StaticText(self, label = "PS_1", size=(HORI, -1))
		buttombox.Add(buttomtext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.PS_1_on_buttom = wx.Button(self, 3, "PS_1 ON", size=(HORI, 50))
		self.PS_1_on_buttom.SetBackgroundColour('white')
		buttombox.Add(self.PS_1_on_buttom, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		self.PS_1_off_buttom = wx.Button(self, 4, "PS_1 OFF", size=(HORI, 50))
		self.PS_1_off_buttom.SetBackgroundColour('white')
		buttombox.Add(self.PS_1_off_buttom, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.PS_1_recall_buttom = wx.Button(self, 5, "PS_1 Recall", size=(HORI, 50))
		self.PS_1_recall_buttom.SetBackgroundColour('white')
		buttombox.Add(self.PS_1_recall_buttom, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.sizer.Add(buttombox, 0, wx.ALIGN_LEFT)
		#}}}
	
	def declare_PS_1_status_box(self):
		#{{{
		#status box	
		PS_1_status_box=wx.BoxSizer(wx.HORIZONTAL)

		statustext=wx.StaticText(self,label='PS_1 status box:', size=(HORI *0.5, VERT))
		PS_1_status_box.Add(statustext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		self.PS_1_status_text = wx.TextCtrl(self, 2, 'PS_1 status', size=(HORI * 2.5, VERT), style=textbox_style)
		PS_1_status_box.Add(self.PS_1_status_text, 1, flag=wx.LEFT |wx.FIXED_MINSIZE,border=5)	
		self.PS_1_operate_text = wx.TextCtrl(self, 3, 'PS_1 operate', size=(HORI , VERT), style=textbox_style)
		PS_1_status_box.Add(self.PS_1_operate_text, 1, flag=wx.LEFT |wx.FIXED_MINSIZE,border=5)	
		
		self.sizer.Add(PS_1_status_box, 0, wx.ALIGN_LEFT)	
		#}}}
		
	def PS_1_buttom_event_bind(self):
	#{{{
		self.Bind(wx.EVT_BUTTON, self.PS_1_on, self.PS_1_on_buttom)
		self.Bind(wx.EVT_BUTTON, self.PS_1_off, self.PS_1_off_buttom)
		self.Bind(wx.EVT_BUTTON, self.PS_1_recall, self.PS_1_recall_buttom)


	def PS_1_on (self, e):
		self.PS_1_on_buttom.SetBackgroundColour('green')
		self.PS_1_off_buttom.SetBackgroundColour('white')
		self.PS_1_recall_buttom.SetBackgroundColour('white')
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_1_operate_text.SetValue(now_time + " PS_1 on")
		self.PS_1_last_opt = "o"
		
	def PS_1_off (self, e):
		self.PS_1_off_buttom.SetBackgroundColour('green')
		self.PS_1_on_buttom.SetBackgroundColour('white')
		self.PS_1_recall_buttom.SetBackgroundColour('white')
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_1_operate_text.SetValue(now_time + " PS_1 off")
		self.PS_1_last_opt = "f"

	def PS_1_recall (self, e):
		self.PS_1_recall_buttom.SetBackgroundColour('green')
		self.PS_1_off_buttom.SetBackgroundColour('white')
		self.PS_1_on_buttom.SetBackgroundColour('white')
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_1_operate_text.SetValue(now_time + " PS_1 recall")
		self.PS_1_last_opt = "r0"
	#}}}

	def PS_1_opt_process(self, e):
		#{{{
		#all operations must be done in the gap of WAIT!
		#my WAIT is 1000 or 1s, if sleep more than that could have error!

		#w: wait, o: on, f: off, r0: recall_0, r1: recall_1

		last_opt = self.PS_1_last_opt

		if last_opt == "w":
			status = self.e3633a.print_status(self.PS_1_ser)
			#get status wait 0.4 s
			self.PS_1_status_text.SetValue(status)
			self.PS_1_last_opt = "w"
		elif last_opt == "o":
			self.e3633a.power_on(self.PS_1_ser)
			self.PS_1_last_opt = "w"
		elif last_opt == "f":
			self.e3633a.power_off(self.PS_1_ser)
			self.PS_1_last_opt = "w"
		elif last_opt == "r0":
			self.e3633a.recall_settings(self.PS_1_ser)
			self.PS_1_last_opt = "r1"
		elif last_opt == "r1":
			status = self.e3633a.redraw_settings(self.PS_1_ser)
			self.PS_1_status_text.SetValue(status)
			self.PS_1_last_opt = "w"
		else:
			self.PS_1_last_opt = "w"
		#}}}

	def PS_1_opt_process_debug(self, e):
		#Example: https://blog.csdn.net/rumswell/article/details/6564181
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_1_status_text.SetValue(now_time + " " + self.PS_1_last_opt)

		#this is the gap all operations must be done!:
		#	WAIT / 1000 - 0.1


	def declare_PS_2_buttom_box(self):
		#{{{
		#three buttons
		buttombox=wx.BoxSizer(wx.HORIZONTAL)
		buttomtext=wx.StaticText(self, label = "PS_2", size=(HORI, -1))
		buttombox.Add(buttomtext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.PS_2_on_buttom = wx.Button(self, 6, "PS_2 ON", size=(HORI, 50))
		self.PS_2_on_buttom.SetBackgroundColour('white')
		buttombox.Add(self.PS_2_on_buttom, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		self.PS_2_off_buttom = wx.Button(self, 7, "PS_2 OFF", size=(HORI, 50))
		self.PS_2_off_buttom.SetBackgroundColour('white')
		buttombox.Add(self.PS_2_off_buttom, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.PS_2_recall_buttom = wx.Button(self, 8, "PS_2 Recall", size=(HORI, 50))
		self.PS_2_recall_buttom.SetBackgroundColour('white')
		buttombox.Add(self.PS_2_recall_buttom, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
		
		self.sizer.Add(buttombox, 0, wx.ALIGN_LEFT)
		#}}}
	
	def declare_PS_2_status_box(self):
		#{{{
		#status box	
		PS_2_status_box=wx.BoxSizer(wx.HORIZONTAL)

		statustext=wx.StaticText(self,label='PS_2 status box:', size=(HORI * 0.5, VERT))
		PS_2_status_box.Add(statustext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		self.PS_2_status_text = wx.TextCtrl(self, 2, 'PS_2 status', size=(HORI * 2.5, VERT), style=textbox_style)
		PS_2_status_box.Add(self.PS_2_status_text, 1, flag=wx.LEFT |wx.FIXED_MINSIZE,border=5)	
		self.PS_2_operate_text = wx.TextCtrl(self, 3, 'PS_2 operate', size=(HORI , VERT), style=textbox_style)
		PS_2_status_box.Add(self.PS_2_operate_text, 1, flag=wx.LEFT |wx.FIXED_MINSIZE,border=5)	
		
		self.sizer.Add(PS_2_status_box, 0, wx.ALIGN_LEFT)	
		#}}}
		
	def PS_2_buttom_event_bind(self):
	#{{{
		self.Bind(wx.EVT_BUTTON, self.PS_2_on, self.PS_2_on_buttom)
		self.Bind(wx.EVT_BUTTON, self.PS_2_off, self.PS_2_off_buttom)
		self.Bind(wx.EVT_BUTTON, self.PS_2_recall, self.PS_2_recall_buttom)


	def PS_2_on (self, e):
		self.PS_2_on_buttom.SetBackgroundColour('green')
		self.PS_2_off_buttom.SetBackgroundColour('white')
		self.PS_2_recall_buttom.SetBackgroundColour('white')
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_2_operate_text.SetValue(now_time + " PS_2 on")
		self.PS_2_last_opt = "o"
		
	def PS_2_off (self, e):
		self.PS_2_off_buttom.SetBackgroundColour('green')
		self.PS_2_on_buttom.SetBackgroundColour('white')
		self.PS_2_recall_buttom.SetBackgroundColour('white')
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_2_operate_text.SetValue(now_time + " PS_2 off")
		self.PS_2_last_opt = "f"

	def PS_2_recall (self, e):
		self.PS_2_recall_buttom.SetBackgroundColour('green')
		self.PS_2_off_buttom.SetBackgroundColour('white')
		self.PS_2_on_buttom.SetBackgroundColour('white')
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_2_operate_text.SetValue(now_time + " PS_2 recall")
		self.PS_2_last_opt = "r0"
	#}}}

	def PS_2_opt_process(self, e):
		#{{{
		#all operations must be done in the gap of WAIT!
		#my WAIT is 1000 or 1s, if sleep more than that could have error!

		#w: wait, o: on, f: off, r0: recall_0, r1: recall_1

		last_opt = self.PS_2_last_opt

		if last_opt == "w":
			status = self.e3633a.get_status(self.PS_2_ser)
			#get status wait 0.4 s
			self.PS_2_status_text.SetValue(status)
			self.PS_2_last_opt = "w"
		elif last_opt == "o":
			self.e3633a.power_on(self.PS_2_ser)
			self.PS_2_last_opt = "w"
		elif last_opt == "f":
			self.e3633a.power_off(self.PS_2_ser)
			self.PS_2_last_opt = "w"
		elif last_opt == "r0":
			self.e3633a.recall_settings(self.PS_2_ser)
			self.PS_2_last_opt = "r1"
		elif last_opt == "r1":
			status = self.e3633a.redraw_settings(self.PS_2_ser)
			self.PS_2_status_text.SetValue(status)
			self.PS_2_last_opt = "w"
		else:
			self.PS_2_last_opt = "w"
		#}}}

	def PS_2_opt_process_debug(self, e):
		#Example: https://blog.csdn.net/rumswell/article/details/6564181
		now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		self.PS_2_status_text.SetValue(now_time + " " + self.PS_2_last_opt)

		#this is the gap all operations must be done!:
		#	WAIT / 1000 - 0.1






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
