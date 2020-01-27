# -*- coding: utf-8 -*-
"""
This file is meant to keep code for AutoTriggers, so that the automod file isn't too big
Everything here should be imported by automod if enabled
"""
import datetime
import re
import sys
import traceback
import typing
from typing import List

import discord

if typing.TYPE_CHECKING:
    from cogs.automod import CheckMessage


class AutoTrigger:
    def __init__(self, message: 'CheckMessage'):
        self.check_message = message
        self.message = message.message
        self.autotrigger_name = "Generic AutoTrigger"
        self.autotrigger_dbname = "generic"

    async def is_enabled(self) -> bool:
        pref_name = f"autotrigger_{self.autotrigger_dbname}_score"

        return (await self.check_message.bot.settings.get(self.message.guild, pref_name)) != 0

    async def get_score(self) -> float:
        pref_name = f"autotrigger_{self.autotrigger_dbname}_score"

        return await self.check_message.bot.settings.get(self.message.guild, pref_name)

    async def check(self) -> bool:
        return False

    async def run(self) -> float:
        if await self.is_enabled():
            try:
                ret = await self.check()
            except AssertionError:
                ret = False
                # _, _, tb = sys.exc_info()
                # traceback.print_tb(tb)  # Fixed format
                # tb_info = traceback.extract_tb(tb)
                # filename, line, func, text = tb_info[-1]

                # shown_text = text.replace("assert await ", "").replace("assert ", "")

                # self.check_message.debug('Wyzwalacz nie zadziałał w linii {} (stmt to `{}`)'.format(line, shown_text))

            self.check_message.debug(f"> Sprawdzono {self.autotrigger_name} z wynikiem {ret}")
            if ret:
                score = await self.get_score()
                self.check_message.debug(f"> > {self.autotrigger_name}: dodawanie {score} punktów do wyniku")
                return score
            else:
                return 0
        else:
            return 0


class SexDatingDiscordBots(AutoTrigger):
    def __init__(self, message):
        super().__init__(message)
        self.autotrigger_name = "Sex Dating Discord Bots"
        self.autotrigger_dbname = "sexdatingdiscordbots"

    async def check(self):
        assert await message_contains_any(self.message, ["discord.amazingsexdating.com", "Sex dating discord >", "Sex Dating >", "Best casino online >"
                                                         "Sex Discord"])
        assert await user_dont_have_a_profile_picture(self.message.author)
        assert await member_joined_x_days_ago(self.message.author, x=1)
        return True


# http://write-me-tender.ml/ - Instant Essay Writing Service! Best Prices - Best Writers !
# http://cool-essay.ga - Order essay writing online! Smarter and faster than your profs!
# http://write-some.ga/ - From admission essays to graduate dissertations - rely on a trusted service to do it for you!
class InstantEssayDiscordBots(AutoTrigger):
    def __init__(self, message):
        super().__init__(message)
        self.autotrigger_name = "Instant Essay Discord Bots"
        self.autotrigger_dbname = "instantessaydiscordbots"

    async def check(self):
        assert await message_contains_x_of(self.message, 4, ["write-me-tender.ml", "cool-essay.ga", "essay", "writers", "profs", "order essay", "instant essay",
                                                             "Instant Essay Writing Service!", "Order essay writing online!", "Best Prices - Best Writers !", "write-some.ga",
                                                             "admission essays", "graduate dissertations"])

        assert await member_joined_x_days_ago(self.message.author, x=1)
        assert await user_created_x_days_ago(self.message.author, x=3)
        assert not await user_have_nitro(self.message.author)

        return True


# :heart_eyes: 🥰 My 18+ photos :stuck_out_tongue_winking_eye: - https://www.nakedphotos.club/
class SexBots(AutoTrigger):
    def __init__(self, message):
        super().__init__(message)
        self.autotrigger_name = "Sex Bots"
        self.autotrigger_dbname = "sexbots"

    async def check(self):
        assert await message_contains_x_of(self.message, 1, ["privatepage.vip", "nakedphotos.club", "viewc.site", "My naked photos", "My 18+ photos", "Awesome Gift of the Day", "Moje nagie fotki"])

        assert await member_joined_x_days_ago(self.message.author, x=2)

        # If the account is not that old or if it's matching the name pattern.
        assert (await user_created_x_days_ago(self.message.author, x=14) or
                bool(re.match(r"([A-Z][a-z]+[0-9]{1,4}|[A-Z][a-z]+\.([a-z]+\.[a-z]+|[a-z]+[0-9]{1,2}))$", self.message.author.name)))

        assert not await user_have_nitro(self.message.author)

        return True


async def user_dont_have_a_profile_picture(user: discord.User) -> bool:
    return user.avatar_url == user.default_avatar_url


async def user_have_nitro(user: discord.User) -> bool:
    return user.is_avatar_animated()


async def member_joined_x_days_ago(member: discord.Member, x=1) -> bool:
    return member.joined_at > datetime.datetime.now() - datetime.timedelta(days=x)


async def user_created_x_days_ago(member: discord.Member, x=1) -> bool:
    return member.created_at > datetime.datetime.now() - datetime.timedelta(days=x)


async def message_contains(message: discord.Message, text: str) -> bool:
    text = text.lower()
    message_content = message.content.lower().strip()
    return text in message_content


async def message_contains_any(message: discord.Message, texts: List[str]) -> bool:
    return await message_contains_x_of(message, 1, texts)


async def message_contains_x_of(message: discord.Message, x: int, texts: List[str]) -> bool:
    assert x <= len(texts)
    assert x > 0

    current_count = 0
    for text in texts:
        if await message_contains(message, text):
            current_count += 1
            if current_count >= x:
                return True
    return False
