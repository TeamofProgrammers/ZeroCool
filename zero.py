#!/usr/bin/env python3
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, ssl
import ipdb, re, configparser, time, sys

config = configparser.ConfigParser()
#config.read("test.ini")
config.read("config.ini")
class HostBot(irc.IRCClient):
	def __init__(self,nick):
		super(HostBot, self).__init__()
		self.nickname = nick

	def connectionMade(self):
		print("host connection made")
		irc.IRCClient.connectionMade(self)

	def connectionLost(self, reason):
		print("host connection  lost %s" % reason)
		irc.IRCClient.connectionLost(self, reason)

	def signedOn(self):
		self.join(self.factory.channel)

	def privmsg(self, user, channel, msg):
		user = user.split('!', 1)[0]
		if(user.lower() == config['host']['personality'].lower()):
			src_str = re.compile(self.nickname, re.IGNORECASE)
			message = src_str.sub("guys", msg)
			victim.protocol.relay("%s"  % message)
			popcorn.protocol.HostRelay(message,user)
		else:
			popcorn.protocol.HostStandard(msg,user)
		print("<%s> %s" % (user, msg))
		
	def alterCollidedNick(self, nickname):
		return nickname + '_'

	def relay(self,msg):
		self.msg(self.factory.channel, msg)

class VictimBot(irc.IRCClient):
	def __init__(self,nick):
		super(VictimBot, self).__init__()
		self.nickname = nick

	def connectionMade(self):
		print("victim connection made")
		irc.IRCClient.connectionMade(self)

	def connectionLost(self, reason):
		print("victim connection  lost %s" % reason)
		irc.IRCClient.connectionLost(self, reason)

	def signedOn(self):
		self.join(self.factory.channel)

	def privmsg(self, user, channel, msg):
		user = user.split('!', 1)[0]
		if (self.nickname.lower() in msg.lower()):
			src_str = re.compile(self.nickname, re.IGNORECASE)
			message = src_str.sub(config['host']['personality'], msg)
			host.protocol.relay("%s" % message)
			popcorn.protocol.VictimRelay(message,user)
		else:
			popcorn.protocol.VictimStandard(msg,user)
		print("<%s> %s" % (user, msg))

	def relay(self,msg):
		self.msg(self.factory.channel, msg)
		
class PopcornBot(irc.IRCClient):
	def __init__(self,nick):
		super(PopcornBot, self).__init__()
		self.nickname = nick

	def connectionMade(self):
		print("popcorn connection made")
		irc.IRCClient.connectionMade(self)

	def connectionLost(self, reason):
		print("popcorn connection  lost %s" % reason)
		irc.IRCClient.connectionLost(self, reason)

	def signedOn(self):
		self.join(self.factory.channel)

	def privmsg(self, user, channel, msg):
		user = user.split('!', 1)[0]
		#ToDo: Need regular expression here. 
		#Rules. 
		#1. String must start with !. White space matters, the very first character MUST be a !. 
		#2. End the match with the first space. Everything after the space will be sent to the dispatch[EventName]Command handler as a string. 
		if(msg.lower().startswith("!host ")):
			message = msg[6:]
			dispatch = self.getCommandDispatch('!host')
			dispatch(message,user)
		if(msg.lower().startswith("!victim ")):
			message = msg[8:]
			victim.protocol.relay(message)
		if(msg.lower().startswith("!personality ")):
			message = msg[13:]
			dispatch = self.getCommandDispatch('!personality')
			dispatch(message,user)
		if(msg.lower().startswith("!help")):
			dispatch = self.getCommandDispatch('!help')
			dispatch()
		if(msg.lower().startswith("!status")):
			dispatch = self.getCommandDispatch('!status')
			dispatch()
		print("<%s> %s" % (user, msg))
		
	def alterCollidedNick(self, nickname):
		return nickname + '_'

	def HostRelay(self,msg,user):
		message = "\x0303Host:\x0f\x02<%s>\x0f\x0303 %s" % (user,msg)
		self.msg(self.factory.channel, message)

	def VictimRelay(self,msg,user):
		message = "\x0304Victim:\x0f\x02<%s>\x0f\x0304 %s" % (user,msg)
		self.msg(self.factory.channel, message)
	
	def HostStandard(self,msg,user):
		message = "\x0311Host:\x0f\x02<%s>\x0f\x0311 %s" % (user,msg)
		self.msg(self.factory.channel, message)
	
	def VictimStandard(self,msg,user):
		message = "\x0313Victim:\x0f\x02<%s>\x0f\x0313 %s" % (user,msg)
		self.msg(self.factory.channel, message)

	def status(self,msg):
		message = "\x02[status]\x0f %s" % msg
		self.msg(self.factory.channel, message)
	
	def dispatchHostCommand(self,message,user):
		host.protocol.relay(message)
	
	def dispatchVictimCommand():pass 
	
	def dispatchHelpCommand(self):
		help = "Commands are: !host <message to host>, !victim <message to victim>, !personality <new nick to follow on host>, and !status"
		self.msg(self.factory.channel, help)
		
	def dispatchUnhandledCommand():pass
		
	#TODO: Input sanitization
	def dispatchPersonalityCommand(self,message,user):
		oldPersonality = config['host']['personality']
		config['host']['personality'] = message
		self.status("%s has changed host personality from %s to %s" % (user,oldPersonality,message))

	def dispatchStatusCommand(self):
		victim = config['victim']
		host = config['host']
		popcorn = config['popcorn']
		message = "\x02Host:\x0f\n   Server: %s\n   Channel: %s\n   Personality: %s\n   BotNick: %s" % (host['server'],host['channel'],host['personality'],host['nick'])
		self.msg(self.factory.channel, message)
		message = "\x02Victim:\x0f\n   Server: %s\n   Channel: %s\n   BotNick:   %s" % (victim['server'], victim['channel'],victim['nick'])
		self.msg(self.factory.channel, message)
		
	def getCommandDispatch(self,command):
		return{
			'!host' : self.dispatchHostCommand,
			'!victim': self.dispatchVictimCommand,
			'!help': self.dispatchHelpCommand,
			'!personality': self.dispatchPersonalityCommand,
			'!status': self.dispatchStatusCommand
		}.get(command, self.dispatchUnhandledCommand)
	
class RelayBotFactory(protocol.ClientFactory):

	def __init__(self, channel, nick,mode):
		self.channel = channel
		self.nick = nick
		self.mode = mode
		self.protocol = None

	def buildProtocol(self, addr):
		if(self.mode == 'host'):
			self.protocol = HostBot(self.nick)
			self.protocol.factory = self
			return self.protocol
		elif(self.mode == 'victim'):
			self.protocol = VictimBot(self.nick)
			self.protocol.factory = self
			return self.protocol
		elif(self.mode == 'popcorn'):
			self.protocol = PopcornBot(self.nick)
			self.protocol.factory = self
			return self.protocol
		else:
			raise Exception("Mode must be host, victim or popcorn")

	def clientConnectionLost(self, connector, reason):
		#connector.connect() #	If we get disconnected, reconnect to server
		pass
	def clientConnectionFailed(self, connector, reason):
		print("connection failed:", reason)
		reactor.stop()

if __name__ == '__main__':
	global host,victim,popcorn
	
	host = RelayBotFactory(config['host']['channel'],config['host']['nick'],'host')
	victim = RelayBotFactory(config['victim']['channel'],config['victim']['nick'],'victim')
	popcorn = RelayBotFactory(config['popcorn']['channel'],config['popcorn']['nick'],'popcorn')
	#ipdb.set_trace()
	if(config['host'].getboolean('ssl') == True):
		#https://twistedmatrix.com/documents/13.1.0/api/twisted.internet.interfaces.IReactorSSL.connectSSL.html
		print("host ssl enabled")
		reactor.connectSSL(config['host']['server'] , int(config['host']['port']), host, ssl.ClientContextFactory())
	else:
		#https://twistedmatrix.com/documents/current/api/twisted.internet.interfaces.IReactorTCP.connectTCP.html
		reactor.connectTCP(config['host']['server'] , int(config['host']['port']), host)
	if(config['victim'].getboolean('ssl') == True):
		print("victim ssl enabled")
		reactor.connectSSL(config['victim']['server'], int(config['victim']['port']), victim, ssl.ClientContextFactory())
	else:
		reactor.connectTCP(config['victim']['server'], int(config['victim']['port']), victim)
	if(config['popcorn'].getboolean('ssl') == True):
		print("popcorn ssl enabled")
		reactor.connectSSL(config['popcorn']['server'], int(config['popcorn']['port']), popcorn, ssl.ClientContextFactory())
	else:
		reactor.connectTCP(config['popcorn']['server'], int(config['popcorn']['port']), popcorn)
	reactor.run()