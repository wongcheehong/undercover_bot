import discord
import json
from datetime import datetime
from discord.ext import commands
from function.message import send_lobby_message, update_lobby_message
from function.helper import randomCombinationInfiltrator
import random, math
from cogs.game_control import GameControl


in_game = False
with open("./databases/default_settings.json", "r") as f:
    SETTINGS = json.load(f)


def switch_game_state():
    global in_game
    in_game = not in_game

class Lobby(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message = None
        self.players = []
        self.settings = SETTINGS

    def cog_check(self, ctx):
        return not in_game # Return false when not in game.

    @commands.command()
    async def new(self, ctx):
        """
        Create a new lobby session
        """
        self.players = []
        self.bot.remove_cog("GameControl")
        self.message = await send_lobby_message(ctx, self.settings)

    async def resume(self):
        self.bot.remove_cog("GameControl")
        switch_game_state()
        self.__enable_listener()
        await self.message.reply("Non-existing player can join by react to the attachment I replied to.\nEnter `!start` to start a new game.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id != self.bot.user.id and (
            payload.message_id == self.message.id
            and payload.member.mention not in self.players
        ):
            if len(self.players) == SETTINGS['MAX_PLAYERS_ALLOWED']:
                await self.message.remove_reaction(payload.emoji, payload.member)
                await self.bot.get_channel(payload.channel_id).send(f":no_entry: **Game is full!**")
                return
            self.players.append(payload.member)
            await update_lobby_message(self.message, self.players, self.settings)
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if (payload.user_id != self.bot.user.id and payload.message_id == self.message.id):
            member = await self.bot.fetch_user(payload.user_id)
            if member in self.players:
                self.players.remove(member)
                await update_lobby_message(self.message, self.players, self.settings)

    @commands.command()
    async def setting(self, ctx, undercover, white):
        """
        Set the number of undercover and Mr. White (eg. `!setting 3 1`)
        """
        if self.message is None:
            await ctx.send(":no_entry: **Please run `!new` fisrt before setting**")
        elif self.settings['random_mode']:
            await ctx.send(":no_entry: **Random mode is on, please turn it off by `!random` before setting**")
        else:
            self.settings['undercover'] = int(undercover)
            self.settings['white'] = int(white)
            await update_lobby_message(self.message, self.players, self.settings)
    
    @commands.command()
    async def random(self, ctx):
        if self.message is None:
            await ctx.send(":no_entry: **Please run `!new` fisrt before setting**")
        else:
            self.settings['random_mode'] = not self.settings['random_mode']
            await update_lobby_message(self.message, self.players, self.settings)

    @commands.command()
    async def start(self, ctx):
        """
        Start the game with the players in the current lobby
        """
        if self.message is None:
            await ctx.send(":no_entry: **Please run `!new` first**")
            return
        
        player_count = len(self.players)
        if(player_count < 3):
            await ctx.send(":warning: **Not enough players. Minimum 3 players**")
            return
        if self.settings['random_mode']:
            self.settings['undercover'], self.settings['white'] = randomCombinationInfiltrator(player_count)
            print("Random mode is on")
        infiltrator_count = self.settings['undercover'] + self.settings['white']
        max_infiltrator_allowed = math.floor(player_count/2)
        if self.message is None:
            await ctx.send(":no_entry: **Please run `!new` first**")
            return
        elif(infiltrator_count < 1):
            await ctx.send(":warning: **Set at least one infiltrator**")
            return
        elif(infiltrator_count > max_infiltrator_allowed):
            await ctx.send(f":warning: **Maximum allowed infiltrator for {player_count} players = {max_infiltrator_allowed}**")
            return
        switch_game_state()
        self.__disable_listener()          
        self.bot.add_cog(GameControl(self.bot, ctx, self.players, self.settings))

    def __disable_listener(self):
        self.bot.remove_listener(self.on_raw_reaction_add)
        self.bot.remove_listener(self.on_raw_reaction_remove)
    
    def __enable_listener(self):
        self.bot.add_listener(self.on_raw_reaction_add)
        self.bot.add_listener(self.on_raw_reaction_remove)
    


def setup(bot):
    bot.add_cog(Lobby(bot))

