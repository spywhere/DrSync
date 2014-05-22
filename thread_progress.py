import sublime


class ThreadProgress():
	def __init__(self, thread, message="Loading", on_done=None, on_fail=None, anim_fx=None):
		self.thread = thread
		self.message = message
		self.on_done = on_done
		self.on_fail = on_fail
		if anim_fx is not None:
			self.anim_fx = anim_fx
		sublime.set_timeout(lambda: self.run(0), 100)

	def anim_fx(self, i, message, thread):
		return {"i": (i+1) % 3, "message": "%s %s" % (self.message, "." * (i+1)), "delay": 300}

	def run(self, i):
		if not self.thread.is_alive():
			if hasattr(self.thread, "result") and not self.thread.result:
				if hasattr(self.thread, "result_message"):
					sublime.status_message(self.thread.result_message)
				else:
					sublime.status_message("")
				if self.on_fail is not None:
					self.on_fail(self.thread)
				return
			sublime.status_message("")
			if self.on_done is not None:
				self.on_done(self.thread)
			return
		info = self.anim_fx(i, self.message, self.thread)
		tmsg = ""
		if hasattr(self.thread, "msg"):
			tmsg = self.thread.msg
		sublime.status_message(info["message"]+tmsg)
		sublime.set_timeout(lambda: self.run(info["i"]), info["delay"])
