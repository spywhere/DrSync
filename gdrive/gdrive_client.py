import re
import os
from .gdrive_connection import *
from .gdrive_session import *
from .gdrive_util import *

OAUTH2_ACCESS_TOKEN_PATTERN = re.compile(r"\A[-_~/A-Za-z0-9\.\+]+=*\Z")
FOLDER_MIMETYPE = "application/vnd.google-apps.folder"
BINARY_MIMETYPE = "application/octet-stream"

class GDriveClient():
	def __init__(self, credential, token_type, access_token):
		self.credential = credential
		self.connection = GDriveConnection()
		if type(access_token) == str:
			if not OAUTH2_ACCESS_TOKEN_PATTERN.match(access_token):
				raise ValueError("invalid format for oauth2_access_token: %r" % (access_token))
			self.session = GDriveSession(token_type, access_token)
		else:
			raise ValueError("'oauth2_access_token' must either be a string or a GDriveSession")

	def request(self, target, params=None, method="POST", no_host=False):
		if params is None:
			params = {}
		params["key"] = self.credential["client_id"]
		host = GDriveUtil.API_URL
		if no_host:
			host = ""
		base = GDriveUtil.build_url(host+target)
		headers = self.session.build_access_headers()
		if method in ("GET", "PUT"):
			url = GDriveUtil.build_url(host+target, params)
		else:
			url = GDriveUtil.build_url(host+target)
		return url, params, headers

	def account_info(self, params=None):
		url, params, headers = self.request(GDriveUtil.build_url("/about", params), method="GET")
		return self.connection.get(url, headers)["data"]

	def is_exists(self, file_title, parent_id="appdata", include_file=True, include_folder=True):
		try:
			folderdata = self.metadata({"q": "'"+parent_id+"' in parents"})
			for item in folderdata["items"]:
				if ((include_file and item["mimeType"] != FOLDER_MIMETYPE) or (include_folder and item["mimeType"] == FOLDER_MIMETYPE)) and item["title"] == file_title:
					return item
		except Exception as e:
			return None
		return None

	def create_folder(self, full_path, parent_id="appdata", no_create=False):
		if len(full_path) > 1:
			folder_id, pid = self.create_folder(full_path[:1], parent_id, no_create)
			return self.create_folder(full_path[1:], folder_id, no_create)
		else:
			folder_data = self.is_exists(full_path[0], parent_id, include_file=False)
			if folder_data is None and not no_create:
				url, params, headers = self.request(target="/files", params={"fields": "id"}, method="GET")
				params = {"title": full_path[0], "parents": [{"id": parent_id}], "mimeType": FOLDER_MIMETYPE}
				folder_data = self.connection.post(url, params, headers, as_json=True)["data"]
			return folder_data["id"], parent_id

	def split_path(self, path):
		rest, tail = os.path.split(path)
		if len(rest) <= 1:
			return tail,
		return self.split_path(rest) + (tail,)

	def put_file(self, full_path, file_obj):
		self.delete_all_file(full_path)

		folderid = "appdata"
		if os.path.dirname(full_path) != "":
			folderid, parentid = self.create_folder(self.split_path(os.path.dirname(full_path)))
		filename = os.path.basename(full_path)
		fields = [
			{
				"headers": {
					"Content-Type": "application/json; charset=UTF-8"
				},
				"body": sublime.encode_value({"title": filename, "parents": [{"id": folderid}]}).encode("utf-8")
			},
			{
				"headers": {
					"Content-Type": BINARY_MIMETYPE
				},
				"body": file_obj.read()
			}
		]
		url, params, headers = self.request(target="https://www.googleapis.com/upload/drive/v2/files", params={"uploadType": "multipart"}, method="GET", no_host=True)
		return self.connection.post_multipart(url, fields, headers)["data"]

	def delete_all_file(self, full_path):
		while(True):
			file_data = self.get_file(full_path)
			if file_data is None:
				break
			else:
				self.delete_file(file_data["id"])

	def delete_file(self, file_id):
		try:
			url, params, headers = self.request(target="/files/"+file_id, method="GET")
			self.connection.delete(url, headers, raw_response=True)
			return True
		except ErrorResponse as e:
			if e.status == 204:
				return True
			else:
				raise e
		return False

	def get_file_content(self, file_id):
		url, params, headers = self.request(target="/files/"+file_id, method="GET")
		file_data = self.connection.get(url, headers)["data"]
		return self.connection.request("GET", file_data["downloadUrl"], headers=headers, raw_response=True)["data"]

	def get_file(self, full_path):
		folderid = "appdata"
		if os.path.dirname(full_path) != "":
			folderid, parentid = self.create_folder(self.split_path(os.path.dirname(full_path)), no_create=True)
		filename = os.path.basename(full_path)
		if folderid is None:
			return None
		return self.is_exists(filename, folderid, include_folder=False)

	def metadata(self, fields=None, parent_id="appdata"):
		url, params, headers = self.request(target="/files", params=fields, method="GET")
		return self.connection.get(url, headers)["data"]

