import re
import os
import sublime
import urllib

class GDriveUtil():
	AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
	TOKEN_URL = "https://accounts.google.com/o/oauth2/token"
	REVOKE_URL = "https://accounts.google.com/o/oauth2/revoke"
	API_URL = "https://www.googleapis.com/drive/v2"
	OOB_CALLBACK_URN = "urn:ietf:wg:oauth:2.0:oob"

	@staticmethod
	def get_cert_file():
		certs = sublime.find_resources("*.crt")
		for cert in certs:
			certparent = os.path.dirname(cert)
			certname = os.path.basename(cert)
			if certparent == "DrSync" and certname == "gdrive.crt":
				return cert
		parent = os.path.join(sublime.packages_path(), "User", "DrSync")
		certs = sublime.find_resources("gdrive.certification")
		for cert in certs:
			if not os.path.exists(parent):
				os.makedirs(parent)
			certfile = os.path.join(parent, "gdrive.crt")
			w = open(certfile, "w")
			w.write(sublime.load_resource(cert))
			w.close()
			return certfile
		return ""

	@staticmethod
	def build_url(target, params=None):
		params = params or {}
		params = params.copy()
		if params:
			return "%s?%s" % (target, urllib.parse.urlencode(params))
		else:
			return target

	@staticmethod
	def format_path(path):
		if not path:
			return path

		path = re.sub(r'/+', '/', path)

		if path == '/':
			return (u"" if isinstance(path, str) else "")
		else:
			return '/' + path.strip('/')
