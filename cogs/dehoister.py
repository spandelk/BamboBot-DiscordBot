# -*- coding: utf-8 -*-
import typing

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

import discord
from discord.ext import commands

from cogs.helpers import checks
from cogs.helpers.helpful_classes import LikeUser, FakeMember
from cogs.helpers.level import get_level
from cogs.helpers.actions import full_process, note, warn
from cogs.helpers.context import CustomContext

import string
polish_letters = 'ąćęłńóśźżĄĆĘŁŃÓŚŹŻ'
all_letters = string.ascii_letters + polish_letters

class FakeCtx:
    def __init__(self, guild: discord.Guild, bot: 'BamboBot'):
        self.guild = guild
        self.bot = bot


class Dehoister(commands.Cog):
    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.bypass = bot.cache.get_cache("dehoister_bypass", expire_after=5, strict=True, default=list)

    async def dehoist_user_in_guild(self, user: typing.Union[discord.User, discord.Member], guild: discord.Guild) -> bool:
        if await self.bot.settings.get(guild, "dehoist_enable"):
            self.bot.logger.info(f"Running dehoister in `{guild}`")
            member = guild.get_member(user.id)
            if user.id in self.bypass[guild]:
                return False

            if await get_level(FakeCtx(guild, self.bot), member) >= int(await self.bot.settings.get(guild, "dehoist_ignore_level")):
                return False

            intensity = int(await self.bot.settings.get(guild, "dehoist_intensity"))

            previous_nickname = member.display_name
            new_nickname = previous_nickname

            if intensity >= 1:
                for pos, char in enumerate(new_nickname):
                    if char in ["!", "\"", "#", "$", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/"]:
                        new_nickname = new_nickname[1:]
                        continue
                    else:
                        break

            if intensity >= 2:
                # for pos, char in enumerate(new_nickname):
                #     if char not in all_letters:
                #         new_nickname = new_nickname[1:]
                #         continue
                #     else:
                #         break
                while True:
                    for pos, char in enumerate(new_nickname):
                        if (new_nickname[:1] not in all_letters) or (new_nickname[1:2] not in all_letters) or (new_nickname[2:3] not in all_letters):
                            # print(f'{pos} :: {char}')
                            new_nickname = new_nickname[1:] + new_nickname[:1]
                            # print(new_name)
                            continue
                        else:
                            break
                    if (new_nickname[:1] in all_letters) and (new_nickname[1:2] in all_letters) and (new_nickname[2:3] in all_letters):
                        # shift_chars = False
                        break
                    elif previous_nickname == new_nickname:
                        new_nickname = ''
                        # shift_chars = False
                        break

            if intensity >= 3:
                new_nickname += "zz"

                while new_nickname.lower()[:2] == "aa":
                    new_nickname = new_nickname[2:]

                new_nickname = new_nickname[:-2]

            if previous_nickname != new_nickname:
                if len(new_nickname) == 0:
                    new_nickname = "zzz_Łatwy_Nick"

                reason = f"Automatyczny DeHoist nazwy użytkownika z `{previous_nickname}` na `{new_nickname}`. " \
                         f"Proszę starać się nie używać znaków specjalnych i/lub cyfr na początku nazwy."

                await member.edit(nick=new_nickname, reason=reason)


                self.bypass[member.guild].append(member.id)
                self.bypass.reset_expiry(member.guild)

                actions_to_take = {
                    "note": note,
                    "warn": warn,
                    "message": None,
                    "nothing": None
                }
                action_name = await self.bot.settings.get(guild, "dehoist_action")

                action_coroutine = actions_to_take[action_name]

                if action_coroutine:
                    moderator = LikeUser(did=3, name="DeHoister", guild=guild)
                    await full_process(self.bot, action_coroutine, member, moderator, reason)

                if action_name != "nothing":

                    try:
                        await member.send(f"Twoja nazwa została zDeHoist'owana na {guild.name}. "
                                          f"Proszę starać się nie używać znaków specjalnych i/lub cyfr na początku nazwy. "
                                          f"Dzięki! Twoja nowa nazwa to `{new_nickname}`")
                    except discord.Forbidden:
                        pass

                return True
            else:
                return False
        else:
            return False

    async def dehoist_user(self, user: discord.User):
        for guild in self.bot.guilds:
            if user in guild.members:
                await self.dehoist_user_in_guild(user, guild)

    @commands.command(aliases=["rename_user", "rename_member"])
    @commands.guild_only()
    @checks.have_required_level(2)
    @checks.bot_have_permissions()
    @commands.cooldown(rate=10, per=30, type=commands.BucketType.guild)
    async def rename(self, ctx: 'CustomContext', user: discord.Member, *, name: str = None):
        with ctx.typing():
            await ctx.send(f"Przetwarzanie, proszę czekać.")

            self.bypass[ctx.guild].append(user.id)
            self.bypass.reset_expiry(ctx.guild)
            await user.edit(nick=name)
            await ctx.send(f"Nazwa zmieniona!")

    @commands.command()
    @commands.guild_only()
    @checks.have_required_level(4)
    @checks.bot_have_permissions()
    @commands.cooldown(rate=1, per=300, type=commands.BucketType.guild)
    async def dehoist_users(self, ctx: 'CustomContext'):
        with ctx.typing():
            guild = ctx.guild
            dehoisted_users_count = 0

            await ctx.send(f"Przetwarzanie, proszę czekać.")

            for member in guild.members:
                dehoisted_users_count += int(await self.dehoist_user_in_guild(member, guild))

            await ctx.send(f"{dehoisted_users_count} użytkowników zostało zDeHoist'owanych.")

    @commands.command(aliases=["dehoist_user", "dehoist_member"])
    @commands.guild_only()
    @checks.have_required_level(3)
    @checks.bot_have_permissions()
    @commands.cooldown(rate=10, per=30, type=commands.BucketType.guild)
    async def dehoist(self, ctx: 'CustomContext', users: commands.Greedy[FakeMember]):
        with ctx.typing():
            await ctx.send(f"Przetwarzanie, proszę czekać...", delete_after=60)
            logs = f':ok_hand: Nazwy zmienione!'
            for user in users:
                old_name = user.display_name
                # await user.edit(nick=None)
                new_name = user.display_name
                if new_name == old_name:
                    await self.dehoist_user_in_guild(user, user.guild)
                    new_name = user.display_name
                logs += (f'\n[{user.mention}] `{old_name}` -->> `{new_name}`')
            await ctx.send(logs)
            # await ctx.send(f":ok_hand: Nazwa zmieniona!\n[{user.mention}] `{old_name}` :arrow_right: `{new_name}`")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            self.bot.logger.info(f"Member `{after}` changed nick (`{before.nick}` -> `{after.nick}`), running dehoister")

            await self.dehoist_user_in_guild(after, after.guild)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.name != after.name:
            self.bot.logger.info(f"User {after} changed name (`{before.name}`-> `{after.name}`), running dehoister")

            await self.dehoist_user(after)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        self.bot.logger.debug(f"User {member} joined {member.guild}, running dehoister")
        await self.dehoist_user_in_guild(member, member.guild)


def setup(bot: 'BamboBot'):
    bot.add_cog(Dehoister(bot))

'''
Changes by Me:
(1) Added support for polish characters
(2) Changed removing special symbols from the begining of a user nickname to shifing them to the end of it
(3) Translated the text to polish
=====
Moje zmiany:
(1) Dodano wsparcie dla polskich znaków
(2) Zmieniono usuwanie znaków specjalnych z począku nazwy użytkownika na przeznoszenie ich na jej koniec
(3) Przetłumaczono na polski
'''
