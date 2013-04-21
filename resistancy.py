""" Bot intended to play The Resistance """
import main
import random

class MasterState(main.State):
	@property
	def name(self):
		return 'Master'
	
	def OnPrivateMessage(self, sender, message):
		if message.lower() == 'turn off':
			self._bot.go_to_state('Off')
		elif message.lower() == 'what state':
			self._bot.send_message(sender, self._bot.state.name)

class OffState(main.State):
	@property
	def name(self):
		return 'Off'

	def OnEnterState(self):
		self._bot.send_message_all_channels('Turning off. Cancelling any game in progress.')

	def OnLeaveState(self):
		self._bot.send_message_all_channels('Turning back on. Type !newgame to start a new game.')
	
	def OnPrivateMessage(self, sender, message):
		if message.lower() == "turn on":
			self._bot.go_to_state('Idle')

class IdleState(main.State):
	@property
	def name(self):
		return 'Idle'
	
	def OnEnterState(self):
		self._bot.unmoderate_channel(channel)

	def OnChannelMessage(self, sender, channel, message):
		if message.lower() == '!newgame':
			self._bot.go_to_state('Forming')

class FormingState(main.State):
	@property
	def name(self):
		return 'Forming'
	
	def OnEnterState(self):
		users = []
		self._bot.send_message(channel, 'Newgame forming, type !join to join.')

	def OnLeaveState(self):
		self._bot.devoice_users(users, channel)
	
	def OnChannelMessage(self, sender, channel, message):
		message = message.lower()
		if message == '!cancel':
			self._bot.send_message(channel, 'Game cancelled.')
			self._bot.go_to_state('Idle')
		elif message == '!join':
			if sender not in players:
				players.append(sender)
				self._bot.voice_user(sender, channel)
		elif message == "!leave":
			if sender in players:
				players.remove(sender)
				self._bot.devoice_user(sender, channel)
		elif message == '!formed':
			if len(players) != 5:
				self._bot.send_message(channel, len(players) + ' players are in the game. Need exactly 5 to start.')
			else:
				self._bot.send_message(channel, 'Game formed.')
				random.shuffle(players)
				print 'The order of leaders will be ' + ', '.join(players)
				roundnum = 1
				self._bot.go_to_state('Leading')

class LeadingState(main.State)
	@property
	def name(self):
		return 'Leading'
	
	def OnEnterstate(self):
		self.leader = players[0]
		teamsize = lookup_team_size(len(players), roundnum)
		sabotagesize = lookup_team_size(len(players), roundnum)
		self._bot.send_message(channel, 'It is round ' + roundnum + '. There have been ' + leaderattempts + ' previously.' + 
		self._bot.send_message(channel, 'The current leader is ' + self.leader + '. Waiting for them to choose a team.')

def lookup_team_size(numplayers, numround):
	teamsize = [3, 4, 4, 5, 5]
	return teamsize[numround-1]

def lookup_sabotage_size(numplayers, numround):
	sabotagesize = [1, 1, 1, 2, 1]
	return sabotagesize[numround-1]
	

masterstate = MasterState()
offstate = OffState()
idlestate = IdleState()
formingstate = FormingState()
leadingstate = LeadingState()

channel = '#mtgresistance'
players = []
roundnum = 0
leaderattempts = 0

resistancebot = main.StateBot('Resistr', 'irc.efnet.nl', [channel], masterstate, [idlestate, offstate, formingstate, leadingstate])
