#!/usr/bin/env python3
"""Origin Script: https://twistedmatrix.com/documents/16.4.1/_downloads/ircLogBot.py"""
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
import time, sys
import ipdb
import configparser
import re

config = configparser.ConfigParser()
config.read("config.ini")
class RelayBot(irc.IRCClient):
	def __init__(self,nick,mode):
		super(RelayBot, self).__init__()
		self.nickname = nick
		self.mode = mode

	def connectionMade(self):
		print("connection made")
		irc.IRCClient.connectionMade(self)

	def connectionLost(self, reason):
		irc.IRCClient.connectionLost(self, reason)

	def signedOn(self):
		self.join(self.factory.channel)

	def privmsg(self, user, channel, msg):
		user = user.split('!', 1)[0]
		if(self.mode == "host" and user.lower() == config['host']['personality'].lower()):
			victim.protocol.relay("%s"  % msg)
		if(self.mode == "victim"):
			if (self.nickname.lower() in msg.lower()):
				src_str = re.compile(self.nickname, re.IGNORECASE)
				message = src_str.sub(config['host']['personality'], msg)
				host.protocol.relay("%s" % message)
		print("<%s> %s" % (user, msg))
		
	def alterCollidedNick(self, nickname):
		return nickname + '_'

	def relay(self,msg):
		self.msg(self.factory.channel, msg)

class RelayBotFactory(protocol.ClientFactory):

	def __init__(self, channel, nick,mode):
		self.channel = channel
		self.nick = nick
		self.mode = mode
		self.protocol = None

	def buildProtocol(self, addr):
		# p = RelayBot(self.nick,self.mode)
		# p.factory = self
		self.protocol = RelayBot(self.nick, self.mode)
		self.protocol.factory = self
		return self.protocol

	def clientConnectionLost(self, connector, reason):
		connector.connect() #	If we get disconnected, reconnect to server

	def clientConnectionFailed(self, connector, reason):
		print("connection failed:", reason)
		reactor.stop()

if __name__ == '__main__':
	global host,victim
	
	host = RelayBotFactory(config['host']['channel'],config['host']['nick'],'host')
	victim = RelayBotFactory(config['victim']['channel'],config['victim']['nick'],'victim')
	reactor.connectTCP(config['host']['server'] , int(config['host']['port']), host)
	reactor.connectTCP(config['victim']['server'], int(config['victim']['port']), victim)

	reactor.run()