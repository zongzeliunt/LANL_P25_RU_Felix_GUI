import wx
import os

class cheatsheet(wx.Frame):
	def __init__(self, parent, title):
		self.dirname = ''
		wx.Frame.__init__(self, parent, title = title, size = (800, 600))
		
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.text_box = wx.TextCtrl(self, style = wx.TE_MULTILINE)
		
		
		self.OnOpen()
		
		self.sizer.Add(self.text_box, 1, wx.EXPAND)    


	def OnOpen(self):
		filename = "cheatsheet.txt"
		dirname = "notes"
		f = open(os.path.join(dirname, filename), 'r')
		self.text_box.SetValue(f.read())
		f.close()




def showcheatsheet (self, e):
	print "show cheat sheet"
	
	frame = cheatsheet(None, title = "cheatsheet")
	frame.Show()


