#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# BamboBot by Krystian Spandel
# Much code from GetBeaned discord bot

version = 'v3.0.0'

print("Loading...")

# Importing the discord API warpper

print("Loading discord...")
import discord

# Load some essentials modules
print("Loading traceback...")

print("Loading collections...")

print("Loading json...")

print("Loading datetime...")

from cogs.helpers.init_logger import init_logger

print("Setting up logging")

base_logger, logger = init_logger()

# Setting up asyncio to use uvloop if possible, a faster implementation on the event loop
import asyncio

try:
    # noinspection PyUnresolvedReferences
    import uvloop
except ImportError:
    logger.warning("Using the not-so-fast default asyncio event loop. Consider installing uvloop.")
    pass
else:
    logger.info("Using the fast uvloop asyncio event loop")
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger.debug("Importing the bot")

from cogs.helpers.BamboBot import BamboBot, get_prefix
logger.debug("Creating a bot instance of commands.AutoShardedBot")

bot = BamboBot(command_prefix=get_prefix, base_logger=base_logger, logger=logger, case_insensitive=True, max_messages=50000)
# bot.remove_command("help")

logger.debug("Loading cogs : ")

######################
#                 |  #
#   ADD COGS HERE |  #
#                 V  #
# ###############   ##

cogs = ['cogs.cache_control',
        'cogs.mod',
        'cogs.purge',
        'cogs.importation',
        'cogs.settings_commands',
        # 'cogs.stats',
        'cogs.automod',
        'cogs.meta',
        'cogs.logging',
        'cogs.help',
        'cogs.support',
        'cogs.dehoister',
        'cogs.autoinspect',
        # 'cogs.suggestions',
        'cogs.donators',
        'cogs.tasks',
        'cogs.role_persist',
        'cogs.zjednoczeni',
        'cogs.inspector',
        'jishaku',]
# cogs = []

for extension in cogs:
    try:
        bot.load_extension(extension)
        logger.debug(f"> {extension} loaded!")
    except Exception as e:
        logger.exception('> Failed to load extension {}\n{}: {}'.format(extension, type(e).__name__, e))

logger.info("Everything seems fine, we are now connecting to discord.")

try:
    # bot.loop.set_debug(True)
    bot.loop.run_until_complete(bot.start(bot.token))
except KeyboardInterrupt:
    pass
finally:
    game = discord.Game(name=f"Restartowanie...")
    bot.loop.run_until_complete(bot.change_presence(status=discord.Status.dnd, activity=game))

    bot.loop.run_until_complete(bot.logout())

    bot.loop.run_until_complete(asyncio.sleep(3))
    bot.loop.close()
