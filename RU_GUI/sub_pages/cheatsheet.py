import wx
import os

class cheatsheet(wx.Frame):
	def __init__(self, parent, title, orig_path):
		self.dirname = ''
		wx.Frame.__init__(self, parent, title = title, size = (800, 600))
		
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.text_box = wx.TextCtrl(self, style = wx.TE_MULTILINE)
		self.orig_path = orig_path
		
		self.OnOpen()
		
		self.sizer.Add(self.text_box, 1, wx.EXPAND)    
		self.Bind(wx.EVT_CLOSE, self.destroy)

	def OnOpen(self):
		filename = "cheatsheet.txt"
		dirname = self.orig_path + "/notes"
		f = open(os.path.join(dirname, filename), 'r')
		self.text_box.SetValue(f.read())
		f.close()

	def destroy(self, e):
		print "page close"
		self.Destroy()

def showcheatsheet (self, e):
	print "show cheat sheet"
	frame = cheatsheet(None, title = "cheatsheet", orig_path = self.orig_path)
	frame.Show()


if __name__ == '__main__':
	root = wx.App()
	frame = cheatsheet(None, title = "Cheatsheet", orig_path = os.getcwd())
	frame.Show()
	root.MainLoop()
