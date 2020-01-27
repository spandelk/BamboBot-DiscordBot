# -*- coding: utf-8 -*-
import asyncio
import datetime
import typing

import discord
from discord.ext import commands

from cogs.helpers import checks
from cogs.helpers import time
from cogs.helpers.actions import full_process, unban, note, warn, kick, softban, ban, mute, unmute, sponsor, donator, kodzik
from cogs.helpers.converters import ForcedMember, BannedMember, InferiorMember
from cogs.helpers.helpful_classes import FakeMember, LikeUser
from cogs.helpers.level import get_level
from cogs.logging import save_attachments
import pytz

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext

# timezone = pytz.timezone("Europe/Warsaw")
timezone = pytz.timezone("Etc/GMT-1")

class Mod(commands.Cog):
    """
    Komendy moderacyjne

    Tutaj znajdziesz takie komendy jak do banowania, wyrzucania, ostrzegania itp.
    """

    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.api = bot.api

    async def parse_arguments(self, ctx: 'CustomContext', users: typing.List[typing.Union[discord.Member, discord.User, ForcedMember, LikeUser]]):
        with ctx.typing():
            if len(users) == 0:
                raise commands.BadArgument("Nie podano użytkownika")

            if len(users) != len(set(users)):
                raise commands.BadArgument("Niektórych użytkowników widziano podwójnie w komendzie. Sprawdź i spróbuj ponownie.")

            for user in users:

                if user.id == ctx.author.id:
                    raise commands.BadArgument("Celowanie w siebie samego...")
                elif user.id == self.bot.user.id:
                    raise commands.BadArgument("Celowanie w BamboBota...")

                if isinstance(user, discord.Member):
                    can_execute = ctx.author == ctx.guild.owner or \
                                ctx.author.top_role > user.top_role

                    if can_execute:
                        if user.top_role > ctx.guild.me.top_role:
                            raise commands.BadArgument(f'Nie możesz wykonać tej akcji na `{user.name}` z powodu hierarchii ról pomiędzy botem a `{user.name}`.')
                    else:
                        raise commands.BadArgument(f'Nie możesz wykonać tej akcji na `{user.name}` z powodu hierarchii ról.')

            if len(users) >= 2:

                list_names = ('`' + ', '.join([user.name for user in users]) + '`')
                await ctx.send_to(f"⚠️ Zamierzasz działać na wielu użytkownikach naraz, jesteś pewien, że chcesz tego dokonać ?\n"
                                f"**Lista użytkowników:** {list_names}")

                await ctx.send_to("Aby potwierdzić, napisz `ok` w ciągu następnych 15 sekund")

                def check(m):
                    return m.content == 'ok' and m.channel == ctx.channel and m.author == ctx.author

                try:
                    await self.bot.wait_for('message', check=check, timeout=15.0)
                except asyncio.TimeoutError:
                    await ctx.send_to("❌ Nic nie robię")
                    raise commands.BadArgument("Anulowane wykonanie")

            attachments_saved_urls, attachments_unsaved_urls = await save_attachments(self.bot, ctx.message)

            if len(attachments_saved_urls) > 0:
                attachments_saved_url = attachments_saved_urls[0]
            elif len(attachments_unsaved_urls) > 0:
                attachments_saved_url = attachments_unsaved_urls[0]
            else:
                attachments_saved_url = None

            return attachments_saved_url

    async def check_reason(self, ctx: 'CustomContext', reason: str, attachments_saved_url: str):
        with ctx.typing():
            level = await get_level(ctx, ctx.message.author)

            justification_level_setting = await ctx.bot.settings.get(ctx.guild, "force_justification_level")

            inferior_levels = {"1": 0, "2": 3, "3": 6}

            if level < inferior_levels[justification_level_setting]:
                if attachments_saved_url is None:
                    raise commands.BadArgument("Musisz uzasadnić swoje akcje, dołączając zrzut ekranu do komendy")
                if len(reason) < 10:
                    raise commands.BadArgument("Musisz uzasadnić swoje akcje, dołączając szczegółowy powód do komendy")

    async def run_actions(self, ctx, users, reason, attachments_saved_url, action, duration=None, tier=None):
        with ctx.typing():
            cases_urls = []
            # print(f'attachments_saved_url: {attachments_saved_url}')
            if duration:
                reason = reason + f"|\nCzas trwania: {time.human_timedelta(duration.dt, source=datetime.datetime.utcnow())}"

            for user in users:
                act = await full_process(ctx.bot, action, user, ctx.author, reason, tier, attachement_url=attachments_saved_url)
                cases_urls.append(act['url'])

                if duration:
                    # print(f'duration -> {duration}')
                    # print(f'duration.dt -> {duration.dt}')
                    utc_dt = pytz.utc.localize(duration.dt)
                    # print(f'utd_dt -> {utc_dt}')
                    dur = utc_dt.astimezone(timezone).replace(tzinfo=None)
                    # dur += datetime.timedelta(hours=1)
                    # print(f'dur -> {dur}')
                    # print(f'dur.dt -> {dur.dt}')
                    if action is mute:
                        await self.api.create_task("unmute", arguments={"target": user.id, "guild": ctx.guild.id, "reason": f"Czas minął | Zobacz sprawę #{act['case_number']} po szczegóły"},  execute_at=dur)
                    elif action is ban:
                        await self.api.create_task("unban", arguments={"target": user.id, "guild": ctx.guild.id, "reason": f"Czas minął | Zobacz sprawę #{act['case_number']} po szczegóły"}, execute_at=dur)
                    elif action is sponsor:
                        await self.api.create_task("rm_sponsor", arguments={"target": user.id, "guild": ctx.guild.id, "reason": f"Czas minął | Zobacz sprawę #{act['case_number']} po szczegóły"}, execute_at=dur)
                    elif action is donator:
                        await self.api.create_task("rm_donator_x", arguments={"target": user.id, "guild": ctx.guild.id, "reason": f"Czas minął | Zobacz sprawę #{act['case_number']} po szczegóły"}, execute_at=dur)
                    elif action is kodzik:
                        await self.api.create_task("rm_kodzik", arguments={"target": user.id, "guild": ctx.guild.id, "reason": f"Czas minął | Zobacz sprawę #{act['case_number']} po szczegóły"}, execute_at=dur)


            await ctx.send(f":ok_hand: - Zobacz {', '.join(cases_urls)} po szczegóły")


    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(3)
    async def unban(self, ctx: 'CustomContext', banned_users: commands.Greedy[BannedMember], *,
                    reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        Odbanowywuje użytkownika. Musi on być aktualnie zbanowany, aby ta komenda zadziałała.

        Użycie b!unban [członek/członkowie] <powód>.

        [członek] może być jako ID lub jego nazwa.
        <powód> to powód unbana.
        """
        with ctx.typing():
            attachments_saved_url = await self.parse_arguments(ctx, users=[b.user for b in banned_users])
            cases_urls = []

            for ban in banned_users:
                # ban is in fact a guild.BanEntry recorvered from the ban list.
                on = ban.user
                ban_reason = ban.reason

                if ban_reason:
                    reason += "\nTen użytkownik został wcześniej zbanowany z następującego powodu: " + str(ban_reason)

                if len(reason) == 0:
                    reason = None

                on_member = FakeMember(guild=ctx.guild, user=on)

                act = await full_process(ctx.bot, unban, on_member, ctx.author, reason, attachement_url=attachments_saved_url)
                cases_urls.append(act['url'])

            await ctx.send(f":ok_hand: - Zobacz {', '.join(cases_urls)} po szczegóły")


    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(3)
    async def sponsor(self, ctx: 'CustomContext', tier:typing.Optional[int], users: commands.Greedy[ForcedMember], *,
                      reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        Nadaje rolę Sponsora

        Użycie b!sponsor [poziom] [członek/członkowie]

        [poziom] 1, 2, 3 lub 4
        [członek] może być jako ID lub jego nazwa.
        """
        with ctx.typing():
            ROLE_id = await self.bot.settings.get_special(ctx.guild, 'zjednoczeni_sponsor_00')
            if ROLE_id is None or ROLE_id == 0:
                await ctx.send_to(f"❌ Rola Sponsorów nie jest ustawiona. Ustaw ją na webinterfejsie.")
                return False

            role = await commands.RoleConverter().convert(ctx, ROLE_id)
            if role is None:
                await ctx.send_to(f"❌ Rola Sponsorów nie jest ustawiona. Ustaw ją na webinterfejsie.")
                return False

            attachments_saved_url = await self.parse_arguments(ctx, users=users)
            # duration: time.FutureTime = time.human_timedelta
            # duration = time.UserFriendlyTime().convert(ctx, '31d')
            duration = time.FutureTime('31d')

            if not type(tier) == int:
                await ctx.send_to(f'❌ Podany przez ciebie poziom `{tier}` jest niepoprawny, lub wcale go nie podałeś.')
                return False
            if tier < 1 or tier is None or tier > 4:
                await ctx.send_to(f'❌ Podany przez ciebie poziom `{tier}` jest niepoprawny, lub wcale go nie podałeś.')
                return False

            reason = (f'Sponsor poziom {tier} | ' + reason)
            await self.run_actions(ctx, users, reason, attachments_saved_url, sponsor, duration=duration, tier=tier)

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(3)
    async def donator(self, ctx: 'CustomContext', tier:typing.Optional[int], users: commands.Greedy[ForcedMember], *,
                      reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        Nadaje rolę Donatora

        Użycie b!donator [poziom] [członek/członkowie]

        [poziom] 1, 2, 3
        [członek] może być jako ID lub jego nazwa.
        """
        with ctx.typing():
            ROLE_id = await self.bot.settings.get_special(ctx.guild, 'zjednoczeni_donator_00')
            if ROLE_id is None or ROLE_id == 0:
                await ctx.send_to(f"❌ Rola Donatorów nie jest ustawiona. Ustaw ją na webinterfejsie.")
                return False

            role = await commands.RoleConverter().convert(ctx, ROLE_id)
            if role is None:
                await ctx.send_to(f"❌ Rola Donatorów nie jest ustawiona. Ustaw ją na webinterfejsie.")
                return False

            attachments_saved_url = await self.parse_arguments(ctx, users=users)
            # duration: time.FutureTime = time.human_timedelta
            # duration = time.UserFriendlyTime().convert(ctx, '31d')
            # duration = time.FutureTime('31d')        

            if not type(tier) == int:
                await ctx.send_to(f'❌ Podany przez ciebie poziom `{tier}` jest niepoprawny, lub wcale go nie podałeś.')
                return False
            if tier < 1 or tier is None or tier > 500:
                await ctx.send_to(f'❌ Podany przez ciebie poziom `{tier}` jest niepoprawny, lub wcale go nie podałeś.')
                return False

            if tier == 1 or 5 <= tier <= 99:
                duration = time.FutureTime('31d')
                tier = 1
                reason = (f'Donator')
            elif tier == 2 or 100 <= tier <= 499:
                tier = 2
                duration = None
                reason = 'Donator+'
            elif tier == 3 or tier == 500:
                tier = 3
                duration = None
                reason = 'Donator Legenda'

            # reason = (f'Donator poziom {tier} | ' + reason)
            await self.run_actions(ctx, users, reason, attachments_saved_url, donator, duration=duration, tier=tier)

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(3)
    async def kodzik(self, ctx: 'CustomContext', users: commands.Greedy[ForcedMember], *,
                     reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        Nadaje rolę Wspierającego w Sklepie

        Użycie b!kodzik [członek/członkowie]

        [członek] może być jako ID lub jego nazwa.
        """
        with ctx.typing():
            # print('[STAGE 1]')
            ROLE_TO_GET = int(await self.bot.settings.get_special(ctx.guild, 'zjednoczeni_kodzik'))
            # print('[STAGE 1] Pass')
            # print('[STAGE 2]')
            if ROLE_TO_GET == 0:
                await ctx.send_to(f"❌ Rola Wspierającego w Sklepie nie jest ustawiona. Ustaw ją na webinterfejsie.")
                # print('[STAGE 2] Fail')
                return False
            # print('[STAGE 2] Pass')
            
            # print('[STAGE 3]')
            ROLE_TO_GET = str(ROLE_TO_GET)
            try:
                ROLE = await commands.RoleConverter().convert(ctx, ROLE_TO_GET)
            except commands.BadArgument:
                await ctx.send_to(f"❌ Rola Wspierającego w Sklepie jest ustawiona niepoprawnie. Ustaw ją na webinterfejsie.")
                return False

            # print('[STAGE 3] Pass')
            # if ROLE is None:
            #     await ctx.send_to(f"❌ Rola Wspierającego w Sklepie nie jest ustawiona. Ustaw ją na webinterfejsie.")
            #     return False
            
            attachments_saved_url = await self.parse_arguments(ctx, users=users)
            duration = time.FutureTime('14d')
            reason = (f'Wspierający w Sklepie | ' + reason)
            await self.run_actions(ctx, users, reason, attachments_saved_url, kodzik, duration=duration)

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(3)
    async def unmute(self, ctx: 'CustomContext', users: commands.Greedy[ForcedMember], *,
                     reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        Usuwa wyciszenie danemu członkowi. Wyciszenie uniemożliwia użytkownikowi pisania/mówienia na dowolnym kanale.
        Użycie tej komendy wymaga ustawienia roli `Muted`. Możesz tego dokonać używająć b!create_muted_role [id roli]

        Jeżelli progi są włączone, wyciszenie danego członka może doprowadzić do jego automatycznego wyrzucenia.

        Użycie b!unmute [członek/członkowie] <powód>.

        [członek] może być jego ID, nazwa#dyskryminator albo wzmianką.
        <powód> to twój powód wyciszenia.
        """
        with ctx.typing():
            # ROLE_NAME = "GetBeaned_muted"
            ROLE_NAME = await self.bot.settings.get(ctx.guild, 'muted_role_id')
            # muted_role = discord.utils.get(ctx.guild.roles, id=ROLE_NAME)
            muted_role = await commands.RoleConverter().convert(ctx, ROLE_NAME)

            if muted_role is None:
                await ctx.send_to(f"❌ Rola `Muted` nie jest ustawiona. Ustaw ją przy pomocy `{ctx.prefix}create_muted_role id_roli`.")
                return False

            attachments_saved_url = await self.parse_arguments(ctx, users=users)

            await self.run_actions(ctx, users, reason, attachments_saved_url, unmute)

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(2)
    async def note(self, ctx: 'CustomContext', users: commands.Greedy[ForcedMember], *,
                   reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False)):
        """
        Zanotuj danego członka. Notatka nie robi nic poza przechowywaniem informacji o danym użytkowniku.

        Użycie b!note [członek/członkowie] [powód].

        [członek] może być jego ID, nazwa#dyskryminator albo wzmianką.
        [powód] to twój powód notatki.
        """
        with ctx.typing():
            # Nothing to do here.

            attachments_saved_url = await self.parse_arguments(ctx, users=users)

            await self.run_actions(ctx, users, reason, attachments_saved_url, note)

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(2)
    async def warn(self, ctx: 'CustomContext', users: commands.Greedy[ForcedMember], *,
                   reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        Ostrzeż członka. Jeżeli progi są włączone, ostrzeżenie użytkownika może doprowadzić do gorszych akcji, takich jak wyrzucenie czy zbanowanie.

        Użycie b!warn [członek/członkowie] <powód>.

        [członek] może być jego ID, nazwa#dyskryminator albo wzmianką.
        <powód> to twój powód ostrzeżenia.
        """
        with ctx.typing():
            attachments_saved_url = await self.parse_arguments(ctx, users=users)
            await self.check_reason(ctx, reason, attachments_saved_url)

            await self.run_actions(ctx, users, reason, attachments_saved_url, warn)

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(3)
    async def mute(self, ctx: 'CustomContext', duration:typing.Optional[time.FutureTime], users: commands.Greedy[InferiorMember], *,
                   reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        Wycisza danego członka. Wyciszenie uniemożliwia użytkownikowi pisania/mówienia na dowolnym kanale.
        Użycie tej komendy wymaga ustawienia roli `Muted`. Możesz tego dokonać używająć b!create_muted_role [id roli]

        Jeżelli progi są włączone, wyciszenie danego członka może doprowadzić do jego automatycznego wyrzucenia.

        Użycie b!mute <czas trwania> [członek/członkowie] <powód>.

        <czas trwania> to czas do wygaśnięcia wyciszenia (na przykład, 1h, 1d, 1w, 3m, ...)
        [członek] może być jego ID, nazwa#dyskryminator albo wzmianką.
        <powód> to twój powód wyciszenia

        Jeżeli nie podasz <czas trwania>, to kara jest permamentna.

        Czas trwania może być podany w krótkiej formie, np. 30d albo bardziej ludzkiej
        jak "until thursday at 3PM" (tylko po angielsku!), albo jako konkretna data
        jak np. "2024-12-31". Nie zapomnij o cudzysłowach.
        """
        with ctx.typing():
            # ROLE_NAME = "GetBeaned_muted"
            ROLE_NAME = await self.bot.settings.get(ctx.guild, 'muted_role_id')
            # print(f'ROLE_NAME = {ROLE_NAME}')
            if ROLE_NAME is None or ROLE_NAME == 0:
                await ctx.send_to(f"❌ Rola `Muted` nie jest ustawiona. Ustaw ją przy pomocy `{ctx.prefix}create_muted_role id_roli`.")
                return False
            # muted_role = discord.utils.get(ctx.guild.roles, id=ROLE_NAME)
            # muted_role = users[0].guild.get_channel(ROLE_NAME)
            muted_role = await commands.RoleConverter().convert(ctx, ROLE_NAME)
            # print(type(ROLE_NAME))
            # print(f'ctx.guild.name = {ctx.guild.name}')
            # print(f'muted_role = {muted_role}')

            if muted_role is None:
                await ctx.send_to(f"❌ Rola `Muted` nie jest ustawiona. Ustaw ją przy pomocy `{ctx.prefix}create_muted_role id_roli`.")
                return False

            attachments_saved_url = await self.parse_arguments(ctx, users=users)
            await self.check_reason(ctx, reason, attachments_saved_url)

            await self.run_actions(ctx, users, reason, attachments_saved_url, mute, duration=duration)

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(3)
    async def kick(self, ctx: 'CustomContext', users: commands.Greedy[InferiorMember], *,
                   reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        Wyrzuć członka z serwera. Jeżeli progi są włączone, wyrzucenie może spowodować automatycznego bana.

        Użycie b!kick [członek/członkowie] <powód>.

        [członek] może być jego ID, nazwa#dyskryminator albo wzmianką.
        <powód> to twój powód wyrzucenia.
        """
        with ctx.typing():
            attachments_saved_url = await self.parse_arguments(ctx, users=users)
            await self.check_reason(ctx, reason, attachments_saved_url)

            await self.run_actions(ctx, users, reason, attachments_saved_url, kick)

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(3)
    async def softban(self, ctx: 'CustomContext', users: commands.Greedy[ForcedMember], *,
                      reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        SoftBanuje członka. SoftBan polega na zbanowaniu użytkownika, aby usunąć jego wszystkie wiadomości,
        a następnie odbanowaniu go, aby mógł ponownie dołączyć na serwer.

        Jeżeli progi są włączone, SoftBan może spowodować automatycznego bana.

        Użycie b!softban [członek/członkowie] <powód>.

        [członek] może być jego ID, nazwa#dyskryminator albo wzmianką.
        <powód> to twój powód SoftBana.
        """
        with ctx.typing():
            attachments_saved_url = await self.parse_arguments(ctx, users=users)
            await self.check_reason(ctx, reason, attachments_saved_url)

            await self.run_actions(ctx, users, reason, attachments_saved_url, softban)

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(3)
    async def ban(self, ctx: 'CustomContext', duration: typing.Optional[time.FutureTime], users: commands.Greedy[ForcedMember(may_be_banned=False)], *,
                  reason: commands.clean_content(fix_channel_mentions=True, use_nicknames=False) = ""):
        """
        Zbanowanie jest ostateczną karą, która powoduje, że użytkownik nie może powrócić na serwer.

        Użycie b!ban <duration> [członek/członkowie] <powód>.

        <czas trwania> to czas do wygaśnięcia wyciszenia (na przykład, 1h, 1d, 1w, 3m, ...)
        [członek] może być jego ID, nazwa#dyskryminator albo wzmianką.
        <powód> to twój powód bana.

        Jeżeli nie podasz <czas trwania>, to kara jest permamentna.

        Czas trwania może być podany w krótkiej formie, np. 30d albo bardziej ludzkiej
        jak "until thursday at 3PM" (tylko po angielsku!), albo jako konkretna data
        jak np. "2024-12-31". Nie zapomnij o cudzysłowach.
        """
        with ctx.typing():
            attachments_saved_url = await self.parse_arguments(ctx, users=users)
            # print(f'attachments_saved_url: {attachments_saved_url}')
            await self.check_reason(ctx, reason, attachments_saved_url)

            await self.run_actions(ctx, users, reason, attachments_saved_url, ban, duration=duration)


def setup(bot: 'BamboBot'):
    bot.add_cog(Mod(bot))

'''
Changes by me:
(1) Translated to polish
(2) Addes some special moderation actions
(3) Changed mute() so it would work with how the `muted` role is handled
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Dodano kilka specjalnych akcji moderacyjnych
(3) Zmieniono mute() tak, aby działało z nowym systemem roli `muted`
'''
