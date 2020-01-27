# -*- coding: utf-8 -*-
import typing

import discord
from discord.ext import commands

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers import checks
from cogs.helpers.helpful_classes import LikeUser
from cogs.helpers.context import CustomContext


class Importation(commands.Cog):

    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.api = bot.api

    @commands.command()
    @commands.guild_only()
    @checks.have_required_level(4)
    @checks.bot_have_minimal_permissions()
    async def import_bans(self, ctx: 'CustomContext'):
        """
        Importuj bany z serwerowej listy banów. Jeżeli możliwe i dostępne, dołącza również powody z dziennika zdarzeń.

        Ta opcja dostępna jest tylko dla administratorów serwera i może zostać wykonana tylko raz na danym serwerze.
        :param ctx:
        :return:
        """
        with ctx.typing():
            if await self.bot.settings.get(ctx.guild, 'imported_bans'):
                await ctx.send("Już zaimportowałeś bany z serwera. "
                            "Jeżeli uważasz, że to błąd, skontaktuj się z deweloperem!")
                return
            else:
                await self.bot.settings.set(ctx.guild, 'imported_bans', True)

            await ctx.send(f"Ta operacja może potrwać trochę czasu, proszę czekać!")

            bans = await ctx.guild.bans()

            i = 0
            t = len(bans)
            for ban in bans:

                user = ban.user
                reason = ban.reason

                if not reason:
                    reason = "W dzienniku zdarzeń nie podano powodu"

                await self.api.add_action(ctx.guild, user, 'ban', reason,
                                          responsible_moderator=LikeUser(did=0, name="BanList Import", guild=ctx.guild))
                i += 1

            await ctx.send(f"Zaimportowano {i}/{t} banów z listy serwerowej.")

    # @commands.command()
    # @commands.guild_only()
    # @checks.have_required_level(4)
    # @checks.bot_have_permissions()
    # @commands.cooldown(rate=2, per=300, type=commands.BucketType.guild)
    # async def create_muted_role(self, ctx):
    #     """
    #     Create or update the muted role to disallow anyone with it to talk in any channel.

    #     :param ctx:
    #     :return:
    #     """

    #     ROLE_NAME = "GetBeaned_muted"
    #     REASON = f"create_muted_role command invoked by {ctx.message.author.name}"

    #     ctx.guild: discord.Guild

    #     current_permissions = ctx.message.guild.me.permissions_in(ctx.channel)

    #     if not current_permissions.manage_roles:
    #         await ctx.send(f"To run this, I additionally need the `manage_roles` permission, because I'll create/update the {ROLE_NAME} role.")
    #         return False

    #     if not current_permissions.manage_channels:
    #         await ctx.send(f"To run this, I additionally need the `manage_channels` permission, because I'll create/update the {ROLE_NAME} role.")
    #         return False

    #     logs_content = ["Creating the muted role, please wait", "Permissions check passed"]

    #     logs_message = await ctx.send("Creating the muted role, please wait")

    #     muted_role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME)

    #     if not muted_role:
    #         logs_content.append("Couldn't find the muted role, creating it...")
    #         muted_role = await ctx.guild.create_role(name=ROLE_NAME, reason=REASON)

    #     logs_content.append(f"The muted role ID is {muted_role.id}")

    #     await logs_message.edit(content="```" + '\n'.join(logs_content) + "```")

    #     text_overwrite = discord.PermissionOverwrite()
    #     text_overwrite.update(send_messages=False, add_reactions=False, create_instant_invite=False)

    #     voice_overwrite = discord.PermissionOverwrite()
    #     voice_overwrite.update(speak=False, create_instant_invite=False)

    #     logs_content.append("Adding a PermissionOverwrite into the server channels :")
    #     for channel in ctx.guild.channels:
    #         current_channel_permissions = ctx.message.guild.me.permissions_in(channel)
    #         if not isinstance(channel, discord.TextChannel) and not isinstance(channel, discord.VoiceChannel):
    #             logs_content.append(f"\tS #{channel.name} (not a text or voicechannel)")
    #             continue

    #         if not current_channel_permissions.manage_roles or not current_channel_permissions.manage_channels:
    #             logs_content.append(f"\tS #{channel.name} (no permissions there)")
    #             continue

    #         if isinstance(channel, discord.TextChannel):
    #             await channel.set_permissions(muted_role, overwrite=None, reason=REASON)
    #             await channel.set_permissions(muted_role, overwrite=text_overwrite, reason=REASON)
    #             logs_content.append(f"\tT #{channel.name}")
    #         elif isinstance(channel, discord.VoiceChannel):
    #             await channel.set_permissions(muted_role, overwrite=None, reason=REASON)
    #             await channel.set_permissions(muted_role, overwrite=voice_overwrite, reason=REASON)
    #             logs_content.append(f"\tV #{channel.name}")

    #     await logs_message.edit(content="```" + '\n'.join(logs_content) + "```", delete_after=60)
    #     await ctx.send("The muted role has been successfully created/updated.")
    @commands.command()
    @commands.guild_only()
    @checks.have_required_level(4)
    @checks.bot_have_permissions()
    @commands.cooldown(rate=2, per=300, type=commands.BucketType.guild)
    async def create_muted_role(self, ctx:' CustomContext', role_id:int = None):
        """
        Ustawia rolę `Muted`

        :param ctx:
        :return:
        """
        with ctx.typing():
            if not role_id:
                await ctx.send(f':x: Nie podano ID roli')
                return False

            ROLE_NAME = role_id
            REASON = f"Komenda create_muted_role wywołana przez {ctx.message.author.name}"

            ctx.guild: discord.Guild

            current_permissions = ctx.message.guild.me.permissions_in(ctx.channel)

            if not current_permissions.manage_roles:
                await ctx.send(f"Aby to wykonać, potrzebuję permisji `manage_roles`.")
                return False

            if not current_permissions.manage_channels:
                await ctx.send(f"Aby to wykonać, potrzebuję permisji `manage_channels`.")
                return False

            logs_content = ["Aktualizowanie roli `Muted`", "Kontrola permisji wykonana"]

            logs_message = await ctx.send("Aktualizowanie roli `Muted`, proszę czekać")
            # await ctx.send(f'Podane ID: {ROLE_NAME}')

            muted_role = discord.utils.get(ctx.guild.roles, id=ROLE_NAME)

            if not muted_role:
                logs_content.append("Nie znaleziono roli o podanym ID, sprawdź i powtórz komendę...")
                # muted_role = await ctx.guild.create_role(name=ROLE_NAME, reason=REASON)
                return False

            logs_content.append(f"Nazwa roli `Muted` to '{muted_role.name}'")
            logs_content.append(f"ID roli `Muted` to '{muted_role.id}'")

            await self.bot.settings.set(ctx.guild, 'muted_role_id', ROLE_NAME)

            await logs_message.edit(content="```" + '\n'.join(logs_content) + "```")

            text_overwrite = discord.PermissionOverwrite()
            text_overwrite.update(send_messages=False, add_reactions=False, create_instant_invite=False)

            voice_overwrite = discord.PermissionOverwrite()
            voice_overwrite.update(speak=False, create_instant_invite=False)

            logs_content.append("Nadpsywanie persmiji kanałów :")
            for channel in ctx.guild.channels:
                current_channel_permissions = ctx.message.guild.me.permissions_in(channel)
                if not isinstance(channel, discord.TextChannel) and not isinstance(channel, discord.VoiceChannel):
                    logs_content.append(f"\tS #{channel.name} (to nie kanał tekstowy lub głosowy)")
                    continue

                if not current_channel_permissions.manage_roles or not current_channel_permissions.manage_channels:
                    logs_content.append(f"\tS #{channel.name} (brak permisji)")
                    continue

                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(muted_role, overwrite=None, reason=REASON)
                    await channel.set_permissions(muted_role, overwrite=text_overwrite, reason=REASON)
                    logs_content.append(f"\tT #{channel.name}")
                elif isinstance(channel, discord.VoiceChannel):
                    await channel.set_permissions(muted_role, overwrite=None, reason=REASON)
                    await channel.set_permissions(muted_role, overwrite=voice_overwrite, reason=REASON)
                    logs_content.append(f"\tV #{channel.name}")

            await logs_message.edit(content="```" + '\n'.join(logs_content) + "```", delete_after=60)
            await ctx.send("Rola `Muted` została zaktualizowana pomyślnie.")


def setup(bot: 'BamboBot'):
    bot.add_cog(Importation(bot))

'''
Changes by me:
(1) Translated to polish
(2) Revamped the function of create_muted_role()
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Zmieniono działanie create_muted_role()
'''
