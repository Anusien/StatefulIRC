""" Bot intended to play The Resistance """
import main
import random
import time

gamechannel = '#mtgresistance'
players = []
lowercaseplayers = []
team = []
spies = []
numplayers = 0
roundnum = 0
failedmissions = 0
leaderattempts = 0

minplayers = 5
maxplayers = 10

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
		self._bot.unmoderate_channel(gamechannel)

	def OnChannelMessage(self, sender, channel, message):
		if message.lower() == '!newgame':
			self._bot.go_to_state('Forming')

class FormingState(main.State):
	@property
	def name(self):
		return 'Forming'
	
	def OnEnterState(self):
		players[:] = []
		self._bot.send_message(gamechannel, 'Newgame forming, type !join to join.')

	def OnLeaveState(self):
		self._bot.devoice_users(players, gamechannel)
	
	def OnChannelMessage(self, sender, channel, message):
		message = message.lower()
		if message == '!cancel':
			self._bot.send_message(gamechannel, 'Game cancelled.')
			self._bot.go_to_state('Idle')
		elif message == '!join':
			if sender not in players:
				players.append(sender)
				self._bot.voice_user(sender, gamechannel)
		elif message == "!leave":
			if sender in players:
				players.remove(sender)
				self._bot.devoice_user(sender, gamechannel)
		elif message == '!formed':
			if len(players) < minplayers or len(players) > maxplayers:
				self._bot.send_message(gamechannel, len(players) + ' players are in the game. Need between ' + minplayers + ' and ' + maxplayers + ' to start.')
			else:
				global numplayers
				global roundnum

				numplayers = len(players)
				numspies = lookup_num_spies(numplayers)
				self._bot.send_message(gamechannel, 'Game formed with ' + numspies + ' spies and ' + numplayers - numspies + ' + Resistance members.')
				lowercaseplayers[:] = [x.lower() for x in players]
				random.shuffle(players)
				spies[:] = players[:numspies]
				for player in spies:
					self._bot.send_message(player, 'You are an IMPERIAL SPY! The spies are ' + ', '.join(spies))
				for player in players[numspies:]:
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
		team[:] = []
		self.teamsize = lookup_team_size(numplayers, roundnum)
		sabotagesize = lookup_team_size(numplayers, roundnum)

		self._bot.send_message(gamechannel,
			'It is round ' + roundnum + '. The spies have won ' + failedmissions + ' of them (3 to win). There have been ' + leaderattempts + ' this round.')
		self._bot.send_message(gamechannel,
			'The team size will be ' + self.teamsize + ' and the number of saboteurs needed is ' + sabotagesize + '.')
		self._bot.send_message(gamechannel,
			'The current leader is ' + self.leader + '. Waiting for them to choose a team. The order of leaders will be ' + ', '.join(players))
		self.send_syntax_to_leader()
		self._bot.voice_users(players, gamechannel)

	def OnLeaveState(self):
		self._bot.devoice_users(players, gamechannel)

	def send_syntax_to_leader(self):
		self._bot.send_message(self.leader, 'You need to pick ' + self.teamsize + ' people to go on a mission.')
		self._bot.send_message(self.leader, 'Syntax: Pick' + ' <Name>' * self.teamsize)

	def OnPrivateMessage(self, sender, message):
		if sender != self.leader:
			return
		messagetokens = message.lower().split()
		if messagetokens[0] == 'help':
			self.send_syntax_to_leader()
		elif messagetokens[0] == 'pick':
			global leaderattempts

			pickedplayers = set(messagetokens[1:])
			numpicked = len(messagetokens[1:])
			if numpicked != self.teamsize:
				self._bot.send_message(self.leader,
					'You picked ' + numpicked + ' players when you should pick ' + self.teamsize + '.')
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
		self._bot.send_message(gamechannel, 'The leader picked this team: ' + ', '.join(team))
		self._bot.send_message(gamechannel,
			'/message me either Yes or No to indicate your support or rejection of this mission. Majority rules, ties ruled in favor of the mission.')
		self._bot.send_message(gamechannel,
			'This is attempt ' + leaderattempts + '. The mission is a failure after 5 attempts.')
		self.playervotes = dict()
		self._bot.voice_users(players, gamechannel)

	def OnLeaveState(self):
		self._bot.devoice_users(players, gamechannel)
		self._bot.send_message(gamechannel, 'Here is the vote:')
		for player in self.playervotes.iterkeys():
			playername = get_proper_capitalized_player(player)
			vote = 'Yes' if self.playervotes[player] else 'No'
			self._bot.send_message(gamechannel, playername + ': ' + vote)

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
			vote = sum(self.playervotes.values()) >= numplayers / 2
			if vote:
				self._bot.go_to_state('Mission')
			else:
				self._bot.send_message(gamechannel, 'The vote was rejected!')
				self._bot.go_to_state('Leading')

class MissionState(main.State):
	@property
	def name(self):
		return 'Mission'

	def EnterState(self):
		self.playervotes = dict()
		sabotagesize = lookup_sabotage_size(numplayers, roundnum)
		votetext = 'vote is' if sabotagesize == 1 else 'votes are'
		self._bot.send_message(gamechannel,
			'The team was accepted! /message me with SUCCESS or FAILURE as your vote for this mission. Loyal resistance members should always vote SUCCESS. ' + sabotagesize + ' ' + votetext + ' required to fail this mission.')
	
	def OnPrivateMessage(self, sender, message):
		global roundnum
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
			numfails = sum(self.playervotes.values())
			vote = numfails >= lookup_sabotage_size(numplayers, roundnum)
			if vote:
				global failedmissions
				failedmissions += 1	
			resulttext = 'failure' if vote else 'success'
			votetext = ' vote' if numfails == 1 else ' votes'

			self._bot.send_message(gamechannel, 'There were ' + numfails + votetext + ' to sabotage. The missions was a ' + resulttext + '!')
			if failedmissions == 3:
				self._bot.send_message(gamechannel, 'The game is over. Spies win!')
				self._bot.go_to_state('Endgame')
			elif (roundnum - failedmissions) == 3:
				self._bot.send_message(gamechannel, 'The game is over, The Resistance wins!')
				self._bot.go_to_state('Endgame')
			else:
				roundnum += 1
				time.sleep(random.randint(2, 6))

				self._bot.got_to_state('Leading')

class EndgameState(main.State):
	@property
	def name(self):
		return 'Endgame'
	
	def EnterState(self):
		self._bot.send_message(gamechannel, 'The roles were:')
		for player in players:
			if player in spies:
				self._bot.send_message(gamechannel, player + ' => Spy')
			else:
				self._bot.send_message(gamechannel, players + ' => Resistance')
		self._bot.go_to_state('Idle')

		

def lookup_team_size(_numplayers, _numround):
	teamsize = [[2, 3, 2, 3, 3],
				[2, 3, 4, 3, 4],
				[2, 3, 3, 4, 4],
				[3, 4, 4, 5, 5],
				[3, 4, 4, 5, 5],
				[3, 4, 4, 5, 5]]
	return teamsize[_numplayers-5][_numround-1]

def lookup_sabotage_size(_numplayers, _numround):
	sabotagesize = [[1, 1, 1, 1, 1],
					[1, 1, 1, 1, 1],
					[1, 1, 1, 2, 1],
					[1, 1, 1, 2, 1],
					[1, 1, 1, 2, 1],
					[1, 1, 1, 2, 1]]

	return sabotagesize[_numplayers - 5][_numround-1]

def lookup_num_spies(_numplayers):
	# The number of spies is one third the size of the group rounded up
	numspies = [2, 2, 3, 3, 3, 4]
	return numspies[_numplayers - 5]
	
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

resistancebot = main.StateBot('Resistr', 'irc.efnet.nl', [gamechannel], masterstate, [idlestate, offstate, formingstate, leadingstate, approvingstate])
