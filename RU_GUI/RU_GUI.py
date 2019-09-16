# -*- coding: utf-8 -*-
import wx
import os
import sys
sys.path.append('./operations')
import class_opts as co 

class my_GUI(wx.Frame):
	def __init__(self, parent, title):
		self.dirname = ''
		wx.Frame.__init__(self, parent, title = title, size = (800, 600))
		#1. overall box	
		co.declare_overall_box(self)

		#2. import function from outside		
		co.import_outside_functions(my_GUI)
			#the variable can only be my_GUI, not self, don't know why, but only in this way.
		
		#3. menu bar
		co.generate_status_bar(self)
	

		co.add_stepcombobox(self)
		co.add_steppathbox(self)
		co.add_stepcommandbox(self)
		co.add_stepexplainbox(self)
		co.add_stepstatusbox(self)


		#co.declare_input_frame(self)
		#co.declare_button(self)
















if __name__ == '__main__':
	root = wx.App()
	frame = my_GUI(None, title = "Ares_GUI")
	frame.Show()
	root.MainLoop()



"""
app = wx.App(False)
frame = my_GUI(None, title = "Ares_GUI")
frame.Show(True)
app.MainLoop()
"""
