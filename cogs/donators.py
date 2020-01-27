# -*- coding: utf-8 -*-
import typing

from discord.ext import commands

from cogs.helpers import checks

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext


class Donators(commands.Cog):
    def __init__(self, bot: 'BamboBot'):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @checks.have_required_level(1)
    async def make_vip(self, ctx: 'CustomContext', guild_id:int):
        """
        Ustawia serwer jako serwer VIP
        """
        with ctx.typing():
            if not ctx.channel.id == 659484422491602944:
                await ctx.send("❌ Tej komendy można użyć tylko na specjalnym kanale")
                return

            guild = self.bot.get_guild(guild_id)
            if guild is None:
                await ctx.send(f"❌ Uh uh, nie znalazłem serwera o ID `{guild_id}` :( Spróbuj ponownie i upewnij się, że bot należy do podanego serwera.")
                return

            if ctx.author.id not in [guild.owner.id, 381243923131138058]:
                await ctx.send(f"❌ Uh uh, *nie* jesteś właścicielem serwera `{guild.name}`.")
                return

            await self.bot.settings.set(guild, 'vip', True)
            await ctx.send(f"👌 Dzięki {ctx.message.author.mention}, serwer {guild.name} (ID: `{guild.id}`) jest teraz serwerem VIP i może używać ustawień VIP.")


def setup(bot: 'BamboBot'):
    bot.add_cog(Donators(bot))

'''
Changes by me:
(1) Translated to polish
(2) Changed the ID of the checked channel
(3) Changed bot owner ID
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Zmionono ID kanału do sprawdzenia
(3) Zmieniono ID właściciela bota
'''
