import urllib
from .gdrive_connection import *
from .gdrive_util import *

class GDriveAuth():
	def __init__(self, credential):
		self.connection = GDriveConnection()
		self.credential = credential

	def scopes_to_string(self, scopes):
		if isinstance(scopes, str):
			return scopes
		else:
			return " ".join(scopes)

	def get_authorize_url(self):
		return GDriveUtil.build_url(GDriveUtil.AUTHORIZE_URL, {"access_type": "offline", "response_type": "code", "client_id": self.credential["client_id"], "redirect_uri": GDriveUtil.OOB_CALLBACK_URN, "scope": self.scopes_to_string(self.credential["scope"])})

	def authorize(self, code):
		params = {
			"grant_type": "authorization_code",
			"client_id": self.credential["client_id"],
			"client_secret": self.credential["client_secret"],
			"code": code,
			"redirect_uri": GDriveUtil.OOB_CALLBACK_URN,
			"scope": self.scopes_to_string(self.credential["scope"])
		}

		response = self.connection.post(GDriveUtil.TOKEN_URL, params=params)["data"]
		access_token = response["access_token"]
		token_type = response["token_type"]
		return access_token, token_type
