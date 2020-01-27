# -*- coding: utf-8 -*-
import json
import typing

import discord
from discord.ext import tasks, commands

from cogs.helpers import checks
from cogs.helpers.actions import full_process, unban, unmute, rm_sponsor, rm_donator, rm_kodzik
from cogs.helpers.helpful_classes import LikeUser

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot


class Tasks(commands.Cog):
    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.run_tasks.start()
        self.count_members_task.start()
        self.tasks_mapping = {
            "refresh_user": self.refresh_user,
            "unmute": self.unmute_task,
            "unban": self.unban_task,
            "rm_sponsor": self.rm_sponsor_task,
            "rm_donator_x": self.rm_donator_task,
            "rm_kodzik": self.rm_kodzik_task,
        }

    def cog_unload(self):
        self.run_tasks.stop()

    async def rm_sponsor_task(self, task: dict):
        arguments = json.loads(task['arguments']) # {"target": 514557845111570447, "guild": 512328935304855555, "reason": "Time is up (1 week, 2 days and 23 hours)"}
        guild_id = arguments["guild"]

        guild:discord.Guild = self.bot.get_guild(guild_id)

        if guild:
            member = guild.get_member(arguments["target"])
            if member:
                tasks_user = LikeUser(did=5, name="DoItLater", guild=guild)
                act = await full_process(self.bot, rm_sponsor, member, tasks_user, arguments["reason"], automod_logs=f"Zadanie numer #{task['id']}")
                return True
            elif not member:
                self.bot.logger.warning(f"Completing task #{task['id']} failed. User (ID {arguments['target']}) not present on the server (ID {guild.id}).")
                return False

    async def rm_donator_task(self, task: dict):
        arguments = json.loads(task['arguments'])
        # print(f'rm_donator_task() arguments -> {arguments}')
        guild_id = arguments["guild"]
        # print(f'rm_donator_task() guild_id -> {guild_id}')
        guild:discord.Guild = self.bot.get_guild(guild_id)

        if guild:
            member = guild.get_member(arguments["target"])
            # print(f'rm_donator_task() member -> {member}')
            if member:
                tasks_user = LikeUser(did=5, name="DoItLater", guild=guild)
                # print(f'rm_donator_task() tasks_user -> {tasks_user}')
                act = await full_process(self.bot, rm_donator, member, tasks_user, arguments["reason"], automod_logs=f"Zadanie numer #{task['id']}")
                # print(f'rm_donator_task() act -> {act}')
                return True
            elif not member:
                self.bot.logger.warning(f"Completing task #{task['id']} failed. User (ID {arguments['target']}) not present on the server (ID {guild.id}).")
                return False

    async def rm_kodzik_task(self, task: dict):
        arguments = json.loads(task['arguments'])
        guild_id = arguments["guild"]
        guild:discord.Guild = self.bot.get_guild(guild_id)

        if guild:
            member = guild.get_member(arguments["target"])
            if member:
                tasks_user = LikeUser(did=5, name="DoItLater", guild=guild)
                act = await full_process(self.bot, rm_kodzik, member, tasks_user, arguments["reason"], automod_logs=f"Zadanie numer #{task['id']}")
                return True
            elif not member:
                self.bot.logger.warning(f"Completing task #{task['id']} failed. User (ID {arguments['target']}) not present on the server (ID {guild.id}).")
                return False

    async def unmute_task(self, task: dict):
        arguments = json.loads(task['arguments']) # {"target": 514557845111570447, "guild": 512328935304855555, "reason": "Time is up (1 week, 2 days and 23 hours)"}
        guild_id = arguments["guild"]

        guild:discord.Guild = self.bot.get_guild(guild_id)

        if guild:
            member = guild.get_member(arguments["target"])
            if member:
                tasks_user = LikeUser(did=5, name="DoItLater", guild=guild)
                act = await full_process(self.bot, unmute, member, tasks_user, arguments["reason"], automod_logs=f"Zadanie numer #{task['id']}")
                return True
            elif not member:
                self.bot.logger.warning(f"Completing task #{task['id']} failed. User (ID {arguments['target']}) not present on the server (ID {guild.id}).")
                return False

    async def unban_task(self, task: dict):
        arguments = json.loads(task['arguments'])  # {"target": 514557845111570447, "guild": 512328935304855555, "reason": "Time is up (1 week, 2 days and 23 hours)"}
        guild_id = arguments["guild"]

        guild: discord.Guild = self.bot.get_guild(guild_id)

        if guild:
            # user = await self.bot.fetch_user(int(task["arguments"]))
            user = await self.bot.fetch_user(int(arguments["target"]))

            if user:
                if not user.id in [b.user.id for b in await guild.bans()]:
                    return True  # Already unbanned
                tasks_user = LikeUser(did=5, name="DoItLater", guild=guild)
                act = await full_process(self.bot, unban, user, tasks_user, arguments["reason"], automod_logs=f"Zadanie numer #{task['id']}")
                return True

        # Failed because no such guild/user
        return True  # Anyway

    async def refresh_user(self, task: dict):
        user = self.bot.get_user(int(task["arguments"]))

        if user is None:
            try:
                user = await self.bot.fetch_user(int(task["arguments"]))
            except discord.errors.NotFound:
                self.bot.logger.warning(f"Completing task #{task['id']} failed. User not found.")
                return True  # Returning true anyway

        if user is not None:
            await self.bot.api.add_user(user)
            return True
        else:
            self.bot.logger.warning(f"Completing task #{task['id']} failed. User not found.")
            return True  # Returning true anyway

    async def dispatch_task(self, task: dict):
        self.bot.logger.info(f"Running task #{task['id']}...")
        self.bot.logger.debug(str(task))

        # print(task)
        # print(task["type"])
        task_type = task["type"]
        # print(self.tasks_mapping[task_type])
        # print(f'{task["type"]}')

        try:
            res = await self.tasks_mapping[task_type](task)
            self.bot.logger.debug(f"Ran task #{task['id']}, result is {res}")
            if res is not False:  # So if res is None, it'll still return True
                return True
            else:
                return False
        except KeyError:
            self.bot.logger.warning(f"Unsupported task #{task['id']}, type is {task['type']}")
            return False  # Unsupported task type

    @tasks.loop(minutes=1)
    async def run_tasks(self):
        try:
            #self.bot.logger.info("Cleaning up cache")
            tasks = await self.bot.api.get_tasks()
            self.bot.logger.debug(f"Got task list: {tasks}")
            for task in tasks:
                res = await self.dispatch_task(task)

                if res:
                    self.bot.logger.info(f"Completed task #{task['id']}")
                    await self.bot.api.complete_task(task["id"])
                else:
                    self.bot.logger.warning(f"Completing task #{task['id']} failed. res={res}")
        except Exception as e:
            self.bot.logger.exception(f"Failed in tasks loop...")
            raise


    @run_tasks.before_loop
    async def before_task(self):
        await self.bot.wait_until_ready()
        self.bot.logger.info("We are running tasks.")


    @tasks.loop(minutes=5)
    async def count_members_task(self):
        try:
            guilds = self.bot.guilds
            # self.bot.logger.debug(f'Got guilds list: {guilds}')
            self.bot.logger.debug('Liczenie członków dla serwerów...')
            for guild in guilds:
                if not await self.bot.settings.get(guild, "vip"):
                    self.bot.logger.debug(f'Licznik członków dla serwera `{guild.name}` (ID {guild.id}) automatycznie wyłączony, ponieważ nie posiada on statusu VIP.')
                else:
                    active = await self.bot.settings.get(guild, 'members_counters')
                    if not active:
                        self.bot.logger.debug(f'Serwer `{guild.name}` (ID {guild.id}) posiada status VIP, ale ustawienie licznika jest wyłączone')
                        continue
                    else:
                        try:
                            members_counters_total_id = int(await self.bot.settings.get(guild, 'members_counters_total_id'))
                        except ValueError:
                            self.bot.logger.warning(f'[{guild.name} (ID {guild.id})] W polu `members_counters_total_id` znajduje się tekst, nie mogę tego przetworzyć')
                        else:
                            try:
                                members_counters_online_id = int(await self.bot.settings.get(guild, 'members_counters_online_id'))
                            except ValueError:
                                self.bot.logger.warning(f'[{guild.name} (ID {guild.id})] W polu `members_counters_online_id` znajduje się tekst, nie mogę tego przetworzyć')
                            else:
                                channel_total = discord.utils.get(guild.channels, id=members_counters_total_id)
                                channel_online = discord.utils.get(guild.channels, id=members_counters_online_id)
                                if not channel_total:
                                    self.bot.logger.warning(f'[{guild.name} (ID {guild.id})] Kanał `members_counters_total_id` ID{members_counters_total_id} nie znaleziony')
                                    continue
                                elif not channel_online:
                                    self.bot.logger.warning(f'[{guild.name} (ID {guild.id})] Kanał `members_counters_online_id` ID{members_counters_online_id} nie znaleziony')
                                    continue
                                else:
                                    self.bot.logger.debug(f'Liczę ilość członków dla serwera `{guild.name}` (ID {guild.id})')
                                    members_total = 0
                                    members_online = 0
                                    for member in guild.members:
                                        if not member.bot:
                                            members_total += 1
                                            if member.status != discord.Status.offline:
                                                members_online += 1
                                    self.bot.logger.info(f'[{guild.name} (ID {guild.id})] Ilość członków total: {members_total}')
                                    self.bot.logger.info(f'[{guild.name} (ID {guild.id})] Ilość członków online: {members_online}')
                                    await channel_total.edit(name=f'💙 Ilość członków: {members_total}')
                                    await channel_online.edit(name=f'💚 Online: {members_online}')
            self.bot.logger.debug('Liczenie członków zakończone!')
        except Exception as e:
            self.bot.logger.exception(f"Failed in count members task loop...")
            raise

    @count_members_task.before_loop
    async def before_task(self):
        await self.bot.wait_until_ready()
        self.bot.logger.info("We are running count members task.")

def setup(bot: 'BamboBot'):
    tasks = Tasks(bot)
    bot.add_cog(tasks)

'''
Changes by me:
(1) Translated (some text) to polish
(2) Added 3 tasks to handle the new special mod actions
(3) Added a server members counting task
=====
Moje zmiany:
(1) Przetłumaczono (trochę tekstu) na polski
(2) Dodano 3 zadania odpowiedzialne za specjalne akcje moderacyjne
(3) Dodano zadanie liczenia członków serwera
'''
