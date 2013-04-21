""" An example bot using the StatefulIRC framework. This is a simple bot with
	two states: noisy and quiet. In the nosy state, it will say to the current
	channel anything it receives in PM. In the quiet state, it will not. """

import main

class NoisyState(main.State):
	@property
	def name(self):
		return 'Noisy'

	def OnPrivateMessage(self, user, message):
		if message == 'be quiet':
			self._bot.go_to_state('Quiet')

		elif user.nickname != self._bot.nickname:
			self._bot.send_message_all_channels(message)

class QuietState(main.State):
	@property
	def name(self):
		return 'Quiet'

	def OnPrivateMessage(self, user, message):
		if message == 'be noisy':
			self._bot.go_to_state('Noisy')

class MasterState(main.State):
	@property
	def name(self):
		return 'Master'
	
	def OnPrivateMessage(self, user, message):
		print user.nickname + "!" + user.ident + "@" + user.hostname + ": " + message

quietstate = QuietState()
noisystate = NoisyState()
masterstate = MasterState()

noisybot = main.StateBot('NoisyBot', 'irc.efnet.nl', ['#NoisyBotTest'], masterstate, [noisystate, quietstate])
