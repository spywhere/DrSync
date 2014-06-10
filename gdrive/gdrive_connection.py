import sublime
import json
import socket
from ..urllib3 import *
from .gdrive_util import *

class GDriveConnection():

	def request(self, method, url, params=None, body=None, headers=None, raw_response=False, as_json=False):
		try:
			import ssl
			pool_manager = PoolManager(
				num_pools=4,
				maxsize=8,
				block=False,
				timeout=60.0,
				cert_reqs=ssl.CERT_REQUIRED,
				ca_certs=GDriveUtil.get_cert_file(),
				ssl_version=ssl.PROTOCOL_TLSv1,
			)
		except (ImportError):
			pool_manager = PoolManager(
				num_pools=4,
				maxsize=8,
				block=False,
				timeout=60.0,
			)

		params = params or {}
		headers = headers or {}
		headers["User-Agent"] = "DrSync/0.1"

		if params:
			if body:
				raise ValueError("body parameter cannot be used with params parameter")
			if as_json:
				body = sublime.encode_value(params)
				headers["Content-type"] = "application/json"
				headers["Content-Length"] = len(body)
			else:
				body = urllib.parse.urlencode(params)
				headers["Content-type"] = "application/x-www-form-urlencoded"

		if hasattr(body, "getvalue"):
			body = str(body.getvalue())
			headers["Content-Length"] = len(body)
		if hasattr(body, "read"):
			headers["Content-Length"] = len(body.read())

		for key, value in headers.items():
			if type(value) == str and "\n" in value:
				raise ValueError("headers should not contain newlines (" + key + ": " + value + ")")

		try:
			response = pool_manager.urlopen(method=method, url=url, body=body, headers=headers, preload_content=False)
		except socket.error as e:
			raise SocketError(url, e)
		except exceptions.SSLError as e:
			raise SocketError(url, "SSL certificate error: %s" % e)

		if response.status != 200:
			raise ErrorResponse(response, response.read())
		return {"headers": response.headers, "data": self.process_response(response, raw_response)}

	def process_response(self, r, raw_response):
		if raw_response:
			return r
		else:
			resp = json.loads(r.read().decode("utf-8"))
			r.close()

		return resp

	def get(self, url, headers=None, raw_response=False):
		return self.request("GET", url, headers=headers, raw_response=raw_response)

	def delete(self, url, headers=None, raw_response=False):
		return self.request("DELETE", url, headers=headers, raw_response=raw_response)

	def post(self, url, params=None, headers=None, raw_response=False, as_json=False):
		return self.request("POST", url, params=params, headers=headers, raw_response=raw_response, as_json=as_json)

	def post_multipart(self, url, fields={}, headers=None, raw_response=False):
		boundary = "drsync_data"
		body = b""
		headers["Content-Type"] = "multipart/related; boundary=\""+boundary+"\""
		for part in fields:
			body += ("\n\n--" + boundary).encode("utf-8")
			if "headers" in part:
				for hk in part["headers"]:
					body += ("\n%s: %s" % (hk, part["headers"][hk])).encode("utf-8")
			body += b"\n\n" + part["body"]
		body += ("\n\n--" + boundary + "--").encode("utf-8")
		headers["Content-Length"] = len(body)
		return self.request("POST", url, body=body, headers=headers, raw_response=raw_response)

	def put(self, url, body, headers=None, raw_response=False):
		return self.request("PUT", url, body=body, headers=headers, raw_response=raw_response)


class SocketError(socket.error):
    def __init__(self, host, e):
        msg = "Error connecting to \"%s\": %s" % (host, str(e))
        socket.error.__init__(self, msg)

class ErrorResponse(Exception):
    def __init__(self, http_resp, body):
        self.status = http_resp.status
        self.reason = http_resp.reason
        self.body = body
        self.headers = http_resp.getheaders()
        http_resp.close() # won't need this connection anymore

        try:
            self.body = json.loads(self.body.decode("utf-8"))
            self.error_msg = self.body.get('error')
            self.user_error_msg = self.body.get('user_error')
        except ValueError:
            self.error_msg = None
            self.user_error_msg = None

    def __str__(self):
        if self.user_error_msg and self.user_error_msg != self.error_msg:
            # one is translated and the other is English
            msg = "%r (%r)" % (self.user_error_msg, self.error_msg)
        elif self.error_msg:
            msg = repr(self.error_msg)
        elif not self.body:
            msg = repr(self.reason)
        else:
            msg = "Error parsing response body or headers: " +\
                  "Body - %.100r Headers - %r" % (self.body, self.headers)

        return "[%d] %s" % (self.status, msg)
