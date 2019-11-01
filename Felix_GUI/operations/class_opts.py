import wx
import function
import os
import sys
sys.path.append('sub_pages')
#sys.path.append('sub_pages')
import subprocess
import time



import cheatsheet
import stave_config 
import power_control 




HORI = 600 #horizontal
VERT = 100 #vertical
#textbox_style = (wx.TE_MULTILINE | wx.TE_AUTO_SCROLL)
textbox_style = (wx.TE_MULTILINE | wx.HSCROLL)
buttom_style = (wx.TE_MULTILINE)
#(wx.TE_MULTILINE | wx.TE_AUTO_SCROLL | wx.TE_DONTWRAP)



def declare_overall_box (self):
#{{{
	#self.box_sizer = wx.BoxSizer(wx.HORIZONTAL)
	self.box_sizer = wx.BoxSizer(wx.VERTICAL)
	#self.box_sizer = wx.WrapSizer()
	self.SetAutoLayout(True)
	self.SetSizer(self.box_sizer)
#}}}


def import_outside_functions(self):
#{{{
	#all below are functions, not menu buttons.
	#but these functions are most related with GUI buttons or text box status change.

	self.OnExit 		=	function.OnExit
	self.OnSelectAll 	= 	function.OnSelectAll
	self.OnButton 		= 	function.OnButton
	self.showorigcheatsheet = 	cheatsheet.showorigcheatsheet
	self.showcheatsheet = cheatsheet.showcheatsheet
	self.show_stave_config = 	stave_config.show_stave_config
	self.show_power_control = 	power_control.show_power_control
	
	#self.change_combobox_command = change_combobox_command
	#self.exe_combobox_command = exe_combobox_command
	
	self.exe_buttonbox_command = exe_buttonbox_command

	#self. = function.
#}}}


def generate_menu_bar(self):
#{{{
	self.CreateStatusBar() #status bar at the bottom 
	filemenu = wx.Menu() #menu on the top
	#menu_page_0 = filemenu.Append(0, "&Page0", "Open Page 0")
#	menu_page_0 = filemenu.Append(wx.ID_ANY, "&Page0", "Open Page 0")
	#menu_page_1 = filemenu.Append(1, "&Page1", "Open Page 1")
	menuExit 	= filemenu.Append(wx.ID_EXIT, "E&xit", " Terminate the program")

	# menu bar will include menu
	menuBar = wx.MenuBar()
	menuBar.Append(filemenu, "&Operations")

	
	cheatsheetmenu = wx.Menu()
	origcheatsheetpage = cheatsheetmenu.Append(2, "&Original cheatsheet", "View original cheatsheet")
	cheatsheetpage = cheatsheetmenu.Append(3, "&cheatsheet", "View cheatsheet")

	menuBar.Append(cheatsheetmenu, "&Cheatsheet")


	self.SetMenuBar(menuBar)

	#self.Bind(wx.EVT_MENU, self.print_page_0, menu_page_0)
		#keep for debug
	
	self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
	self.Bind(wx.EVT_MENU, self.showorigcheatsheet, origcheatsheetpage)
	#this is a way use step_commands as function argument
		#in fact, self.step_commands is a global variable, I can access it in showcheatsheet function
		#however, maybe in the future, I need to make class's inline function pointer to have input argument
		#so keep this way for future reference
	self.Bind(wx.EVT_MENU, lambda evt = origcheatsheetpage.GetId():self.showorigcheatsheet(evt, self.step_commands), cheatsheetpage)
	self.Bind(wx.EVT_MENU, lambda evt = cheatsheetpage.GetId():self.showcheatsheet(evt, self.step_commands), cheatsheetpage)
#}}}

def add_step_button_box(self):
#{{{
	button_box = wx.BoxSizer(wx.HORIZONTAL)

	self.step_button_list = []
	for i in range (len(self.step_commands)):
		com = self.step_commands[i]
		title = com[0]
		step_exe_button = wx.Button(self, i, title, size=(200, 50), style=wx.TE_MULTILINE )
		self.step_button_list.append(step_exe_button)	
		self.step_button_list[i].SetBackgroundColour('white')
		button_box.Add(self.step_button_list[i], 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5  )
	
		self.Bind(wx.EVT_BUTTON, lambda evt,i=self.step_button_list[i].GetId():self.exe_buttonbox_command(evt, i), self.step_button_list[i])
		if (i + 1) % 3 == 0:
			self.box_sizer.Add(button_box, 0, wx.ALIGN_LEFT)
			button_box = wx.BoxSizer(wx.HORIZONTAL)
	
	if button_box != "":
		self.box_sizer.Add(button_box, 0, wx.ALIGN_LEFT)
#}}}

def exe_buttonbox_command(self, event, button_num):
#{{{
	com = self.step_commands[button_num]
	title = com [0]
	path = com [1] 
	cmd = com[2]
	explain = com[3]
	exe_mode = com[4]

	self.path_text.SetValue(path)
	self.command_text.SetValue(cmd)
	self.explain_text.SetValue(explain)
	clicked_button = self.step_button_list[button_num]

	
	if exe_mode == 0:
		external_command_exec(self, button_num)
	else:
		path = self.path_text.GetValue()
		command = self.command_text.GetValue()
		exec(command + "(event, " + str(button_num) + "," + path + ")")	
#}}}

def external_command_exec (self, button_num):
	path = self.path_text.GetValue()
	command = self.command_text.GetValue()
	cmd = "cd " + path + "; " + command
	
	sp = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

	stdout_list = sp.stdout.readlines()
	stderr_list = sp.stderr.readlines()

	stdout_tmp = ""	
	for line in stdout_list:
		stdout_tmp += str(line)
	for line in stderr_list:
		stdout_tmp += str(line)

	time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
	if stderr_list == []:
		self.status_list.append(time_format + " " + "STEP " + str(button_num) + " exec success")
		self.step_button_list[button_num].SetBackgroundColour('green')
	else:
		self.status_list.append(time_format + " " + "STEP " + str(button_num) + " exec fail")
		self.step_button_list[button_num].SetBackgroundColour('red')
	
	if len(self.status_list) == 10:
		del(self.status_list[0])

	status_tmp = ""
	for status in self.status_list:
		status_tmp += status + "\n"

	self.status_text.SetValue(status_tmp)
	self.stdout_text.SetValue(stdout_tmp)

	
def add_steppathbox (self):
#{{{
	pathbox=wx.BoxSizer(wx.HORIZONTAL)

	statictext=wx.StaticText(self,label='Step Path:')
	pathbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

	self.path_text = wx.TextCtrl(self, -1, 'path', size=(HORI, -1), style = textbox_style)
	pathbox.Add(self.path_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)	
	self.box_sizer.Add(pathbox, 0, wx.ALIGN_LEFT)	
#}}}

def add_stepcommandbox (self):
#{{{
	commandbox=wx.BoxSizer(wx.HORIZONTAL)

	statictext=wx.StaticText(self,label='Step Command:')
	commandbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

	self.command_text = wx.TextCtrl(self, -1, 'command', size=(HORI, -1), style=textbox_style)
	commandbox.Add(self.command_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)	
	self.box_sizer.Add(commandbox, 0, wx.ALIGN_LEFT)	
#}}}

def add_stepexplainbox (self):
#{{{
	explainbox=wx.BoxSizer(wx.HORIZONTAL)

	statictext=wx.StaticText(self,label='Step Explain:')
	explainbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

	self.explain_text = wx.TextCtrl(self, -1, 'explain', size=(HORI, -1), style=textbox_style)
	explainbox.Add(self.explain_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)	
	self.box_sizer.Add(explainbox, 0, wx.ALIGN_LEFT)	
#}}}

def add_stepstatusbox (self):
#{{{
	statusbox=wx.BoxSizer(wx.HORIZONTAL)

	statictext=wx.StaticText(self,label='Step Status:')
	statusbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

	self.status_text = wx.TextCtrl(self, -1, 'status', size=(HORI, VERT), style=textbox_style)
	statusbox.Add(self.status_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)	
	self.box_sizer.Add(statusbox, 0, wx.ALIGN_LEFT)	
#}}}

def add_stdoutbox (self):
#{{{
	stdoutbox=wx.BoxSizer(wx.HORIZONTAL)

	statictext=wx.StaticText(self,label='Linux Stdout:')
	stdoutbox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

	self.stdout_text = wx.TextCtrl(self, -1, 'stdout', size=(HORI, VERT), style=textbox_style)
	stdoutbox.Add(self.stdout_text, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)	
	self.box_sizer.Add(stdoutbox, 0, wx.ALIGN_LEFT)	
#}}}














#combobox, just keep it
def add_stepcombobox (self):
#{{{
	combobox=wx.BoxSizer(wx.HORIZONTAL)

	statictext=wx.StaticText(self,label='Select step:')
	combobox.Add(statictext, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)

	list0=[]
	for i in range (len(self.step_commands)):
		com = self.step_commands[i]
		title = com[0]
		step_name = str(i)
		list0.append(step_name)		

	self.ch1=wx.ComboBox(self, -1, value='Steps', choices=list0, style=wx.CB_SORT)
	combobox.Add(self.ch1, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5)
	
	step_exe_button = wx.Button(self, -1, "Execute step command" )
	combobox.Add(step_exe_button, 1, flag=wx.LEFT |wx.RIGHT|wx.FIXED_MINSIZE,border=5 )
	self.box_sizer.Add(combobox, 0, wx.ALIGN_LEFT)
	self.Bind(wx.EVT_COMBOBOX, self.change_combobox_command, self.ch1)
	self.Bind(wx.EVT_BUTTON, self.exe_combobox_command, step_exe_button)
#}}}

def change_combobox_command(self, event):
#{{{
	combo_box_value = int(self.ch1.GetValue())
	
	self.path_text.SetValue(self.step_commands[combo_box_value][1])
	self.command_text.SetValue(self.step_commands[combo_box_value][2])
	self.explain_text.SetValue(self.step_commands[combo_box_value][3])

	#print("select{0}".format(event.GetString()))
#}}}

def exe_combobox_command(self, event):
#{{{
	path = self.path_text.GetValue()
	command = self.command_text.GetValue()
	step = self.ch1.GetValue()

	#for python script debug, use exec
	#exec(command)

	#for system execute
	"""
	os.chdir(path)
	
	print os.getcwd()
	
	result = os.system(command)
	print result
	
	if result == 0:
		self.status_text.SetValue("step " + str(step) + " exec success")
	else:
		self.status_text.SetValue("step " + str(step) + " exec fail")
	
	"""
	cmd = "cd " + path + "; " + command
	
	sp = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

	stdout_list = sp.stdout.readlines()
	stderr_list = sp.stderr.readlines()

	stdout_tmp = ""	
	for line in stdout_list:
		stdout_tmp += line
	for line in stderr_list:
		stdout_tmp += line

	time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
	if stderr_list == []:
		self.status_list.append(time_format + " " + "STEP " + str(step) + " exec success")
	else:
		self.status_list.append(time_format + " " + "STEP " + str(step) + " exec fail")
	
	if len(self.status_list) == 10:
		del(self.status_list[0])

	status_tmp = ""
	for status in self.status_list:
		status_tmp += status + "\n"

	
	self.status_text.SetValue(status_tmp)
	self.stdout_text.SetValue(stdout_tmp)
#}}}

#keep for future use
def declare_input_frame (self):
	########## Label ##########


	text_sizer = wx.BoxSizer(wx.HORIZONTAL)
	static_text = wx.StaticText(self, -1, 'Label_0', style=wx.ALIGN_CENTER)
	static_text.SetForegroundColour('red')  
	wx_font = wx.Font(18, wx.DECORATIVE, wx.ITALIC, wx.BOLD)
	static_text.SetFont(wx_font)
	text_sizer.Add(static_text, 0, wx.ALIGN_LEFT)	
	input_text = wx.TextCtrl(self, -1, 'input_0', size=(HORI, -1))
	input_text.SetInsertionPoint(0)
	text_sizer.Add(input_text, 0, wx.ALIGN_LEFT)
	self.box_sizer.Add(text_sizer, 0, wx.ALIGN_LEFT)	
	
	text_sizer = wx.BoxSizer(wx.HORIZONTAL)
	static_text_1 = wx.StaticText(self, -1, 'Label_1', style=wx.ALIGN_CENTER)
	static_text_1.SetForegroundColour('red')  
	wx_font = wx.Font(18, wx.DECORATIVE, wx.ITALIC, wx.BOLD)
	static_text_1.SetFont(wx_font)
	text_sizer.Add(static_text_1, 0, wx.ALIGN_LEFT)
	input_text_1 = wx.TextCtrl(self, -1, 'input_1', size=(HORI, -1))
	input_text_1.SetInsertionPoint(0)
	text_sizer.Add(input_text_1, 0, wx.ALIGN_LEFT)
	self.box_sizer.Add(text_sizer, 0, wx.ALIGN_LEFT)	
	





	self.area_text = wx.TextCtrl(self, -1, "", size=(HORI, 100), style=(wx.TE_MULTILINE | wx.TE_AUTO_SCROLL | wx.TE_DONTWRAP))
	self.area_text.SetInsertionPoint(0)
	self.area_text.Bind(wx.EVT_KEY_UP, self.OnSelectAll)
	self.box_sizer.Add(self.area_text)
	
	
	
	
	
	"""
	self.rich_text = wx.TextCtrl(self, -1, u'rich', size=(200, 100),
	                             style=(wx.TE_MULTILINE | wx.TE_AUTO_SCROLL | wx.TE_DONTWRAP | wx.TE_RICH2))
	self.rich_text.SetInsertionPoint(0)
	f = wx.Font(18, wx.ROMAN, wx.ITALIC, wx.BOLD, True)  
	self.rich_text.SetStyle(0, self.rich_text.GetLastPosition(), wx.TextAttr("red", "green", f))
	self.box_sizer.Add(self.rich_text)
	"""


def declare_button (self):
	#button
	#self.control = wx.TextCtrl(self, style = wx.TE_MULTILINE)
	self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
	self.buttons = []

	for i in range (0, 2):
		self.buttons.append(wx.Button(self, -1, "Button &" + str(i)))
		self.sizer2.Add(self.buttons[i], 1, wx.SHAPED)    
	
	self.sizer = wx.BoxSizer(wx.VERTICAL)
	#self.sizer.Add(self.control, 1, wx.EXPAND)    	
	self.sizer.Add(self.sizer2, 0, wx.GROW)    
	

	self.box_sizer.Add(self.sizer)

	self.Bind(wx.EVT_BUTTON, self.OnButton, self.buttons[0])
	
	self.Bind(wx.EVT_BUTTON, function.print_warning, self.buttons[1])
