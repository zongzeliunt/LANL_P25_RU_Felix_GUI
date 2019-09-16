import wx

def print_warning(self):
	print "warning"

def OnExit(self,e):
	self.Close(True)

def OnSelectAll(self, event):
	if (event.GetKeyCode() == 65 and event.ControlDown()):
		self.area_text.SelectAll()
	
def OnButton (self, e):
	dlg = wx.MessageDialog(self, "A small text editor.", "About Sample Editor", wx.OK)
	if dlg.ShowModal() == wx.ID_OK:
		print self.area_text.GetValue()
		dlg.Destroy()

def print_page_0 (self):
	print "this is page_0"
	os.system("python ./page_0.py")


