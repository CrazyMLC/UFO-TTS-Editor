from appJar import gui
import time
import os

settings_filename = "patcher_settings.ini"
byte_filename = "BYTE_LOCATIONS.ini"
ufo_filename = "Ufo_sh2.exe"
ufopaedia_filename = "entries.txt"
filenames = [byte_filename, ufo_filename, ufopaedia_filename]
settings = {"byte_location_file":"", "ufo_tts_exe":"", "ufopaedia_text":""}
exe_values = {}#{"GROUP_NAME":{ADDRESS:class Value, ADDRESS:class Value,...{}
new_values = {}#{ADDRESS:["GROUP_NAME",VALUE],...}
active_group = False
version = "0.8"


def safeInt(string, base, error):
	try:
		return int(string,base)
	except:
		print(error)
		return None

class Value:#Container for byte location entries
	def __init__(self, address=None, byte_length=None, name=None, default=None, val=-1, comm="", copy = None):
		if copy == None:
			if isinstance(address, str):
				address = safeInt(address, 16, "Invalid address on parameter "+name)
			if isinstance(val, str):
				val = safeInt(val, 10, "Invalid value on parameter "+name)
			if isinstance(default, str):
				default = safeInt(default, 10, "Invalid default value on parameter "+name)
			if isinstance(byte_length, str):
				byte_length = safeInt(byte_length, 10, "Invalid byte length on parameter "+name)
			if "|" in name:
				split = name.split("|")
				name = split[0]
				comm = split[1]
			self.valid = False if None in [address, default, byte_length, val] else True
			self.address = address
			self.byte_length = byte_length
			self.name = name
			self.default = default
			self.value = val
			self.comment = comm
		else:
			self.valid = copy.valid
			self.address = copy.address
			self.byte_length = copy.byte_length
			self.name = copy.name
			self.default = copy.default
			self.value = copy.value
			self.comment = copy.comment
		

#####################################################################
############### FILE LOGIC ##########################################
#####################################################################

def load_locations():#Load the byte location file
	exe_values.clear()
	new_values.clear()
	failed_reads = 0
	if not os.path.exists(settings["byte_location_file"]):
		print("Location file not found!")
		return
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
					val = Value(address = data[0], byte_length = data[1], name = data[3], default = data[4])
					if val.valid:
						group_name = data[2]
						if not group_name in exe_values:
							exe_values[group_name] = {}
						exe_values[group_name][val.address] = val
					else:
						failed_reads+=1
				except:
					failed_reads+=1
	if valid_lines == 0:
		print("\nNo valid data found in byte location file! Incompatible or empty?\n")
	if failed_reads > 0:
		print("\n{} byte location file entries failed.\n".format(failed_reads))

def initialize_settings():#Manage the loading, generation, and saving of settings
	if load_settings() == "No file!":
		generate_settings()
		if not verify_exe():
			print("Couldn't find valid EXE!")
		save_settings()

def load_settings():#Load settings from a found settings file
	if os.path.exists(settings_filename):
		with open(settings_filename) as file:
			for line in file:
				if '=' in line:
					split_line = line.rstrip('\n').split('=')
					if split_line[0] in settings:
						settings[split_line[0]] = split_line[1]
	else:
		print("Unable to find settings file.")
		return "No file!"

def generate_settings():#Initiate the search for files, and assign settings
	search = filenames.copy()
	search_files(search,5)
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

def save_settings():#Create/overwrite settings file
	try:
		with open(settings_filename, "w+") as file:
			for key in settings:
				file.write(key+'='+settings[key]+'\n')
	except:
		print("Saving settings file failed!")
		return False
	return True

def verify_exe(filepath = None):#Check that the exe being modified is UFO TTS
	if filepath == None:
		filepath = settings["ufo_tts_exe"]
	if not os.path.exists(filepath):
		return False
	with open(filepath,'rb') as file:
		try:
			file.seek(1308380,0)
			return file.read(3) == b'bad'
		except:
			return False

def search_files(list, depth):#Take in a list of filenames, try to find them nearby, and return them through the list
	search = list.copy()
	walker = os.walk('..')
	while search:
		root, dirs, files = next(walker)
		if root.count(os.path.sep) > depth:
			break
		for name in files:
			if name in search:
				search.remove(name)
				list[list.index(name)] = os.path.join(root,name)
	if search:
		print("\nUnable to find the following files:")
		for name in search:
			print(name)
		print("")
		

def save_to_exe():#Save new_values to EXE and exe_values
	if not os.path.exists(settings["ufo_tts_exe"]):
		print("EXE not found!")
		return False
	if not verify_exe():
		print("EXE is incompatible")
		return False
	failed_writes = []
	with open(settings["ufo_tts_exe"], 'rb+') as file:
		for address in list(new_values.keys()):
			try:
				new_val = new_values[address][1]
				group_name = new_values[address][0]
				entry = exe_values[group_name][address]
				try:
					file.seek(address, 0)
					file.write(new_val.to_bytes(entry.byte_length, 'little'))
					entry.value = new_val
					new_values.pop(address)
				except:
					failed_writes.append(entry.name)	
			except:
				print("\nNew values desynced? Can this even happen? {}, {}\n".format(address, new_values[address]))
	if failed_writes:
		print("\nFailed to write the following values to EXE:",failed_writes)
	return True

def load_from_exe():#Load exe_values from EXE
	if not os.path.exists(settings["ufo_tts_exe"]):
		print("EXE not found!")
		return False
	if not verify_exe():
		print("EXE is incompatible")
		return False
	if new_values:
		print("Error loading EXE, change list must be empty before loading from EXE! (Try restarting)")
		return False
	failed_reads = []
	with open(settings["ufo_tts_exe"], 'rb') as file:
		for group in exe_values:
			for address in exe_values[group]:
				entry = exe_values[group][address]
				try:
					file.seek(address, 0)
					entry.value = int.from_bytes(file.read(entry.byte_length),'little')
				except:
					failed_reads.append(entry.name)
	if failed_reads:
		print("\nFailed to read the following values from EXE:",failed_reads)
	return True

def set_to_default():#Set exe_values to default
	if new_values:
		print("Error resetting to default, change list must be empty before resetting! (Try restarting)")
		return False
	for group in exe_values:
		for address in exe_values[group]:
			entry = exe_values[group][address]
			if entry.value != entry.default:
				new_values[entry.address] = [group, entry.default]
	return True

def load_from_file(filepath):#Loading to new_values from a saved file
	loaded = {}
	failed = 0
	if not os.path.exists(filepath):
		print("File not found!")
		return False
	with open(filepath, 'r') as file:
		for line in file:
			if line[:2] == "0x":#It's only a valid load if the line starts with a hex address
				split = line.split()
				try:#Just in case the address isn't as valid as we thought, or the value isn't valid either...
					location = int(split[0], 16)
					value = int(split[-1].replace(",",""))
					loaded[location] = value
				except:
					failed+=1
	if loaded:#If we loaded something, let's go ahead and update the change dictionary with the information
		for address in list(loaded.keys()):
			for group in exe_values:
				if address in exe_values[group]:
					if loaded[address] != exe_values[group][address].value:
						new_values[address] = [group, loaded.pop(address)]
						break
					elif address in new_values:
						new_values.pop(address)
						loaded.pop(address)
						
	print("Number of failed reads: {}\nNumber of unapplied changes: {}".format(failed, len(loaded)))
	if loaded:
		print("There were unapplied changes! Maybe your byte location file is out of date?")
	return True
	
def save_to_file(filepath):#Save the game configuration to a file
	file_contents = {}
	#Let's assemble a list of values that would need to change to patch an original EXE to the current state...
	for group in exe_values:
		file_contents[group] = {}
		for address in exe_values[group]:
			entry = exe_values[group][address]
			#We're looking for values that differ from the default
			if address in new_values:#If there's a changed value, let's check that instead
				if new_values[address][1] != entry.default:#But if it's changed back to default, let's skip the address entirely
					file_contents[group][address] = Value(copy = entry)
					file_contents[group][address].value = new_values[address][1]
			elif entry.value != entry.default:
				file_contents[group][address] = Value(copy = entry)
	#Now that we've collected all the data we need to save, let's open the file and get started
	#We'll assume the function that called us already checked for permission to overwrite any files...
	with open(filepath, "w") as file:
		for group in file_contents:
			if file_contents[group]:
				file.write(group.center(40,"-")+"\n")#We don't use this when loading, but let's try to make it human readable
				for address in file_contents[group]:
					entry = file_contents[group][address]
					address_string = "0x"+format(address, 'x').rjust(8,"0")
					file.write(address_string+"\t"+entry.name+": {:,} -> {:,}\n".format(entry.default,entry.value))#Same story here
					#All that matters is that the address is at the start, and the value at the end
				file.write("\n")
		file.write("\n\nWritten with UFO TTS Editor version {}. Check the Github page for the latest version.".format(version))

def current_is_default():
	for group in exe_values:
		for address in exe_values[group]:
			entry = exe_values[group][address]
			if address in new_values:
				val = new_values[address][1]
			else:
				val = entry.value
			if val != entry.default:
				return False
	return True

def groups_with_changes():
	result = []
	for address in new_values:
		if not new_values[address][0] in result:
			result.append(new_values[address][0])
	return result


#####################################################################
################ INTERFACE ##########################################
#####################################################################

initialize_settings()
load_locations()
load_from_exe()

def check_stop():
	if new_values:
		return app.okBox("Confirm exit", "Your changes will be lost if you quit now.\n\nIs that okay?")
	return True

recommended_defaulting = 0
time_window = 5
saved_filepath = None
def toolbar_manager(toolbar):
	global recommended_defaulting
	global time_window
	global saved_filepath
	
	if toolbar == "Set to Default":#If we just recently suggested that the user default, don't pester them with another popup.
		if not new_values or (time.time() - recommended_defaulting) < time_window or app.okBox("Confirm losing changes","If you set to default now, you'll lose your unsaved changes."):
			new_values.clear()
			set_to_default()
			display_values("GroupList")
	elif toolbar == "Load from EXE":
		if not new_values or app.okBox("Confirm losing changes","If you load from the EXE now, you'll lose your unsaved changes."):
			new_values.clear()
			load_from_exe()
			display_values("GroupList")
	elif toolbar == "Save to EXE":
		save_to_exe()
		display_values("GroupList")
	elif toolbar == "Import File":
		filepath = app.openBox("File to import", dirName=saved_filepath)
		if filepath:
			if current_is_default() or app.okBox("Confirm file import", "Some of your current changes could be lost during the import process.\nIt's recommended to set to default before importing a file.\n\nDo you wish to continue anyway?"):
				load_from_file(filepath)
				saved_filepath = None
				display_values("GroupList")
			else:
				recommended_defaulting = time.time()#We'll not ask them if they want to default for a couple seconds...
				saved_filepath = filepath#And we'll make them automatically come back to where they left off.
	elif toolbar == "Export File":
		filepath = app.saveBox("File to export")
		save_to_file(filepath)
	elif toolbar == "Settings":
		for setting in ["byte_location_file", "ufo_tts_exe"]:
			app.setEntry(setting, settings[setting])
		app.disableButton("Apply")
		app.showSubWindow(toolbar)

def update_values(name):
	global active_group
	value = app.getEntry(name)
	if value:
		for address in exe_values[active_group]:
			entry = exe_values[active_group][address]
			if entry.name == name:
				if int(value) == entry.value:
					new_values.pop(address, None)
					app.setEntryBg(name, "white")
				else:
					new_values[address] = [active_group, int(value)]
					app.setEntryBg(name, "light yellow")
		update_listbox_colors("GroupList")

def display_values(list):
	global active_group
	try:
		group = app.getListBox(list)[0]
	except:
		return
	if group in exe_values:
		if active_group:
			for address in exe_values[active_group]:
				entry = exe_values[active_group][address]
				app.removeLabelFrame(entry.name+"_Label")
		active_group = group
		app.setSticky("NEWS")
		app.setStretch("both")
		app.openScrollPane("Values")
		for address in exe_values[active_group]:
			entry = exe_values[active_group][address]
			with app.labelFrame(entry.name+"_Label", label=entry.name):
				app.addNumericEntry(entry.name)
				if address in new_values:
					val = new_values[address][1]
					app.setEntryBg(entry.name, "light yellow")
				else:
					val = entry.value
					app.setEntryBg(entry.name, "white")
				app.setEntry(entry.name, "{}".format(val), callFunction = False)
				app.setEntryChangeFunction(entry.name,update_values)
				if entry.comment:
					app.addLabel(entry.comment)
		app.stopScrollPane()
		update_listbox_colors(list)

def update_listbox_colors(list):
	changed_groups = groups_with_changes()
	items = app.getAllListItems(list)
	for item in items:
		if item in changed_groups:
			app.setListItemBg(list,item,"light yellow")
		else:
			app.setListItemBg(list,item,"white")
	if changed_groups:
		app.setStatusbar("{} groups with unsaved changes.".format(len(changed_groups)),0)
		app.setStatusbarBg("light yellow",0)
	else:
		app.setStatusbar("No groups with unsaved changes.",0)
		app.setStatusbarBg("white",0)

def settings_window_change(set):
	disable = True
	for setting in ["byte_location_file", "ufo_tts_exe"]:
		if app.getEntry(setting) != settings[setting]:
			disable = False
			app.setEntryBg(setting, "light yellow")
		else:
			app.setEntryBg(setting, "white")
	if disable:
		app.disableButton("Apply")
	else:
		app.enableButton("Apply")

def settings_buttons(btn):
	if btn == "Apply":
		changes = False
		byte_filepath = app.getEntry("byte_location_file")
		if byte_filepath != settings["byte_location_file"]:
			if not os.path.exists(byte_filepath):
				print("Invalid byte filepath!")
			else:
				settings["byte_location_file"] = byte_filepath
				load_locations()
				app.clearListBox("GroupList")
				app.updateListBox("GroupList", exe_values, select = True, callFunction = True)
				changes = True
		exe_filepath = app.getEntry("ufo_tts_exe")
		if exe_filepath != settings["ufo_tts_exe"]:
			if not os.path.exists(exe_filepath):
				print("Invalid ufo tts filepath!")
			elif verify_exe(exe_filepath):
				settings["ufo_tts_exe"] = exe_filepath
				changes = True
			else:
				print("EXE isn't compatible")
		if changes:
			new_values.clear()
			load_from_exe()
			display_values("GroupList")
			save_settings()
	app.hideSubWindow("Settings")

with gui("UFO TTS Editor v1.0") as app:
	app.setIcon("Ico.ico")
	app.setSize(640,480)
	app.setStopFunction(check_stop)
	tools = ["Settings", "Set to Default", "Load from EXE", "Save to EXE", "Import File", "Export File"]
	app.addToolbar(tools,toolbar_manager)
	app.setSticky("NEWS")
	app.setStretch("both")
	with app.panedFrame("Left"):
		with app.labelFrame("Groups", label = "Select an item to edit", sticky = "news"):
			app.addListBox("GroupList",exe_values)
			app.setListBoxGroup("GroupList",group=True)
			app.setListBoxChangeFunction("GroupList",display_values)
		with app.panedFrame("Right"):
			with app.scrollPane("Values"):
				app.addLabel(" ")
	app.selectListItemAtPos("GroupList",0)
	display_values("GroupList")
	app.addStatusbar(fields = 1)
	app.setStatusbar("No groups with unsaved changes.", 0)
	app.setStatusbarBg("white",0)
	
	with app.subWindow("Settings", modal = True):
		app.setResizable(False)
		app.setSticky("EW")
		app.setStretch("column")
		with app.labelFrame("Byte Location file", sticky = "news"):
			app.addOpenEntry("byte_location_file")
			app.setEntryChangeFunction("byte_location_file",settings_window_change)
		with app.labelFrame("UFO TTS Executable", sticky = "news"):
			app.addOpenEntry("ufo_tts_exe")
			app.setEntryChangeFunction("ufo_tts_exe",settings_window_change)
		app.addLabel("Any unsaved changes will be lost if you apply new settings.".center(120))
		app.addButtons(["Cancel","Apply"],settings_buttons)
		app.setButton("Cancel","Cancel".center(20))
		app.setButton("Apply","Apply".center(20))