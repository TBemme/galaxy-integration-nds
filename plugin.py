import asyncio
import json
import os
import subprocess
import sys

import config
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.consts import Platform, LicenseType, LocalGameState
from galaxy.api.types import Authentication, Game, LocalGame, LicenseInfo
from version import __version__

from bs4 import BeautifulSoup
import re

titleregex = re.compile("([^\(]*) \(.*")
datregex = re.compile("^[xz0-9]+[0-9]+[0-9]+[0-9]+\s+-")
revregex = re.compile("^.*\(Rev (\d)\).*")

class NintendoDsPlugin(Plugin):
	def __init__(self, reader, writer, token):
		super().__init__(Platform.NintendoDs, __version__, reader, writer, token)
		self.games = []
		self.local_games_cache = self.local_games_list()


	async def authenticate(self, stored_credentials=None):
		usercred = {}
		username = config.username
		usercred["username"] = config.username
		self.store_credentials(usercred)

		return Authentication("NDSuserId", usercred["username"])

	async def launch_game(self, game_id):
		emu_path = config.emu_path
		
		for game in self.games:
			if str(game[1]) == game_id:
				subprocess.Popen([emu_path, game[0]])
				break
		return

	# async def install_game(self, game_id):
		# pass

	# async def uninstall_game(self, game_id):
		# pass
		
	def shutdown(self):
		pass

	def local_games_list(self):
		local_games = []
		
		for game in self.games:
			if os.path.exists(game[0]):
				local_games.append(
					LocalGame(
						str(game[1]),
						LocalGameState.Installed
					)
				)
		return local_games


	def tick(self):

		async def update_local_games():
			loop = asyncio.get_running_loop()
			new_local_games_list = await loop.run_in_executor(None, self.local_games_list)
			notify_list = get_state_changes(self.local_games_cache, new_local_games_list)
			self.local_games_cache = new_local_games_list
			for local_game_notify in notify_list:
				self.update_local_game_status(local_game_notify)

		asyncio.create_task(update_local_games())


	async def get_owned_games(self):
		self.games = get_games()
		owned_games = []
		
		for game in self.games:
			owned_games.append(
				Game(
					str(game[1]),
					game[2],
					None,
					LicenseInfo(LicenseType.SinglePurchase, None)
				)
			)
			
		return owned_games

	async def get_local_games(self):
		return self.local_games_cache


def get_games():
	roms = []
	results = []

	try:
		with open(game_list) as f:
			for line in f:
				roms.append(line.rstrip())
	except UnicodeDecodeError:
		with open(game_list, encoding='utf-8-sig') as f:
			for line in f:
				roms.append(line.rstrip())

	with open(game_dat) as fp:
		soup = BeautifulSoup(fp, "xml")

	for rom in roms:
		try:
			ndsgamedata = soup.find("rom", {"name":rom + '.nds'})
			path = config.roms_path + rom + '.nds'
			title_id = ndsgamedata['serial'] + 'N' + (revregex.match(ndsgamedata['name'])[1] if revregex.match(ndsgamedata['name']) != None else '0')
			#datregex used to check num/not-num and titleregex strip unneeded parts to create game_title
			if datregex.match(rom):
				results.append(
						[path, title_id, titleregex.match(ndsgamedata['name'][7:])[1]]
					)
			else:
				results.append(
						[path, title_id, titleregex.match(ndsgamedata['name'])[1]]
					)
		except:
			print('Error processing', rom)
			
	return results

def get_state_changes(old_list, new_list):
	old_dict = {x.game_id: x.local_game_state for x in old_list}
	new_dict = {x.game_id: x.local_game_state for x in new_list}
	result = []
	# removed games
	result.extend(LocalGame(id, LocalGameState.None_) for id in old_dict.keys() - new_dict.keys())
	# added games
	result.extend(local_game for local_game in new_list if local_game.game_id in new_dict.keys() - old_dict.keys())
	# state changed
	result.extend(LocalGame(id, new_dict[id]) for id in new_dict.keys() & old_dict.keys() if new_dict[id] != old_dict[id])
	return result

default_game_list = os.environ['localappdata'] + '\\GOG.com\\Galaxy\\plugins\\installed\\nds_81f936fb-39d9-48bc-b2c5-d4d45b80fbd9\\NDS-list.txt'	
if os.path.exists(config.game_list) and os.path.isfile(config.game_list):
	game_list = config.game_list
else:
	game_list = default_game_list
	
default_game_dat = os.environ['localappdata'] + '\\GOG.com\\Galaxy\\plugins\\installed\\nds_81f936fb-39d9-48bc-b2c5-d4d45b80fbd9\\NDS.dat'	
if os.path.exists(config.game_dat) and os.path.isfile(config.game_dat):
	game_dat = config.game_dat
else:
	game_dat = default_game_dat


def main():
	create_and_run_plugin(NintendoDsPlugin, sys.argv)


# run plugin event loop
if __name__ == "__main__":
	main()