""" Bot intended to play The Resistance """
import main
import random
import time

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
		self._bot.devoice_users(players, channel)
	
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
				lowercaseplayers = [x.lower() for x in players]
				random.shuffle(players)
				numplayers = len(players)
				numspies = lookup_num_spies(numplayers)
				spies = players[:numspies]
				for player in spies:
					self._bot.send_message(player, 'You are an IMPERIAL SPY!')
				for layer in players[numspies:]:
					self._bot.send_message(player, 'You are a loyal member of The Resistance.')
				random.shuffle(players)
				roundnum = 1
				self._bot.go_to_state('Leading')

class LeadingState(main.State):
	@property
	def name(self):
		return 'Leading'
	
	def OnEnterstate(self):
		self.leader = players[0]
		team = []
		teamsize = lookup_team_size(roundnum)
		sabotagesize = lookup_team_size(roundnum)

		self._bot.send_message(channel,
			'It is round ' + roundnum + '. The spies have won ' + failedmissions + ' of them (3 to win). There have been ' + leaderattempts + ' this round.')
		self._bot.send_message(channel,
			'The team size will be ' + teamsize + ' and the number of saboteurs needed is ' + sabotagesize + '.')
		self._bot.send_message(channel,
			'The current leader is ' + self.leader + '. Waiting for them to choose a team. The order of leaders will be ' + ', '.join(players))
		send_syntax_to_leader()
		self._bot.voice_users(players, channel)

	def OnLeaveState(self):
		self._bot.devoice_users(players, channel)

	def send_syntax_to_leader(self):
		self._bot.send_message(self.leader, 'You need to pick ' + teamsize + ' people to go on a mission.')
		self._bot.send_message(self.leader, 'Syntax: Pick' + ' <Name>' * teamsize)

	def OnPrivateMessage(self, sender, message):
		if sender != self.leader:
			return
		messagetokens = message.lower().split()
		if messagetokens[0] == 'help':
			send_syntax_to_leader()
		elif messagetokens[0] == 'pick':
			pickedplayers = set(messagetokens[1:])
			numpicked = len(messagetokens[1:])
			if numpicked != teamsize:
				self._bot.send_message(self.leader,
					'You picked ' + numpicked + ' players when you should pick ' + teamsize + '.')
				return
			for picked in pickedplayers:
				if picked not in lowercaseplayers:
					self._bot.send_message(self.leader, picked = ' is not in the list of players. Pick again!')
					return
				team.append(get_proper_capitalized_player(picked))
			leaderattempts += 1
			self._bot.go_to_state('Approving')

class ApprovingState(main.State):
	@property
	def name(self):
		return 'Approving'

	def OnEnterState(self):
		players.append(players.pop(0))
		self._bot.send_message(channel, 'The leader picked this team: ' + ', '.join(team))
		self._bot.send_message(channel,
			'/message me either Yes or No to indicate your support or rejection of this mission. Majority rules, ties ruled in favor of the mission.')
		self._bot.send_message(channel,
			'This is attempt ' + leaderattempts + '. The mission is a failure after 5 attempts.')
		self.playervotes = dict()
		self._bot.voice_users(players, channel)

	def OnLeaveState(self):
		self._bot.devoice_users(players, channel)

	def OnLeaveState(self):
		self._bot.send_message(channel, 'Here is the vote:')
		for player in self.playervotes.iterkeys():
			playername = get_proper_capitalized_player(player)
			vote = 'Yes' if self.playervotes[player] else 'No'
			self._bot.send_message(channel, playername + ': ' + vote)

	def OnPrivateMessage(self, sender, message):
		message = message.lower()
		sender = sender.lower()
		if sender not in lowercaseplayers:
			return
		if message == 'help':
			self._bot.send_message(sender, '/message YES or NO to support or reject the mission.')
			return
		if message == 'yes' or message == 'y':
			self.playervotes[sender] = 1
		elif message == 'no' or message == 'n':
			self.playervotes[sender] = 0
		if len(self.playervotes) == numplayers:
			vote = sum(dictionary.values()) >= numplayers / 2
			if vote:
				self._bot.go_to_state('Mission')
			else:
				self._bot.send_message(channel, 'The vote was rejected!')
				self._bot.go_to_state('Leading')

class MissionState(main.State):
	@property
	def name(self):
		return 'Mission'

	def EnterState(self):
		self.playervotes = dict()
		sabotagesize = lookup_sabotage_size(roundnum)
		votetext = 'vote is' if sabotagesize == 1 else 'votes are'
		self._bot.send_message(channel,
			'The team was accepted! /message me with SUCCESS or FAILURE as your vote for this mission. Loyal resistance members should always vote SUCCESS. ' + sabotagesize + ' ' + votetext + ' required to fail this mission.')
	
	def OnPrivateMessage(self, sender, message):
		if sender not in team:
			return
		if message == 'help':
			self._bot.send_message(sender, '/message SUCCESS or FAILURE to pass or fail the mission.')
			return
		if message == 'success' or message == 's':
			self.playervotes[sender] = 0
		elif message == 'failure' or message == 'f':
			if sender not in spies:
				self._bot.send_message(sender, 'Loyal Resistance members should always vote SUCCESS, please vote again.')
				return
			self.playervotes[sender] = 1
		if len(self.playervotes) == len(team):
			numfails = sum(dictionary.values())
			vote = numfailures >= lookup_sabotage_size(roundnum)
			if vote:
				failedmissions += 1	
			resulttext = 'failure' if vote else 'success'
			votetext = ' vote' if numfails == 1 else ' votes'

			self._bot.send_message(channel, 'There were ' + numfails + votetext + ' to sabotage. The missions was a ' + resulttext + '!')
			if failedmissions == 3:
				self._bot_send_message(channel, 'The game is over. Spies win!')
				self._bot.go_to_state('Endgame')
			elif roundnum - failedmissions == 3:
				self._bot_send_message(channel, 'The game is over, The Resistance wins!')
				self._bot.go_to_state('Endgame')
			else:
				roundnum += 1
				time.sleep(random.randint(2,6))

				self._bot.got_to_state('Leading')

class EndgameState(main.State):
	@property
	def name(self):
		return 'Endgame'
	
	def EnterState(self):
		self._bot.send_message(channel, 'The roles were:')
		for player in players:
			if player in spies:
				self._bot.send_message(channel, player + ' => Spy')
			else:
				self._bot.send_message(channe, players + ' => Resistance')
		self._bot.go_to_state('Idle')

		

def lookup_team_size(numround):
	teamsize = [3, 4, 4, 5, 5]
	return teamsize[numround-1]

def lookup_sabotage_size(numround):
	sabotagesize = [1, 1, 1, 2, 1]
	return sabotagesize[numround-1]

def lookup_num_spies(numplayers):
	return 2
	
def get_proper_capitalized_player(lowercase_player_name):
	for player in players:
		if player.lower() == lowercase_player_name:
			return player

masterstate = MasterState()
offstate = OffState()
idlestate = IdleState()
formingstate = FormingState()
leadingstate = LeadingState()
approvingstate = ApprovingState()

channel = '#mtgresistance'
players = []
lowercaseplayers = []
team = []
spies = []
numplayers = 0
roundnum = 0
failedmissions = 0
leaderattempts = 0

resistancebot = main.StateBot('Resistr', 'irc.efnet.nl', [channel], masterstate, [idlestate, offstate, formingstate, leadingstate, approvingstate])
