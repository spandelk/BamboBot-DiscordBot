# -*- coding: utf-8 -*-
import collections
import io
import typing
import datetime

import discord

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from discord.ext import commands

from cogs.helpers import context, checks
from cogs.helpers.hastebins import upload_text
from cogs.helpers.context import CustomContext

ATTACHMENTS_UPLOAD_CHANNEL_ID = 658421789613096981 # bambobot-attachments
BOT_SERVERS_CHANNEL_ID = 669180863099174912


async def save_attachments(bot: 'BamboBot', message: discord.Message):
    if len(message.attachments) >= 1:
        attachments_upload_channel = bot.get_channel(ATTACHMENTS_UPLOAD_CHANNEL_ID)
        saved_attachments_files = []
        attachments_unsaved_urls = []
        total_files = len(message.attachments)
        saved_files = 0
        for i, attachment in enumerate(message.attachments):
            file = io.BytesIO()
            attachment: discord.Attachment
            try:
                await attachment.save(file, seek_begin=True, use_cached=True)  # Works most of the time
            except discord.HTTPException:
                try:
                    await attachment.save(file, seek_begin=True, use_cached=False)  # Almost never works, but worth a try!
                except discord.HTTPException:
                    attachments_unsaved_urls.append(attachment.url)
                    break  # Couldn't save
            saved_files += 1
            saved_attachments_files.append(discord.File(fp=file, filename=attachment.filename))
        if saved_files >= 0:
            try:
                saved = await attachments_upload_channel.send(
                    content=f"`[{saved_files}/{total_files}]` - Załącznik(ów) dla wiadomości `{message.id}` na kanale `#{message.channel.name}` (ID `{message.channel.id}`), na serwerze `{message.guild.name}` (`{message.guild.id}`). Autorem jest `{message.author}` (ID `{message.author.id}`) ",
                    files=saved_attachments_files)
            except discord.HTTPException:
                # Too large for the bot
                return [], [a.url for a in message.attachments]

            attachments_saved_urls = [a.url for a in saved.attachments]
        else:
            attachments_saved_urls = []
    else:
        return [], []

    return attachments_saved_urls, attachments_unsaved_urls


class Logging(commands.Cog):
    """
    Rejestrowanie zdarzeń

    Tutaj znajdziesz zdarzenia, które nasłuchują edycji i usuwania wiadomości
    i wysyłają odpowiednie osadzenia na odpowiednich kanałach, jeżeli ustawienia serwera tego chcą.
    """

    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.api = bot.api
        self.snipes = bot.cache.get_cache("logging_deleted_messages", expire_after=7200, default=lambda: collections.deque(maxlen=15))  # channel: [message, message]

    async def perms_okay(self, channel):
        wanted_permissions = discord.permissions.Permissions.none()
        wanted_permissions.update(
            send_messages=True,
            embed_links=True,
            attach_files=True,
        )

        my_permissions = channel.guild.me.permissions_in(channel)

        return my_permissions.is_strict_superset(wanted_permissions)

    async def get_logging_channel(self, guild: discord.Guild, pref: str):
        # Beware to see if the channel id is actually in the same server (to compare, we will see if the current server
        # owner is the same as the one in the target channel). If yes, even if it's not the same server, we will allow
        # logging there

        if not await self.bot.settings.get(guild, 'logs_enable'):
            return None

        channel_id = int(await self.bot.settings.get(guild, pref))

        if channel_id == 0:
            # That would be handled later but no need to pass thru discord API if it's clearly disabled.
            return None

        channel = self.bot.get_channel(channel_id)

        if not channel:
            self.bot.logger.warning(f"There is something fishy going on with guild={guild.id}! Their {pref}="
                                    f"{channel_id} can't be found!")
            return None

        elif not channel.guild.owner == guild.owner:
            self.bot.logger.warning(f"There is something fishy going on with guild={guild.id}! Their {pref}="
                                    f"{channel_id} don't belong to them!")
            return None


        else:
            return channel

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: typing.List[discord.Message]):
        """
        Handle bulk message deletions. However, older deleted messages that aren't in discord internal cache will not fire
        this event so we kinda "hope" that the messages weren't too old when they were deleted, and that they were in the cache

        This may log other bots
        """

        first_message = messages[0]

        if first_message.guild is None:
            return

        if "[bambobot:disable_logging]" in str(first_message.channel.topic):
            return

        logging_channel = await self.get_logging_channel(first_message.guild, 'logs_delete_channel_id')

        if not logging_channel:
            return

        guild = first_message.guild

        channel = first_message.channel
        channel_id = channel.id

        bulky_messages_list = [f"Wiadomości masowo usunięte na #{channel.name} (https://discordapp.com/channels/{guild.id}/{channel_id})\n",
                               f"Data utworzenia :: ID Wiadomości :: [ID] Autor - Zawartość"]

        authors = set()

        for message in messages:
            author = message.author

            authors.add(author)

            bulky_messages_list.append(f"{message.created_at} :: {message.id} :: `[{author.id}]` {author.name}#{author.discriminator} \t - {message.content}")

        if await self.perms_okay(logging_channel):
            embed = discord.Embed(title=f"#{channel.name}",
                                  colour=discord.Colour.dark_red(),
                                  description=f"Kanał: \t`[{channel_id}]` [#{channel.name}](https://discordapp.com/channels/{guild.id}/{channel_id}) \n"
                                              f"Ilość autorów: \t `{len(authors)}` \n"
                                              f"Ilość wiadomości: \t `{len(messages)}`"
                                  )

            embed.set_author(name="Wiadomości usunięte (masowo)", url="https://bambobot.herokuapp.com")  # , icon_url="ICON_URL_DELETE")

            embed.timestamp = first_message.created_at

            embed.set_footer(text="Pierwsza wiadomość utworzona",
                             icon_url="https://cdn.discordapp.com/avatars/552611724419792907/fded780340148db800e317cb4b417b88.png")

            embed.add_field(name="Lista usuniętych wiadomości",
                            value=await upload_text("\n".join(bulky_messages_list)))

            await logging_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, raw_message_update: discord.RawMessageUpdateEvent):
        """
        Handle **raw** message edits. ~~However, older messages that aren't in discord internal cache will not fire
        this event so we kinda "hope" that the message wasn't too old when it was edited, and that it was in the cache~~

        This doesn't logs other bots
        """

        message_id = raw_message_update.message_id
        channel_id = int(raw_message_update.data["channel_id"])  # TODO: In d.py 1.3.0, make that raw_message_update.channel_id

        new_content = raw_message_update.data.get("content", None)  # Embed may be partial, see doc.

        if not new_content:
            return

        if len(new_content) > 450:
            new_content = new_content[:450] + " [...] — Wiadomość zbyt długa, aby ją tu wyświetlić, całość dostępna na " + await upload_text(new_content)

        if raw_message_update.cached_message:
            cached_message = True
            old_message = raw_message_update.cached_message
            channel = old_message.channel
            author = old_message.author

            old_content = old_message.content

        else:
            cached_message = False
            channel = self.bot.get_channel(channel_id)

            author = self.bot.get_user(int(raw_message_update.data["author"]["id"]))

            if author is None:
                return

        if channel is None or isinstance(channel, discord.abc.PrivateChannel):
            return

        if "[bambobot:disable_logging]" in str(channel.topic):
            return

        guild = channel.guild

        if author.bot:
            return

        logging_channel = await self.get_logging_channel(guild, 'logs_edits_channel_id')

        if not logging_channel:
            return

        embed = discord.Embed(title=f"{author.name}#{author.discriminator}",
                              colour=discord.Colour.orange(),
                              url=f"https://bambobot.herokuapp.com/users/{guild.id}/{author.id}",
                              description=f"\n[► Zobacz Wiadomość](https://discordapp.com/channels/{guild.id}/{channel_id}/{message_id}).\n\n"
                                          f"Kanał: \t`[{channel_id}]` [#{channel.name}](https://discordapp.com/channels/{guild.id}/{channel_id}) \n"
                                          f"Autor: \t`[{author.id}]` {author.mention} \n"
                                          f"Wiadomość: \t`[{message_id}]`"
                              )

        embed.set_thumbnail(url=str(author.avatar_url))
        embed.set_author(name="Wiadomość Edytowana", url="https://bambobot.herokuapp.com")  # , icon_url="ICON_URL_EDIT")

        if cached_message:
            embed.timestamp = old_message.created_at

            embed.set_footer(text="Wiadomość została oryginalnie stworzona",
                             icon_url="https://cdn.discordapp.com/avatars/552611724419792907/fded780340148db800e317cb4b417b88.png")

            if len(old_content) > 450:
                old_content = old_content[:450] + " [...] — Wiadomość zbyt długa, aby ją tu wyświetlić, całość dostępna na " + await upload_text(old_content)

            embed.add_field(name="Oryginalna wiadomość",
                            value=old_content)

        embed.add_field(name="Edytowana wiadomość",
                        value=new_content)

        if not cached_message:
            embed.set_footer(text="Oryginalna data utworzenia wiadomości jest niedostępna",
                             icon_url="https://cdn.discordapp.com/avatars/552611724419792907/fded780340148db800e317cb4b417b88.png")
            embed.add_field(name="🙄",
                            value="Wiadomość **nie** znajdowała się w pamięci podręcznej bota i tylko edytowana wiadomość może zostać wyświetlona. Najczęściej oznacza to, że wiadomość została napisana zbyt dawno temu.")

        if await self.perms_okay(channel):
            await logging_channel.send(embed=embed)



    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """
        Handle message deletions. However, older deleted messages that aren't in discord internal cache will not fire
        this event so we kinda "hope" that the message wasn't too old when it was deleted, and that it was in the cache

        This dosen't logs other bots
        """

        if message.guild is None:
            return

        # if message.author.bot:
        #     return

        if not message.type == discord.MessageType.default:
            return

        if len(message.content) == 0 and len(message.attachments) == 0:
            return

        self.snipes[message.channel].append(message)
        self.snipes.reset_expiry(message.channel)

        if "[bambobot:disable_logging]" in str(message.channel.topic):
            return

        logging_channel = await self.get_logging_channel(message.guild, 'logs_delete_channel_id')

        if not logging_channel:
            return

        if len(message.attachments) >= 1:
            attachments_saved_urls, attachments_unsaved_urls = await save_attachments(self.bot, message)

            attachments_text = []
            if len(attachments_saved_urls) >= 1:
                attachments_text = ["\n- ".join(attachments_saved_urls)]
            if len(attachments_saved_urls) < len(message.attachments):
                attachments_text.append("Następujące załączniki **nie** mogły zostać zapisane przez bota: " + "\n- ".join(attachments_unsaved_urls))
            attachments_text = "\n".join(attachments_text)

        if len(message.content) > 450:
            content = message.content[:450] + " [...] — Wiadomość zbyt długa, aby ją tu wyświetlić, całość dostępna na " + await upload_text(message.content)
        elif len(message.content) == 0:
            content = f"Wiadomość nie zawierała żadnego tekstu oraz {len(message.attachments)} załączników."

        else:
            content = message.content

        ctx = await self.bot.get_context(message, cls=context.CustomContext)
        ctx.logger.info(f"Logging message deletion")

        if await self.bot.settings.get(message.guild, 'logs_as_embed') and await self.perms_okay(logging_channel):
            author = message.author
            guild = message.guild
            channel = message.channel
            channel_id = channel.id
            message_id = message.id

            embed = discord.Embed(title=f"{author.name}#{author.discriminator}",
                                  colour=discord.Colour.red(),
                                  url=f"https://bambobot.herokuapp.com/users/{guild.id}/{author.id}",
                                  description=f"Kanał: \t`[{channel_id}]` [#{channel.name}](https://discordapp.com/channels/{guild.id}/{channel_id}) \n"
                                              f"Autor: \t`[{author.id}]` {author.mention} \n"
                                              f"Wiadomość: \t`[{message_id}]`"
                                  )

            embed.set_thumbnail(url=str(author.avatar_url))
            embed.set_author(name="Wiadomość usunięta", url="https://bambobot.herokuapp.com")  # , icon_url="ICON_URL_DELETE")

            embed.timestamp = message.created_at

            embed.set_footer(text="Wiadomość została utworzona",
                             icon_url="https://cdn.discordapp.com/avatars/552611724419792907/fded780340148db800e317cb4b417b88.png")

            embed.add_field(name="Usunięta wiadomość",
                            value=content)

            if len(message.attachments) >= 1:
                embed.add_field(name="Załączniki wiadomości",
                                value=attachments_text)

            await logging_channel.send(embed=embed)

        else:
            textual_log = f"Wiadomość usunięta | " \
                          f"Autor: {message.author.name}#{message.author.discriminator}({message.author.id})\n" \
                          f"Kanał: {message.channel.mention}" \
                          f"**Wiadomość**:{content}"

            try:
                await logging_channel.send(textual_log)
            except discord.errors.Forbidden:
                ctx.logger.info(f"Couldn't log message deletion {message} (No perms)")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = await self.get_logging_channel(member.guild, 'logs_joins_channel_id')

        if not channel:
            return

        if await self.bot.settings.get(member.guild, 'logs_as_embed') and await self.perms_okay(channel):

            embed = discord.Embed(title=f"{member.name}#{member.discriminator}",
                                  colour=discord.Colour.green(),
                                  url=f"https://bambobot.herokuapp.com/users/{member.guild.id}/{member.id}",
                                  description=f"Członek: \t `[{member.id}]` {member.mention} \n"
                                  )

            embed.set_thumbnail(url=str(member.avatar_url))
            embed.set_author(name="Członek dołączył", url="https://bambobot.herokuapp.com")  # , icon_url="ICON_URL_DELETE")

            embed.timestamp = member.created_at

            embed.set_footer(text="Członek utworzył swoje konto",
                             icon_url="https://cdn.discordapp.com/avatars/552611724419792907/fded780340148db800e317cb4b417b88.png")

            embed.add_field(name="Aktualna ilość członków",
                            value=str(member.guild.member_count))

            await channel.send(embed=embed)

        else:
            textual_log = f"Członek dołączył | {member.name}#{member.discriminator} (`{member.id}`)\n" \
                          f"**Aktualna ilość członków**: {member.guild.member_count}"

            try:
                await channel.send(textual_log)
            except discord.errors.Forbidden:
                self.bot.logger.info(f"Couldn't log user leave {member} (No perms)")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = await self.get_logging_channel(member.guild, 'logs_joins_channel_id')
        if not channel:
            return

        self.bot.logger.info(f"Logging user leave {member}")

        if await self.bot.settings.get(member.guild, 'logs_as_embed') and await self.perms_okay(channel):
            embed = discord.Embed(title=f"{member.name}#{member.discriminator}",
                                  colour=discord.Colour.dark_orange(),
                                  url=f"https://bambobot.herokuapp.com/users/{member.guild.id}/{member.id}",
                                  description=f"Członek: \t `[{member.id}]` {member.mention} \n"
                                              f"Dołączył: \t {str(member.joined_at)}\n"
                                              f"Role: \t `{len(member.roles)}` : {', '.join([r.name for r in member.roles])}"
                                  )

            embed.set_thumbnail(url=str(member.avatar_url))
            embed.set_author(name="Członek wyszedł/został wyrzucony", url="https://bambobot.herokuapp.com")  # , icon_url="ICON_URL_DELETE")

            embed.timestamp = member.created_at

            embed.set_footer(text="Członek utworzył swoje konto",
                             icon_url="https://cdn.discordapp.com/avatars/552611724419792907/fded780340148db800e317cb4b417b88.png")

            embed.add_field(name="Aktualna ilość członków",
                            value=str(member.guild.member_count))

            await channel.send(embed=embed)
        else:

            textual_log = f"Członek wyszedł | {member.name}#{member.discriminator} (`{member.id}`)\n" \
                          f"**Aktualna ilość członków**: {member.guild.member_count}"
            try:
                await channel.send(textual_log)
            except discord.errors.Forbidden:
                self.bot.logger.info(f"Couldn't log user leave {member} (No perms)")

    @commands.Cog.listener()
    async def on_member_update(self, old: discord.Member, new: discord.Member):

        if old.nick != new.nick:
            # Nickname update
            channel = await self.get_logging_channel(old.guild, 'logs_member_edits_channel_id')

            if not channel:
                return

            self.bot.logger.info(f"Logging user edit {old}->{new}")

            if await self.bot.settings.get(old.guild, 'logs_as_embed') and await self.perms_okay(channel):

                embed = discord.Embed(title=f"{new.name}#{new.discriminator}",
                                      colour=discord.Colour.dark_orange(),
                                      url=f"https://bambobot.herokuapp.com/users/{new.guild.id}/{new.id}",
                                      description=f"Członek: \t `[{new.id}]` {new.mention} \n"
                                                  f"Stary nickname: \t `{old.nick}`\n"
                                                  f"Nowy nickname: \t `{new.nick}`"
                                      )

                embed.set_thumbnail(url=str(new.avatar_url))
                embed.set_author(name="Członek zmienił nickname", url="https://bambobot.herokuapp.com")  # , icon_url="ICON_URL_DELETE")

                embed.timestamp = new.joined_at

                embed.set_footer(text="Członek dołączył",
                                 icon_url="https://cdn.discordapp.com/avatars/552611724419792907/fded780340148db800e317cb4b417b88.png")

                await channel.send(embed=embed)
            else:
                textual_log = f"Zmieniony Nickname Członka | {old.name}#{old.discriminator} (`{old.id}`)\n" \
                              f"**Stary**: `{old.nick}`\n" \
                              f"**Nowy**: `{new.nick}`"

                try:
                    await channel.send(textual_log)
                except discord.errors.Forbidden:
                    self.bot.logger.info(f"Couldn't log member update {old}->{new} (No perms)")

    @staticmethod
    async def snipe_as_embed(ctx: 'CustomContext', message: discord.Message):
        embed = discord.Embed()
        embed.title = f"Przechwycona wiadomość | {message.id}"
        embed.add_field(name="Przez", value=message.author.mention)
        embed.add_field(name="W", value=message.channel.mention)
        embed.description = message.content
        embed.set_footer(text=f"Możesz uzyskać więcej informacji o tym, jak AutoMod potraktował tą wiadomość używająć {ctx.prefix}automod_logs {message.id}")
        embed.timestamp = message.created_at
        await ctx.send(embed=embed)

    @staticmethod
    async def snipe_as_webhook(ctx: 'CustomContext', webhook: discord.Webhook, message: discord.Message):
        embed = discord.Embed()
        embed.title = f"Przechwycona wiadomość | {message.id}"
        embed.description = "To jest przechwycona wiadomość przez BamboBota"
        embed.set_footer(text=f"Możesz uzyskać więcej informacji o tym, jak AutoMod potraktował tą wiadomość używająć {ctx.prefix}automod_logs {message.id}")
        embed.timestamp = message.created_at

        await webhook.send(message.content, embed=embed)
        # await webhook.send(f"```\nWiadomość została utworzona {message.created_at}\nMożesz uzyskać więcej informacji o tym, jak AutoMod potraktował tą wiadomość używająć {ctx.prefix}automod_logs {message.id}```")
        await webhook.delete()

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_minimal_permissions()
    @checks.have_required_level(2)
    async def snipe(self, ctx: 'CustomContext'):
        with ctx.typing():
            try:
                message = self.snipes[ctx.channel].pop()
            except IndexError:  # Nothing in deque
                await ctx.send("❌Nic do przechwycenia")
                return

            avatar = await message.author.avatar_url.read()

            try:
                webhook = await ctx.channel.create_webhook(name=message.author.display_name, avatar=avatar, reason=f"Kodenda Snipe od {ctx.message.author.name}")
                await self.snipe_as_webhook(ctx, webhook, message)
            except discord.Forbidden:
                await self.snipe_as_embed(ctx, message)
                return

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.guild):
        embed = discord.Embed(title="Dołączono do serwera", colour=discord.Colour.green(), url=f"https://bambobot.herokuapp.com/guilds/{guild.id}",
                                timestamp=datetime.datetime.utcnow(),
                                description=f'**Serwer:** \t `{guild.name}` ({guild.id})\n'
                                            f'**Data utworzenia:** \t {guild.created_at}\n'
                                            f'**Właściciel:** \t {guild.owner.name}#{guild.owner.discriminator} ({guild.owner.id})\n'
                                            f'**Ilość członków:** \t {guild.member_count}')
        embed.set_thumbnail(url=str(guild.icon_url))
        # embed.add_field(name='Serwer', value=f'{guild.name} ({guild.id})', inline=False)
        # embed.add_field(name='Data utworzenia', value=f'{guild.created_at}', inline=True)
        # embed.add_field(name='Właściciel', value=f'{guild.owner.name}#{guild.owner.discriminator} ({guild.owner.id})', inline=False)
        # embed.add_field(name='Ilość członków', value=f'{guild.member_count}', inline=True)
        embed.set_footer(text='Dołączono')

        channel = self.bot.get_channel(BOT_SERVERS_CHANNEL_ID)
        await channel.send(content='', embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        # guild = self.bot.get_guild(guild.id)
        # joined_at = guild.get_member(self.bot.user.id).joined_at
        joined_at = '\U0001F937'
        # joined_at = guild.me.joined_at
        # print(guild)
        embed = discord.Embed(title="Opuszczono serwer", colour=discord.Colour.red(), url=f"https://bambobot.herokuapp.com/guilds/{guild.id}",
                                timestamp=datetime.datetime.utcnow(),
                                description=f'**Serwer:** \t `{guild.name}` ({guild.id})\n'
                                            f'**Data utworzenia:** \t {guild.created_at}\n'
                                            f'**Właściciel:** \t {guild.owner.name}#{guild.owner.discriminator} ({guild.owner.id})\n'
                                            f'**Ilość członków:** \t {guild.member_count}\n'
                                            f'**Dołączono:** \t {joined_at}')
        embed.set_thumbnail(url=str(guild.icon_url))
        # embed.add_field(name='Serwer', value=f'{guild.name} ({guild.id})', inline=False)
        # embed.add_field(name='Data utworzenia', value=f'{guild.created_at}', inline=True)
        # embed.add_field(name='Właściciel', value=f'{guild.owner.name}#{guild.owner.discriminator} ({guild.owner.id})', inline=False)
        # embed.add_field(name='Ilość członków', value=f'{guild.member_count}', inline=True)
        embed.set_footer(text='Opuszczono')

        channel = self.bot.get_channel(BOT_SERVERS_CHANNEL_ID)
        await channel.send(content='', embed=embed)



def setup(bot: 'BamboBot'):
    bot.add_cog(Logging(bot))

'''
Changes by me:
(1) Translated to polish
(2) Changed embed url=
(3) Changed embed icon_url=
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Zmieniono url= osadzenia
(3) Zmieniono icon_url= osadzenia
'''
