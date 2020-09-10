from appJar import gui
import tkinter
import os

settings_filename = "patcher_settings.ini"
byte_filename = "BYTE_LOCATIONS.ini"
ufo_filename = "Ufo_sh2.exe"
ufopaedia_filename = "entries.txt"
settings = {"byte_location_file":"", "ufo_tts_exe":"", "ufopaedia_text":""}
game_values = {} # {"GROUP_NAME":[[ADDRESS,VALUE,DEFAULT,"PARAMETER_NAME","COMMENTS",LENGTH],[]...]}
active_group = [False]

#####################################################################
############### FILE LOGIC ##########################################
#####################################################################

def load_locations():
	game_values.clear()
	failed_reads = 0
	if not os.path.exists(settings["byte_location_file"]):
		return "No file!"
	lines = 0
	valid_lines = 0
	with open(settings["byte_location_file"]) as file:
		for line in file:
			lines += 1
			if line.count(" - ") == 4:
				valid_lines += 1
				data = line.rstrip("\n").split(" - ")
				#line format is address - number of bytes - group name - parameter name|comments - default value
				try:
					data[0] = int(data[0],16)
					data[4] = int(data[4])
					data[1] = int(data[1])
					if not data[2] in game_values:
						game_values[data[2]] = []
					name = data[3].split("|")
					if len(name) == 1:
						name.append("")
					game_values[data[2]].append([data[0], -1, data[4], name[0], name[1], data[1]])
				except:
					failed_reads+=1
	return failed_reads

def initialize_settings():
	if load_settings() == "No file!":
		generate_settings()
		save_settings()

def load_settings():
	if os.path.exists(settings_filename):
		with open(settings_filename) as file:
			for line in file:
				if '=' in line:
					split_line = line.rstrip('\n').split('=')
					if split_line[0] in settings:
						settings[split_line[0]] = split_line[1]
	else:
		return "No file!"

def generate_settings():
	search = [byte_filename,ufo_filename,ufopaedia_filename]
	search_files(search,50)
	print(search[0][0])
	if search[0][0] == '.':
		settings["byte_location_file"] = os.path.realpath(search[0])
	if search[1][0] == '.':
		settings["ufo_tts_exe"] = os.path.realpath(search[1])
	if search[2][0] == '.':
		settings["ufopaedia_text"] = os.path.realpath(search[2])
	elif os.path.exists(settings["ufo_tts_exe"]):
		p = os.path.dirname(settings["ufo_tts_exe"])
		p = os.path.join(p,"ufopaedia",ufopaedia_filename)
		if os.path.exists(p):
			settings["ufopaedia_text"] = os.path.realpath(p)

def save_settings():
	try:
		with open(settings_filename, "w+") as file:
			for key in settings:
				file.write(key+'='+settings[key]+'\n')
	except:
		return

def search_files(list, depth):
	search = list.copy()
	walker = os.walk('..')
	i = 0;
	while len(search) > 0:
		i+=1
		root, dirs, files = next(walker)
		if root.count("\\") > depth:
			break
		for name in files:
			if name in search:
				search.remove(name)
				list[list.index(name)] = os.path.join(root,name)

def patch_values():
	for group in game_values:
		errors = patch_file(settings["ufo_tts_exe"],game_values[group])
		if errors:
			print("{} patch errors occured.".format(errors))

def patch_file(filename, array):
	failed_writes = []
	with open(filename, 'rb+') as file:
		for entry in array:
			try:
				file.seek(entry[0], 0)
				file.write(entry[1].to_bytes(entry[5],'little'))
			except:
				failed_writes.append(entry)
	return failed_writes

def load_values():
	for group in game_values:
		errors = load_file(settings["ufo_tts_exe"],game_values[group])
		if errors:
			print("")
			print("{} read errors occured.".format(errors))

def load_file(filename, array):
	failed_reads = []
	with open(filename, 'rb') as file:
		for entry in array:
			try:
				file.seek(entry[0], 0)
				entry[1] = int.from_bytes(file.read(entry[5]),'little')
			except:
				failed_reads.append(entry)
	return failed_reads

def set_to_default():
	for group in game_values:
		for values in game_values[group]:
			values[1] = values[2]


#####################################################################
################ INTERFACE ##########################################
#####################################################################

initialize_settings()
print(load_locations())
try:
	load_values()
except:
	pass
def placeholder(p):
	print(p)

def toolbar_manager(toolbar):
	if toolbar == "Set to Default":
		set_to_default()
		display_values("GroupList")
	if toolbar == "Load from EXE":
		load_values()
		display_values("GroupList")
	if toolbar == "Save to EXE":
		patch_values()

def update_values(entry):
	value = app.getEntry(entry)
	if value:
		for values in game_values[active_group[0]]:
			if values[3] == entry:
				values[1] = int(value)

def display_values(list):
	name = app.getListBox(list)[0]
	if name in game_values:
		if active_group[0]:
			for values in game_values[active_group[0]]:
				app.removeLabelFrame(values[3]+"_Label")
		active_group[0] = name
		
		app.setSticky("NEWS")
		app.setStretch("both")
		app.openScrollPane("Values")
		for values in game_values[name]:
			with app.labelFrame(values[3]+"_Label", label=values[3]):
				app.addNumericEntry(values[3])
				app.setEntry(values[3], "{}".format(values[1]), callFunction = False)
				app.setEntryChangeFunction(values[3],update_values)
				if values[4]:
					app.addLabel(values[4])
		app.stopScrollPane()

with gui("UFO TTS Editor Beta") as app:
	app.setIcon("Ico.ico")
	app.setSize(640,480)
	tools = ["Settings", "Set to Default", "Load from EXE", "Save to EXE", "Import File", "Export File"]
	app.addToolbar(tools,toolbar_manager)
	
	for i in ["Settings","Import File","Export File"]:
		app.setToolbarButtonDisabled(i)
	
	app.setSticky("NEWS")
	app.setStretch("both")
	with app.panedFrame("Left"):
		with app.labelFrame("Groups", label = "Select an item to edit", sticky = "news"):
				app.addListBox("GroupList",game_values)
				app.setListBoxGroup("GroupList",group=True)
				app.setListBoxChangeFunction("GroupList",display_values)
		with app.panedFrame("Right"):
			with app.scrollPane("Values"):
				app.addLabel(" ")