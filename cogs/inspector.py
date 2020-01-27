# -*- coding: utf-8 -*-
import datetime
import time
import typing

from cogs.helpers.time import human_timedelta
import discord
from discord.ext import commands

from cogs.helpers import checks
from cogs.helpers.converters import ForcedMember

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext
STATUS_EMOJIS = {"offline": "<:offline:668409703168081944>",
                 "online": "<:online:668409703532986368>",
                 "idle": "<:away:668409703164018730>",
                 "dnd": "<:dnd:668409703411351563>",
                 "invisible": "<:invisible:668409703449100308>"}
STATUS_VERBOSE = {
    'offline': 'Offline',
    'online': 'Online',
    'idle': 'Zaraz Wracam',
    'dnd': 'Nie Przeszkadzać',
    'invisible': 'Niewidoczny'
}

async def inspect_member(ctx: 'CustomContext', inspected: typing.Union[discord.Member, discord.User]):
    icon_url = ctx.guild.me.avatar_url
    e = discord.Embed(title="Inspekcja BamboBota")

    if isinstance(inspected, discord.Member) and inspected.guild.id == ctx.guild.id:
        e.set_footer(text="Członek jest aktualnie na serwerze", icon_url=icon_url)
    elif ctx.guild.get_member(inspected.id):
        e.set_footer(text="Użytkownik jest aktualnie na serwerze", icon_url=icon_url)
    else:
        e.set_footer(text="Użytkownik nie znajduje się na serwerze", icon_url=icon_url)

    e.add_field(name="Nazwa", value=inspected.name, inline=True)
    e.add_field(name="Dyskryminator", value=inspected.discriminator, inline=True)
    e.add_field(name="ID", value=str(inspected.id), inline=True)

    if isinstance(inspected, discord.Member):
        e.add_field(name="(PC) Status", value=f"{STATUS_EMOJIS[inspected.desktop_status.name]} {STATUS_VERBOSE[inspected.desktop_status.name]}", inline=True)
        e.add_field(name="(Mobilnie) Status", value=f"{STATUS_EMOJIS[inspected.mobile_status.name]} {STATUS_VERBOSE[inspected.mobile_status.name]}", inline=True)
        e.add_field(name="Status", value=f"{STATUS_EMOJIS[inspected.status.name]} {STATUS_VERBOSE[inspected.status.name]}", inline=True)

        human_delta = human_timedelta(inspected.joined_at, source=datetime.datetime.utcnow())
        e.add_field(name="Dołączył", value=str(inspected.joined_at) + f" ({human_delta})", inline=False)

    human_delta = human_timedelta(inspected.created_at, source=datetime.datetime.utcnow())
    e.add_field(name="Konto utworzone", value=str(inspected.created_at) + f" ({human_delta})", inline=False)

    e.add_field(name="URL awataru", value=inspected.avatar_url, inline=False)

    e.add_field(name="URL domyślnego awataru", value=inspected.default_avatar_url, inline=False)
    e.set_author(name=inspected.name, url=f"https://bambobot.herokuapp.com/users/{inspected.id}", icon_url=inspected.avatar_url)

    e.set_image(url=str(inspected.avatar_url))


    await ctx.send(embed=e)


async def inspect_channel(ctx: 'CustomContext', inspected: typing.Union[discord.TextChannel, discord.VoiceChannel]):
    icon_url = ctx.guild.me.avatar_url
    e = discord.Embed(title="Inspekcja BamboBota")

    if ctx.guild.get_channel(inspected.id):
        e.set_footer(text="Kanał jest na tym serwerze", icon_url=icon_url)
    else:
        e.set_footer(text="Kanał nie znajduje się na tym serwerze", icon_url=icon_url)

    e.add_field(name="Nazwa", value=inspected.name, inline=True)
    e.add_field(name="Rodzaj", value=inspected.type.name, inline=True)
    e.add_field(name="ID", value=str(inspected.id), inline=True)

    e.add_field(name="Na Serwerze", value=inspected.guild.name + f" `[{inspected.guild.id}]`", inline=False)

    human_delta = human_timedelta(inspected.created_at, source=datetime.datetime.utcnow())
    e.add_field(name="Utworzony", value=str(inspected.created_at) + f" ({human_delta})", inline=False)

    if isinstance(inspected, discord.VoiceChannel):
        e.add_field(name="Limit użytkowników", value=str(inspected.user_limit), inline=True)
        e.add_field(name="Bitrate", value=str(inspected.bitrate / 1000) + " kbps", inline=True)
    elif isinstance(inspected, discord.TextChannel):
        e.add_field(name="Przypięcia", value=str(len(await inspected.pins())), inline=True)
        e.add_field(name="Opóźnienie SlowMode", value=str(inspected.slowmode_delay), inline=True)
        topic = inspected.topic
        if not topic:
            topic = "Brak"
        e.add_field(name="Temat", value=topic, inline=False)

    e.add_field(name="Kategoria", value=inspected.category.name, inline=False)
    await ctx.send(embed=e)


async def inspect_guild(ctx: 'CustomContext', inspected: discord.Guild):
    e = discord.Embed(title="Inspekcja BamboBota")

    e.add_field(name="Nazwa", value=inspected.name, inline=True)
    e.add_field(name="Ilość członków", value=str(inspected.member_count), inline=True)
    e.add_field(name="ID", value=str(inspected.id), inline=True)

    e.add_field(name="Ilość kanałów", value=f"{len(inspected.channels)} łącznie, {len(inspected.text_channels)} tekstowych", inline=True)
    e.add_field(name="Ilość kategorii", value=str(len(inspected.categories)), inline=True)
    e.add_field(name="Ilość emoji", value=f"{len(inspected.emojis)}/{inspected.emoji_limit}", inline=True)

    e.add_field(name="Region", value=inspected.region.name, inline=True)
    owner = inspected.owner
    e.add_field(name="Właściciel", value=f"{owner.name}#{owner.discriminator} `[{owner.id}]`", inline=True)
    bans = await inspected.bans()
    e.add_field(name="Ilość banów", value=f"{len(bans)} aktualnie", inline=True)

    human_delta = human_timedelta(inspected.created_at, source=datetime.datetime.utcnow())
    e.add_field(name="Utworzony", value=str(inspected.created_at) + f" ({human_delta})", inline=False)

    e.add_field(name="URL ikony", value=str(inspected.icon_url), inline=False)

    icon_url = ctx.guild.me.avatar_url
    if ctx.guild.id == inspected.id:
        e.set_footer(text="Sprawdzasz serwer, na którym teraz jesteś", icon_url=icon_url)
    else:
        e.set_footer(text="Sprawdzasz inny serwer", icon_url=icon_url)

    e.set_image(url=str(inspected.icon_url))

    await ctx.send(embed=e)


async def inspect_emoji(ctx: 'CustomContext', inspected: discord.Emoji):
    e = discord.Embed(title="Inspekcja BamboBota")

    e.add_field(name="Nazwa", value=inspected.name, inline=True)
    e.add_field(name="Reprezentacja", value=str(inspected), inline=True)
    e.add_field(name="ID", value=str(inspected.id), inline=True)

    e.add_field(name="Animowane", value=str(inspected.animated), inline=True)
    e.add_field(name="Dostępne", value=str(inspected.available), inline=True)
    e.add_field(name="Zarządane", value=str(inspected.managed), inline=True)

    e.add_field(name="Serwer", value=f"{inspected.guild.name} `[{inspected.guild_id}]`", inline=False)

    human_delta = human_timedelta(inspected.created_at, source=datetime.datetime.utcnow())
    e.add_field(name="Utworzone", value=str(inspected.created_at) + f" ({human_delta})", inline=False)

    e.add_field(name="URL", value=str(inspected.url), inline=False)

    icon_url = ctx.guild.me.avatar_url
    if ctx.guild.id == inspected.guild_id:
        e.set_footer(text="Emoji jest na tym Serwerze", icon_url=icon_url)
    else:
        e.set_footer(text="Emoji jest na innym Serwerze", icon_url=icon_url)

    e.set_image(url=str(inspected.url))

    await ctx.send(embed=e)


async def inspect_message(ctx: 'CustomContext', inspected: discord.Message):
    e = discord.Embed(title="Inspekcja BamboBota")

    e.add_field(name="Autor", value=f"{inspected.author.name}#{inspected.author.discriminator} `[{inspected.author.id}]`", inline=True)
    e.add_field(name="Kanał", value=f"{inspected.channel.name} `[{inspected.channel.id}]`", inline=True)
    e.add_field(name="Serwer", value=f"{inspected.guild.name} `[{inspected.guild.id}]`", inline=True)

    e.add_field(name="Zawartość", value=str(inspected.content)[:1000], inline=False)

    human_delta = human_timedelta(inspected.created_at, source=datetime.datetime.utcnow())
    e.add_field(name="Utworzono", value=str(inspected.created_at) + f" ({human_delta})", inline=False)
    e.add_field(name="Załączniki", value=str([a.url for a in inspected.attachments]), inline=False)

    icon_url = ctx.guild.me.avatar_url
    if ctx.channel.id == inspected.channel.id:
        e.set_footer(text="Wiadomość znajduje się na tym Kanale", icon_url=icon_url)
    elif ctx.guild.id == inspected.guild.id:
        e.set_footer(text="Wiadomość znajduje się na tym Serwerze", icon_url=icon_url)
    else:
        e.set_footer(text="Wiadomość znajduje się na innym Serwerze", icon_url=icon_url)

    e.set_image(url=str(inspected.author.avatar_url))

    await ctx.send(embed=e)


class Inspector(commands.Cog):

    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self._last_result = None
        self.sessions = set()
        self.api = bot.api

    async def universal_converter(self, ctx: 'CustomContext', inspected: int) -> typing.Union[discord.Guild, discord.Emoji, discord.Message, discord.User,
                                                                                              discord.TextChannel, discord.VoiceChannel]:
        # Maybe it's a guild ID, or an user ID we don't have in cache, try everything, but since fetch_user is ratelimited, try that one after everything
        maybe_guild = self.bot.get_guild(inspected)
        if maybe_guild:
            return maybe_guild

        maybe_channel = self.bot.get_channel(inspected)
        if maybe_channel and not any([isinstance(maybe_channel, t) for t in [discord.StoreChannel, discord.DMChannel, discord.GroupChannel, discord.CategoryChannel]]):
            return maybe_channel

        maybe_emoji = self.bot.get_emoji(inspected)
        if maybe_emoji:
            return maybe_emoji

        maybe_message = discord.utils.get(self.bot.cached_messages, id=inspected)
        if maybe_message:
            return maybe_message

        # These are "expensive" API calls to make, but we exhausted the cache
        # Any user on Discord
        try:
            return await self.bot.fetch_user(inspected)
        except discord.NotFound:
            pass

        # Check for an older message in that channel
        try:
            return await ctx.channel.fetch_message(inspected)
        except discord.NotFound:
            pass

        raise discord.ext.commands.errors.BadArgument("Oops, podane ID nie pasuje do niczego, co mogę sprawdzić. Upewnij się, że podajesz poprawne ID.")

    @commands.command(aliases=["inspector"])
    @commands.guild_only()
    @checks.have_required_level(2)
    async def inspect(self, ctx: 'CustomContext', inspected: typing.Union[discord.Member, discord.User, discord.TextChannel, discord.VoiceChannel, int]):
        """Sprawdź dany obiekt i zwróć jego właściwości"""
        with ctx.typing():
            if isinstance(inspected, int):
                inspected = await self.universal_converter(ctx, inspected)

            if isinstance(inspected, discord.Member) or isinstance(inspected, discord.User):
                return await inspect_member(ctx, inspected)

            elif isinstance(inspected, discord.TextChannel) or isinstance(inspected, discord.VoiceChannel):
                return await inspect_channel(ctx, inspected)

            elif isinstance(inspected, discord.Guild):
                return await inspect_guild(ctx, inspected)

            elif isinstance(inspected, discord.Emoji):
                return await inspect_emoji(ctx, inspected)

            elif isinstance(inspected, discord.Message):
                return await inspect_message(ctx, inspected)

            await ctx.send(f"Typ: {type(inspected)}, Str:{str(inspected)}")


def setup(bot: 'BamboBot'):
    bot.add_cog(Inspector(bot))
