from .gdrive_connection import *

class GDriveSession():
	def __init__(self, token_type, access_token):
		self.token_type = token_type
		self.access_token = access_token
		self.root = "auto"

	def is_linked(self):
		return bool(self.token)

	def unlink(self):
		self.token = None

	def build_access_headers(self):
		headers = {"Authorization": self.token_type + " " + self.access_token}
		return headers

class OAuthToken():
	def __init__(self, key, secret):
		self.key = key
		self.secret = secret
