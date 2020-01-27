# -*- coding: utf-8 -*-
"""
Since purge is a more complex command, I've thrown it in a separate file

Stolen from R.Danny, will probably need a rewrite to be more user-friendly
"""
import argparse
import re
import shlex
import textwrap
import typing
from collections import Counter

import discord
from discord.ext import commands

from cogs.helpers import checks

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext


class Arguments(argparse.ArgumentParser):
    def error(self, message: str):
        raise RuntimeError(message)


class ModPurge(commands.Cog):
    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.api = bot.api

    @commands.group(aliases=['purge', 'usuń', 'kasuj'])
    @commands.guild_only()
    @checks.bot_have_permissions()
    @checks.have_required_level(2)
    async def remove(self, ctx: 'CustomContext'):
        """Usuwa wiadomości, które spełniają kryterium.
        Kiedy ta komenda zakończy swoje działania, dostaniesz wiadomość
        z informacją od kogo i ile wiadomości zostało usuniętych.
        """
        with ctx.typing():
            if ctx.invoked_subcommand is None:
                #help_cmd = self.bot.get_command('help')
                #await ctx.invoke(help_cmd, command='remove')
                await ctx.send_to(textwrap.dedent(f"""
                To jest komenda do usuwania na sterydach. Oto kilka szybkich przykładów:

                **Usuwa ostatnie 50 wiadomości**:
                ```
                {ctx.prefix}purge all 50
                ```

                **Usuwa ostatnie 100 wiadomości bota oraz wiadomości zaczynające się na {ctx.prefix} (prefix bota)**:
                ```
                {ctx.prefix}purge bot {ctx.prefix}
                ```

                **Usuwa ostatnie 50 załączonych plików**:
                ```
                {ctx.prefix}purge files 50
                ```

                **Usuwa ostatnie 100 wiadomości, które zawierają ciąg "owo"**:
                ```
                {ctx.prefix}purge contains owo
                ```

                *Aby uzyskać bardziej złóżone użycia, zobacz `{ctx.prefix}purge custom`*.
                Więcej informacji na https://docs.getbeaned.me/bot-documentation/using-the-purge-command-to-remove-messages (po angielsku!)
                """))

    async def do_removal(self, ctx: 'CustomContext', limit: int, predicate_given: typing.Callable, *, before: int = None, after: int = None):
        if limit > 2000:
            return await ctx.send(f'Podałeś za dużo wiadomości do wyszukania ({limit}/2000)')

        if before is None:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after is not None:
            after = discord.Object(id=after)

        def predicate(message: discord.Message):
            # Don't delete pinned message in any way
            return not message.pinned and predicate_given(message)

        try:
            deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
        except discord.Forbidden as e:
            return await ctx.send('Nie mam uprawnień do usuwania wiadomości.')
        except discord.HTTPException as e:
            return await ctx.send(f'Błąd: {e} (spróbuj mniejszego wyszukania?)')

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        # messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        messages = [f'{deleted}{" wiadomość została usunięta" if deleted == 1 else " wiadomości zostało usuniętych"}.']
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        to_send = '\n'.join(messages)

        if len(to_send) > 2000:
            await ctx.send(f'Pomyślnie usunięta {deleted} wiadomości.')
        else:
            await ctx.send(to_send)

    @remove.command()
    async def embeds(self, ctx: 'CustomContext', search: int = 100):
        """Usuwa wiadomości, które zawierają osadzenia."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @remove.command()
    async def files(self, ctx: 'CustomContext', search: int = 100):
        """Usuwa wiadomości, które zawierają załączniki."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @remove.command()
    async def images(self, ctx: 'CustomContext', search: int = 100):
        """Usuwa wiadomości, które zawierają osadzenia lub załączniki."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

    @remove.command(name='all')
    async def _remove_all(self, ctx: 'CustomContext', search: int = 100):
        """Usuwa wszystkie wiadomości."""
        await self.do_removal(ctx, search, lambda e: True)

    @remove.command()
    async def user(self, ctx: 'CustomContext', member: discord.Member, search: int = 100):
        """Usuwa wszystkie wiadomości danego użytkownik."""
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @remove.command()
    async def contains(self, ctx: 'CustomContext', *, substr: str):
        """Usuwa wszystkie wiadomości zawierające podany ciąg.
        Ciąg ten musi mieć przynajmniej 3 znaki.
        """
        if len(substr) < 3:
            await ctx.send('Ciąg musi mieć przynajmniej 3 znaki.')
        else:
            await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @remove.command(name='bot')
    async def _bot(self, ctx: 'CustomContext', prefix: str = None, search: int = 100):
        """Usuwa wiadomości bota i wiadomości z jego opcjonalnym prefixem."""

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))

        await self.do_removal(ctx, search, predicate)

    @remove.command(name='emoji')
    async def _emoji(self, ctx: 'CustomContext', search: int = 100):
        """Usuwa wszystkie wiadomości zawierające własne emotki."""
        custom_emoji = re.compile(r'<:(\w+):(\d+)>')

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @remove.command(name='reactions')
    async def _reactions(self, ctx: 'CustomContext', search: int = 100):
        """Usuwa wszystkie reakcje z wiadomości, które je posiadają."""

        if search > 2000:
            return await ctx.send(f'Za dużo wiadomości do szukania ({search}/2000)')

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        await ctx.send(f'Pomyślnie usunięto {total_reactions} reakcji.')

    @remove.command()
    async def custom(self, ctx: 'CustomContext', *, args: str):
        """Bardziej zaawansowana komenda do usuwania.
        Ta komenda używa potężną składnie "wiersza poleceń".
        Większość opcji wspiera wiele wartości, aby wskazać 'dowolne' dopasowanie.
        Jeżeli wartość posiada spacje, musi ona zostać podana w cudzysłowiu.
        Wiadomości zostaną usunięte tylko, jeżeli wszystkie kryteria zostaną spełnionie chyba,
        że flaga `--or` jest obecna, wtedy dowolne kryterium może zostać spełnione.
        Następujące opcje są poprawne.
        `--user`: Wzmianka lub nazwa użytkownika, którego wiadomość ma zostać usunięta.
        `--contains`: Ciąg znaków do wyszukania w wiadomości.
        `--starts`: Ciąg znaków, którym wiadomośc musi się rozpoczynać.
        `--ends`: Ciąg znaków, którym wiadomośc musi się kończyć.
        `--search`: Ile wiadomości ma zostać przeszukanych. Domyslnie 100, max 2000.
        `--after`: Wiadomość musi być napisana po wiadomości o podanym ID.
        `--before`: Wiadomość musi być napisana przed wiadomością o podanym ID.
        Flagi (bez argumentów):
        `--bot`: Sprawdza, czy użytkownik jest botem.
        `--embeds`: Sprawdza, czy wiadomość zawiera osadzenia.
        `--files`: Sprawdza, czy wiadomość zawiera załączniki.
        `--emoji`: Sprawdza, czy wiadomość zawiera własne emotki.
        `--reactions`: Sprawdza, czy wiadomość zawiera reakcje.
        `--or`: Uzyj logicznego OR dla wszystkich opcji.
        `--not`: Uzyj logicznego NOT dla wszystkich opcji.
        """
        parser = Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument('--user', nargs='+')
        parser.add_argument('--contains', nargs='+')
        parser.add_argument('--starts', nargs='+')
        parser.add_argument('--ends', nargs='+')
        parser.add_argument('--or', action='store_true', dest='_or')
        parser.add_argument('--not', action='store_true', dest='_not')
        parser.add_argument('--emoji', action='store_true')
        parser.add_argument('--bot', action='store_const', const=lambda m: m.author.bot)
        parser.add_argument('--embeds', action='store_const', const=lambda m: len(m.embeds))
        parser.add_argument('--files', action='store_const', const=lambda m: len(m.attachments))
        parser.add_argument('--reactions', action='store_const', const=lambda m: len(m.reactions))
        parser.add_argument('--search', type=int, default=100)
        parser.add_argument('--after', type=int)
        parser.add_argument('--before', type=int)

        try:
            args = parser.parse_args(shlex.split(args))
        except Exception as e:
            await ctx.send(str(e))
            return

        predicates = []
        if args.bot:
            predicates.append(args.bot)

        if args.embeds:
            predicates.append(args.embeds)

        if args.files:
            predicates.append(args.files)

        if args.reactions:
            predicates.append(args.reactions)

        if args.emoji:
            custom_emoji = re.compile(r'<:(\w+):(\d+)>')
            predicates.append(lambda m: custom_emoji.search(m.content))

        if args.user:
            users = []
            converter = commands.MemberConverter()
            for u in args.user:
                try:
                    user = await converter.convert(ctx, u)
                    users.append(user)
                except Exception as e:
                    await ctx.send(str(e))
                    return

            predicates.append(lambda m: m.author in users)

        if args.contains:
            predicates.append(lambda m: any(sub in m.content for sub in args.contains))

        if args.starts:
            predicates.append(lambda m: any(m.content.startswith(s) for s in args.starts))

        if args.ends:
            predicates.append(lambda m: any(m.content.endswith(s) for s in args.ends))

        op = all if not args._or else any

        def predicate(m):
            r = op(p(m) for p in predicates)
            if args._not:
                return not r
            return r

        args.search = max(0, min(2000, args.search))  # clamp from 0-2000

        await self.do_removal(ctx, args.search, predicate, before=args.before, after=args.after)


def setup(bot: 'BamboBot'):
    bot.add_cog(ModPurge(bot))

'''
Changes by me:
(1) Translated to polish
=====
Moje zmiany:
(1) Przetłumaczono na polski
'''
