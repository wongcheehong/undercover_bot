import discord
import json


async def send_lobby_message(ctx, settings: dict):
    MAX_PLAYERS_ALLOWED = settings['MAX_PLAYERS_ALLOWED']
    if settings['random_mode']:
        random_mode = "On"
        civilian = "?"
        undercover = "?"
        white = "?"
    else:
        random_mode = "Off"
        civilian = "0"
        undercover = settings['undercover']
        white = settings['white']

    embed = discord.Embed(
        title = "Undercover Lobby",
        description = "Press the link emoji to join the game! `!start` to start the game",
        color = discord.Colour.blue()
    )

    embed.set_footer(text="Made with ❤️ by Wong Chee Hong")
    embed.add_field(name='Current Players Count', value=f"0/{MAX_PLAYERS_ALLOWED}", inline=False)
    embed.add_field(name='Current Settings', value="\u200b", inline=False)
    embed.add_field(name='Civilians', value=civilian, inline=True)
    embed.add_field(name='Undercovers', value=undercover, inline=True)
    embed.add_field(name='Mr. Whites', value=white, inline=True)
    embed.add_field(name='Random Mode', value=random_mode, inline=False)
    
    message = await ctx.send(embed=embed)
    await message.add_reaction('🔗')
    return message

async def update_lobby_message(message: discord.Message, players_list: list, settings: dict):
    MAX_PLAYERS_ALLOWED = settings['MAX_PLAYERS_ALLOWED']
    if settings['random_mode']:
        random_mode = "On"
        civilian = "?"
        undercover = "?"
        white = "?"
    else:
        random_mode = "Off"
        undercover = settings['undercover']
        white = settings['white']
        if((num := len(players_list)) > undercover + white):
            civilian = num - undercover - white
        else:
            civilian = 0
    
    embed = discord.Embed(
        title = "Undercover Lobby",
        description = "Press the link emoji to join the game! `!start` to start the game",
        color = discord.Colour.blue()
    )

    embed.set_footer(text="Made with ❤️ by Wong Chee Hong")
    embed.add_field(name='Players', value=f"{len(players_list)}/{MAX_PLAYERS_ALLOWED}", inline=False)
    embed.add_field(name='Current Settings', value="\u200b", inline=False)
    embed.add_field(name='Civilians', value=civilian, inline=True)
    embed.add_field(name='Undercovers', value=undercover, inline=True)
    embed.add_field(name='Mr. Whites', value=white, inline=True)
    embed.add_field(name='Random Mode (`!random` to switch)', value=random_mode, inline=False)

    if players_list:
        embed.add_field(name='Players Linked', value="\n".join([player.mention for player in players_list]), inline=False)

    await message.edit(embed=embed)

async def send_secret_word(member: discord.Member, secret_word: str=None):
    if not secret_word:
        embed = discord.Embed(
            title = "You are Mr. White",
            description = "Try to act as you had the word, while trying to guess the Civillians word",
            color = 0xFFFFFF
        )
    else:
        title = f"Your secret word: {secret_word}" 
        embed = discord.Embed(
            title = title,
            description = "Describe your secret word",
            color = discord.Colour.blurple()
        )
    print("Sending secret")
    channel = await member.create_dm()
    await channel.send(embed=embed)

async def send_playing_order(ctx, player_obj: list, player_data: dict):
    embed = discord.Embed(
        title = "Playing Order",
        description = "Describe your word when it's your turn. Run `!vote` to start voting",
        color = discord.Colour.red()
    )
    order = "\n".join(
        f"{item['emoji']} {player_obj[item['index']].mention}"
        for id_, item in player_data.items()
    )

    embed.add_field(name='Players', value=order, inline=False)
    await ctx.send(embed=embed)

async def send_vote_message(ctx, player_obj: list, player_data, time_left: int):
    embed = discord.Embed(
        title = "Vote",
        description = "Vote the player to be eliminated by reacting to their corresponding emoji.\n"+ 
                    f":stopwatch: Vote will end in {int(time_left)} seconds\n" + 
                    "You can only vote once. Once you remove your vote, you cannot vote anymore.",
        color = discord.Colour.green()
    )
    order = "\n".join(
        f"{item['emoji']} {player_obj[item['index']].mention}"
        for id_, item in player_data.items()
    )

    embed.add_field(name='Players', value=order, inline=False)
    message = await ctx.send(embed=embed)
    for id_, item in player_data.items():
        await message.add_reaction(item['emoji'])
    return message

async def update_vote_time(message: discord.Message, player_obj: list, player_data, time_left: int):
    embed = discord.Embed(
        title = "Vote",
        description = "Vote the player to be eliminated by reacting to their corresponding emoji.\n"+ 
                    f":stopwatch: Vote will end in {int(time_left)} seconds\n" + 
                    "You can only vote once. Once you remove your vote, you cannot vote anymore.",
        color = discord.Colour.green()
    )
    order = "\n".join(
        f"{item['emoji']} {player_obj[item['index']].mention}"
        for id_, item in player_data.items()
    )

    embed.add_field(name='Players', value=order, inline=False)
    await message.edit(embed=embed)

async def send_gameover_summary(ctx, c_word, u_word, winner_role, player_obj: list, player_data):
    embed = discord.Embed(
        title = f"{winner_role} Won :tada:",
        color = discord.Colour.dark_purple()
    )
    embed.add_field(name='Civilian Word', value=c_word, inline=True)
    embed.add_field(name='Undercover Word', value=u_word, inline=True)
    
    civilian_list_str = ""
    undercover_list_str = ""
    white_list_str = ""
    for ids_, item in player_data.items():
        if item['role'] == 'civilian':
            civilian_list_str += f"{item['emoji']} {player_obj[item['index']].mention}\n"
        elif item['role'] == 'undercover':
            undercover_list_str += f"{item['emoji']} {player_obj[item['index']].mention}\n"
        else:
            white_list_str += f"{item['emoji']} {player_obj[item['index']].mention}\n"
    
    embed.add_field(name='Civilians', value=civilian_list_str, inline=False)
    if undercover_list_str:
        embed.add_field(name='Undercover', value=undercover_list_str, inline=False)
    if white_list_str:
        embed.add_field(name='Mr. White', value=white_list_str, inline=False)

    await ctx.send(embed=embed)


async def send_guess_prompt(eliminate_player_data, players, c_word):
    id_ = list(eliminate_player_data.keys())[0]
    index = eliminate_player_data[id_]['index']
    member = players[index]
    await member.send("**You just elimineted. Guess the civilian's word sending `!guess word` (eg. `!guess apple`)**")