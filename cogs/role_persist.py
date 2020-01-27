# -*- coding: utf-8 -*-
import datetime
import typing

import discord
from discord.ext import commands

from cogs.helpers import checks

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext

class RolePersist(commands.Cog):
    """
    Przywracanie ról (RolePersist)
    """

    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.api = bot.api

    async def is_role_persist_enabled(self, guild:discord.Guild):
        return await self.bot.settings.get(guild, "rolepersist_enable") and await self.bot.settings.get(guild, "vip")

    async def get_restorable_roles(self, guild, roles):
        my_top_role = guild.me.top_role

        restorable_roles = []
        for role in roles:
            if role < my_top_role:
                restorable_roles.append(my_top_role)

    async def log_role_persist(self, guild, member, roles_to_give):
        roles_to_give_names = [r.name for r in roles_to_give]
        roles_to_give_mentions = [r.mention for r in roles_to_give]


        reason = f"Przywracanie ról dla {member.name}#{member.discriminator} w {guild}: {len(roles_to_give)} role do nadania: {roles_to_give_names}"
        self.bot.logger.info(reason)

        logging_channel = await self.bot.get_cog('Logging').get_logging_channel(member.guild, "logs_rolepersist_channel_id")

        if not logging_channel:
            return 'No logging channel configured for RolePersist.'
        if not await self.bot.get_cog('Logging').perms_okay(logging_channel):
            return 'No permissions to log'
        embed = discord.Embed(title=f"{member.name}#{member.discriminator} dołączył",
                              colour=discord.Colour.dark_blue(),
                              description=f"Nadano {len(roles_to_give)} ról\n"
                                          f"{', '.join(roles_to_give_mentions)}"
                              )

        embed.set_author(name="Przywrócenie Ról", url="https://bambobot.herokuapp.com")  # , icon_url="ICON_URL_DELETE")

        embed.timestamp = datetime.datetime.utcnow()

        embed.set_footer(text="Role przywrócone",
                         icon_url="https://cdn.discordapp.com/avatars/552611724419792907/fded780340148db800e317cb4b417b88.png")

        await logging_channel.send(embed=embed)

    @commands.command(hidden=True)
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(8)
    async def clear_rp(self, ctx: 'CustomContext'):
        async with ctx.typing():
            guild = ctx.guild

            count = 0
            m_count = len(guild.members)
            cmc = 0
            hits = 0
            logs = ''
            to_delete = []
            msg = await ctx.send('**Usuwam niepotrzebne wpisy zapisanych ról...** \n\n\nPobieram wszystkie wpisy dla serwera...')
            res = await self.api.get_stored_roles(guild, self.bot.user)
            rows = res['rows']
            rows_len = len(rows)
            logs = (f'**Usuwam niepotrzebne wpisy zapisanych ról...** \n\n\n'
                    f'Ilość wpisów dla serwera: `{rows_len}` \n\n'
                    f'Porównuję listę użytkowników serwera do listy wpisów...')
            await msg.edit(content=logs)
            for i, member in enumerate(guild.members, start=1):
                if member.id in rows:
                    cmc = i
                    hits += 1
                    to_delete.append(member.id)
                if i % 100 == 0:
                    await msg.edit(content=logs + f'\nSprawdzono `{i}/{m_count}` członków. \nTrafiono `{hits}/{rows_len}` porównań')
            logs = (f'**Usuwam niepotrzebne wpisy zapisanych ról...** \n\n\n'
                    f'Ilość wpisów dla serwera: `{rows_len}` \n'
                    f'Porównano listę użytkowników do listy wpisów. \n'
                    f'Sprawdzono `{cmc}/{m_count}` członków. \n'
                    f'Trafiono `{hits}/{rows_len}` porównań.\n\n'
                    f'Usuwam wpisy z bazy...')
            await msg.edit(content=logs)
            for i, member_id in enumerate(to_delete, start=1):
                member = guild.get_member(member_id)
                await self.api.delete_stored_roles(guild, member)
                count += 1
                if i % 100 == 0:
                    await msg.edit(content=logs + f'\nUsunięto `{count}/{len(to_delete)}` wpisów...')
            logs = (f'**Usunięto niepotrzebne wpisy zapisanych ról!** \n\n\n'
                    f'Ilość wpisów dla serwera: `{rows_len}` \n'
                    f'Porównano listę użytkowników do listy wpisów. \n'
                    f'Sprawdzono `{cmc}/{m_count}` członków. \n'
                    f'Trafiono `{hits}/{rows_len}` porównań.\n\n'
                    f'Usunięto wpisy z bazy.\n'
                    f'Usunięto `{count}/{len(to_delete)}` wpisów.')
            await msg.edit(content=logs)

            # for i, member in enumerate(guild.members, start=1):
            #     roles = await self.api.get_stored_roles(guild, member)
            #     cmc = i
            #     if len(roles) == 0:
            #         pass
            #     else:
            #         await self.api.delete_stored_roles(guild, member)
            #         count += 1
            #     await msg.edit(content=f'🔁 Przetworzono `{i}/{m_count}` członków. \n⏰ Usunięto `{count}` wpisów...')
                
            # await msg.edit(content=f'🔁 Przetworzono `{cmc}/{m_count}` członków. \n✅ Usunięto `{count}` wpisów!')
    

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        if not await self.is_role_persist_enabled(guild):
            return

        # print('getting stored roles')
        roles_to_give = await self.api.get_stored_roles(guild, member)
        # print(f'roles_to_give = {roles_to_give}')
        if len(roles_to_give) < 2:
            return
        await self.api.delete_stored_roles(guild, member)
        await member.edit(roles=roles_to_give, reason="Przywracanie ról")
        await self.log_role_persist(guild, member, roles_to_give)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        if not await self.is_role_persist_enabled(guild):
            return
        # print('saving roles to give')
        self.bot.logger.debug(f"Użytkownik `{member}` opuścił serwer `{member.guild}`")
        if len(member.roles) == 1:
            self.bot.logger.debug(f'Użytkownik `{member}` miał tylko jedną rolę (@everyone) - nie zapisuję')
            return
        elif len(member.roles) > 1:
            self.bot.logger.debug(f'Zapisuję {len(member.roles)} ról')
            await self.api.save_roles(guild, member, member.roles)
        # print(f'member.roles = {member.roles}')




def setup(bot: 'BamboBot'):
    bot.add_cog(RolePersist(bot))

'''
Changes by me:
(1) Translated to polish
(2) Changed embed url=
(3) Changed embed icon_url=
(4) Changed role persist so that the roles are not stored if the user had only one role (the default @everyone)
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Zmieniono url= osadzenia
(3) Zmieniono icon_url= osadzenia
(4) Zmieniono trwałość ról w taki sposób, że role użytkownika nie są zapisywane, jeżeli posiadał on tylko jedną rolę (domyślną @everyone)
'''