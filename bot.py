import discord
from discord.ext import commands
import os, traceback, sys
from dotenv import load_dotenv
from function.helper import empty_vote_scheduler_file
import requests


load_dotenv()
client = commands.Bot(command_prefix='!')

@client.event
async def on_ready():
    empty_vote_scheduler_file()
    print("Bot is ready!")

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send(":no_entry: **You don't have permission to use this command**")
    elif isinstance(error, commands.errors.CheckFailure):
        await ctx.send(":no_entry: **Game is currently running. Commands is disable temporary**")
    else:
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

@client.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(client.latency * 1000)}ms")

@client.command()
@commands.has_permissions(administrator=True)
async def clear(ctx, number=2):
    await ctx.channel.purge(limit=number)

@client.command()
@commands.has_permissions(administrator=True)
async def load(ctx, extension):
    client.load_extension(f'cogs.{extension}')

@client.command()
@commands.has_permissions(administrator=True)
async def unload(ctx, extension):
    client.unload_extension(f'cogs.{extension}')

@client.command()
@commands.has_permissions(administrator=True)
async def reload(ctx, extension="lobby"):
    client.unload_extension(f'cogs.{extension}')
    client.load_extension(f'cogs.{extension}')
    print("Extension Reloaded")


client.load_extension(f'cogs.lobby')


client.run(os.getenv("DISCORD_TOKEN"))
