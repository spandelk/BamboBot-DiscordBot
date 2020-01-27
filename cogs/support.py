# -*- coding: utf-8 -*-
import asyncio
import datetime
import time
import typing

import discord
from discord import Color
from discord.ext import commands

from cogs.helpers import checks
from cogs.helpers.hastebins import upload_text
from cogs.helpers.level import get_level

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext


PM_VIEWING_CHANNEL_ID = 659803781243863057
PM_SENT_CHANNEL_ID = 669143623677247508


class Support(commands.Cog):
    """Różne komendy wspracia."""

    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.conversations = bot.cache.get_cache("support_conversations", expire_after=3600, strict=True)
        self.temp_ignores = set()

    async def handle_private_message(self, received_message: discord.Message):
        if received_message.author.id in self.temp_ignores:
            return

        if received_message.author.id == self.bot.user.id:
            pm_channel = self.bot.get_channel(PM_SENT_CHANNEL_ID)
            dm_channel: discord.DMChannel = received_message.channel
            recipient = dm_channel.recipient
            attachments_list = [e.url for e in received_message.attachments]            
            embed = discord.Embed(title='Wysłano wiadomość do użytkownika', colour=discord.Colour(0x28d6ae), description=f'{received_message.content[:1700]}', timestamp=datetime.datetime.utcnow())
            embed.set_author(name=f'{recipient.name}', icon_url=recipient.avatar_url, url=f'https://bambobot.herokuapp.com/users/{recipient.id}')
            embed.set_footer(text=f'{recipient.name}#{recipient.discriminator}', icon_url=recipient.avatar_url)
            if len(received_message.content) < 1:
                embed.add_field(name='💬', value='[Wiadomość nie zawiera tekstu 🤷]')
            if len(attachments_list) > 0:
                embed.add_field(name='📎', value=f'Załączniki: {attachments_list}', inline=False)
            await pm_channel.send(content=f'{recipient.id}', embed=embed)
            if len(received_message.embeds) > 0:
                for i, e in enumerate(received_message.embeds, start=1):
                    await pm_channel.send(content=f'🔗 Bogate osadzenie {i}/{len(received_message.embeds)}', embed=e)
        else:
            pm_channel = self.bot.get_channel(PM_VIEWING_CHANNEL_ID)
            user:discord.User = received_message.author

            if "discord.gg/" in received_message.content:
                await user.send("Zauważyłem, że wysłałeś mi zaproszenie. To **nie** jest sposób, w jaki dodaje się boty na serwer. Aby zaprosić BamboBota, kliknij w ten link: "
                                "https://discordapp.com/oauth2/authorize?client_id=552611724419792907&permissions=8&scope=bot")
                # await user.send("If you have any questions, join the support server -> https://discord.gg/cPbhK53")

            attachments_list = [e.url for e in received_message.attachments]

            embed = discord.Embed(title="Zobacz najnowsze akcje użytkownika", colour=discord.Colour(0x28d6ae), url=f"https://bambobot.herokuapp.com/users/{user.id}",
                                description=f"{received_message.content[:1700]}", timestamp=datetime.datetime.utcnow())

            embed.set_author(name=f"{user.name}", url="https://bambobot.herokuapp.com", icon_url=f"{user.avatar_url}")
            embed.set_footer(text=f"{user.name}#{user.discriminator}", icon_url=f"{user.avatar_url}")

            if len(attachments_list) > 0:
                embed.add_field(name="📎 ", value=f"Załączniki : {attachments_list}", inline=False)
            # embed.add_field(name="\U0001f507 ", value="Mute the user")
            # embed.add_field(name="\U0001f4de ", value="Join this conversation")

            sent_message = await pm_channel.send(content=f"{user.id}", embed=embed)

            emotes = [
                "\U0001f507",  # SPEAKER WITH CANCELLATION STROKE - :mute:
                # "\U0001f4f2",  # MOBILE PHONE WITH RIGHTWARDS ARROW AT LEFT - :calling:
                "\U0001f4de",  # TELEPHONE RECEIVER - :telephone_receiver:"
            ]

            for emote in emotes:
                await sent_message.add_reaction(emote)

            def check(reaction, user):
                return str(reaction.emoji) in emotes and reaction.message.id == sent_message.id

            try:
                while True:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=3600.0, check=check)

                    if user.id == self.bot.user.id:
                        continue

                    if str(reaction.emoji) == "\U0001f507": # Mute
                        self.temp_ignores.add(received_message.author.id)
                        await pm_channel.send(f"{user.mention}, dodałeś {received_message.author.name} do listy ignorowanych. "
                                            f"Zostanie on usunięty z tej listy, jeżeli bot zostanie zrestartowany lub wyślesz mu wiadomość przez bota: `b!pm {received_message.author.id} WIADOMOŚĆ`")

                    elif str(reaction.emoji) == "\U0001f4de":  # Answer
                        await pm_channel.send(f"{user.mention}, piszesz właśnie z {received_message.author.name}.")
                        self.conversations[user.id] = received_message.author

            except asyncio.TimeoutError:
                await sent_message.clear_reactions()  # Nobody reacted :)

    async def handle_support_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        
        if message.content.startswith("#") or message.content.startswith("b!"):
            return

        target_user = self.conversations.get(message.author.id, None)

        if target_user is None:
            return

        r = await self.send_pm(sender=message.author, receiver=target_user, message_content=message.content)

        if not r:
            await message.add_reaction("👌")
        else:
            await message.add_reaction("❌")
            pm_channel = self.bot.get_channel(PM_VIEWING_CHANNEL_ID)
            await pm_channel.send(r)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # if message.author.id == self.bot.user.id:
        #     return

        if not message.guild:
            await self.handle_private_message(message)

        elif message.channel.id == PM_VIEWING_CHANNEL_ID:
            await self.handle_support_message(message)

    @commands.command(aliases=["endpm"])
    @checks.have_required_level(8)
    async def end_pm(self, ctx: 'CustomContext'):
        self.conversations[ctx.author.id] = None
        await ctx.message.add_reaction("👌")

    @commands.command(aliases=["answer", "send_pm", "sendpm"])
    @checks.have_required_level(8)
    async def pm(self, ctx: 'CustomContext', user: discord.User, *, message_content:str):
        self.conversations[ctx.author.id] = user
        await self.send_pm(sender=ctx.author, receiver=user, message_content=message_content)

    async def send_pm(self, sender: discord.Member, receiver: discord.User, message_content:str):
        try:  # Remove from ignore list if replying
            self.temp_ignores.remove(receiver)
        except KeyError:
            pass

        try:
            # await receiver.send(f"🐦 {sender.name}#{sender.discriminator}, moderator bota, wysyła ci następującą wiadomość:\n>>> {message_content}")
            # await receiver.send(f"🐦\n>>> {message_content}")
            await receiver.send(f"{message_content}")
        except Exception as e:
            return f"Błąd podczas wysyłania wiadomości do {sender.mention} ({sender.name}#{sender.discriminator}) : {e}"

        pm_channel = self.bot.get_channel(PM_VIEWING_CHANNEL_ID)

        await pm_channel.send(f"**{sender.name}#{sender.discriminator}** odpowiedział {receiver.mention} ({receiver.name}#{receiver.discriminator})\n>>> {message_content[:1900]}")


    @commands.command()
    @commands.guild_only()
    @checks.have_required_level(1)
    async def level(self, ctx: 'CustomContext', user: discord.Member = None):
        """
        Pokazuje twój aktualny poziom dostępu

        ---------------------------------------------
        | Poziom | Opis                             |
        |-------------------------------------------|
        | 10     | Właściciel bota (Jutjuberzy)     |
        | 09     | Zarezerwowane na przyszłość      |
        | 08     | Moderator Bota                   |
        | 07     | Zarezerwowane na przyszłość      |
        | 06     | Zarezerwowane na przyszłość      |
        | 05     | Aktualny właściciel serwera      |
        | 04     | Administrator serwera            |
        | 03     | Moderator serwera                |
        | 02     | Zaufany użytkownik               |
        | 01     | Zwyczajny członek                |
        | 00     | Użytkownik zbanowany w bocie     |
        ---------------------------------------------
        """
        with ctx.typing():
            if user is None:
                user = ctx.message.author

            l = await get_level(ctx, user)

            levels_names = {10: "Właściciel bota",
                            9: "Zarezerwowane na przyszłość",
                            8: "Globalny moderator bota",
                            7: "Zarezerwowane na przyszłość",
                            6: "Zarezerwowane na przyszłość",
                            5: "Właściciel serwera",
                            4: "Administrator serwera ",
                            3: "Moderator serwera ",
                            2: "Zaufany użytkownik serwera",
                            1: "Członek",
                            0: "Zbanowany w bocie"
                            }

            await ctx.send(f"Obecny poziom: {l} ({levels_names[l]})")

    async def safe_add_field(self, embed, *, name, value, inline=None, strip=True):
        if len(value) > 1000:
            if strip:
                value = value.strip("`")

            value = await upload_text(value)
        embed.add_field(name=name, value=value, inline=inline)

    @commands.command(aliases=["message_info", "report_message", "message_report", "minfo"])
    @commands.guild_only()
    @checks.have_required_level(2)
    async def info_message(self, ctx: 'CustomContext', message_id: int):
        with ctx.typing():
            try:
                target_message:discord.Message = await ctx.channel.fetch_message(message_id)
            except discord.NotFound:
                await ctx.send("❌ Wiadomość nie znaleziona na kanale.")
                return False

            automod_cache = self.bot.cache.get_cache("automod_logs", expire_after=3600)

            embed = discord.Embed(timestamp=target_message.created_at,
                                title=f"Raport wiadomości od {ctx.author.name}#{ctx.author.discriminator}")

            embed.set_author(name=f"{target_message.author.name}#{target_message.author.discriminator}", icon_url=target_message.author.avatar_url)
            await self.safe_add_field(embed, name="Zawartość", value=target_message.content, inline=False, strip=False)

            if len(target_message.attachments) > 0:
                attachments = ", ".join(target_message.attachments)
                embed.add_field(name="Załącznik(i)", value=attachments, inline=False)

            embed.add_field(name="ID Autora", value=target_message.author.id, inline=True)
            embed.add_field(name="ID Kanału", value=target_message.channel.id, inline=True)
            embed.add_field(name="ID Wiadomości", value=target_message.id, inline=True)

            embed.add_field(name="Autor utworzony", value=target_message.author.created_at, inline=True)

            await self.safe_add_field(embed, name="Logi AutoModa", value="```\n" + automod_cache.get(message_id, "Brak :(") + "\n```", inline=False)

            await ctx.send(embed=embed)

    @commands.command(aliases=["permissions_checks", "permission_check", "bot_permissions_check"])
    @commands.guild_only()
    @checks.have_required_level(1)
    async def permissions_check(self, ctx: 'CustomContext'):
        with ctx.typing():
            current_permissions: discord.Permissions = ctx.message.guild.me.permissions_in(ctx.channel)

            emojis = {
                True: "✅",
                False: "❌"
            }

            perms_check = []

            for permission in ["kick_members", "ban_members", "read_messages", "send_messages", "manage_messages", "embed_links", "attach_files",
                            "read_message_history", "external_emojis", "change_nickname", "view_audit_log", "add_reactions"]:
                have_perm = current_permissions.__getattribute__(permission)
                emoji = emojis[have_perm]
                perms_check.append(
                    f"{emoji}\t{permission}"
                )

            await ctx.send("\n".join(perms_check))

    @commands.command(aliases=["hierarchy", "check_hierarchy"])
    @commands.guild_only()
    @checks.have_required_level(1)
    async def hierarchy_check(self, ctx: 'CustomContext', m: discord.Member):
        with ctx.typing():
            can_execute = ctx.author == ctx.guild.owner or \
                        ctx.author.top_role > m.top_role

            if can_execute:
                if m.top_role > ctx.guild.me.top_role:
                    await ctx.send(f'❌ W Systemie Permisji Discorda, rola bota jest niżej lub na tym samym poziome jak najwyższa rola celu.')
                    return False
                await ctx.send("✅ Wszystko się zgadza!")
                return True
            else:
                await ctx.send('❌  W Systemie Permisji Discorda, twoja rola jest niżej lub na tym samym poziome jak najwyższa rola celu.')
                return False

    @commands.command(aliases=["bot_doctor", "support_check"])
    @commands.guild_only()
    @commands.cooldown(2, 60, commands.BucketType.guild)
    @checks.have_required_level(1)
    async def doctor(self, ctx: 'CustomContext'):
        with ctx.typing():
            waiting_message = await ctx.send("<a:loading:567788165415436310> Proszę czekać, przeprowadzanie kontroli `lekarza`")  # <a:loading:393852367751086090> is a loading emoji
            t_1 = time.perf_counter()
            await ctx.trigger_typing()  # tell Discord that the bot is "typing", which is a very simple request
            t_2 = time.perf_counter()
            time_delta = round((t_2 - t_1) * 1000)  # calculate the time needed to trigger typing
            del self.bot.settings.settings_cache[ctx.guild]
            messages = {}
            message = []
            # Permissions
            wanted_permissions = discord.permissions.Permissions.none()
            wanted_permissions.update(
                kick_members=True,
                ban_members=True,
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                external_emojis=True,
                change_nickname=True,
                add_reactions=True
            )

            message.append("```diff")

            errored_in = []
            for channel in ctx.guild.channels:
                my_permissions = ctx.message.guild.me.permissions_in(channel)
                if not my_permissions.is_strict_superset(wanted_permissions):
                    errored_in.append(channel)

            if len(errored_in) == 0:
                message.append("+ Wszystko się zgadza! Żadnych problemów z permisjami")
            else:
                message.append(f"= Następujące kanały mają problem z permisjami, użyj komendy {ctx.prefix}bot_permissions_check w danych kanale, żeby zobaczyć, czego brakuje")
                message.extend(["- #" + channel.name for channel in errored_in])

            top_role = ctx.message.guild.me.top_role

            # Position isn't guaranteed to not have gaps
            # Discord pls

            message.append(f"= Najwyższa rola bota jest na pozycji {top_role.position}/{ctx.guild.roles[-1].position} [wyżej = lepiej] - "
                        f"Każdy użytkownik, którego rola jest równa lub wyższa od <{top_role.name}> nie może zostać wyrzucony/zbanowany")
            message.append("```")

            messages["Permisje Bota"] = discord.Embed(description="\n".join(message), color=Color.green() if len(errored_in) == 0 else Color.red())

            # Settings

            message = ["Jeżeli opcja jest aktywna, linia będzie na zielono. Jeżeli jest nieaktywna, linia będzie na czerwono ```diff"]

            settings_char = {True: "+ ", False: "- "}

            guild = ctx.guild
            settings_to_check = {"automod_enable": "AutoMod",
                                "autotrigger_enable": "AutoTriggery (specialne zasady AutoModa przecikwo walce ze specyficznym spamem — Wymaga włączonego AutoModa)",
                                "thresholds_enable": "Progi (automatyczne akcje, gdy użytkownik otrzymał X strike'ów)",
                                "logs_enable": "Logi",
                                "autoinspect_enable": "AutoInspect (Weryfikacja członków, którzy dołączają na serwer)",
                                "rolepersist_enable": "Przywracanie ról (RolePersist (VIP))"
                                }

            for setting, display_name in settings_to_check.items():
                setting_enabled = await self.bot.settings.get(guild, setting)

                message.append(settings_char[setting_enabled] + display_name)

            message.append(f"```\n Aby zmienić ustawienia i zobaczyć ich więcej, użyj komendy `{ctx.prefix}urls` aby zobaczyć stronę serwera, "
                        "następnie edytuj tam ustawienia (Najpierw może być konieczne zalogowanie się)\n")

            messages["Bot Settings"] = discord.Embed(description="\n".join(message), color=Color.dark_green())

            # Logs

            logs_enabled = await self.bot.settings.get(guild, "logs_enable")

            if logs_enabled:
                logs = {"logs_moderation_channel_id": "Akcje Moderacji",
                        "logs_joins_channel_id": "Członkowie dołączyli/wyszli",
                        "logs_rolepersist_channel_id": "Przywrócenie ról",
                        "logs_member_edits_channel_id": "Edycja użytkowników",
                        "logs_edits_channel_id": "Edycja wiadomości",
                        "logs_delete_channel_id": "Usunięcie wiadomości",
                        "logs_autoinspect_channel_id": "AutoInspect"}
                everything_good = True
                message = ["Logi są włączone globalnie na tym serwerze. Następujące określone logi są włączone i skonfigurowane: \n```diff"]
                for setting, display_name in logs.items():
                    try:
                        setting_value = int(await self.bot.settings.get(guild, setting))
                    except ValueError:
                        message.append(f"= logi {display_name} (włączony, ale w polu ID znajduje się tekst, nie mogę tego przetworzyć)")
                    else:
                        if setting_value == 0:
                            message.append(f"- logi {display_name} ")
                            everything_good = False
                        else:
                            channel_logged = discord.utils.get(guild.channels, id=setting_value)
                            if channel_logged:
                                message.append(f"+ logi {display_name} (kanał #{channel_logged.name})")
                            else:
                                message.append(f"= logi {display_name} (włączone, ale nie mogę znaleźć kanału o ID {setting_value})")
                                everything_good = False

                message.append("```")

                messages["Logi"] = discord.Embed(description="\n".join(message), color=Color.green() if everything_good else Color.dark_orange())

            message = []

            # Staff

            l = await get_level(ctx, ctx.author)

            levels_names = {10: "Właściciel bota",
                            9: "Zarezerwowane na przyszłość",
                            8: "Globalny moderator bota",
                            7: "Zarezerwowane na przyszłość",
                            6: "Zarezerwowane na przyszłość",
                            5: "Właściciel serwera",
                            4: "Administrator serwera ",
                            3: "Moderator serwera ",
                            2: "Zaufany użytkownik serwera",
                            1: "Członek",
                            0: "Zbanowany w bocie"
                            }

            message.append(f"Twój obecny poziom dostępu to `{l}` ({levels_names[l]}).")

            embed = discord.Embed(description="\n".join(message), color=Color.green() if l >= 3 else Color.orange())

            ids = await self.bot.settings.get(guild, 'permissions_admins')
            if len(ids) > 0:

                message = ["Następujący użytkownicy zostali dodani jako **administratorzy** (4) "
                        "(Ta lista nie jest kompletna, ponieważ **nie** zawiera osób z permisją `administratora`) \n```diff"]
                for admin_id in ids:
                    admin = discord.utils.get(guild.members, id=admin_id)
                    if admin:
                        message.append(f"+ {admin.name}#{admin.discriminator} ({admin_id})")
                    else:
                        role = discord.utils.get(guild.roles, id=admin_id)
                        if role:
                            message.append(f"+ (Rola) {role.name} ({admin_id})")
                        else:
                            message.append(f"- Użytkownik wyszedł z serwera ({admin_id})")
                message.append("```")

                embed.add_field(name="Administratorzy serwera", value="\n".join(message), inline=False)

            ids = await self.bot.settings.get(guild, 'permissions_moderators')
            if len(ids) > 0:
                message = ["Następujący użytkownicy zostali dodani jako **moderatorzy** (3) "
                        "(Ta lista nie jest kompletna, ponieważ **nie** zawiera osób z permisją `ban_members`) \n```diff"]
                for mod_id in ids:
                    mod = discord.utils.get(guild.members, id=mod_id)
                    if mod:
                        message.append(f"+ {mod.name}#{mod.discriminator} ({mod_id})")
                    else:
                        role = discord.utils.get(guild.roles, id=mod_id)
                        if role:
                            message.append(f"+ (Rola) {role.name} ({mod_id})")
                        else:
                            message.append(f"- Użytkownik wyszedł z serwera ({mod_id})")
                message.append("```")

                embed.add_field(name="Moderatorzy serwera", value="\n".join(message), inline=False)

            ids = await self.bot.settings.get(guild, 'permissions_trusted')
            if len(ids) > 0:
                message = ["Następujący użytkownicy zostali dodani jako **zaufani** (2) "
                        "(Ta lista nie jest kompletna, ponieważ **nie** zawiera osób z permisją `kick_members`) \n```diff"]
                for trusted_id in ids:
                    trusted = discord.utils.get(guild.members, id=trusted_id)
                    if trusted:
                        message.append(f"+ {trusted.name}#{trusted.discriminator} ({trusted_id})")
                    else:
                        role = discord.utils.get(guild.roles, id=trusted_id)
                        if role:
                            message.append(f"+ (Rola) {role.name} ({trusted_id})")
                        else:
                            message.append(f"- Użytkownik wyszedł z serwera ({trusted_id})")
                message.append("```")

                embed.add_field(name="Zaufani użytkownicy", value="\n".join(message), inline=False)


            messages["Personel"] = embed

            embed = discord.Embed(description="Nie możesz na to za dużo poradzić, ale poczekaj aż problemy znikną, jeżeli jakieś występują. \n"
                                            "Być może zechcesz sprawdzić https://status.discordapp.com po więcej informacji",
                                color=Color.green() if time_delta < 200 else Color.red())

            embed.add_field(name="Ping Bota", value=f"{time_delta}ms")
            embed.add_field(name="Opóźnienie Bota", value=f"{round(self.bot.latency * 1000)}ms")

            messages["Połączenie"] = embed

            # Send everything
            for message_title, embed in messages.items():
                embed.title = message_title
                await ctx.send(embed=embed)
                # await ctx.trigger_typing()
                await asyncio.sleep(.8)

            await waiting_message.delete()


def setup(bot: 'BamboBot'):
    bot.add_cog(Support(bot))

'''
Changes by me:
(1) Translated to polish
(2) Changed `PM_VIEWING_CHANNEL_ID`
(3) Changed the urls in embed
(4) Changed the emoji in doctor()
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Zmieniono `PM_VIEWING_CHANNEL_ID`
(3) Zmieniono URLe w osadzeniu
(4) Zmieniono emoji w doctor()
'''
