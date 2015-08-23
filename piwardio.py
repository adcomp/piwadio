#!/usr/bin/python 
# -*- coding: utf-8 -*-

# PIWADIO - Web Radio Player
# Python WebSocket Server / Mplayer / HTML5 client
# by David Art [aka] adcomp <david.madbox@gmail.com>

import json
import os
import sys
import subprocess

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

class MPlayer:
	
	last_cmd = ''
	url = ''
	state = 'stop'
	volume = '100%'

	def __init__(self):

		mplayer_cmd = ['mplayer', '-softvol', '-slave', '-quiet', '-idle', '-vo', 'null']
		self.proc = subprocess.Popen(mplayer_cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

	def cmd(self, txt):

		self.last_cmd = txt
		
		# set command to load url ( file or playlist )
		if txt.startswith('loadfile') or txt.startswith('loadlist'):

			if self.state == 'pause':
				self.proc.stdin.write("pause\n")
				
			# stop before loading
			self.proc.stdin.write("stop\n")
			
			# get the url
			self.url = txt.split(' ')[1]
			self.state = 'play'
			print('URL = %s' % self.url)
			
		# play / pause
		elif txt == 'pause':

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
		
		# send command to mplayer
		self.proc.stdin.write("%s\n" % txt)
	
	def readlines(self):
		ret = []
		return ret
		
	def getData(self):
		return {"state": self.state, "url": self.url.split('/')[-1], "volume": self.volume}

class IndexHandler(tornado.web.RequestHandler):
	
    @tornado.web.asynchronous
    def get(self):
        self.render("index.html")

class WebSocketHandler(tornado.websocket.WebSocketHandler):

	clients = []

	def open(self):

		self.connected = True
		print("new connection")
		self.clients.append(self)
		
		# update client data
		data = data = mplayer.getData()
		self.write_message(json.dumps(data))

	""" Tornado 4.0 introduced an, on by default, same origin check.
	This checks that the origin header set by the browser is the same as the host header """
	def check_origin(self, origin):
		
		# this is needed .. 
		return True

	def on_message(self, message):
		
		# send command to mplayer
		mplayer.cmd(message)
		
		# return data to all clients
		data = mplayer.getData()
		for client in self.clients:
			client.write_message(json.dumps(data))

	def on_close(self):
		
		self.connected = False
		print("connection closed")
		self.clients.remove(self)


application = tornado.web.Application([
	(r'/favicon.ico', tornado.web.StaticFileHandler, {'path': './static/favicon.png'}),
	(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': './static/'}),
	(r'/', IndexHandler),
	(r'/piwardio', WebSocketHandler)
])

mplayer = MPlayer()

if __name__ == "__main__":
	
	http_server = tornado.httpserver.HTTPServer(application)
	http_server.listen(8888)
	print("Web Radio Player")
	print("WebSocket Server start ..")
	try:
		tornado.ioloop.IOLoop.instance().start()
	except KeyboardInterrupt:
		print('\nExit ..')
	sys.exit(0)
