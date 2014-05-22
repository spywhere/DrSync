import sublime
import sublime_plugin
import datetime
import os
import re
import threading
from tempfile import gettempdir
from .dropbox import *
from .thread_progress import *


USER_FOLDER = "User"
SYNC_SCHEMA = "/DrSync.drsync-data"
DRSYNC_SETTINGS = None


def get_settings(key, default=None):
	return DRSYNC_SETTINGS.get(key, default)

def plugin_loaded():
	global DRSYNC_SETTINGS
	DRSYNC_SETTINGS = sublime.load_settings("DrSync.sublime-settings")
	print("DrSync ready")


class DrsyncCommand(sublime_plugin.WindowCommand):
	APP_KEY = "<AppKey>"
	APP_SECRET = "<AppSecret>"

	def connect_fx(self, i, message, thread):
		msg = message
		if hasattr(thread, "message"):
			msg = thread.message
		return {"i": (i+1) % 3, "message": "%s %s" % (msg, "." * (i+1)), "delay": 300}

	def sync_fx(self, i, message, thread):
		direction = ">" if self.upload else "<"
		maxsize = 25
		percentage = int(maxsize*thread.percentage/100)
		loadbar = list(" " * (percentage-1))
		loadbar.append(direction)
		while len(loadbar) < maxsize:
			loadbar.append(" ")
		if not self.upload:
			loadbar.reverse()
		return {"i": (i+1) % maxsize, "message": "Syncing... [{0}] {1}%".format("".join(loadbar), thread.percentage), "delay": 100}

	def run(self):
		self.auth = DropboxAuth(self.APP_KEY, self.APP_SECRET)
		self.window.show_input_panel("Authorize Code:", "Please allow DrSync and get code from: "+self.auth.get_authorize_url(), self.on_code_entered, None, None)

	def on_code_entered(self, code):
		thread = AuthenticationThread(self.auth, code)
		thread.start()
		ThreadProgress(thread, "Connecting to Dropbox", self.on_authorized, self.on_authorized, self.connect_fx)

	def get_timestamp(self):
		months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
		dt = datetime.datetime.now()
		return "{0:d} {1} {2:d} {3:02d}:{4:02d}".format(dt.day, months[dt.month], dt.year, dt.hour, dt.minute)

	def get_paths(self):
		paths = {}
		paths["packages"] = sublime.packages_path()
		paths["packages_user"] = os.path.join(sublime.packages_path(), USER_FOLDER)
		paths["installed_packages"] = sublime.installed_packages_path()
		return paths

	def on_authorized(self, thread):
		if thread.result:
			self.client = thread.client
			self.sync_data = thread.sync_data
			self.paths = self.get_paths()
			if thread.sync_data is None:
				self.sync_to()
			else:
				self.window.show_quick_panel([["Sync from Dropbox", "Overwrite current data [" + thread.sync_data["last_sync"] + "]"], ["Sync to Dropbox", "Overwrite previously sync data [" + self.get_timestamp() + "]"]], self.on_sync_selection)
		else:
			sublime.error_message(thread.result_message)

	def on_sync_selection(self, index):
		if index < 0:
			return
		if index > 0:
			self.sync_to()
		else:
			self.sync_from()

	def match_regex(self, string, key):
		patterns = get_settings(key)
		for pattern in patterns:
			matches = re.match(pattern, string)
			if matches is not None and matches.start() == 0:
				return True
		return False

	def add_all(self, dir_path, subdir=True, folder_filter=None, file_filter=None, base_path=None):
		files = []
		for name in os.listdir(dir_path):
			pathname = os.path.join(dir_path, name)
			if subdir and os.path.isdir(pathname) and not self.match_regex(name, "exclude_folder_patterns") and (folder_filter is None or (folder_filter is not None and folder_filter(name))):
				if base_path is None:
					files += self.add_all(pathname, subdir, folder_filter, file_filter, dir_path)
				else:
					files += self.add_all(pathname, subdir, folder_filter, file_filter, base_path)
			elif os.path.isfile(pathname) and not self.match_regex(name, "exclude_file_patterns") and (file_filter is None or (file_filter is not None and file_filter(name))):
				if base_path is None:
					files.append([dir_path, pathname])
				else:
					files.append([base_path, pathname])
		return files

	def user_folder_exclude_filter(self, name):
		return name != USER_FOLDER

	def sync_from(self):
		thread = SyncGatherThread(self.paths, self.sync_data, self.client)
		thread.start()
		self.upload = False
		ThreadProgress(thread, "DrSync is verifying data", self.on_verified, self.on_verified, self.connect_fx)

	def on_verified(self, thread):
		if thread.result:
			sthread = SyncDownThread(self.sync_data, thread.file_list, self.client)
			sthread.start()
			self.upload = False
			ThreadProgress(sthread, "", self.on_sync_done, self.on_sync_done, self.sync_fx)
		else:
			sublime.error_message(thread.result_message)

	def sync_to(self):
		file_list = []

		settings = get_settings("synchronization_settings")
		if settings["installed_packages"]:
			file_list += self.add_all(dir_path=self.paths["installed_packages"])
		if settings["local_packages"]:
			file_list += self.add_all(dir_path=self.paths["packages"], folder_filter=self.user_folder_exclude_filter)
		if settings["user_directory"]:
			file_list += self.add_all(dir_path=self.paths["packages_user"])
		else:
			files = []
			if settings["package_control_preferences"]:
				files += ["Package Control.sublime-settings"]
			if settings["drsync_preferences"]:
				files += ["DrSync.sublime-settings"]
			if settings["sublime_preferences"]:
				files += ["Preferences.sublime-settings", "Default (Windows).sublime-keymap", "Default (OSX).sublime-keymap", "Default (Linux).sublime-keymap"]
			for filename in files:
				filepath = os.path.join(self.paths["packages_user"], filename)
				if os.path.exists(filepath):
					file_list.append([self.paths["packages_user"], filepath])

		data = {}
		data["settings"] = settings
		data["last_sync"] = self.get_timestamp()

		thread = SyncUpThread(data, file_list, self.client)
		thread.start()
		self.upload = True
		ThreadProgress(thread, "", self.on_sync_done, self.on_sync_done, self.sync_fx)

	def on_sync_done(self, thread):
		if thread.result:
			sublime.status_message("Data has been synchronized successfully")
		else:
			sublime.error_message(thread.result_message)

class AuthenticationThread(threading.Thread):
	def __init__(self, authenticator, authorize_code):
		self.authenticator = authenticator
		self.authorize_code = authorize_code
		threading.Thread.__init__(self)

	def run(self):
		try:
			self.access_token, user_id = self.authenticator.authorize(self.authorize_code)
			self.client = DropboxClient(self.access_token)
			self.message = "Connected. Gathering account informations"
			self.account = self.client.account_info()
			self.message = "Hello, %s! DrSync is checking previously synchronized data" % (self.account["display_name"])
			self.folder_data = self.client.metadata("/")
			self.sync_data = None
			for item in self.folder_data["contents"]:
				if not item["is_dir"] and item["path"] == SYNC_SCHEMA:
					fp = self.client.get_file(SYNC_SCHEMA)
					self.sync_data = sublime.decode_value(fp.read().decode("utf-8"))
			self.result = True
		except ErrorResponse as e:
			self.result_message = "ErrorRes: %s" % (e)
			self.result = False
		except Exception as e:
			self.result_message = "Error: %s" % (e)
			self.result = False


class SyncUpThread(threading.Thread):
	def __init__(self, data, file_list, client):
		self.data = data
		self.file_list = file_list
		self.client = client
		self.percentage = 0
		threading.Thread.__init__(self)

	def run(self):
		try:
			index = 0
			for parent, filepath in self.file_list:
				self.percentage = int(index*100/(len(self.file_list)+1))
				path = os.path.join(os.path.basename(parent), os.path.relpath(filepath, parent))
				f = open(filepath, "rb")
				response = self.client.put_file(DropboxUtil.format_path(path), f, True)
				index += 1

			tmppath = os.path.join(gettempdir(), "DrSync.drsync-tmp")
			out = open(tmppath, "wb")
			out.write(sublime.encode_value(self.data).encode("utf-8"))
			out.close()
			f = open(tmppath, "rb")
			response = self.client.put_file(SYNC_SCHEMA, f, True)

			self.result = True
		except Exception as e:
			print("Error: %s" % (e))
			self.result = False

class SyncGatherThread(threading.Thread):
	def __init__(self, paths, data, client):
		self.paths = paths
		self.data = data
		self.client = client
		threading.Thread.__init__(self)

	def is_exists(self, file_path):
		try:
			filedata = self.client.metadata(file_path)
			return "is_deleted" not in filedata or not filedata["is_deleted"]
		except Exception as e:
			return False
		return False

	def get_all(self, dir_path):
		file_list = []
		try:
			folderdata = self.client.metadata(dir_path)
			for item in folderdata["contents"]:
				if item["is_dir"]:
					file_list += self.get_all(item["path"])
				else:
					file_list.append(item["path"])
		except Exception as e:
			pass
		return file_list

	def run(self):
		try:
			self.file_list = []
			settings = self.data["settings"]
			if settings["installed_packages"]:
				files = self.get_all(DropboxUtil.format_path(os.path.basename(self.paths["installed_packages"])))
				for filepath in files:
					self.file_list.append([self.paths["installed_packages"], filepath])
			if settings["local_packages"]:
				files = self.get_all(DropboxUtil.format_path(os.path.basename(self.paths["packages"])))
				for filepath in files:
					self.file_list.append([self.paths["packages"], filepath])
			if settings["user_directory"]:
				files = self.get_all(DropboxUtil.format_path(os.path.basename(self.paths["packages_user"])))
				for filepath in files:
					self.file_list.append([self.paths["packages_user"], filepath])
			else:
				files = []
				if settings["package_control_preferences"]:
					files += ["Package Control.sublime-settings"]
				if settings["drsync_preferences"]:
					files += ["DrSync.sublime-settings"]
				if settings["sublime_preferences"]:
					files += ["Preferences.sublime-settings", "Default (Windows).sublime-keymap", "Default (OSX).sublime-keymap", "Default (Linux).sublime-keymap"]
				for filename in files:
					filepath = os.path.join(os.path.basename(self.paths["packages_user"]), filename)
					if self.is_exists(DropboxUtil.format_path(filepath)):
						self.file_list.append([self.paths["packages_user"], DropboxUtil.format_path(filepath)])
			self.result = True
		except Exception as e:
			self.result_message = "Error: %s" % (e)
			self.result = False


class SyncDownThread(threading.Thread):
	def __init__(self, data, file_list, client):
		self.data = data
		self.file_list = file_list
		self.client = client
		self.percentage = 0
		threading.Thread.__init__(self)

	def run(self):
		currentfile = ""
		try:
			index = 0
			for target, filepath in self.file_list:
				currentfile = filepath
				self.percentage = int(index*100/len(self.file_list))
				targetname = DropboxUtil.format_path(os.path.basename(target))
				targetpath = os.path.join(target, filepath[len(targetname)+1:])
				targetdir = os.path.dirname(targetpath)
				f = self.client.get_file(filepath)
				if not os.path.exists(targetdir):
					os.makedirs(targetdir)
				out = open(targetpath, "wb")
				out.write(f.read())
				out.close()
				index += 1
			self.result = True
		except Exception as e:
			self.result_message = "Error on %s: %s" % (currentfile, e)
			self.result = False
