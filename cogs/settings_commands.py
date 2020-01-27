# -*- coding: utf-8 -*-
import typing

import discord
from discord.ext import commands

from cogs.helpers import checks
from cogs.helpers.helpful_classes import LikeUser

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext


class Importation(commands.Cog):

    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.api = bot.api

    # assert staff_type in ['banned', 'trusted', 'moderators', 'admins']
    @commands.command(aliases=["addadmin", "dodajadmina", "dodaj_admina"])
    @commands.guild_only()
    @checks.have_required_level(4)
    async def add_admin(self, ctx: 'CustomContext', user: typing.Union[discord.Member, discord.Role]):
        """
        Dodaj Administratorów serwera. Mogą oni moderować serwer, ale również edytować powody innych moderatorów na webinterfejsie.

        Możesz zarządzać użytkownikami z dostępem w ustawieniach serwera na webinterfejsie. Zobacz `b!urls`.
        """
        with ctx.typing():
            if isinstance(user, discord.Role):
                user = LikeUser(did=user.id, name=f"[ROLE] {user.name}", guild=ctx.guild, discriminator='0000',
                                do_not_update=False)

            await self.api.add_to_staff(ctx.guild, user, 'admins')
            await ctx.send_to(':ok_hand: Zrobione. Możesz edytować personel na webinterfejsie.')

    @commands.command(aliases=["addmoderator", "addmod", "add_mod", "dodaj_moda", "dodajmoda"])
    @commands.guild_only()
    @checks.have_required_level(4)
    async def add_moderator(self, ctx: 'CustomContext', user: typing.Union[discord.Member, discord.Role]):
        """
        Dodaj Moderatora na tym serwerze. Moderator może ostrzegać, wyrzucać, banować...

        Możesz zarządzać użytkownikami z dostępem w ustawieniach serwera na webinterfejsie. Zobacz `b!urls`.
        """
        with ctx.typing():
            if isinstance(user, discord.Role):
                user = LikeUser(did=user.id, name=f"[ROLE] {user.name}", guild=ctx.guild, discriminator='0000',
                                do_not_update=False)

            await self.api.add_to_staff(ctx.guild, user, 'moderators')
            await ctx.send_to(':ok_hand: Zrobione. Możesz edytować personel na webinterfejsie.')

    @commands.command(aliases=["addtrusted", "addtrustedmember", "add_trusted", "dodajzaufanego", "dodaj_zaufanego"])
    @commands.guild_only()
    @checks.have_required_level(4)
    async def add_trusted_member(self, ctx: 'CustomContext', user: typing.Union[discord.Member, discord.Role]):
        """
        Dodaj Zaufanego Członka. Zaufany może wykonywać podstawowe akcje, takie jak notowanie, ostrzeganie czy wyrzucanie.

        Możesz zarządzać użytkownikami z dostępem w ustawieniach serwera na webinterfejsie. Zobacz `b!urls`.
        """
        with ctx.typing():
            if isinstance(user, discord.Role):
                user = LikeUser(did=user.id, name=f"[ROLE] {user.name}", guild=ctx.guild, discriminator='0000',
                                do_not_update=False)

            await self.api.add_to_staff(ctx.guild, user, 'trusted')
            await ctx.send_to(':ok_hand: Zrobione. Możesz edytować personel na webinterfejsie.')

    @commands.command(aliases=["add_banned", "addbanned", "addbannedmember", "dodaj_zbanowanego", "dodajzbanowanego"])
    @commands.guild_only()
    @checks.have_required_level(4)
    async def add_banned_member(self, ctx: 'CustomContext', user: typing.Union[discord.Member, discord.Role]):
        """
        Zbanuj członka w bocie na tym serwerze. Dostanie karę w AutoModzie i nie będzie mógł używać większości komend bota. 

        Możesz zarządzać użytkownikami z dostępem w ustawieniach serwera na webinterfejsie. Zobacz `b!urls`.
        """
        with ctx.typing():
            await self.api.add_to_staff(ctx.guild, user, 'banned')
            await ctx.send_to(':ok_hand: Zrobione. Możesz edytować personel na webinterfejsie.')

    @commands.command(aliases=["me", "ja"])
    # @commands.guild_only()
    # @checks.have_required_level(1)
    async def urls(self, ctx, user: discord.Member = None):
        """
        Zobacz swój profil oraz inne przydatne linki.
        """
        with ctx.typing():
            await self.api.add_user(ctx.message.author)
            await self.api.add_user(user) if user else None
            if not ctx.guild:
                user_id = ctx.author.id
                await ctx.send_to(f'**Pomocne URLe:**\n'
                                f' - **Strona Bota:** https://bambobot.herokuapp.com \n'
                                f' - **Twój profil:** https://bambobot.herokuapp.com/users/{user_id}')
            else:
                await self.api.add_guild(ctx.guild)        

                user_id = user.id if user else ctx.message.author.id
                if user:
                    await ctx.send_to(f"**Pomocne URLe**:\n"
                                    f"- **Profil użytkownika {user.name} na serwerze**: https://bambobot.herokuapp.com/users/{ctx.guild.id}/{user_id}\n")
                else:
                    await ctx.send_to(f"**Pomocne URLe**:\n"
                                    f"- **Strona serwera**: https://bambobot.herokuapp.com/guilds/{ctx.guild.id} \n"
                                    f"- **Twój profil serwera**: https://bambobot.herokuapp.com/users/{ctx.guild.id}/{user_id}\n"
                                    f"- **Twój globalny profil**: https://bambobot.herokuapp.com/users/{user_id}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.guild):
        self.bot.logger.info(f"New server joined! {guild.id} - {guild.name} ({guild.member_count} members)")
        # print('adding new guild')
        await self.api.add_guild(guild)


def setup(bot: 'BamboBot'):
    bot.add_cog(Importation(bot))

'''
Changes by me:
(1) Translated to polish
(2) Changed urls() so that one can see the urls of a given member
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Zmienione urls() w taki sposób, że użytkownik może zobaczyć URLe danego członka
'''