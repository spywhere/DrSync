import threading
from tempfile import gettempdir
from .gdrive import *


GDRIVE_SYNC_SCHEMA = "DrSync.drsync-data"


class GDrivePreAuthenticationThread(threading.Thread):
	def __init__(self, credential, authenticator, refresh_token):
		self.credential = credential
		self.authenticator = authenticator
		self.refresh_token = refresh_token
		threading.Thread.__init__(self)

	def run(self):
		try:
			self.require_code = True
			if self.refresh_token is not None:
				access_token, token_type = self.authenticator.refresh_access_token(self.refresh_token)
				self.client = GDriveClient(self.credential, token_type, access_token)
				self.message = "Connected. Gathering account informations"
				account = self.client.account_info()
				self.message = "Hello, %s! DrSync is checking previously synchronized data" % (account["name"])
				self.sync_data = None
				file_data = self.client.get_file(GDRIVE_SYNC_SCHEMA)
				if file_data is not None:
					fp = self.client.get_file_content(file_data["id"])
					self.sync_data = sublime.decode_value(fp.read().decode("utf-8"))
				self.require_code = False
			self.result = True
		except ErrorResponse as e:
			self.result_message = "GDrive ErrorRes [P]: %s" % (e)
			self.result = False
		except Exception as e:
			self.result_message = "GDrive Error [P]: %s" % (e)
			self.result = False
			self.exception = e


class GDriveAuthenticationThread(threading.Thread):
	def __init__(self, credential, authenticator, authorize_code):
		self.credential = credential
		self.authenticator = authenticator
		self.authorize_code = authorize_code
		threading.Thread.__init__(self)

	def run(self):
		try:
			self.refresh_token, access_token, token_type = self.authenticator.authorize(self.authorize_code)
			self.client = GDriveClient(self.credential, token_type, access_token)
			self.message = "Connected. Gathering account informations"
			account = self.client.account_info()
			self.message = "Hello, %s! DrSync is checking previously synchronized data" % (account["name"])
			self.sync_data = None
			file_data = self.client.get_file(GDRIVE_SYNC_SCHEMA)
			if file_data is not None:
				fp = self.client.get_file_content(file_data["id"])
				self.sync_data = sublime.decode_value(fp.read().decode("utf-8"))
			self.result = True
		except ErrorResponse as e:
			self.result_message = "GDrive ErrorRes [A]: %s" % (e)
			self.result = False
		except Exception as e:
			self.result_message = "GDrive Error [A]: %s" % (e)
			self.result = False
			self.exception = e


class GDriveSyncUpThread(threading.Thread):
	def __init__(self, data, file_list, client):
		self.data = data
		self.file_list = file_list
		self.client = client
		self.percentage = 0
		threading.Thread.__init__(self)

	def run(self):
		currentfile = ""
		try:
			self.filename = "Preparing"
			self.client.delete_all_file(GDRIVE_SYNC_SCHEMA)
			index = 0
			for parent, filepath in self.file_list:
				self.percentage = int(index*100/(len(self.file_list)+1))
				currentfile = os.path.basename(filepath)
				self.filename = currentfile
				path = os.path.join(os.path.basename(parent), os.path.relpath(filepath, parent))
				f = open(filepath, "rb")
				self.client.put_file(path, f)
				index += 1
			self.percentage = int(index*100/(len(self.file_list)+1))
			tmppath = os.path.join(gettempdir(), "DrSync.drsync-tmp")
			out = open(tmppath, "wb")
			out.write(sublime.encode_value(self.data).encode("utf-8"))
			out.close()
			f = open(tmppath, "rb")
			self.client.put_file(GDRIVE_SYNC_SCHEMA, f)

			self.result = True
		except Exception as e:
			self.result_message = "GDrive Error [U] on %s: %s" % (currentfile, e)
			self.result = False
			self.exception = e


class GDriveSyncGatherThread(threading.Thread):
	def __init__(self, paths, data, client):
		self.paths = paths
		self.data = data
		self.client = client
		threading.Thread.__init__(self)

	def get_all(self, full_path, parent_id="appdata", current_path=[]):
		file_list = []
		try:
			if len(full_path) > 1:
				folder_data = self.client.is_exists(full_path[0], parent_id)
				return file_list if folder_data is None else self.get_all(full_path[1:], folder_data["id"], current_path+[full_path[0]])
			else:
				file_data = self.client.is_exists(full_path[0], parent_id)
				folder_data = self.client.metadata({"q": "'"+file_data["id"]+"' in parents"})
				if folder_data is not None:
					if "items" in folder_data:
						for item in folder_data["items"]:
							if item["mimeType"] == FOLDER_MIMETYPE:
								file_list += self.get_all([item["title"]], file_data["id"], current_path+[full_path[0]])
							else:
								file_path = []
								file_path += current_path
								file_path.append(full_path[0])
								file_path.append(item["title"])
								file_list.append([os.path.join(*file_path), item["id"]])
				return file_list
		except Exception as e:
			pass
		return file_list

	def run(self):
		try:
			self.file_list = []
			settings = self.data["settings"]
			if settings["installed_packages"]:
				files = self.get_all(self.client.split_path(os.path.basename(self.paths["installed_packages"])))
				for current_path, item_id in files:
					self.file_list.append([self.paths["installed_packages"], current_path, item_id])
			if settings["local_packages"]:
				files = self.get_all(self.client.split_path(os.path.basename(self.paths["packages"])))
				for current_path, item_id in files:
					self.file_list.append([self.paths["packages"], current_path, item_id])
			if settings["user_directory"]:
				files = self.get_all(self.client.split_path(os.path.basename(self.paths["packages_user"])))
				for current_path, item_id in files:
					self.file_list.append([self.paths["packages_user"], current_path, item_id])
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
					file_data = self.client.get_file(filepath)
					if file_data is not None:
						self.file_list.append([self.paths["packages_user"], filepath, file_data["id"]])
			self.result = True
		except Exception as e:
			self.result_message = "GDrive Error [G] gathering: %s" % (e)
			self.result = False
			self.exception = e


class GDriveSyncDownThread(threading.Thread):
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
			for target, filepath, file_id in self.file_list:
				currentfile = os.path.basename(filepath)
				self.filename = currentfile
				self.percentage = int(index*100/len(self.file_list))
				targetname = os.path.basename(target)
				targetpath = os.path.join(target, filepath[len(targetname)+1:])
				targetdir = os.path.dirname(targetpath)
				f = self.client.get_file_content(file_id)
				if not os.path.exists(targetdir):
					os.makedirs(targetdir)
				out = open(targetpath, "wb")
				out.write(f.read())
				out.close()
				index += 1
			self.result = True
		except Exception as e:
			self.result_message = "GDrive Error [D] on %s: %s" % (currentfile, e)
			self.result = False
			self.exception = e
