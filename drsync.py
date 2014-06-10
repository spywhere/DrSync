import sublime
import sublime_plugin
import datetime
import os
import re
from .dropbox import *
from .gdrive import *
from .dropbox_thread import *
from .gdrive_thread import *
from .drsync_key import *
from .thread_progress import *


VERSION = "0.1.10"
SETTINGSBASE = "DrSync.sublime-settings"
USER_FOLDER = "User"
DRSYNC_SETTINGS = None


def get_settings(key, default=None):
	return DRSYNC_SETTINGS.get(key, default)

def set_settings(key, value):
	DRSYNC_SETTINGS.set(key, value)
	sublime.save_settings(SETTINGSBASE)

def cloud_is(cloud):
	return get_settings("cloud_service") == cloud

def plugin_loaded():
	global DRSYNC_SETTINGS
	DRSYNC_SETTINGS = sublime.load_settings(SETTINGSBASE)
	print("DrSync v%s ready" % (VERSION))


class DrsyncCommand(sublime_plugin.WindowCommand):
	def connect_fx(self, i, message, thread):
		msg = message
		if hasattr(thread, "message"):
			msg = thread.message
		return {"i": (i+1) % 3, "message": "%s%s" % (msg, "." * (i+1)), "delay": 300}

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
		filename = ""
		if hasattr(thread, "filename"):
			filename = " "+thread.filename
		return {"i": (i+1) % maxsize, "message": "Syncing... [{0}] {1}%{2}{3}".format("".join(loadbar), thread.percentage, filename, "."*(1+(i%3))), "delay": 300}

	def run(self):
		credential = DrSyncCredential.get_credential(self, get_settings("cloud_service"))
		refresh_token = get_settings("refresh_token")

		if cloud_is("drive"):
			self.auth = GDriveAuth(credential)
			if "drive" not in refresh_token:
				refresh_token["drive"] = None
			thread = GDrivePreAuthenticationThread(DrSyncCredential.get_credential(self, "drive"), self.auth, refresh_token["drive"])
		elif cloud_is("dropbox"):
			self.auth = DropboxAuth(credential["app_key"], credential["app_secret"])
			if "dropbox" not in refresh_token:
				refresh_token["dropbox"] = None
			thread = DropboxPreAuthenticationThread(self.auth, refresh_token["dropbox"])
		else:
			return
		thread.start()
		if cloud_is("drive"):
			ThreadProgress(thread, "Connecting to GoogleDrive", self.on_pre_authorized, self.on_pre_authorized, self.connect_fx)
		elif cloud_is("dropbox"):
			ThreadProgress(thread, "Connecting to Dropbox", self.on_pre_authorized, self.on_pre_authorized, self.connect_fx)

	def on_pre_authorized(self, thread):
		if thread.result:
			if thread.require_code:
				self.window.show_input_panel("Authorize Code:", "Please allow DrSync and get code from: "+self.auth.get_authorize_url(), self.on_code_entered, None, None)
			else:
				self.on_authorized(thread)
		else:
			sublime.error_message(thread.result_message)
			raise thread.exception

	def on_code_entered(self, code):
		if cloud_is("drive"):
			thread = GDriveAuthenticationThread(DrSyncCredential.get_credential(self, "drive"), self.auth, code)
		elif cloud_is("dropbox"):
			thread = DropboxAuthenticationThread(self.auth, code)
		else:
			return
		thread.start()
		if cloud_is("drive"):
			ThreadProgress(thread, "Authenticating into GoogleDrive", self.on_authorized, self.on_authorized, self.connect_fx)
		elif cloud_is("dropbox"):
			ThreadProgress(thread, "Authenticating into Dropbox", self.on_authorized, self.on_authorized, self.connect_fx)

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
			if thread.refresh_token is not None:
				refresh_token = get_settings("refresh_token") or {}
				if cloud_is("drive"):
					refresh_token["drive"] = thread.refresh_token
				elif cloud_is("dropbox"):
					refresh_token["dropbox"] = thread.refresh_token
				set_settings("refresh_token", refresh_token)
			self.client = thread.client
			self.sync_data = thread.sync_data
			self.paths = self.get_paths()
			if thread.sync_data is None:
				self.sync_to()
			else:
				if cloud_is("drive"):
					items = [["Sync from GoogleDrive", "Overwrite current data [" + thread.sync_data["last_sync"] + "]"], ["Sync to GoogleDrive", "Overwrite previously sync data [" + self.get_timestamp() + "]"]]
				elif cloud_is("dropbox"):
					items = [["Sync from Dropbox", "Overwrite current data [" + thread.sync_data["last_sync"] + "]"], ["Sync to Dropbox", "Overwrite previously sync data [" + self.get_timestamp() + "]"]]
				self.window.show_quick_panel(items, self.on_sync_selection)
		else:
			sublime.error_message(thread.result_message)
			raise thread.exception

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
		if cloud_is("drive"):
			thread = GDriveSyncGatherThread(self.paths, self.sync_data, self.client)
		elif cloud_is("dropbox"):
			thread = DropboxSyncGatherThread(self.paths, self.sync_data, self.client)
		thread.start()
		self.upload = False
		ThreadProgress(thread, "DrSync is verifying data", self.on_verified, self.on_verified, self.connect_fx)

	def on_verified(self, thread):
		if thread.result:
			if cloud_is("drive"):
				sthread = GDriveSyncDownThread(self.sync_data, thread.file_list, self.client)
			elif cloud_is("dropbox"):
				sthread = DropboxSyncDownThread(self.sync_data, thread.file_list, self.client)
			sthread.start()
			self.upload = False
			ThreadProgress(sthread, "", self.on_sync_done, self.on_sync_done, self.sync_fx)
		else:
			sublime.error_message(thread.result_message)
			raise thread.exception

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

		if cloud_is("drive"):
			thread = GDriveSyncUpThread(data, file_list, self.client)
		elif cloud_is("dropbox"):
			thread = DropboxSyncUpThread(data, file_list, self.client)
		thread.start()
		self.upload = True
		ThreadProgress(thread, "", self.on_sync_done, self.on_sync_done, self.sync_fx)

	def on_sync_done(self, thread):
		if thread.result:
			sublime.status_message("Data has been synchronized successfully")
		else:
			sublime.error_message(thread.result_message)
			raise thread.exception
