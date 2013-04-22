""" Bot intended to play The Resistance """
import main
import random
import time
from ircutils import format as textformat

gamechannel = '#mtgresistance'
players = dict() #Maps lowercase representation of the user to the User object
leaderlist = []
team = []
spies = []
roundnum = 0
failedmissions = 0
leaderattempts = 0
voiced = False #For replacing. Everyone is +v or -v together. Replaced players come in with this status

minplayers = 5
maxplayers = 10

class MasterState(main.State):
	@property
	def name(self):
		return 'Master'
	
	def OnPrivateMessage(self, user, message):
		owner = is_owner(user)
		if owner and message.lower() == 'turn off':
			self._bot.go_to_state('Off')
		elif owner and message.lower() == 'what state':
			self._bot.send_message(user.nickname, self._bot.state.name)

class OffState(main.State):
	@property
	def name(self):
		return 'Off'

	def OnEnterState(self):
		self._bot.send_message_all_channels(textformat.bold('Turning off. Cancelling any game in progress.'))

	def OnLeaveState(self):
		self._bot.send_message_all_channels(textformat.bold('Turning back on. Type !newgame to start a new game.'))
	
	def OnPrivateMessage(self, user, message):
		if is_owner(user) and message.lower() == "turn on":
			self._bot.go_to_state('Idle')

class IdleState(main.State):
	@property
	def name(self):
		return 'Idle'
	
	def OnEnterState(self):
		self._bot.unmoderate_channel(gamechannel)

	def OnChannelMessage(self, user, channel, message):
		if message.lower() == '!newgame':
			self._bot.go_to_state('Forming')

class FormingState(main.State):
	@property
	def name(self):
		return 'Forming'
	
	def OnEnterState(self):
		global voiced
		voiced = True 

		players.clear()
		self._bot.send_message(gamechannel, textformat.bold('Newgame forming, type !join to join.'))

	def OnLeaveState(self):
		devoice_room(self._bot)
	
	def OnChannelMessage(self, user, channel, message):
		message = message.lower()
		playing = is_nickname_in_game(user.nickname)
		if message == '!cancel':
			self._bot.send_message(gamechannel, textformat.bold('Game cancelled.'))
			self._bot.go_to_state('Idle')
		elif message == '!join':
			if not playing:
				players[user.nickname.lower()] = user
				self._bot.voice_user(user.nickname, gamechannel)
		elif message == "!leave":
			if playing:
				players.pop(user.nickname.lower())
				self._bot.devoice_user(user.nickname, gamechannel)
		elif message == '!formed':
			if len(players) < minplayers or len(players) > maxplayers:
				self._bot.send_message(gamechannel, textformat.bold(len(players) + ' players are in the game. Need between ' + minplayers + ' and ' + maxplayers + ' to start.'))
			else:
				global roundnum
				roundnum = 1

				self._bot.moderate_channel(gamechannel)
				numplayers = len(players)
				numspies = lookup_num_spies(numplayers)
				self._bot.send_message(gamechannel, textformat.bold('Game formed with ' + numspies + ' spies and ' + numplayers - numspies + ' + Resistance members.'))

				leaderlist[:] = []
				for user in players.itervalues():
					leaderlist.append(user.nickname)

				random.shuffle(leaderlist)
				spies[:] = players[:numspies]
				for player in spies:
					self._bot.send_message(player, 'You are an IMPERIAL SPY! The spies are ' + ', '.join(spies))
				for player in leaderlist[numspies:]:
					self._bot.send_message(player, 'You are a loyal member of The Resistance.')
				random.shuffle(leaderlist)
				self._bot.go_to_state('Leading')

class LeadingState(main.State):
	@property
	def name(self):
		return 'Leading'
	
	def OnEnterstate(self):
		self.leader = players[0]
		team[:] = []
		numplayers = len(players)
		self.teamsize = lookup_team_size(numplayers, roundnum)
		sabotagesize = lookup_team_size(numplayers, roundnum)

		self._bot.send_message(gamechannel, textformat.bold(
			'It is round ' + roundnum + '. The spies have won ' + failedmissions + ' of them (3 to win). There have been ' + leaderattempts + ' this round.'))
		self._bot.send_message(gamechannel, textformat.bold(
			'The team size will be ' + self.teamsize + ' and the number of saboteurs needed is ' + sabotagesize + '.'))
		self._bot.send_message(gamechannel, textformat.bold(
			'The current leader is ' + self.leader + '. Waiting for them to choose a team. The order of leaders will be ' + ', '.join(players)))
		self.send_syntax_to_leader()
		self._bot.voice_users(players, gamechannel)

	def OnLeaveState(self):
		self._bot.devoice_users(players, gamechannel)

	def send_syntax_to_leader(self):
		self._bot.send_message(self.leader, 'You need to pick ' + self.teamsize + ' people to go on a mission.')
		self._bot.send_message(self.leader, 'Syntax: Pick' + ' <Name>' * self.teamsize)

	def OnPrivateMessage(self, user, message):
		if user.nickname != self.leader:
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
				if not is_nickname_in_game(picked):
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
		leaderlist.append(players.pop(0))
		self._bot.send_message(gamechannel, textformat.bold(
			'The leader picked this team: ' + ', '.join(team) + 'This is attempt ' + leaderattempts + '. The mission is automatically accepted after 5 attempts.'))
		if leaderattempts == 5:
			self._bot.go_to_state('Mission')
			return
		self._bot.send_message(gamechannel, textformat.bold(
			'/message me either Yes or No to indicate your support or rejection of this mission. Majority rules, ties ruled in favor of the mission.'))
		self.playervotes = dict()
		self._bot.voice_users(players, gamechannel)

	def OnLeaveState(self):
		self._bot.devoice_users(players, gamechannel)
		self._bot.send_message(gamechannel, textformat.bold('Here is the vote:'))
		for player in self.playervotes.iterkeys():
			playername = get_proper_capitalized_player(player)
			vote = 'Yes' if self.playervotes[player] else 'No'
			self._bot.send_message(gamechannel, textformat.bold(playername + ': ' + vote))

	def OnPrivateMessage(self, user, message):
		message = message.lower()
		sender = user.nickname.lower()
		if not is_nickname_in_game(sender):
			return
		if message == 'help':
			self._bot.send_message(sender, '/message YES or NO to support or reject the mission.')
			return
		if message == 'yes' or message == 'y':
			self.playervotes[sender] = 1
		elif message == 'no' or message == 'n':
			self.playervotes[sender] = 0
		numplayers = len(players)
		if len(self.playervotes) == numplayers:
			vote = sum(self.playervotes.values()) >= numplayers / 2
			if vote:
				self._bot.go_to_state('Mission')
			else:
				self._bot.send_message(gamechannel, textformat.bold('The vote was rejected!'))
				self._bot.go_to_state('Leading')

class MissionState(main.State):
	@property
	def name(self):
		return 'Mission'

	def EnterState(self):
		self.playervotes = dict()
		sabotagesize = lookup_sabotage_size(len(players), roundnum)
		votetext = 'vote is' if sabotagesize == 1 else 'votes are'
		self._bot.send_message(gamechannel, textformat.bold(
			'The team was accepted! /message me with SUCCESS or FAILURE as your vote for this mission. Loyal resistance members should always vote SUCCESS. ' + sabotagesize + ' ' + votetext + ' required to fail this mission.'))
	
	def OnPrivateMessage(self, user, message):
		global roundnum
		if user.nickname not in team:
			return
		if message == 'help':
			self._bot.send_message(user.nickname, '/message SUCCESS or FAILURE to pass or fail the mission.')
			return
		if message == 'success' or message == 's':
			self.playervotes[user.nickname] = 0
		elif message == 'failure' or message == 'f':
			if user.nickname not in spies:
				self._bot.send_message(user.nickname, 'Loyal Resistance members should always vote SUCCESS, please vote again.')
				return
			self.playervotes[user.nickname] = 1
		if len(self.playervotes) == len(team):
			numfails = sum(self.playervotes.values())
			vote = numfails >= lookup_sabotage_size(len(players), roundnum)
			if vote:
				global failedmissions
				failedmissions += 1	
			resulttext = 'failure' if vote else 'success'
			votetext = ' vote' if numfails == 1 else ' votes'

			self._bot.send_message(gamechannel, textformat.bold('There were ' + numfails + votetext + ' to sabotage. The missions was a ' + resulttext + '!'))
			if failedmissions == 3:
				self._bot.send_message(gamechannel, textformat.bold('The game is over. Spies win!'))
				self._bot.go_to_state('Endgame')
			elif (roundnum - failedmissions) == 3:
				self._bot.send_message(gamechannel, textformat.bold('The game is over, The Resistance wins!'))
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
		self._bot.send_message(gamechannel, textformat.bold('The roles were:'))
		for player in players:
			if player in spies:
				self._bot.send_message(gamechannel, textformat.bold(player + ' => Spy'))
			else:
				self._bot.send_message(gamechannel, textformat.bold(players + ' => Resistance'))
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

def is_owner(user):
	return user.hostname == "cpe-24-27-11-24.austin.res.rr.com"

def is_nickname_in_game(nickname):
	return nickname.lower() in players

def is_hostname_in_game(hostname):
	for user in players.itervalues():
		if user.hostname == hostname:
			return True
	return False

def voice_room(bot):
	""" Automatically voice all the players and set the voiced state to true. """
	global voiced
	voiced = True
	bot.voice_users(players.keys(), gamechannel)

def devoice_room(bot):
	""" Automatically devoice all the players and set the voiced state to false. """
	global voiced
	voiced = False
	bot.devoice_users(players.keys(), gamechannel)

masterstate = MasterState()
offstate = OffState()
idlestate = IdleState()
formingstate = FormingState()
leadingstate = LeadingState()
approvingstate = ApprovingState()

resistancebot = main.StateBot('Resistr', 'irc.efnet.nl', [gamechannel], masterstate, [idlestate, offstate, formingstate, leadingstate, approvingstate])
