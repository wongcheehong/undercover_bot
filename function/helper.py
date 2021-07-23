import random
import asyncio
import json
import discord
import math

def decide_playing_order(players: dict):
    l = list(players.items())
    random.shuffle(l)
    while l[0][1]['role'] == 'white':
        random.shuffle(l)
    return dict(l)

async def eliminate(ctx, vote_outcome, players, players_data, alived_players_data):
    id_ = vote_outcome[0][0]
    index = alived_players_data[id_]['index']
    players_data[id_]['alive'] = False
    await ctx.send(
    f':skull: **{players[index].mention}** is eliminated with **{vote_outcome[0][1]}** votes!')
    return alived_players_data.pop(id_)

def check_game_over(civilians_alive_count, infiltrator_alive_count):
    """
    return a tuple (game_over, winner_team)
    game_over is a boolean (True: Game ended, False: Game continues)
    winner_team represent the winning team, None if no one win in this round
    """
    if civilians_alive_count == 1:
        return True, 'Infiltrator'
    elif infiltrator_alive_count == 0:
        return True, 'Civillian'
    else:
        return False, None

async def handle_guess(self, member):
    def check(message):
        return message.author.id == member.id and isinstance(message.channel, discord.DMChannel)

    await member.send("**Guess the civilian's word and sent it right here within 15 seconds :stopwatch:**")
    try:
        msg = await self.bot.wait_for(event='message', timeout=15, check=check)
    except asyncio.TimeoutError:
        await member.send(":stopwatch: Timeout! Try harder next time :wink:")
        return False
    else:
        if msg.content.replace(' ', '').lower() == self.c_word.replace(' ', '').lower():
            await member.send("**:tada: Congrats! You got it RIGHT!** :white_check_mark::white_check_mark:")
            return True
        else:
            await member.send("**:x: Wrong! Try harder next time :wink:**")
            return False

def empty_vote_scheduler_file():
    empty_dict = {}
    with open('./databases/vote.json', 'w') as vote_file:
        json.dump(empty_dict, vote_file, indent=4)

    with open('./databases/scheduler.json', 'w') as schedule_file:
        json.dump(empty_dict, schedule_file, indent=4)

# Given a number N, find and return all possible combination (a, b) where a>b and a+b=N
def find_possible_combinations(number_of_infiltrators: int) -> list:
    result = []
    for a in range(number_of_infiltrators+1):
        for b in range(a, number_of_infiltrators+1):
            if a + b == number_of_infiltrators:
                result.append((b, a))
    return result

def get_random_number_of_infiltrators(total_players: int):
    min = math.floor(total_players/4) + 1
    max = math.floor(total_players/2)
    return random.randint(min, max)

def randomCombinationInfiltrator(total_players):
    number_of_infiltrators = get_random_number_of_infiltrators(total_players)
    possible_combinations = find_possible_combinations(number_of_infiltrators)
    return random.choice(possible_combinations) # returns a tuple (Undercover, Mr.White)
