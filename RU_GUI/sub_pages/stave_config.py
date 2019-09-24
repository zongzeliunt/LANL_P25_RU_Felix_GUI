import wx
import os

HORI = 200 #horizontal
VERT = 100 #vertical
textbox_style = (wx.TE_MULTILINE | wx.TE_AUTO_SCROLL)
#(wx.TE_MULTILINE | wx.TE_AUTO_SCROLL | wx.TE_DONTWRAP)


class stave_config(wx.Frame):
	def __init__(self, parent, title, orig_path, call_button):
		self.dirname = ''
		#over all frame
		wx.Frame.__init__(self, parent, title = title, size = (800, 600))	
		
		#over all sizer
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(self.sizer)
		
		#orig path assign, maybe not useful
		self.orig_path = orig_path
		
		#initilize call button and light it on 
		self.call_button_light_on(call_button)

		#declare all parameter input box
		self.declare_parameter_input_box()

		#
		
		
		#this is destroy function, with light off call button feature
		self.Bind(wx.EVT_CLOSE, self.destroy)

	def call_button_light_on(self, call_button):
		self.call_button = call_button
		self.call_button.SetBackgroundColour('green') 

	def destroy(self, e):
		print "stave config page close"
		self.call_button.SetBackgroundColour('blue') 
		self.Destroy()

	def declare_parameter_input_box (self):
		text_box = wx.TextCtrl(self, -1, 'this is stave config page', size=(HORI, -1), style = textbox_style)
		self.sizer.Add(text_box, 0, wx.ALIGN_LEFT)    
		
		
		labelbox=wx.BoxSizer(wx.HORIZONTAL)

		statictext=wx.StaticText(self,label='label')
		labelbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

		input_text = wx.TextCtrl(self, -1, 'parameter', size=(HORI, -1), style = textbox_style)
		labelbox.Add(input_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)	
		self.sizer.Add(labelbox, 0, wx.ALIGN_LEFT)	

		"""
		text_sizer = wx.BoxSizer(wx.HORIZONTAL)
		static_text = wx.StaticText(self, -1, 'Label_0', style=wx.ALIGN_CENTER)
		static_text.SetForegroundColour('red')  
		wx_font = wx.Font(18, wx.DECORATIVE, wx.ITALIC, wx.BOLD)
		static_text.SetFont(wx_font)
		text_sizer.Add(static_text, 0, wx.ALIGN_LEFT)	
		input_text = wx.TextCtrl(self, -1, 'input_0', size=(400, -1))
		input_text.SetInsertionPoint(0)
		text_sizer.Add(input_text, 0, wx.ALIGN_LEFT)
		self.sizer.Add(text_sizer, 0, wx.ALIGN_LEFT)	
		"""


def show_stave_config (self, e, button_num):
	print "show stave_config"
	
	frame = stave_config(None, title = "Stave_config", orig_path = self.orig_path, call_button = self.step_button_list[button_num])
	frame.Show()
	frame.Bind(wx.EVT_CLOSE, frame.destroy)


"""
if __name__ == '__main__':
	root = wx.App()
	frame = stave_config(None, title = "Stave_config", orig_path = os.getcwd())
	frame.Show()
	root.MainLoop()
"""
