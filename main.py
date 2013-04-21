from ircutils import bot
import abc 

class State:
	__metaclass__ = abc.ABCMeta
	def __init__(self):
		self._bot = None

	@abc.abstractproperty
	def name(self):
		return ''

	def OnPrivateMessage(self, sender, message):
		return

	def OnChannelMessage(self, sender, channel, message):
		return

	def OnEnterState(self):
		return

	def OnLeaveState(self):
		return

	def _set_bot(self, bottoset):
		self._bot = bottoset

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
			self.state.OnLeaveState()
		self.state = state
		state.OnEnterState()

	def on_channel_message(self, event):
		sender = event.source
		channel = event.target
		message = event.message

		self.masterstate.OnChannelMessage(sender, channel, message)
		self.state.OnChannelMessage(sender, channel, message)
	
	def on_private_message(self, event):
		sender = event.source
		message = event.message

		self.masterstate.OnPrivateMessage(sender, message)
		self.state.OnPrivateMessage(sender, message)

	def send_message_all_channels(self, message):
		for channel in self.channels.iterkeys():
			self.send_message(channel, message)
