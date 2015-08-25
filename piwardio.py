#!/usr/bin/python 
# -*- coding: utf-8 -*-

# PIWADIO - Web Radio Player
# Python WebSocket Server / wrp / HTML5 client
# by David Art [aka] adcomp <david.madbox@gmail.com>

import json
import os
import sys
import subprocess
import select

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

VOLUME_DOWN = "amixer sset Master 5%+"
VOLUME_UP = "amixer sset Master 5%-"

class WebRadioPlayer:
	""" A class to access a slave wrp process """

	url = ''
	state = 'stop'
	info = {
		"Name": '',
		"Genre": '',
		"Website": '',
		"Bitrate": ''}

	def __init__(self):

		# start mplayer in slave mode
		self.proc = subprocess.Popen(
			['mplayer', '-slave', '-quiet', '-idle', '-vo', 'null', '-nolirc'], 
			shell=False, 
			stdin=subprocess.PIPE, 
			stdout=subprocess.PIPE,
			bufsize=1)
		self._readlines()

	def cmd(self, txt):

		# play / pause
		if txt == 'pause':

			if self.state == 'play':
				self.state = 'pause'

			elif self.state == 'pause':
				self.state = 'play'
		
		# stop
		elif txt == 'stop':
			
			if self.state == 'pause':
				self.proc.stdin.write("pause\n")

			self.state = 'stop'
			self.url = ''
			self.clearInfo()
		
		# send command to wrp
		self.proc.stdin.write("%s\n" % txt)
		return self._readlines()

	def loadUrl(self, cmd, url):
		
		if self.state == 'pause':
			self.proc.stdin.write("pause\n")
			
		# stop before loading
		self.proc.stdin.write("stop\n")
		
		# get the url
		self.url = url
		self.state = 'play'
		self.clearInfo()
		
		print('\n[wrp] StreamURL = %s' % self.url)

		# send command to wrp
		self.proc.stdin.write("%s %s\n" % (cmd, url))
		return self._readlines()

	def clearInfo(self):
		
		self.info = {
			"Name": '',
			"Genre": '',
			"Website": '',
			"Bitrate": ''}
			
	def _readlines(self):

		while any(select.select([self.proc.stdout.fileno()], [], [], 0.6)):
			line = self.proc.stdout.readline()
			line = line.strip()
			linesplit = line.split(":")
			if line and linesplit[0].strip() in self.info:
				inf = ''.join(linesplit[1:])
				self.info[linesplit[0].strip()] = inf.strip()
				print("[wrp] %s : %s" % (linesplit[0],inf.strip()))

		return 
	
	def changeVolume(self, value):
		cmd = ['amixer', 'sset', 'Master', value]
		subprocess.Popen(cmd).communicate()
		
	def getData(self):
		return {"state": self.state, "url": self.url.split('/')[-1], "info": self.info}

class IndexHandler(tornado.web.RequestHandler):
	
	@tornado.web.asynchronous
	def get(self):
		self.render("index.html")

class WebSocketHandler(tornado.websocket.WebSocketHandler):

	clients = []

	def open(self):

		self.connected = True
		# print("new connection", self.request.remote_ip)
		self.clients.append(self)
		
		# update client data
		data = data = wrp.getData()
		self.write_message(json.dumps(data))

	""" Tornado 4.0 introduced an, on by default, same origin check.
	This checks that the origin header set by the browser is the same as the host header """
	def check_origin(self, origin):
		
		# this is needed .. 
		return True

	def on_message(self, message):
		
		data = json.loads(message)

		# mplayer command 
		if "cmd" in data:
			if data["cmd"] == "loadlist" or data["cmd"] == "loadfile":
				wrp.loadUrl(data["cmd"], data["url"])
			else:
				wrp.cmd(data["cmd"])
		
		# volume change
		elif "volume" in data:
			wrp.changeVolume(data["volume"])

		elif "shutdown" in data:
			shutdown(data["shutdown"])

		else:
			# later
			pass
		
		# return data to all clients
		data = wrp.getData()
		for client in self.clients:
			client.write_message(json.dumps(data))

	def on_close(self):
		
		self.connected = False
		# print("[websocket] connection closed")
		self.clients.remove(self)

def shutdown(mode="h"):
	print('[wrp] shutdown now ..\nBye :)')
	cmd = "sudo shutdown -%s now" % mode
	subprocess.Popen(cmd.split()).communicate()
	sys.exit(0)

application = tornado.web.Application([
	(r'/favicon.ico', tornado.web.StaticFileHandler, {'path': './static/favicon.png'}),
	(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': './static/'}),
	(r'/', IndexHandler),
	(r'/piwardio', WebSocketHandler)
])

wrp = WebRadioPlayer()

if __name__ == "__main__":
	
	http_server = tornado.httpserver.HTTPServer(application)
	http_server.listen(8888)
	print("")
	print("[piwadio] WebSocket Server start ..")
	try:
		tornado.ioloop.IOLoop.instance().start()
	except KeyboardInterrupt:
		print('\nExit ..')
	sys.exit(0)
