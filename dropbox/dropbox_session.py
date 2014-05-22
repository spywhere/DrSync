from .dropbox_connection import *

class DropboxSession():
	def __init__(self, access_token):
		self.access_token = access_token
		self.root = "auto"

	def is_linked(self):
		return bool(self.token)

	def unlink(self):
		self.token = None

	def build_access_headers(self, method, resource_url, params=None, token=None):
		headers = {"Authorization": "Bearer " + self.access_token}
		return headers, params

class OAuthToken():
	def __init__(self, key, secret):
		self.key = key
		self.secret = secret
