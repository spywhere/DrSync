import threading
from tempfile import gettempdir
from .dropbox import *


DROPBOX_SYNC_SCHEMA = "/DrSync.drsync-data"


class DropboxPreAuthenticationThread(threading.Thread):
	def __init__(self, authenticator, refresh_token):
		self.authenticator = authenticator
		threading.Thread.__init__(self)

	def run(self):
		self.result = True
		self.require_code = True


class DropboxAuthenticationThread(threading.Thread):
	def __init__(self, authenticator, authorize_code):
		self.authenticator = authenticator
		self.authorize_code = authorize_code
		threading.Thread.__init__(self)

	def run(self):
		try:
			access_token, user_id = self.authenticator.authorize(self.authorize_code)
			self.refresh_token = None
			self.client = DropboxClient(access_token)
			self.message = "Connected. Gathering account informations"
			account = self.client.account_info()
			self.message = "Hello, %s! DrSync is checking previously synchronized data" % (account["display_name"])
			folder_data = self.client.metadata("/")
			self.sync_data = None
			for item in folder_data["contents"]:
				if not item["is_dir"] and item["path"] == DROPBOX_SYNC_SCHEMA:
					fp = self.client.get_file(DROPBOX_SYNC_SCHEMA)
					self.sync_data = sublime.decode_value(fp.read().decode("utf-8"))
			self.result = True
		except ErrorResponse as e:
			self.result_message = "Dropbox [A] ErrorRes: %s" % (e)
			self.result = False
		except Exception as e:
			self.result_message = "Dropbox [A] Error: %s" % (e)
			self.result = False
			self.exception = e


class DropboxSyncUpThread(threading.Thread):
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
			for parent, filepath in self.file_list:
				self.percentage = int(index*100/(len(self.file_list)+1))
				currentfile = os.path.basename(filepath)
				self.filename = currentfile
				path = os.path.join(os.path.basename(parent), os.path.relpath(filepath, parent))
				f = open(filepath, "rb")
				self.client.put_file(DropboxUtil.format_path(path), f)
				index += 1
			self.percentage = int(index*100/(len(self.file_list)+1))
			tmppath = os.path.join(gettempdir(), "DrSync.drsync-tmp")
			out = open(tmppath, "wb")
			out.write(sublime.encode_value(self.data).encode("utf-8"))
			out.close()
			f = open(tmppath, "rb")
			self.client.put_file(DROPBOX_SYNC_SCHEMA, f)

			self.result = True
		except Exception as e:
			self.result_message = "Dropbox Error [U] on %s: %s" % (currentfile, e)
			self.result = False
			self.exception = e


class DropboxSyncGatherThread(threading.Thread):
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
			self.result_message = "Dropbox Error [G] gathering: %s" % (e)
			self.result = False
			self.exception = e


class DropboxSyncDownThread(threading.Thread):
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
				currentfile = os.path.basename(filepath)
				self.filename = currentfile
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
			self.result_message = "Dropbox Error [D] on %s: %s" % (currentfile, e)
			self.result = False
			self.exception = e
