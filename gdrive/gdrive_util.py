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
	TRUSTED_CERT_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)),"trusted-certs.crt")

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
