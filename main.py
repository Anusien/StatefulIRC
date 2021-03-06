from ircutils import bot
import abc 

class State:
	__metaclass__ = abc.ABCMeta
	def __init__(self):
		self._bot = None

	@abc.abstractproperty
	def name(self):
		return ''

	def OnPrivateMessage(self, user, message):
		return

	def OnChannelMessage(self, user, channel, message):
		return

	def OnEnterState(self):
		return

	def OnLeaveState(self):
		return

	def OnJoin(self, channel, user):
		return

	def _set_bot(self, bottoset):
		self._bot = bottoset

class User:
	def __init__(self, nickname, hostname, ident):
		self.nickname = nickname
		self.hostname = hostname
		self.ident = ident

class StateBot(bot.SimpleBot):
	def __init__(self, name, server, channels, masterstate, states):
		self.state = None
		self.statedictionary = dict()
		self.masterstate = masterstate
		masterstate._set_bot(self)

		for state in states:
			self.statedictionary[state.name] = state
			state._set_bot(self)

		self.channelstojoin = channels
		self.startingstate = states[0].name

		super(StateBot, self).__init__(name)
		self.connect(server)
		self.start()

	def on_welcome(self, event):
		for channel in self.channelstojoin:
			self.join(channel)
		self.go_to_state(self.startingstate)

	def _find_state(self, statename):
		if statename in self.statedictionary:
			return self.statedictionary[statename]
		raise Exception("No such state: " + statename)

	def go_to_state(self, statename):
		state = self._find_state(statename)
		if self.state != None:
			#print 'Leaving ' + self.state.name + ' state and entering ' + statename + ' state.'
			self.state.OnLeaveState()
		#else:
			#print 'Leaving None state and entering ' + statename + ' state.'
		self.state = state
		state.OnEnterState()

	def _get_user_from_event(self, event):
		nickname = event.source
		hostname = event.host
		ident = event.user
		user = User(nickname, hostname, ident)
		return user

	def on_channel_message(self, event):
		user = self._get_user_from_event(event)
		channel = event.target
		message = event.message

		self.masterstate.OnChannelMessage(user, channel, message)
		self.state.OnChannelMessage(user, channel, message)

	def on_join(self, event):
		user = self._get_user_from_event(event)
		channel = event.target

		self.masterstate.OnJoin(channel, user)
		self.state.OnJoin(channel, user)

	
	def on_private_message(self, event):
		user = self._get_user_from_event(event)
		message = event.message

		self.masterstate.OnPrivateMessage(user, message)
		self.state.OnPrivateMessage(user, message)

	def on_error(self, event):
		print "in on_error:"
		print event.source
		print event.target
		print event.command
		print event.user
		print event.host
		for param in event.params:
			print param

	def on_disconnect(self, event):
		print "in on_disconnect:"
		print event.source
		print event.target
		print event.command
		print event.user
		print event.host
		for param in event.params:
			print param

	def on_quit(self, event):
		user = self._get_user_from_event(event)
		if user.nickname == self.nickname:
			quit()


	def send_message_all_channels(self, message):
		for channel in self.channels.iterkeys():
			self.send_message(channel, message)

	def op_user(self, nick, channel):
		self.execute('MODE', channel, '+o ' + nick)

	def voice_nick(self, nick, channel):
		""" Remove operator status and set voice on a given user """
		self.execute('MODE', channel, '-o+v ' + nick + ' ' +  nick)

	def devoice_nick(self, nick, channel):
		self.execute('MODE', channel, '-v ' + nick)

	def voice_nicks(self, nicks, channel):
		left_to_voice = nicks[:]
		while left_to_voice:
			num_to_voice = min(len(left_to_voice), 4)
			self.execute('MODE', channel, '+v' * num_to_voice + " "  + " ".join(left_to_voice[:num_to_voice]))
			left_to_voice = left_to_voice[num_to_voice:]
	
	def devoice_nicks(self, nicks, channel):
		left_to_devoice = nicks[:]
		while left_to_devoice:
			num_to_devoice = min(len(left_to_devoice), 4)
			self.execute('MODE', channel, '-v' * num_to_devoice + " "  + " ".join(left_to_devoice[:num_to_devoice]))
			left_to_devoice = left_to_devoice[num_to_devoice:]

	def moderate_channel(self, channel):
		self.execute('MODE', channel, '+m')
	
	def unmoderate_channel(self, channel):
		self.execute('MODE', channel, '-m')
