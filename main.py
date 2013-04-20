from ircutils import bot
from abc 

class State:
	__metaclass__ = ABCMeta

	@abc.abstractproperty
	def name(self):
		return ''

	# sender: string nickname
	# message: list of message split by word
	def OnPrivateMessage(self, sender, message):
		return

	# sender: string nickname
	# channel: string channel name
	# message: list of message split by word
	def OnChannelMessage(self, sender, channel, message):
		return

	def OnEnterState(self):
		return

	def OnLeaveState(self):
		return

class StateBot(bot.SimpleBot):
	def __init__(self, name, server, channels, masterstate, states):
		self.statedictionary = dict()
		self.masterstate = masterstate

		for state in states:
			self.statedictionary[state.name] = state

		super(StateBot, self).__init__(name)
		self.connect(server, channnel=channels)
		self.start()

		self.GoToState(states[0])

	def FindState(self, statename):
		if statename in self.statedictionary:
			return statedictionary[statename]
		raise Exception("No such state: " + statename)

	def GoToState(self, state):
		self.state.OnLeaveState()
		self.state = state
		state.OnEnterState()

	def on_channel_message(self, event):
		sender = event.source
		channel = event.target
		message = event.message.split()
		return
	
	def on_private_message(self, event):
		sender = event.source
		message = event.message.split()

		self.masterstate.OnPrivateMessage(sender, message)
		self.state.OnPrivateMessage(sender, message)
		return
