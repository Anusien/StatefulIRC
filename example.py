""" An example bot using the StatefulIRC framework. This is a simple bot with
	two states: noisy and quiet. In the nosy state, it will say to the current
	channel anything it receives in PM. In the quiet state, it will not. """

import main

class NoisyState(main.State):
	@property
	def name(self):
		return 'Noisy'

	def OnPrivateMessage(self, sender, message):
		if message == 'be quiet':
			self._bot.GoToState('Quiet')

		elif sender != self._bot.nickname:
			for channel in self._bot.channels.iterkeys():
				self._bot.send_message(channel, message[:])

class QuietState(main.State):
	@property
	def name(self):
		return 'Quiet'

	def OnPrivateMessage(self, sender, message):
		if message == 'be noisy':
			self._bot.GoToState('Noisy')

class MasterState(main.State):
	@property
	def name(self):
		return 'Master'
	
	def OnPrivateMessage(self, sender, message):
		print sender + ": " + message

quietstate = QuietState()
noisystate = NoisyState()
masterstate = MasterState()

noisybot = main.StateBot('NoisyBot', 'irc.efnet.nl', ['#NoisyBotTest'], masterstate, [noisystate, quietstate])
