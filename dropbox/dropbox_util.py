import re
import os
import sublime
import urllib

class DropboxUtil():
	API_VERSION = 1
	WEB_HOST = "www.dropbox.com"
	API_HOST = "api.dropbox.com"
	API_CONTENT_HOST = "api-content.dropbox.com"
	TRUSTED_CERT_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)),"trusted-certs.crt")

	@staticmethod
	def build_path(target, params=None):
		target_path = urllib.parse.quote(target)
		params = params or {}
		params = params.copy()
		if params:
			return "/%s%s?%s" % (DropboxUtil.API_VERSION, target_path, urllib.parse.urlencode(params))
		else:
			return "/%s%s" % (DropboxUtil.API_VERSION, target_path)

	@staticmethod
	def build_url(host, target, params=None):
		return "https://" + host + DropboxUtil.build_path(target, params)

	@staticmethod
	def format_path(path):
		if not path:
			return path

		path = re.sub(r'/+', '/', path)

		if path == '/':
			return (u"" if isinstance(path, str) else "")
		else:
			return '/' + path.strip('/')
