import discord
import json
from datetime import datetime
from discord.ext import commands, tasks
from databases import db
from function.message import send_secret_word, send_playing_order, send_vote_message
from function.message import send_gameover_summary, update_vote_time
from function.helper import decide_playing_order, eliminate, check_game_over, handle_guess, empty_vote_scheduler_file
import random, os

with open("./databases/emoji.json", 'r', encoding='utf-8') as f:
    EMOJI = json.load(f)

def check_if_alive(alived_players_data):
    @commands.check
    async def check(ctx):
        return str(ctx.message.author.id) in alived_players_data

class GameControl(commands.Cog):
    def __init__(self, bot, ctx, players: list, settings: dict):
        self.bot = bot 
        self.ctx = ctx
        self.players = players
        self.settings = settings
        self.players_data = {}
        self.alived_players_data = None
        self.infiltrator_alive_count = 0
        self.civillians_alive_count = 0
        self.message = None
        self.voted_player = []
        self.c_word = ""
        self.u_word = ""
        self.bot.loop.create_task(self.startup())
        

    async def startup(self):
        await self.bot.wait_until_ready()
        self.vote_result.start()
        await self.shuffle_and_send_secret()
    
    async def shuffle_and_send_secret(self):
        self.players_data = {}
        random.shuffle(EMOJI)
        for index, player in enumerate(self.players):
            player_dict = {
                'index': index,
                'emoji': EMOJI[index],
                'role': 'civilian',
                'alive': True
            }
            self.players_data[str(player.id)] = player_dict
        self.infiltrator_alive_count = self.settings['undercover'] + self.settings['white']
        self.civillians_alive_count = len(self.players_data) - self.infiltrator_alive_count
        self.c_word, self.u_word = db.get_word_pair()
        undercover_count = self.settings['undercover']
        infiltrator_ids = random.sample(list(self.players_data.keys()), self.infiltrator_alive_count)
        for id_ in infiltrator_ids[:undercover_count]:
            self.players_data[id_]['role'] = 'undercover'
        for id_ in infiltrator_ids[undercover_count:]:
            self.players_data[id_]['role'] = 'white'

        # DEBUG Purpose
        # with open("./databases/players.json", 'w', encoding='utf-8') as f:
        #     json.dump(self.players_data, f)

        for id_, player in self.players_data.items():
            index = player['index']
            if player['role'] == 'civilian':
                await send_secret_word(self.players[index], self.c_word)
            elif player['role'] == 'undercover':
                await send_secret_word(self.players[index], self.u_word)
            else:
                await send_secret_word(self.players[index])
        self.alived_players_data = decide_playing_order(self.players_data.copy())
        print("Sending playing order")
        await send_playing_order(self.ctx, self.players, self.alived_players_data)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def skip(self, ctx):
        empty_vote_scheduler_file()
        await ctx.send("Skipping these words")
        await self.shuffle_and_send_secret()
    

    @commands.guild_only()
    @commands.command()
    async def vote(self, ctx):
        """
        Vote the player to be eliminated
        """
        if str(ctx.message.author.id) not in self.alived_players_data:
            await ctx.send(":no_entry: **Eliminated player are allowed to start poll**")
            return
        self.voted_player = []
        with open("./databases/scheduler.json", 'r') as f:
            scheduler_data = json.load(f)
            if str(ctx.message.guild.id) not in scheduler_data:
                self.message = await send_vote_message(ctx, self.players, self.alived_players_data, self.settings['vote_time'])
            
                # Vote data
                with open("./databases/vote.json", 'r') as vf:
                    vote_data = json.load(vf)
                    message_id = str(self.message.id)
                    
                    vote_dictionary = dict.fromkeys(self.players_data.keys(), 0)
                    vote_data[message_id] = vote_dictionary

                    with open("./databases/vote.json", 'w') as new_vote_data:
                        json.dump(vote_data, new_vote_data, indent=4)
                
                # Vote Scheduler (max_vote is now set to number of player no matter alive or not) Need revision later
                scheduler_data[str(self.message.guild.id)] = {'message_id': message_id, 'scheduler_time': self.settings['vote_time'], 'vote_start_time': datetime.now().isoformat(), 'max_vote': len(self.alived_players_data)} 
                with open("./databases/scheduler.json", 'w') as new_scheduler_data:
                    json.dump(scheduler_data, new_scheduler_data, indent=4)
            else:
                await ctx.send(":no_entry: **Vote is already started!**")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):  # sourcery no-metrics skip: last-if-guard
        if payload.member.id != self.bot.user.id:
            with open("./databases/vote.json", 'r') as file: 
                vote_data = json.load(file)

            if str(payload.message_id) in vote_data:
                message_id = str(payload.message_id)
                if str(payload.user_id) in self.voted_player:
                    await self.message.remove_reaction(payload.emoji, payload.member)
                    await self.bot.get_channel(payload.channel_id).send(f":no_entry: **{payload.member.mention} You already voted once**")
                    return
                if str(payload.user_id) not in self.alived_players_data:
                    await self.message.remove_reaction(payload.emoji, payload.member)
                    await self.bot.get_channel(payload.channel_id).send(f":no_entry: **Eliminated player or non-player cannot vote**")
                    return
                self.voted_player.append(str(payload.user_id))
                # Time and max vote calculation
                with open('./databases/scheduler.json', 'r') as schedule:
                    scheduler_data = json.load(schedule)
                
                max_vote_count = 0
                time_counter = 0

                for item in scheduler_data.items():
                    if str(payload.guild_id) in item[0]:
                        max_vote_count += item[1]['max_vote']

                        cur_time = datetime.now()
                        prev_time = datetime.strptime(item[1]['vote_start_time'].replace('T', ' '),
                                                        '%Y-%m-%d %H:%M:%S.%f')
                        time_delta = (cur_time - prev_time)
                        total_seconds_passed = time_delta.total_seconds()

                        time_counter += item[1]['scheduler_time'] - total_seconds_passed
                
                #  Add vote count
                players_vote_count = vote_data[message_id]
                for id_, player in self.players_data.items():
                    if player['emoji'] == payload.emoji.name:
                        players_vote_count[id_] += 1
                        break
                        
                vote_data[message_id] = players_vote_count
                with open("./databases/vote.json", 'w') as file: 
                    json.dump(vote_data, file, indent=4)
                await update_vote_time(self.message, self.players, self.alived_players_data, time_counter)

    @tasks.loop(seconds=5)
    async def vote_result(self):
        time = datetime.now()
        time = time.strftime('%H:%M:%S')
        print(f"{time} - Running task loop")
        with open('./databases/scheduler.json', 'r') as schedule_file:
            scheduler_data = json.load(schedule_file)
            if not scheduler_data:
                return

            for guild_id, item in scheduler_data.items():
                cur_time = datetime.now()
                prev_time = datetime.strptime(item['vote_start_time'].replace('T', ' '), '%Y-%m-%d %H:%M:%S.%f')
                time_delta = (cur_time - prev_time)
                total_seconds_passed = int(time_delta.total_seconds())

                with open('./databases/vote.json', 'r') as vote_file:
                    vote_data = json.load(vote_file)

                # total up all the vote in the vote_dictionary
                total_vote_count = sum(
                    vote_count
                    for id_, vote_count in vote_data[str(self.message.id)].items()
                )

                vote_outcome = sorted(vote_data[str(self.message.id)].items(), key=lambda i: i[1], reverse=True)
                if total_seconds_passed > item['scheduler_time'] or total_vote_count >= item['max_vote']:
                    if str(self.message.id) in vote_data:
                        if vote_outcome[0][1] == vote_outcome[1][1]:
                            await self.ctx.send("**Draw! No one got eliminated**")
                            await send_playing_order(self.ctx, self.players, self.alived_players_data)
                            remove_vote_and_scheduler(vote_data, scheduler_data, self.message.id, guild_id)
                            break
                        else:
                            self.eliminated_player_data = await eliminate(self.ctx, 
                            vote_outcome, self.players, self.players_data, self.alived_players_data)
                            correct = False
                            if self.eliminated_player_data['role'] == 'civilian':
                                self.civillians_alive_count -= 1
                            else:
                                self.infiltrator_alive_count -= 1
                                if self.eliminated_player_data['role'] == 'white':
                                    member = self.players[self.eliminated_player_data['index']]
                                    await self.ctx.send(f"**Waiting for {member.mention} to guess the civilian's word in DM :speech_balloon:**")
                                    correct = await handle_guess(self, member)

                            if correct:
                                game_ended = correct
                                winner_role = "Mr. White"
                            else:
                                game_ended, winner_role = check_game_over(self.civillians_alive_count, self.infiltrator_alive_count)
                            
                            if game_ended:
                                await send_gameover_summary(self.ctx, self.c_word, self.u_word, winner_role, self.players, self.players_data)
                                cog = self.bot.get_cog('Lobby')
                                await cog.resume()
                                self.vote_result.stop() # finish its current iteration before gracefully exiting
                            else:
                                await send_playing_order(self.ctx, self.players, self.alived_players_data)

                            remove_vote_and_scheduler(vote_data, scheduler_data, self.message.id, guild_id)
                            break


def remove_vote_and_scheduler(vote_data, scheduler_data, message_id, guild_id):
    # Remove vote data
    vote_data.pop(str(message_id))
    with open('./databases/vote.json', 'w') as update_vote_data:
        json.dump(vote_data, update_vote_data, indent=4)

    # Remove schedule
    scheduler_data.pop(guild_id)
    with open('./databases/scheduler.json', 'w') as update_scheduler_data:
        json.dump(scheduler_data, update_scheduler_data, indent=4)


