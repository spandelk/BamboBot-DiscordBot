# -*- coding: utf-8 -*-
"""
A good enough help command for general use
"""
import asyncio
import random
import typing

import discord
from discord.ext import commands

from cogs.helpers import checks

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext


class Pages:
    """Implements a paginator that queries the user for the
    pagination interface.

    Pages are 1-index based, not 0-index based.

    If the user does not reply within 2 minutes then the pagination
    interface exits automatically.

    Parameters
    ------------
    ctx: Context
        The context of the command.
    entries: List[str]
        A list of entries to paginate.
    per_page: int
        How many entries show up per page.
    show_entry_count: bool
        Whether to show an entry count in the footer.

    Attributes
    -----------
    embed: discord.Embed
        The embed object that is being used to send pagination info.
        Feel free to modify this externally. Only the description,
        footer fields, and colour are internally modified.
    permissions: discord.Permissions
        Our permissions for the channel.
    """

    def __init__(self, ctx, *, entries, per_page=12, show_entry_count=True):
        self.bot = ctx.bot
        self.entries = entries
        self.message = ctx.message
        self.channel = ctx.channel
        self.author = ctx.author
        self.per_page = per_page
        pages, left_over = divmod(len(self.entries), self.per_page)
        if left_over:
            pages += 1
        self.maximum_pages = pages
        self.embed = discord.Embed(colour=discord.Colour.blurple())
        self.paginating = len(entries) > per_page
        self.show_entry_count = show_entry_count
        self.reaction_emojis = [
            ('\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}', self.first_page),
            ('\N{BLACK LEFT-POINTING TRIANGLE}', self.previous_page),
            ('\N{BLACK RIGHT-POINTING TRIANGLE}', self.next_page),
            ('\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}', self.last_page),
            ('\N{INPUT SYMBOL FOR NUMBERS}', self.numbered_page),
            ('\N{BLACK SQUARE FOR STOP}', self.stop_pages),
            ('\N{INFORMATION SOURCE}', self.show_help),
        ]

        if ctx.guild is not None:
            self.permissions = self.channel.permissions_for(ctx.guild.me)
        else:
            self.permissions = self.channel.permissions_for(ctx.bot.user)

        if not self.permissions.embed_links:
            raise CannotPaginate('Bot nie może zamieszcać osadzeń.')

        if not self.permissions.send_messages:
            raise CannotPaginate('Bot nie może wysyłać wiadomości.')

        if self.paginating:
            # verify we can actually use the pagination session
            if not self.permissions.add_reactions:
                raise CannotPaginate('Bot nie posiada permisji na dodawanie reakcji.')

            if not self.permissions.read_message_history:
                raise CannotPaginate('Bot nie posiada permisji do czytania historii kanału.')

    def get_page(self, page):
        base = (page - 1) * self.per_page
        return self.entries[base:base + self.per_page]

    async def show_page(self, page, *, first=False):
        self.current_page = page
        entries = self.get_page(page)
        p = []
        for index, entry in enumerate(entries, 1 + ((page - 1) * self.per_page)):
            p.append(f'{index}. {entry}')

        if self.maximum_pages > 1:
            if self.show_entry_count:
                text = f'Strona {page}/{self.maximum_pages} ({len(self.entries)} wpisów)'
            else:
                text = f'Strona {page}/{self.maximum_pages}'

            self.embed.set_footer(text=text)

        if not self.paginating:
            self.embed.description = '\n'.join(p)
            return await self.channel.send(embed=self.embed)

        if not first:
            self.embed.description = '\n'.join(p)
            await self.message.edit(embed=self.embed)
            return

        p.append('')
        p.append('Zagubiony? Zareaguj używając \N{INFORMATION SOURCE} aby uzystać więcej info.')
        self.embed.description = '\n'.join(p)
        self.message = await self.channel.send(embed=self.embed)
        for (reaction, _) in self.reaction_emojis:
            if self.maximum_pages == 2 and reaction in ('\u23ed', '\u23ee'):
                # no |<< or >>| buttons if we only have two pages
                # we can't forbid it if someone ends up using it but remove
                # it from the default set
                continue

            await self.message.add_reaction(reaction)

    async def checked_show_page(self, page):
        if page != 0 and page <= self.maximum_pages:
            await self.show_page(page)

    async def first_page(self):
        """goes to the first page"""
        await self.show_page(1)

    async def last_page(self):
        """goes to the last page"""
        await self.show_page(self.maximum_pages)

    async def next_page(self):
        """goes to the next page"""
        await self.checked_show_page(self.current_page + 1)

    async def previous_page(self):
        """goes to the previous page"""
        await self.checked_show_page(self.current_page - 1)

    async def show_current_page(self):
        if self.paginating:
            await self.show_page(self.current_page)

    async def numbered_page(self):
        """lets you type a page number to go to"""
        to_delete = []
        to_delete.append(await self.channel.send('Na którą stronę chcesz się wybrać?'))

        def message_check(m):
            return m.author == self.author and \
                   self.channel == m.channel and \
                   m.content.isdigit()

        try:
            msg = await self.bot.wait_for('message', check=message_check, timeout=30.0)
        except asyncio.TimeoutError:
            to_delete.append(await self.channel.send('Czekałem zbyt długo.'))
            await asyncio.sleep(5)
        else:
            page = int(msg.content)
            to_delete.append(msg)
            if page != 0 and page <= self.maximum_pages:
                await self.show_page(page)
            else:
                to_delete.append(await self.channel.send(f'Podano nieprawidłową stronę. ({page}/{self.maximum_pages})'))
                await asyncio.sleep(5)

        try:
            await self.channel.delete_messages(to_delete)
        except Exception:
            pass

    async def show_help(self):
        """shows this message"""
        messages = ['Witaj w interaktywnym paginatorze!\n', 'To pozwali ci interaktywnie przeglądać strony tekstu nawigująć reakcjami:\n']

        for (emoji, func) in self.reaction_emojis:
            messages.append(f'{emoji} {func.__doc__}')

        self.embed.description = '\n'.join(messages)
        self.embed.clear_fields()
        self.embed.set_footer(text=f'Byliśmy na stronie {self.current_page} przed tą wiadomością.')
        await self.message.edit(embed=self.embed)

        async def go_back_to_current_page():
            await asyncio.sleep(60.0)
            await self.show_current_page()

        self.bot.loop.create_task(go_back_to_current_page())

    async def stop_pages(self):
        """stops the interactive pagination session"""
        await self.message.delete()
        self.paginating = False

    def react_check(self, reaction, user):
        if user is None or user.id != self.author.id:
            return False

        if reaction.message.id != self.message.id:
            return False

        for (emoji, func) in self.reaction_emojis:
            if reaction.emoji == emoji:
                self.match = func
                return True
        return False

    async def paginate(self):
        """Actually paginate the entries and run the interactive loop if necessary."""
        first_page = self.show_page(1, first=True)
        if not self.paginating:
            await first_page
        else:
            # allow us to react to reactions right away if we're paginating
            self.bot.loop.create_task(first_page)

        while self.paginating:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=self.react_check, timeout=120.0)
            except asyncio.TimeoutError:
                self.paginating = False
                try:
                    await self.message.clear_reactions()
                except:
                    pass
                finally:
                    break

            try:
                await self.message.remove_reaction(reaction, user)
            except:
                pass  # can't remove it so don't bother doing so

            await self.match()


class FieldPages(Pages):
    """Similar to Pages except entries should be a list of
    tuples having (key, value) to show as embed fields instead.
    """

    async def show_page(self, page, *, first=False):
        self.current_page = page
        entries = self.get_page(page)

        self.embed.clear_fields()
        self.embed.description = discord.Embed.Empty

        for key, value in entries:
            self.embed.add_field(name=key, value=value, inline=False)

        if self.maximum_pages > 1:
            if self.show_entry_count:
                text = f'Strona {page}/{self.maximum_pages} ({len(self.entries)} wspisów)'
            else:
                text = f'Strona {page}/{self.maximum_pages}'

            self.embed.set_footer(text=text)

        if not self.paginating:
            return await self.channel.send(embed=self.embed)

        if not first:
            await self.message.edit(embed=self.embed)
            return

        self.message = await self.channel.send(embed=self.embed)
        for (reaction, _) in self.reaction_emojis:
            if self.maximum_pages == 2 and reaction in ('\u23ed', '\u23ee'):
                # no |<< or >>| buttons if we only have two pages
                # we can't forbid it if someone ends up using it but remove
                # it from the default set
                continue

            await self.message.add_reaction(reaction)


import itertools
import inspect
import re

# ?help
# ?help Cog
# ?help command
#   -> could be a subcommand

_mention = re.compile(r'<@\!?([0-9]{1,19})>')


def cleanup_prefix(bot, prefix):
    m = _mention.match(prefix)
    if m:
        user = bot.get_user(int(m.group(1)))
        if user:
            return f'@{user.name} '
    return prefix


async def _can_run(cmd, ctx):
    try:
        return await cmd.can_run(ctx)
    except:
        return False


def _command_signature(cmd):
    # this is modified from discord.py source
    # which I wrote myself lmao

    result = [cmd.qualified_name]
    if cmd.usage:
        result.append(cmd.usage)
        return ' '.join(result)

    params = cmd.clean_params
    if not params:
        return ' '.join(result)

    for name, param in params.items():
        if param.default is not param.empty:
            # We don't want None or '' to trigger the [name=value] case and instead it should
            # do [name] since [name=None] or [name=] are not exactly useful for the user.
            should_print = param.default if isinstance(param.default, str) else param.default is not None
            if should_print:
                result.append(f'[{name}={param.default!r}]')
            else:
                result.append(f'[{name}]')
        elif param.kind == param.VAR_POSITIONAL:
            result.append(f'[{name}...]')
        else:
            result.append(f'<{name}>')

    return ' '.join(result)


class HelpPaginator(Pages):
    def __init__(self, ctx, entries, *, per_page=4):
        super().__init__(ctx, entries=entries, per_page=per_page)
        self.reaction_emojis.append(('\N{WHITE QUESTION MARK ORNAMENT}', self.show_bot_help))
        self.total = len(entries)

    @classmethod
    async def from_cog(cls, ctx, cog):
        cog_name = cog.__class__.__name__

        # get the commands
        entries = sorted(ctx.bot.get_cog_commands(cog_name), key=lambda c: c.name)

        # remove the ones we can't run
        entries = [cmd for cmd in entries if (await _can_run(cmd, ctx)) and not cmd.hidden]

        self = cls(ctx, entries)
        self.title = f'Komendy {cog_name}'
        self.description = inspect.getdoc(cog)
        self.prefix = cleanup_prefix(ctx.bot, ctx.prefix)

        # no longer need the database
        return self

    @classmethod
    async def from_command(cls, ctx, command):
        try:
            entries = sorted(command.commands, key=lambda c: c.name)
        except AttributeError:
            entries = []
        else:
            entries = [cmd for cmd in entries if (await _can_run(cmd, ctx)) and not cmd.hidden]

        self = cls(ctx, entries)
        self.title = command.signature

        if command.description:
            self.description = f'{command.description}\n\n{command.help}'
        else:
            self.description = command.help or 'Brak pomocy.'

        self.prefix = cleanup_prefix(ctx.bot, ctx.prefix)
        return self

    @classmethod
    async def from_bot(cls, ctx):
        def key(c):
            return c.cog_name or '\u200bRóżne'

        entries = sorted(ctx.bot.commands, key=key)
        nested_pages = []
        per_page = 9

        # 0: (cog, desc, commands) (max len == 9)
        # 1: (cog, desc, commands) (max len == 9)
        # ...

        for cog, commands in itertools.groupby(entries, key=key):
            # plausible = [cmd for cmd in commands if (await _can_run(cmd, ctx)) and not cmd.hidden]
            plausible = [cmd for cmd in commands if not cmd.hidden]
            if len(plausible) == 0:
                continue

            description = ctx.bot.get_cog(cog)
            if description is None:
                description = discord.Embed.Empty
            else:
                description = inspect.getdoc(description) or discord.Embed.Empty

            nested_pages.extend((cog, description, plausible[i:i + per_page]) for i in range(0, len(plausible), per_page))

        self = cls(ctx, nested_pages, per_page=1)  # this forces the pagination session
        self.prefix = cleanup_prefix(ctx.bot, ctx.prefix)

        # swap the get_page implementation with one that supports our style of pagination
        self.get_page = self.get_bot_page
        self._is_bot = True

        # replace the actual total
        self.total = sum(len(o) for _, _, o in nested_pages)
        return self

    def get_bot_page(self, page):
        cog, description, commands = self.entries[page - 1]
        self.title = f'Komendy {cog}'
        self.description = description
        return commands

    async def show_page(self, page, *, first=False):
        self.current_page = page
        entries = self.get_page(page)

        self.embed.clear_fields()
        self.embed.description = self.description
        self.embed.title = self.title

        if hasattr(self, '_is_bot'):
            # value = 'For more help, join the official bot support server: https://discord.gg/cPbhK53\n' \
            #         'There is a way better list of commands there: https://docs.getbeaned.me/bot-documentation/list-of-commands'
            value = 'Istnieje o wiele lepsza lista komend: https://docs.getbeaned.me/bot-documentation/list-of-commands (po angielsku!)'
            self.embed.add_field(name='Wsparcie', value=value, inline=False)

        messages = [f'Użyj "b!help komenda" aby uzyskać więcej info o danej komendzie.',
                    "Pamiętaj, że BamboBot posiada AutoModa, który nie posiada komend, ale może zostać skonfugurowany na WebInterfejsie.",
                    "Większość komend wymaga, aby permisje bota były ustawione prawidłowo. "
                    "Jeżeli napotykasz problem, upewnij się, że bot posiada następujęca permisje: "
                    "kick_members, ban_members, manage_messages, embed_links, attach_files, external_emojis, read_message_history and change_nickname"
                    ]
        self.embed.set_footer(text=random.choice(messages))

        signature = _command_signature

        for entry in entries:
            self.embed.add_field(name=signature(entry), value=entry.short_doc or "Brak pomocy", inline=False)

        if self.maximum_pages:
            self.embed.set_author(name=f'Strona {page}/{self.maximum_pages} ({self.total} komend)')

        if not self.paginating:
            return await self.channel.send(embed=self.embed)

        if not first:
            await self.message.edit(embed=self.embed)
            return

        self.message = await self.channel.send(embed=self.embed)
        for (reaction, _) in self.reaction_emojis:
            if self.maximum_pages == 2 and reaction in ('\u23ed', '\u23ee'):
                # no |<< or >>| buttons if we only have two pages
                # we can't forbid it if someone ends up using it but remove
                # it from the default set
                continue

            await self.message.add_reaction(reaction)

    async def show_help(self):
        """shows this message"""

        self.embed.title = 'Pomoc Paginatora'
        self.embed.description = 'Cześć! Witaj na stronie pomocy.'

        messages = [f'{emoji} {func.__doc__}' for emoji, func in self.reaction_emojis]
        self.embed.clear_fields()
        self.embed.add_field(name='Do czego słuzą te reakcje?', value='\n'.join(messages), inline=False)

        self.embed.set_footer(text=f'Byliśmy na stronie {self.current_page} przed tą wiadomością.')
        await self.message.edit(embed=self.embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_current_page()

        self.bot.loop.create_task(go_back_to_current_page())

    async def show_bot_help(self):
        """shows how to use the bot"""

        self.embed.title = 'Używanie bota'
        self.embed.description = 'Cześć! Witaj na stronie pomocy.'
        self.embed.clear_fields()

        entries = (
            ('<argument>', 'To oznacza, że argument jest __**wymagany**__.'),
            ('[argument]', 'To oznacza, że argument jest __**opcjonalny**__.'),
            ('[A|B]', 'To oznacza, że może to być __**albo A, albo B**__.'),
            ('[argument...]', 'To oznacza, że możesz podać wiele argumentów.\n' \
                              'Teraz gdy znasz podstawy, wiedz, że...\n' \
                              '__**Nie wpisuje się tych nawiasów!**__')
        )

        # self.embed.add_field(name='Jak używać bota?', value='Reading the bot signature is pretty simple.')
        self.embed.add_field(name='Jak używać bota?', value='Czytanie sygnatury bota jest naprawdę łatwe.')

        for name, value in entries:
            self.embed.add_field(name=name, value=value, inline=False)

        self.embed.set_footer(text=f'Byliśmy na stronie {self.current_page} przed tą wiadomością.')
        await self.message.edit(embed=self.embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_current_page()

        self.bot.loop.create_task(go_back_to_current_page())


class Help(commands.Cog):
    def __init__(self, bot: 'BamboBot'):
        self.bot = bot

    @commands.command(name='help')
    async def _help(self, ctx: 'CustomContext', *, command: str = None):
        """Shows help about a command or the bot"""
        with ctx.typing():
            await ctx.send("Ta przeglądarka pomocy jest nieaktualna. Lepsza i ładniejsza wersja dostępna tutaj: https://docs.getbeaned.me/bot-documentation/list-of-commands (po angielsku!)\n"
                        "Wkrótce zostanie ona usunięta.")

            try:
                if command is None:
                    p = await HelpPaginator.from_bot(ctx)
                else:
                    entity = self.bot.get_cog(command) or self.bot.get_command(command)

                    if entity is None:
                        clean = command.replace('@', '@\u200b')
                        return await ctx.send(f'Komenda lub kategoria "{clean}" nie znaleziona.')
                    elif isinstance(entity, commands.Command):
                        p = await HelpPaginator.from_command(ctx, entity)
                    else:
                        p = await HelpPaginator.from_cog(ctx, entity)

                await p.paginate()
            except Exception as e:
                await ctx.send(e)

    @commands.command(aliases=["join", "zaproś", "dodaj"])
    @checks.have_required_level(1)
    async def invite(self, ctx: 'CustomContext'):
        """
        Get this bot invite link
        """
        with ctx.typing():
            await ctx.send_to(
                "Zaproś bota: https://discordapp.com/oauth2/authorize?client_id=552611724419792907&permissions=8&scope=bot")
        # await ctx.send_to(':x: Na tę chwilę nie możesz mnie zaprosić na swój serwer :(')

    @commands.command(name='info')
    @checks.have_required_level(1)
    async def _info(self, ctx: 'CustomContext'):
        """Shows bot info"""
        with ctx.typing():
            # await ctx.send_to(f"This bot was made by Eyesofcreeper#0001. For help, type {ctx.prefix}help, for support go to https://discord.gg/cPbhK53. "
            #                   f"To invite the bot, find the link using {ctx.prefix}invite. This bot universal prefix is g+")
            await ctx.send_to(f'Ten bot stworzony został przez `JutjuBerzy#0963` z użyciem kodu od `Eyesofcreeper#0001`. Wsparcie dostępne na https://discord.gg/7tgynkn \n'
                            f'Aby uzyskać pomoc, wpisz `{ctx.prefix}help`. Aby dodać mnie na serwer, wpisz `{ctx.prefix}dodaj`. Uniwersalnym prefixem bota jest `b!`')

#
#     @commands.command()
#     @checks.have_required_level(1)
#     async def help(self, ctx):
#         """Get the bot help."""
#
#         message = textwrap.dedent(f"""
#         ** {ctx.me.mention} help**
#
#         The following commands are the most used ones. The required access level is shown as a prefix to the command. Remember that {ctx.me.mention} features include the automod, which dosen't have any commands, but that can be configured on the webinterface.
#         Also, if you have any question, we have answers on the support server: https://discord.gg/cPbhK53
#
#         ```
#         1. {ctx.prefix}level\t\tCheck your current access level
#         1. {ctx.prefix}urls <user>\tGive you the link to pages about a specific user on the webinterface
#         1. {ctx.prefix}invite\t\tGive an invite link to invite me :)
#
#         3. {ctx.prefix}unban [banned user(s)] <reason>\tUnban users that were banned on the server
#         2. {ctx.prefix}note [user(s)] [reason]\t\tAdd a note on users profiles. Notes are just informationnal and don't suffer from as many consequences as warns
#         2. {ctx.prefix}warn [user(s)] <reason>\t\tWarn users, adding a note on their profile. Warning can be subject to thresholds
#         2. {ctx.prefix}kick [user(s)] <reason>\t\tKick users from the server
#         3. {ctx.prefix}softban [user(s)] <reason>\t\tKick users while also deleting their most recent messages
#         3. {ctx.prefix}ban [user(s)] <reason>\t\tRemove users from the server and keep them out
#
#         4. {ctx.prefix}import_bans\t\tImport bans from the server banlist into the website
#
#         2. {ctx.prefix}purge\tMass delete messages (see {ctx.prefix}purge for usage info)
#         ```
#
#         Most of the commands shown here require the bot permissions to be correctly setup. Please give the bot the following permissions if you encounter problems
#         ```
#         kick_members,
#         ban_members,
#         read_messages,
#         send_messages,
#         manage_messages,
#         embed_links,
#         attach_files,
#         read_message_history,
#         external_emojis,
#         change_nickname
#         ```
#         """)
#
#         await ctx.send_to(message)
#
#         if await get_level(ctx, ctx.author) >= 4:
#             message = textwrap.dedent(f"""
#             Since you seem to be a server admin, a few more commands that could be helpful include
#
#             ```
#             {ctx.prefix}add_admin\t[user]\tAdd a user to the admin rank (level 4)
#             {ctx.prefix}add_moderator\t[user]\tAdd a user to the moderator rank (level 3)
#             {ctx.prefix}add_trusted_member\t[user]\tAdd a user to the trusted rank (level 2)
#             {ctx.prefix}add_banned_member\t[user]\tRemove a user right from using the bot on this server
#             ```
#             """)
#
#             await ctx.send_to(message)


def setup(bot: 'BamboBot'):
    bot.remove_command("help")
    bot.add_cog(Help(bot))

'''
Changes by me:
(1) Translated to polish
(2) Removed the ability to invite the bot
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Usunięto możliwość zapraszania bota
'''
