# -*- coding: utf-8 -*-
import collections
import datetime
import logging
import re
import typing
import unicodedata
from typing import Union
import string
import discord
import numpy

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot


from discord.ext import commands

from cogs.helpers import checks, context
from cogs.helpers.actions import full_process, note, warn, kick, softban, ban
from cogs.helpers.helpful_classes import LikeUser
from cogs.helpers.level import get_level
from cogs.helpers.triggers import SexDatingDiscordBots, InstantEssayDiscordBots, SexBots
from cogs.helpers.context import CustomContext

ZALGO_CHAR_CATEGORIES = ['Mn', 'Me']
DEBUG = False

TRIGGERS_ENABLED = [SexDatingDiscordBots, InstantEssayDiscordBots, SexBots]

polish_letters = 'ąćęłńóśźżĄĆĘŁŃÓŚŹŻ'
all_letters = string.ascii_letters + polish_letters

class CheckMessage:
    def __init__(self, bot: 'BamboBot', message: discord.Message):
        self.bot = bot
        self.message = message
        self.multiplicator = 1
        self.score = 0

        self.old_multiplicator = self.multiplicator
        self.old_score = self.score

        self.logs = []

        self.invites = []

        self.debug(f"WIADOMOŚĆ : {message.content:.100} (na #{message.channel.name})")

    @property
    def total(self) -> float:
        return round(self.multiplicator * self.score, 3)

    @property
    def old_total(self) -> float:
        return round(self.old_multiplicator * self.old_score, 3)

    @property
    def invites_code(self) -> typing.Iterable[str]:
        return [i.code for i in self.invites]

    @property
    def logs_for_discord(self) -> str:
        return "```\n" + "\n".join(self.logs) + "\n```"

    def debug(self, s):
        fs = f"[s={self.score:+.2f} ({self.score - self.old_score:+.2f})," \
             f" m={self.multiplicator:+.2f} ({self.multiplicator - self.old_multiplicator:+.2f})," \
             f" t={self.total:+.2f} ({self.total - self.old_total:+.2f})] > " + s

        if DEBUG:
            if self.message.channel:
                cname = self.message.channel.name
            else:
                cname = "PRIVATE_MESSAGE"

            extra = {"channelname": f"#{cname}", "userid": f"{self.message.author.id}",
                     "username": f"{self.message.author.name}#{self.message.author.discriminator}"}
            logger = logging.LoggerAdapter(self.bot.base_logger, extra)
            logger.debug(f"AM " + fs)

        self.logs.append(fs)
        self.old_score = self.score
        self.old_multiplicator = self.multiplicator


class AutoMod(commands.Cog):
    """
    Własny parser on_message do wykrywania i zapobiegania taki rzeczom jak spam, wzmianki <@>here/everyone...
    """

    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.api = bot.api

        # https://regex101.com/r/6EotUl/1
        self.invites_regex = re.compile(
            r"""
                discord      # Literally just discord
                \s?          # Sometimes people use spaces before dots to twhart the AutoMod. Let's stop that by allowing 1 space here
                (?:app\s?\.\s?com\s?/invite|\.\s?gg)\s?/ # All the domains
                \s?          # And here too
                ((?!.*[Ii10OolL]).[a-zA-Z0-9]{5,6}|[a-zA-Z0-9\-]{2,32}) # Rest of the fucking owl.
                """, flags=re.VERBOSE)

        # self.message_history = collections.defaultdict(
        #    lambda: collections.deque(maxlen=7))  # Member -> collections.deque(maxlen=7)

        self.message_history = bot.cache.get_cache("automod_previous_messages", expire_after=600, default=lambda: collections.deque(maxlen=7))

        self.invites_codes_cache = bot.cache.get_cache("automod_invites_codes", expire_after=3600)

        self.automod_cache = bot.cache.get_cache("automod_logs", expire_after=3600)

    async def contains_zalgo(self, message: str):
        THRESHOLD = 0.5
        if len(message) == 0:
            return False, 0
        word_scores = []
        for word in message.split():
            cats = [unicodedata.category(c) for c in word]
            score = sum([cats.count(banned) for banned in ZALGO_CHAR_CATEGORIES]) / len(word)
            word_scores.append(score)
        total_score = numpy.percentile(word_scores, 75)
        contain = total_score > THRESHOLD
        return contain, total_score

    async def get_invites(self, message: str) -> typing.List[str]:
        #message = message.lower() -- Don't do that, invites are Case Sensitive :x

        invites = self.invites_regex.findall(message)

        return list(set(invites)) or None

    async def get_invites_count(self, check_message: CheckMessage) -> int:
        message_str = check_message.message.content
        invites = await self.get_invites(message_str)

        if invites is None:
            return 0
        else:
            total = 0
            for invite in invites:
                check_message.debug(f"Sprawdzam kod zaproszenia : {invite}")
                invite_obj = self.invites_codes_cache.get(invite, None)
                try:
                    if invite_obj is None:
                        invite_obj = await self.bot.fetch_invite(invite, with_counts=True)
                    self.invites_codes_cache[invite] = invite_obj
                    if invite_obj.guild.id not in [469179839304302615, 436177140942241792, 637348322679717889, 586450144292110337, 552611048868413441, 404938113551695892] + [check_message.message.guild.id]:
                        minimal_membercount = await self.bot.settings.get(check_message.message.guild, 'automod_minimal_membercount_trust_server')

                        try:
                            member_count = invite_obj.approximate_member_count
                        except AttributeError:
                            member_count = 0
                        if 0 < minimal_membercount < member_count:
                            check_message.debug(
                                f">> Wykryto kod zaproszenia z niezaufanego serwera, ale znanego na tyle, żeby nie wykonywać akcji (liczba członków ok. {member_count}): "
                                f"{invite_obj.code} (serwer : {invite_obj.guild.name} - {invite_obj.guild.id})")
                        else:
                            check_message.debug(
                                f">> Wykryto kod zaproszenia z niezaufanego serwera (liczba członków ok. {member_count}): "
                                f"{invite_obj.code} (serwer : {invite_obj.guild.name} - {invite_obj.guild.id})")

                            check_message.invites.append(invite_obj)
                            total += 1
                    else:
                        check_message.debug(f">> Wykryto kod zaproszenia z zaufanego serwera:"
                                            f"{invite_obj.code}")
                except discord.errors.NotFound:
                    self.invites_codes_cache[invite] = None
                    check_message.debug(f">> Niepoprawny kod zaproszenia")

                    continue

            return total

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_minimal_permissions()
    # @checks.have_required_level(8)
    async def automod_debug(self, ctx: 'CustomContext', *, message_str: str):
        ctx.message.content = message_str
        cm = await self.check_message(ctx.message, act=False)
        if isinstance(cm, CheckMessage):
            await ctx.send_to(cm.logs_for_discord)
        else:
            await ctx.send_to(f"Automod jest wyłączony, lub coś innego. (cm={cm})")

    @commands.command()
    # @checks.have_required_level(8)
    async def automod_logs(self, ctx: 'CustomContext', message_id: int):
        await ctx.send_to("Ta komenda jest przestarzała. Użyj nowej komendy `message_info` :)")
        log = self.automod_cache.get(message_id, "Nie znaleziono logów dla tego ID wiadomości, może została usunięta ?")

        await ctx.send_to(log)

    async def check_message(self, message: discord.Message, act: bool = True) -> Union[CheckMessage, str]:
        await self.bot.wait_until_ready()
        author = message.author

        if author.bot:
            return "Jesteś botem"  # ignore messages from other bots

        if message.guild is None:
            return "Nie na serwerze"  # ignore messages from PMs

        if not await self.bot.settings.get(message.guild, 'automod_enable') and not "[bambobot:enable_automod]" in str(message.channel.topic):
            return "Automod jest tutaj wyłączony"

        if "[bambobot:disable_automod]" in str(message.channel.topic):
            return "`[bambobot:disable_automod]` w temacie kanału, Automod jest tutaj wyłączony"

        current_permissions = message.guild.me.permissions_in(message.channel)
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
            change_nickname=True
        )

        cond = current_permissions >= wanted_permissions

        if not cond:
            return "Brak permisji aby działać"

        check_message = CheckMessage(self.bot, message)
        ctx = await self.bot.get_context(message, cls=context.CustomContext)

        author_level = await get_level(ctx, check_message.message.author)
        automod_ignore_level = await self.bot.settings.get(message.guild, 'automod_ignore_level')

        if author_level >= automod_ignore_level and act:
            return "Poziom autora wiadomości jest za wysoki, nie idę dalej"

        if author.status is discord.Status.offline:
            check_message.multiplicator += await self.bot.settings.get(message.guild, 'automod_multiplictor_offline')
            check_message.debug("Autor wiadomości jest offline (prawdopodobnie niewidoczny)")

        if author.created_at > datetime.datetime.now() - datetime.timedelta(days=7):
            check_message.multiplicator += await self.bot.settings.get(message.guild, 'automod_multiplictor_new_account')
            check_message.debug("Konto autora jest młodsze niż tydzień")

        if author.joined_at > datetime.datetime.now() - datetime.timedelta(days=1):
            check_message.multiplicator += await self.bot.settings.get(message.guild, 'automod_multiplictor_just_joined')
            check_message.debug("Użytkownik dołączył nie dawniej niż dobę temu")

        if author.is_avatar_animated():
            check_message.multiplicator += await self.bot.settings.get(message.guild, 'automod_multiplictor_have_nitro')
            check_message.debug("Użytkownik ma Nitro (albo przynajmniej potrawię wykryć, że ma animowany awatar)")

        if len(author.roles) > 2:  # Role duckies is given by default
            check_message.multiplicator += await self.bot.settings.get(message.guild, 'automod_multiplictor_have_roles')
            check_message.debug("Użytkownik ma rolę na serwerze")

        if author_level == 0:
            check_message.multiplicator += await self.bot.settings.get(message.guild, 'automod_multiplictor_bot_banned')
            check_message.debug("Użytkownij jest zbanowany w bocie")

        if check_message.multiplicator <= 0:
            check_message.debug("Mnożnik wynosi <= 0, kończenie bez liczenia wyniku")
            return check_message  # Multiplicator too low!

        check_message.debug("Obliczenie mnożników wykonane")

        ## Multiplicator calculation done!

        msg_letters = ''
        for pos, char in enumerate(message.content):
            if char in all_letters:
                msg_letters += message.content[pos]
        total_letters = len(msg_letters)
        total_captial_letters = sum(1 for c in msg_letters if c.isupper())
        # If no letters, then 100% caps.
        caps_percentage = total_captial_letters / total_letters if total_letters > 0 else 1

        if caps_percentage >= 0.7 and total_letters > 10:
            check_message.score += await self.bot.settings.get(message.guild, 'automod_score_caps')
            check_message.debug(f"Wiadomość napisana jest WIELKIMI LITERAMI (% capsa: {round(caps_percentage * 100, 3)} —"
                                f" całkowita długość: {len(message.content)})")

        # if len(message.embeds) >= 1 and any([e.type == "rich" for e in message.embeds]):
        #   check_message.score += await self.bot.settings.get(message.guild, 'automod_score_embed')
        #   check_message.debug(f"Message from a USER contain an EMBED !? (Used to circumvent content blocking)")

        if "@everyone" in message.content and not message.mention_everyone:
            check_message.score += await self.bot.settings.get(message.guild, 'automod_score_everyone')
            check_message.debug(
                f"Wiadomość zawiera <@>everyone, który Discord nie zarejestrował jako wzmiankę (próba nieudana)")

        mentions = set(message.mentions)
        if len(mentions) > 3:
            check_message.score += await self.bot.settings.get(message.guild, 'automod_score_too_many_mentions')
            m_list = [a.name + '#' + a.discriminator for a in mentions]
            check_message.debug(f"Wiadomość zawiera wzmiankę więcej niż 3 osób ({m_list})")

        if "[bambobot:disable_invite_detection]" not in str(message.channel.topic) and await self.get_invites_count(check_message) >= 1:  # They can add multiple channels separated by a " "
            check_message.score += await self.bot.settings.get(message.guild, 'automod_score_contain_invites')
            check_message.debug(f"Wiadomość zawiera zaproszenie/a ({check_message.invites_code})")

        if message.content and "[bambobot:disable_spam_detection]" not in str(message.channel.topic):
            # TODO: Check images repeat
            repeat = self.message_history[check_message.message.author].count(check_message.message.content)
            if repeat >= 3:
                check_message.score += await self.bot.settings.get(message.guild, 'automod_score_repeated') * repeat
                check_message.debug(f"Wiadomość została powtórzona {repeat} razy")

        bad_words_matches = await self.bot.settings.get_bad_word_matches(message.guild, check_message.message.content)
        bad_words_count = len(bad_words_matches)

        if bad_words_count >= 1:
            check_message.score += await self.bot.settings.get(message.guild, 'automod_score_bad_words') * bad_words_count
            bad_words_list = []
            for match in bad_words_matches:
                string, pattern = match
                bad_words_list.append(f"{string} odpowiada wzorowi {pattern}")
            check_message.debug(f"Wiadomość zawiera {bad_words_count} złych słów ({', '.join(bad_words_list)})")

        spam_cond = (not check_message.message.content.lower().startswith(("dh", "!", "?", "§", "t!", ">", "<", "-", "+")) or
                     len(message.mentions) or
                     len(check_message.message.content) > 30) and (
                check_message.message.content.lower() not in ['yes', 'no', 'maybe', 'hey', 'hi', 'hello', 'oui',
                                                                  'non', 'bonjour', '\o', 'o/', ':)', ':D', ':(', 'ok',
                                                                  'this', 'that', 'yup', 'tak', 'nie', 'może', 'hej', 'hejo',
                                                                  'hejka', 'to', 'tamto', 'jb', 'rx']
        ) and act

        if spam_cond:
            # Not a command or something
            self.message_history[check_message.message.author].append(check_message.message)  # Add content for repeat-check later.
            self.message_history.reset_expiry(check_message.message.author)

        if len(message.mentions):

            historic_mentions_users = []

            for historic_message in self.message_history[check_message.message.author]:
                historic_mentions_users.extend(historic_message.mentions)

            historic_mentions_total = len(historic_mentions_users)
            historic_mentions_users = set(historic_mentions_users)
            historic_mentions_different = len(historic_mentions_users)

            if historic_mentions_total > 7:  # He mentioned 7 times in the last 7 messages
                check_message.score += await self.bot.settings.get(message.guild, 'automod_score_multimessage_too_many_mentions')
                check_message.debug(f"Historia wiadomości zawiera za dużo wzmianek (historic_mentions_total={historic_mentions_total})")

            if historic_mentions_different > 5:  # He mentioned 5 different users in the last 7 messages
                check_message.score += await self.bot.settings.get(message.guild, 'automod_score_multimessage_too_many_users_mentions')
                check_message.debug(f"Historia wiadomości zawiera za dużo wzmianek (historic_mentions_different={historic_mentions_different} | users_mentionned: {historic_mentions_users})")

        contains_zalgo, zalgo_score = await self.contains_zalgo(message.content)

        if contains_zalgo:
            check_message.score += await self.bot.settings.get(message.guild, 'automod_score_zalgo')
            check_message.debug(f"Wiadomość zawiera zalgo (zalgo_score={zalgo_score})")

        if await self.bot.settings.get(message.guild, 'autotrigger_enable'):
            check_message.debug("Uruchamianie kontroli AutoTrigger'ów")
            instancied_triggers = [t(check_message) for t in TRIGGERS_ENABLED]

            for trigger in instancied_triggers:
                score = await trigger.run()
                if score != 0:
                    check_message.score += score

        check_message.debug("Obliczanie wyniku wykonane")
        check_message.debug(f"Suma dla wiadomości wynosi {check_message.total}, wykonuję akcje, jeżeli jakieś są")

        automod_user = LikeUser(did=1, name="AutoModerator", guild=message.guild)

        # Do we need to delete the message ?
        automod_delete_message_score = await self.bot.settings.get(message.guild, 'automod_delete_message_score')
        if check_message.total >= automod_delete_message_score > 0:
            check_message.debug(f"Usuwanie wiadomości, ponieważ punktacja "
                                f"**{check_message.total}** >= {automod_delete_message_score}")
            try:
                if act:
                    await message.delete()
                    if await self.bot.settings.get(message.guild, 'automod_note_message_deletions'):
                        await full_process(ctx.bot, note, message.author, automod_user, reason="Automod usunął wiadomość tego użytkownika",
                                           automod_logs="\n".join(check_message.logs))

            except discord.errors.NotFound:
                check_message.debug(f"Wiadomość została już usunięta!")

        else:  # Too low to do anything else
            return check_message

        # That's moderation acts, where the bot grabs his BIG HAMMER and throw it in the user face
        # Warning
        automod_warn_score = await self.bot.settings.get(message.guild, 'automod_warn_score')
        automod_kick_score = await self.bot.settings.get(message.guild, 'automod_kick_score')
        automod_softban_score = await self.bot.settings.get(message.guild, 'automod_softban_score')
        automod_ban_score = await self.bot.settings.get(message.guild, 'automod_ban_score')

        # Lets go in descending order:
        if check_message.total >= automod_ban_score > 0:
            check_message.debug(f"Banowanie użytkownika, ponieważ punktacja **{check_message.total}** >= {automod_ban_score}")
            if act:
                r = f"Automatyczna akcja od AutoModa. " \
                    f"Banowanie użytkownika, ponieważ punktacja **{check_message.total}** >= {automod_ban_score}"
                await full_process(ctx.bot, ban, message.author, automod_user,
                                   reason=r,
                                   automod_logs="\n".join(check_message.logs))

        elif check_message.total >= automod_softban_score > 0:
            check_message.debug(f"SoftBanowanie użytkownika, ponieważ punktacja **{check_message.total}** >= {automod_softban_score}")
            if act:
                r = f"Automatyczna akcja od AutoModa. " \
                    f"SoftBanowanie użytkownika, ponieważ punktacja **{check_message.total}** >= {automod_softban_score}"
                await full_process(ctx.bot, softban, message.author, automod_user,
                                   reason=r,
                                   automod_logs="\n".join(check_message.logs))

        elif check_message.total >= automod_kick_score > 0:
            check_message.debug(f"Wyrzucanie użytkownika, ponieważ punktacja **{check_message.total}** >= {automod_kick_score}")
            if act:
                r = f"Automatyczna akcja od AutoModa. " \
                    f"Wyrzucanie użytkownika, ponieważ punktacja  **{check_message.total}** >= {automod_kick_score}"
                await full_process(ctx.bot, kick, message.author, automod_user,
                                   reason=r,
                                   automod_logs="\n".join(check_message.logs))
        elif check_message.total >= automod_warn_score > 0:
            check_message.debug(f"Ostrzeganie użytkownika, ponieważ punktacja  **{check_message.total}** >= {automod_warn_score}")
            if act:
                r = f"Automatyczna akcja od AutoModa. " \
                    f"Ostrzeganie użytkownika, ponieważ punktacja  **{check_message.total}** >= {automod_warn_score}"
                await full_process(ctx.bot, warn, message.author, automod_user,
                                   reason=r,
                                   automod_logs="\n".join(check_message.logs))

        ctx.logger.info("AutoMod zadziałał na wiadomości, oto logi:")
        ctx.logger.info("\n".join(check_message.logs))
        return check_message

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.bot.wait_until_ready()
        if not message.guild:
            return False  # No PMs

        ret = await self.check_message(message)

        try:
            logs = ret.logs_for_discord
        except AttributeError:
            logs = str(ret)

        self.automod_cache[message.id] = logs

    @commands.Cog.listener()
    async def on_message_edit(self, _: discord.Message, message: discord.Message):
        await self.bot.wait_until_ready()
        if not len(message.content): return
        ret = await self.check_message(message)

        try:
            logs = ret.logs_for_discord
        except AttributeError:
            logs = str(ret)

        logs = self.automod_cache.get(message.id, "(Brak logów przed edycją)") + "\n==DOKONANO EDYCJI==\n" + logs

        self.automod_cache[message.id] = logs


def setup(bot: 'BamboBot'):
    bot.add_cog(AutoMod(bot))

'''
Changes by me:
(1) Translated to polish
(2) Addes some polish words to the message content check
(3) Changed detecting CAPS so that it only counts letters and not other characters
=====
Moje zmiany:
(1) Przetłumaczono na polski
(2) Dodano kilka polskich słów do sprawdzania zawartości wiadomości
(3) Zmiana w sprawdzaniu CAPSA, teraz sprawdza tylko litery a nie wszystkie znaki
'''
