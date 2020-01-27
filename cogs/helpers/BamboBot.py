# -*- coding: utf-8 -*-
import collections
import datetime
import json
import logging
import traceback

import discord
import typing
from discord.ext import commands as commands

from cogs.helpers import api
from cogs.helpers import context, checks
from cogs.helpers.cache import Cache
from cogs.helpers.converters import NotStrongEnough, HierarchyError
from cogs.helpers.guild_settings import Settings


class BamboBot(commands.AutoShardedBot):
    def __init__(self, command_prefix: typing.Union[str, typing.Callable[[discord.Message], typing.Awaitable]], base_logger: logging.Logger, logger: logging.Logger, **options):
        super().__init__(command_prefix, **options)

        self.cache = Cache(self)
        self.commands_used = collections.Counter()
        self.admins = [381243923131138058]
        self.base_logger, self.logger = base_logger, logger

        # Load credentials so they can be used later
        with open("credentials.json", "r", encoding='utf-8') as f:
            credentials = json.load(f)

        self.token = credentials["discord_token"]

        self.uptime = datetime.datetime.utcnow()

        self.api = api.Api(self)

        self.settings = Settings(self)

    async def on_message(self, message):
        if message.author.bot:
            return  # ignore messages from other bots

        ctx = await self.get_context(message, cls=context.CustomContext)
        if ctx.prefix is not None:
            await self.invoke(ctx)

    async def on_command(self, ctx):
        self.commands_used[ctx.command.name] += 1
        ctx.logger.info(f"<{ctx.command}> {ctx.message.clean_content}")

    async def on_ready(self):
        game = discord.Game(name=f"b!help | b!urls")
        await self.change_presence(status=discord.Status.online, activity=game)
        self.logger.info("We are all set, on_ready was fired! Yeah!")
        total_members = len(self.users)
        self.logger.info(f"I see {len(self.guilds)} guilds, and {total_members} members")

    async def on_command_error(self, context: context.CustomContext, exception):
        # print(f'self -> {self}\n')
        # print(f'context -> {context}\n')
        # print(f'exception -> {exception}\n')
        # print(f'exception -> {''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))}\n')
        # print(f'exception -> {exception}\n{''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))}\n')

        if isinstance(exception, discord.ext.commands.errors.CommandNotFound):
            return

        context.logger.debug(f"Error during processing: {exception} ({repr(exception)})")

        if isinstance(exception, discord.ext.commands.errors.MissingRequiredArgument):
            await context.send_to(f":x: Brakuje wymaganego argumentu.\nUżycie : `{context.prefix}{context.command.signature}`", delete_after=60)
            await context.message.delete(delay=60)

            return
        elif isinstance(exception, checks.NoPermissionsError):
            await context.send_to(f":x: Oof, wystąpił problem! "
                                  f"Bot wymaga więcej permisji. Skontaktuj się w ten sprawie z adminstratorem serwera. "
                                  f"Jeżeli jesteś administratorem, wpisz `{context.prefix}bot_permissions_check` aby zobaczyć brakkujące permisje. "
                                  f"Pamiętaj o sprawdzeniu nadpisań kanału")
            return
        elif isinstance(exception, checks.PermissionsError):
            await context.send_to(f":x: Heh, nie masz wymaganych uprawnień do tej komendy! "
                                  f"Twój poziom to `{exception.current}`, a wymagany `{exception.required}` :(", delete_after=60)
            await context.message.delete(delay=60)
            return
        # elif isinstance(exception, discord.ext.commands.errors.CheckFailure):
        #       return
        elif isinstance(exception, discord.ext.commands.errors.ConversionError):
            if isinstance(exception.original, NotStrongEnough):
                await context.send_to(f":x: Nawet jeżeli posiadasz wymmagany poziom do tej komendy, nie możesz celować "
                                      f"w kogoś z wyższym/takim samym poziomem jak twój :("
                                      f"```{exception.original}```", delete_after=60)
                await context.message.delete(delay=60)
                return
            elif isinstance(exception.original, HierarchyError):
                await context.send_to(f":x: Masz wymagany poziom do tej komendy, ale nie mogę tago wykonać, "
                                      f"ponieważ twój cel jest wyżej ode mnie. Aby to naprawić, przenieś moją rolę "
                                      f"na samą górę listy ról serwera"
                                      f"```{exception.original}```")
                return
        elif isinstance(exception, discord.ext.commands.errors.BadArgument):
            await context.send_to(f":x: Jeden z argumentów jest niepoprawny: \n"
                                  f"**{exception}**", delete_after=60)
            await context.message.delete(delay=60)
            return
        elif isinstance(exception, discord.ext.commands.errors.ArgumentParsingError):
            await context.send_to(f":x: Wystąpił problem podczas analizowania komendy, upewnij się, że wszystkie czudzysłowy są poprawne: \n"
                                  f"**{exception}**", delete_after=60)
            await context.message.delete(delay=60)
            return
        elif isinstance(exception, discord.ext.commands.errors.BadUnionArgument):
            await context.send_to(f":x: Wystąpił problem podczas analizowania arugmentów, upewnij się, że są one poprawnego typu: \n"
                                  f"**{exception}**", delete_after=60)
            await context.message.delete(delay=60)
            return
        elif isinstance(exception, discord.ext.commands.errors.CommandOnCooldown):
            if context.message.author.id in [381243923131138058]:
                await context.reinvoke()
                return
            else:

                await context.send_to("Jesteś na cooldown'ie :(, spróbuj ponownie za {seconds} sekund".format(
                    seconds=round(exception.retry_after, 1)), delete_after=60)
                return
        elif isinstance(exception, discord.ext.commands.errors.TooManyArguments):
            await context.send_to(f":x: Dałeś mi za dużo argumentów. Być może powinieneś użyć cudzysłowów.\nUżyj komendy tak : `{context.prefix}{context.command.signature}`", delete_after=60)
            await context.message.delete(delay=60)
            return
        elif isinstance(exception, discord.ext.commands.NoPrivateMessage):
            await context.send_to('Ta komenda nie może zostać wykonana w wiadomości prywatnej.')
            return
        elif isinstance(exception, discord.ext.commands.errors.CommandInvokeError):
            # await context.author.send(f"Przepraszam, wystąpił błąd podczas przetwarzania twojej komendy. "
            #                           f"Sprawdź uprawnienia bota i spróbuj ponownie. Aby zgłosić bug, wyślij deweloperowi co następuje: ```py\n{exception}\n{''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))}\n```", delete_after=3600)
            # print(f'{exception}\n{''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))}\n')
            self.logger.error(f'Exeption in command {context.command}')
            try:
                self.logger.error(''.join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
            except Exception as ex:
                self.logger.error(exception)
            try:
                await context.author.send(f"Przepraszam, wystąpił błąd podczas przetwarzania twojej komendy. "
                                          f"Sprawdź uprawnienia bota i spróbuj ponownie. Aby zgłosić bug, zgłoś na Serwerze Wsparcia co następuje: ```py\n{exception}\n{''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))}\n```", delete_after=3600)
            except discord.HTTPException:
                await context.author.send(f"Przepraszam, wystąpił błąd podczas przetwarzania twojej komendy. "
                                          f"Sprawdź uprawnienia bota i spróbuj ponownie. Aby zgłosić bug, zgłoś na Serwerze Wsparcia co następuje: ```py\n{exception}\n```", delete_after=3600)
            finally:
                await context.message.delete(delay=3600)
            return
        elif isinstance(exception, discord.ext.commands.errors.NotOwner):
            return  # Jsk uses this
        else:
            self.logger.error('Ignoring exception in command {}:'.format(context.command))
            self.logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))


async def get_prefix(bot: BamboBot, message: discord.Message):
    forced_prefixes = ['b!', 'B!', '!b', '!B']

    if not message.guild:
        return commands.when_mentioned_or(*forced_prefixes)(bot, message)

    prefix_set = await bot.settings.get(message.guild, "bot_prefix")
    extras = [prefix_set] + forced_prefixes

    return commands.when_mentioned_or(*extras)(bot, message)
