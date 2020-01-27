# -*- coding: utf-8 -*-
import time
import typing

import discord
from discord.ext import commands

from cogs.helpers import checks
from cogs.helpers.converters import ForcedMember

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext


class Meta(commands.Cog):

    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self._last_result = None
        self.sessions = set()
        self.api = bot.api

    @commands.command()
    @commands.guild_only()
    @checks.have_required_level(1)
    async def ping(self, ctx: 'CustomContext'):
        """Oblicza czas pingowania."""
        with ctx.typing():
            t_1 = time.perf_counter()
            await ctx.trigger_typing()  # tell Discord that the bot is "typing", which is a very simple request
            t_2 = time.perf_counter()
            time_delta = round((t_2-t_1)*1000)  # calculate the time needed to trigger typing
            await ctx.send("Pong. — Czas: {}ms".format(time_delta))  # send a message telling the user the calculated ping time

    def cleanup_code(self, content: str):
        """Automatycznie usuwa bloki kodowe z kodu."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @staticmethod
    def get_syntax_error(e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    @commands.command(hidden=True)
    @checks.have_required_level(8)
    async def refresh_user(self, ctx: 'CustomContext', whos: commands.Greedy[ForcedMember]):
        """Odśwież profil użytkownika na webinterfejsie."""
        with ctx.typing():
            for who in whos:
                await self.bot.api.add_user(who)
                await ctx.send_to(f"{who.name}: https://bambobot.herokuapp.com/users/{who.id}")

    @commands.command()
    @checks.have_required_level(1)
    async def channel_id(self, ctx: 'CustomContext'):
        """Pokazuje ID aktualnego kanału."""
        with ctx.typing():
            await ctx.send_to(f"ID {ctx.channel.mention} to {ctx.channel.id}")

    @commands.command(aliases=['fake_msg'])
    @checks.have_required_level(5)
    async def fake_message(self, ctx: 'CustomContext', where: typing.Optional[discord.TextChannel], who: ForcedMember, *, message:str):
        """Odśwież profil użytkownika na webinterfejsie."""
        with ctx.typing():
            avatar = await who.avatar_url.read()
            if where:
                channel = where
            else:
                channel = ctx.channel
            try:
                webhook = await channel.create_webhook(name=who.display_name, avatar=avatar, reason=f"Fałszywa wiadomość od {ctx.message.author.name}")
            except discord.Forbidden:
                await ctx.send_to("Brak permisji na stworzenie webhooka :(")
                return

            await webhook.send(message)
            await webhook.delete()

    @commands.command(aliases=['msg'])
    @checks.have_required_level(4)
    async def message(self, ctx: 'CustomContext', where: typing.Optional[discord.TextChannel], *, message: str):
        with ctx.typing():
            if where:
                channel = where
            else:
                channel = ctx.channel
            await channel.send(content=message)

    @commands.command(hidden=True)
    @checks.have_required_level(10)
    async def reload(self, ctx: 'CustomContext', *, module):
        '''Przeładowywuje moduł'''
        with ctx.typing():
            try:
                self.bot.reload_extension(module)
            except commands.ExtensionError as e:
                await ctx.send(f'{e.__class__.__name__}: {e}')
            except Exception as e:
                await ctx.send(f'{e.__class__.__name__}: {e}')
            else:
                await ctx.send('\N{OK HAND SIGN}')

    @commands.command(hidden=True, aliases=['logout', 'wyloguj'])
    @checks.have_required_level(8)
    async def shutdown(self, ctx: 'CustomContext'):
        '''Wyłącza bota'''
        with ctx.typing():
            await ctx.send("Restartuję bota..")
            try:
                await self.bot.close()
            except Exception as e:
                await ctx.send(f'`shutdown()` error: {e}')
            else:
                await ctx.send('\N{OK HAND SIGN}')

def setup(bot: 'BamboBot'):
    bot.add_cog(Meta(bot))


'''
Changes by me:
(1) Translated to polish
(2) Changed the url in refresh_user()
(3) Added an optional argument of `TextChannel` to fake_message()
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Zmieniono URL w refresh_user()
'''
