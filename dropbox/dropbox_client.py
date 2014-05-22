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

	def put_file(self, full_path, file_obj, overwrite=False, parent_rev=None):
		path = "/files_put/%s%s" % (self.session.root, DropboxUtil.format_path(full_path))
		params = {"overwrite": bool(overwrite)}
		if parent_rev is not None:
			params["parent_rev"] = parent_rev
		url, params, headers = self.request(path, params, method="PUT", content_server=True)
		return self.connection.put(url, file_obj, headers)

	def get_file(self, from_path, rev=None):
		path = "/files/%s%s" % (self.session.root, DropboxUtil.format_path(from_path))
		params = {}
		if rev is not None:
			params["rev"] = rev
		url, params, headers = self.request(path, params, method="GET", content_server=True)
		return self.connection.request("GET", url, headers=headers, raw_response=True)

	def get_file_and_metadata(self, from_path, rev=None):
		file_res = self.get_file(from_path, rev)
		metadata = DropboxClient.__parse_metadata_as_dict(file_res)
		return file_res, metadata

	@staticmethod
	def __parse_metadata_as_dict(dropbox_raw_response):
		metadata = None
		for header, header_val in dropbox_raw_response.getheaders().items():
			if header.lower() == "x-dropbox-metadata":
				try:
					metadata = json.loads(header_val)
				except ValueError:
					raise ErrorResponse(dropbox_raw_response)
		if not metadata: raise ErrorResponse(dropbox_raw_response)
		return metadata

	def delta(self, cursor=None, path_prefix=None):
		path = "/delta"
		params = {}
		if cursor is not None:
			params["cursor"] = cursor
		if path_prefix is not None:
			params["path_prefix"] = path_prefix
		url, params, headers = self.request(path, params)
		return self.connection.post(url, params, headers)

	def create_copy_ref(self, from_path):
		path = "/copy_ref/%s%s" % (self.session.root, DropboxUtil.format_path(from_path))
		url, params, headers = self.request(path, {}, method="GET")
		return self.connection.get(url, headers)

	def add_copy_ref(self, copy_ref, to_path):
		path = "/fileops/copy"
		params = {
			"from_copy_ref": copy_ref,
			"to_path": format_path(to_path),
			"root": self.session.root
		}
		url, params, headers = self.request(path, params)
		return self.connection.post(url, params, headers)

	def file_copy(self, from_path, to_path):
		params = {
			"root": self.session.root,
			"from_path": format_path(from_path),
			"to_path": format_path(to_path),
		}
		url, params, headers = self.request("/fileops/copy", params)
		return self.connection.post(url, params, headers)

	def file_create_folder(self, path):
		params = {"root": self.session.root, "path": format_path(path)}
		url, params, headers = self.request("/fileops/create_folder", params)
		return self.connection.post(url, params, headers)

	def file_delete(self, path):
		params = {"root": self.session.root, "path": format_path(path)}
		url, params, headers = self.request("/fileops/delete", params)
		return self.connection.post(url, params, headers)

	def file_move(self, from_path, to_path):
		params = {
			"root": self.session.root,
			"from_path": format_path(from_path),
			"to_path": format_path(to_path)
		}
		url, params, headers = self.request("/fileops/move", params)
		return self.connection.post(url, params, headers)

	def metadata(self, path, list=True, file_limit=25000, hash=None, rev=None, include_deleted=False):
		path = "/metadata/%s%s" % (self.session.root, DropboxUtil.format_path(path))
		params = {
			"file_limit": file_limit,
			"list": "true",
			"include_deleted": include_deleted,
		}
		if not list:
			params["list"] = "false"
		if hash is not None:
			params["hash"] = hash
		if rev:
			params["rev"] = rev
		url, params, headers = self.request(path, params, method="GET")
		return self.connection.get(url, headers)

	def thumbnail(self, from_path, size="m", format="JPEG"):
		path = "/thumbnails/%s%s" % (self.session.root, DropboxUtil.format_path(from_path))
		url, params, headers = self.request(path, {"size": size, "format": format}, method="GET", content_server=True)
		return self.rest_client.request("GET", url, headers=headers, raw_response=True)

	def thumbnail_and_metadata(self, from_path, size="m", format="JPEG"):
		thumbnail_res = self.thumbnail(from_path, size, format)
		metadata = DropboxClient.__parse_metadata_as_dict(thumbnail_res)
		return thumbnail_res, metadata

	def search(self, path, query, file_limit=1000, include_deleted=False):
		path = "/search/%s%s" % (self.session.root, DropboxUtil.format_path(path))
		params = {
			"query": query,
			"file_limit": file_limit,
			"include_deleted": include_deleted,
		}
		url, params, headers = self.request(path, params)
		return self.connection.post(url, params, headers)

	def revisions(self, path, rev_limit=1000):
		path = "/revisions/%s%s" % (self.session.root, DropboxUtil.format_path(path))
		params = {
			"rev_limit": rev_limit,
		}
		url, params, headers = self.request(path, params, method="GET")
		return self.connection.get(url, headers)

	def restore(self, path, rev):
		path = "/restore/%s%s" % (self.session.root, DropboxUtil.format_path(path))
		params = {
			"rev": rev,
		}
		url, params, headers = self.request(path, params)
		return self.connection.post(url, params, headers)

	def media(self, path):
		path = "/media/%s%s" % (self.session.root, DropboxUtil.format_path(path))
		url, params, headers = self.request(path, method="GET")
		return self.connection.get(url, headers)

	def share(self, path, short_url=True):
		path = "/shares/%s%s" % (self.session.root, DropboxUtil.format_path(path))
		params = {
			"short_url": short_url,
		}
		url, params, headers = self.request(path, params, method="GET")
		return self.connection.get(url, headers)
