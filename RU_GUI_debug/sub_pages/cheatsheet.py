import wx
import os

class origcheatsheet(wx.Frame):
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
		filename = "origcheatsheet.txt"
		dirname = self.orig_path + "/notes"
		f = open(os.path.join(dirname, filename), 'r')
		self.text_box.SetValue(f.read())
		f.close()

	def destroy(self, e):
		self.Destroy()

class cheatsheet(wx.Frame):
	def __init__(self, parent, title, step_commands):
		self.dirname = ''
		wx.Frame.__init__(self, parent, title = title, size = (800, 600))
		
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.text_box = wx.TextCtrl(self, style = wx.TE_MULTILINE)
		self.step_commands = step_commands
		
		self.OnOpen()
		
		self.sizer.Add(self.text_box, 1, wx.EXPAND)    
		self.Bind(wx.EVT_CLOSE, self.destroy)

	def OnOpen(self):
		total_line = ""
		command_count = 0
		for command in self.step_commands:
			title = command[0]
			path = command[1]
			exe_command = command[2]
			explain = command[3]
			mode = command[4]
			total_line += "Step " + str(command_count) + " : " + title + "\n"
			total_line += "	Execute path is: " + path + "\n"
			total_line += "	Execute command is: " + exe_command + "\n"
			total_line += "	User explain is: " + explain + "\n"
			if mode == 0:
				total_line += "	This is executing Linux command line command.\n"
			else:
				total_line += "	This step is calling Python internal function.\n"
			total_line += "\n"
			command_count += 1


		self.text_box.SetValue(total_line )

	def destroy(self, e):
		self.Destroy()

def showorigcheatsheet (self, e):
	frame = origcheatsheet(None, title = "origcheatsheet", orig_path = self.orig_path)
	frame.Show()

def showcheatsheet (self, e, step_commands):
	frame = cheatsheet(None, title = "cheatsheet", step_commands = step_commands)
	frame.Show()

if __name__ == '__main__':
	root = wx.App()
	frame = cheatsheet(None, title = "Cheatsheet", orig_path = os.getcwd())
	frame.Show()
	root.MainLoop()
