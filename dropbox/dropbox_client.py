import re
from .dropbox_connection import *
from .dropbox_session import *
from .dropbox_util import *

OAUTH2_ACCESS_TOKEN_PATTERN = re.compile(r"\A[-_~/A-Za-z0-9\.\+]+=*\Z")

class DropboxClient():
	def __init__(self, access_token):
		self.connection = DropboxConnection()
		if type(access_token) == str:
			if not OAUTH2_ACCESS_TOKEN_PATTERN.match(access_token):
				raise ValueError("invalid format for oauth2_access_token: %r" % (access_token))
			self.session = DropboxSession(access_token)
		else:
			raise ValueError("'oauth2_access_token' must either be a string or a DropboxSession")

	def request(self, target, params=None, method="POST", content_server=False):
		if params is None:
			params = {}
		host = DropboxUtil.API_CONTENT_HOST if content_server else DropboxUtil.API_HOST
		base = DropboxUtil.build_url(host, target)
		headers, params = self.session.build_access_headers(method, base, params)
		if method in ("GET", "PUT"):
			url = DropboxUtil.build_url(host, target, params)
		else:
			url = DropboxUtil.build_url(host, target)
		return url, params, headers

	def account_info(self):
		url, params, headers = self.request("/account/info", method="GET")
		return self.connection.get(url, headers)

	def put_file(self, full_path, file_obj):
		path = "/files_put/%s%s" % (self.session.root, DropboxUtil.format_path(full_path))
		params = {"overwrite": True}
		url, params, headers = self.request(path, params, method="PUT", content_server=True)
		return self.connection.put(url, file_obj, headers)

	def get_file(self, full_path):
		path = "/files/%s%s" % (self.session.root, DropboxUtil.format_path(full_path))
		params = {}
		url, params, headers = self.request(path, params, method="GET", content_server=True)
		return self.connection.request("GET", url, headers=headers, raw_response=True)

	def metadata(self, path):
		path = "/metadata/%s%s" % (self.session.root, DropboxUtil.format_path(path))
		params = {
			"file_limit": 15000,
			"list": "true",
			"include_deleted": False,
		}
		url, params, headers = self.request(path, params, method="GET")
		return self.connection.get(url, headers)
