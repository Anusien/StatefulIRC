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
		#print user.nickname + "!" + user.ident + "@" + user.hostname + ": " + message
		owner = is_owner(user)
		if owner and message.lower() == 'turn off':
			self._bot.go_to_state('Off')
			return
		elif owner and message.lower() == 'what state':
			self._bot.send_message(user.nickname, self._bot.state.name)
			return
		elif owner and message.lower() == 'what players':
			for player in players.iterkeys():
				tempuser = players[player]
				self._bot.send_message(user.nickname, player + ': ' + tempuser.nickname + "!" + tempuser.ident + "@" + tempuser.hostname) 
		elif owner and message.lower() == 'demoderate':
			self._bot.unmoderate_channel(gamechannel)

		messagetokens = message.split()
		if messagetokens[0].lower() == 'replace' and len(messagetokens[0]) == 3:
			if not nickname_in_game(messagetokens[1].lower()):
				return
			olduser = players[messagetokens[1].lower()]
			newuser = main.User(messagetokens[2], "", "")
			replace_user(olduser, newuser, self._bot)
			return

	def OnChannelMessage(self, user, channel, message):
		if is_owner(user) and message.lower() == '!nullgame' and self._bot.state.name != 'Off':
			self._bot.send_message(gamechannel, textformat.bold('Game nulled.'))
			self._bot.go_to_state('Idle')
	
	def OnJoin(self, channel, user):
		if nickname_in_game(user.nickname) and voiced:
			self._bot.voice_nick(user.nickname, channel)
		elif not nickname_in_game(user.nickname) and hostmask_in_game(user.ident, user.hostname):
			replace_user(find_user_by_hostmask(user.ident, user.hostname), user, self._bot)
			

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
		devoice_room(bot)

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

		global leaderattempts
		leaderattempts = 0

		global failedmissions
		failedmissions = 0

		players.clear()
		send_and_notice(self._bot, gamechannel, textformat.bold('New game forming, type !join to join.'))

	def OnLeaveState(self):
		return
	
	def OnChannelMessage(self, user, channel, message):
		message = message.lower()
		playing = nickname_in_game(user.nickname)
		if message == '!cancel':
			self._bot.send_message(gamechannel, textformat.bold('Game cancelled.'))
			self._bot.go_to_state('Idle')
			return
		elif message == '!join':
			if not playing:
				players[user.nickname.lower()] = user
				self._bot.voice_nick(user.nickname, gamechannel)
			return
		elif message == "!leave":
			if playing:
				players.pop(user.nickname.lower())
				self._bot.devoice_nick(user.nickname, gamechannel)
				if len(players) == 0:
					self._bot.send_message(gamechannel, textformat.bold('Game cancelled.'))
					self._bot.go_to_state('Idle')
			return
		elif message == '!formed':
			if len(players) < minplayers or len(players) > maxplayers:
				playertext = 'is 1 player' if len(players) == 1 else 'are ' + str(len(players)) + ' players'
				self._bot.send_message(gamechannel,
					textformat.bold('There ' + playertext + ' in the game. Need between ' + str(minplayers) + ' and ' + str(maxplayers) + ' to start.'))
				return
			else:
				global roundnum
				roundnum = 1

				self._bot.moderate_channel(gamechannel)
				numplayers = len(players)
				numspies = lookup_num_spies(numplayers)
				self._bot.send_message(gamechannel, textformat.bold('Game formed with ' + str(numspies) + ' spies and ' + str(numplayers - numspies) + ' + Resistance members.'))

				leaderlist[:] = []
				for player in players.iterkeys():
					leaderlist.append(player)

				random.shuffle(leaderlist)
				spies[:] = leaderlist[:numspies]
				for player in spies:
					send_and_notice(self._bot, player, 'You are an IMPERIAL SPY! The spies are ' + collate_players(spies))
				for player in leaderlist[numspies:]:
					send_and_notice(self._bot, player, 'You are a loyal member of The Resistance.')
				random.shuffle(leaderlist)

				text = "Team size by round: "
				for i in range(1, 6):
					if i != 1:
						text = text + ', '
					text = text + str(lookup_team_size(numplayers, i))
				self._bot.send_message(gamechannel, textformat.bold(text))

				text = "Number of fails needed by round: "
				for i in range(1, 6):
					if i != 1:
						text = text + ', '
					text = text + str(lookup_sabotage_size(numplayers, i))
				self._bot.send_message(gamechannel, textformat.bold(text))

				self._bot.go_to_state('Leading')

class LeadingState(main.State):
	@property
	def name(self):
		return 'Leading'
	
	def OnEnterState(self):
		self.leader = leaderlist[0]
		team[:] = []
		numplayers = len(players)
		self.teamsize = lookup_team_size(numplayers, roundnum)
		sabotagesize = lookup_sabotage_size(numplayers, roundnum)

		self._bot.send_message(gamechannel, textformat.bold(
			'Round ' + str(roundnum) + '/5. Resistance: ' + str(roundnum-1-failedmissions) + ', Spies: ' + str(failedmissions) + '. Rejected teams this round: ' + str(leaderattempts) + '. Team size: ' + str(self.teamsize) + '. Fails required: ' + str(sabotagesize) + '.'))
		self._bot.send_message(gamechannel, textformat.bold(
			'The current leader is ' + players[self.leader].nickname + '. The order of leaders will be ' + collate_players(leaderlist)))
		self.send_syntax_to_leader()

	def OnLeaveState(self):
		return

	def send_syntax_to_leader(self):
		send_and_notice(self._bot, self.leader, 'You are the leader. picking a team of size ' + str(self.teamsize) + '. /msg ' + self._bot.nickname + ' Pick ' + ' <Name>' * self.teamsize)

	def OnPrivateMessage(self, user, message):
		if user.nickname.lower() != self.leader:
			return
		messagetokens = message.lower().split()
		if messagetokens[0] == 'help':
			self.send_syntax_to_leader()
		elif messagetokens[0] == 'pick':
			global leaderattempts

			team[:] = []
			pickedplayers = set(messagetokens[1:])
			numpicked = len(messagetokens[1:])
			if numpicked != self.teamsize:
				send_and_notice(self._bot, self.leader,
					'You picked ' + str(numpicked) + ' players when you should pick ' + str(self.teamsize) + '.')
				return
			for picked in pickedplayers:
				if not nickname_in_game(picked):
					send_and_notice(self._bot, self.leader, picked + ' is not in the list of players. Pick again!')
					return
				if picked.lower() in team:
					send_and_notice(self._bot, self.leader, "You can't pick " + picked + ' twice.')
					return
				team.append(picked.lower())
			leaderattempts += 1
			self._bot.go_to_state('Approving')

class ApprovingState(main.State):
	@property
	def name(self):
		return 'Approving'

	def OnEnterState(self):
		self.leader = leaderlist[0]
		leaderlist.append(leaderlist.pop(0))
		self._bot.send_message(gamechannel, textformat.bold(
			players[self.leader].nickname + ' picked this team: ' + collate_players(team) + '. This is attempt ' + str(leaderattempts) + '. The mission is automatically accepted after 5 attempts.'))
		if leaderattempts == 5:
			self._bot.go_to_state('Mission')
			return
		for player in players.iterkeys():
			send_and_notice(self._bot, player, 
				'/msg ' + self._bot.nickname + ' either (A)pprove or (R)eject to indicate your support or rejection of this mission. Majority rules, ties ruled in favor of the mission.')
		self.playervotes = dict()

	def OnLeaveState(self):
		return

	def OnPrivateMessage(self, user, message):
		message = message.lower()
		sender = user.nickname.lower()
		if not nickname_in_game(sender):
			return
		if message == 'help':
			send_and_notice(self._bot, sender, '/msg ' + self._bot.nickname + ' (A)pprove or (R)eject to approve or reject the mission.')
			return
		if message == 'retract':
			self.playervotes.pop(sender)
			return
		if message == 'approve' or message == 'a':
			if sender in self.playervotes:
				self.playervotes.pop(sender)
			self.playervotes[sender] = 1
		elif message == 'reject' or message == 'r':
			if sender in self.playervotes:
				self.playervotes.pop(sender)
			self.playervotes[sender] = 0
		numplayers = len(players)
		if len(self.playervotes) == numplayers:
			vote = sum(self.playervotes.values()) >= (numplayers / 2.0)
			self._bot.send_message(gamechannel, textformat.bold('Here is the vote:'))
			for player in self.playervotes.iterkeys():
				playername = get_proper_capitalized_player(player)
				votetext = 'Yes' if self.playervotes[player] else 'No'
				self._bot.send_message(gamechannel, textformat.bold(playername + ': ' + votetext))
			if vote:
				self._bot.go_to_state('Mission')
			else:
				self._bot.send_message(gamechannel, textformat.bold('The team was rejected!'))
				self._bot.go_to_state('Leading')

class MissionState(main.State):
	@property
	def name(self):
		return 'Mission'

	def OnEnterState(self):
		global leaderattempts
		leaderattempts = 0

		self.playervotes = dict()
		sabotagesize = lookup_sabotage_size(len(players), roundnum)
		votetext = 'vote is' if sabotagesize == 1 else 'votes are'
		self._bot.send_message(gamechannel, textformat.bold(
			'The team was accepted! Team is ' + collate_players(team) + '. ' + str(sabotagesize) + ' ' + votetext + ' required to fail this mission.'))
		for player in team:
			send_and_notice(self._bot, player, '/message (S)uccess or (F)ailure to succeed or fail the mission.')

	
	def OnPrivateMessage(self, user, message):
		message = message.lower()
		global roundnum
		if user.nickname.lower() not in team:
			return
		if message == 'help':
			send_and_notice(self._bot, user.nickname, '/message (S)uccess or (F)ailure to succeed or fail the mission.')
			return
		if message == 'retract':
			self.playervotes.pop(user.nickname.lower())
		if message == 'success' or message == 's':
			self.playervotes[user.nickname.lower()] = 0
		elif message == 'failure' or message == 'f':
			if user.nickname.lower() not in spies:
				self._bot.send_message(user.nickname, 'Loyal Resistance members should always vote SUCCESS, please vote again.')
				return
			self.playervotes[user.nickname.lower()] = 1
		if len(self.playervotes) == len(team):
			numfails = sum(self.playervotes.values())
			vote = numfails >= lookup_sabotage_size(len(players), roundnum)
			if vote:
				global failedmissions
				failedmissions += 1	
			resulttext = 'failure' if vote else 'success'
			votetext = ' vote' if numfails == 1 else ' votes'

			self._bot.send_message(gamechannel, textformat.bold('There were ' + str(numfails) + votetext + ' to sabotage. The mission was a ' + resulttext + '!'))
			if failedmissions == 3:
				self._bot.send_message(gamechannel, textformat.bold('The game is over. Spies win!'))
				self._bot.go_to_state('Endgame')
			elif (roundnum - failedmissions) == 3:
				self._bot.send_message(gamechannel, textformat.bold('The game is over, The Resistance wins!'))
				self._bot.go_to_state('Endgame')
			else:
				roundnum += 1
				time.sleep(random.randint(2, 6))

				self._bot.go_to_state('Leading')

class EndgameState(main.State):
	@property
	def name(self):
		return 'Endgame'
	
	def OnEnterState(self):
		self._bot.send_message(gamechannel, textformat.bold('The roles were:'))
		for player in players:
			if player in spies:
				self._bot.send_message(gamechannel, textformat.bold(player + ' => Spy'))
			else:
				self._bot.send_message(gamechannel, textformat.bold(player + ' => Resistance'))
		self._bot.go_to_state('Idle')

	def OnLeaveState(self):	
		self._bot.unmoderate_channel(gamechannel)

		

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
	
def get_proper_capitalized_player(playername):
	return players[playername].nickname

def is_owner(user):
	return user.hostname == "cpe-24-27-11-24.austin.res.rr.com"

def find_user_by_hostmask(ident, hostname):
	for user in players.itervalues():
		if user.hostname == hostname and user.ident == ident:
			return user 
	return None 

def nickname_in_game(nickname):
	return nickname.lower() in players

def hostmask_in_game(ident, hostname):
	return find_user_by_hostmask(ident, hostname) is not None

def voice_room(bot):
	""" Automatically voice all the players and set the voiced state to true. """
	global voiced
	voiced = True
	bot.voice_nicks(players.keys(), gamechannel)

def devoice_room(bot):
	""" Automatically devoice all the players and set the voiced state to false. """
	global voiced
	voiced = False
	bot.devoice_nicks(players.keys(), gamechannel)

def replace_user(olduser, newuser, bot):
	# This is a little ugly; we can't replace the underlying user object with the right info
	# Since there's no way to get hostmask on demand
	if not nickname_in_game(olduser.nickname) or nickname_in_game(newuser.nickname):
		return
	bot.devoice_nick(olduser.nickname, gamechannel)

	bot.send_message(gamechannel, textformat.bold('Replacing ' + olduser.nickname + ' with ' + newuser.nickname + '.'))
	players.pop(olduser.nickname.lower())
	players[newuser.nickname.lower()] = newuser

	if olduser.nickname in leaderlist:
		leaderlist[leaderlist.index(olduser.nickname)] = newuser.nickname.lower()

	if olduser.nickname in team:
		team[team.index(olduser.nickname)] = newuser.nickname.lower()

	if olduser.nickname in spies:
		spies[spies.index(olduser.nickname)] = newuser.nickname.lower()
		send_and_notice(bot, newuser.nickname, 'You are an IMPERIAL SPY! The spies are ' + collate_players(spies))
	elif bot.state.name != 'Forming':
		send_and_notice(bot, newuser.nickname, 'You are a loyal member of The Resistance.')

	if voiced:
		bot.voice_nick(newuser.nickname, gamechannel)

def collate_players(playerlist):
	newplayerlist = []
	for player in playerlist:
		newplayerlist.append(players[player].nickname)
	return ', '.join(newplayerlist)
	
def send_and_notice(bot, target, message):
	bot.send_message(target, message)
	bot.send_notice(target, message)

masterstate = MasterState()
offstate = OffState()
idlestate = IdleState()
formingstate = FormingState()
leadingstate = LeadingState()
approvingstate = ApprovingState()
missionstate = MissionState()
endgamestate = EndgameState()

resistancebot = main.StateBot('Spymaster', 'irc.efnet.nl', [gamechannel], masterstate, [idlestate, offstate, formingstate, leadingstate, approvingstate, missionstate, endgamestate])
