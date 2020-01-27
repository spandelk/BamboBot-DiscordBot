# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
import typing
import json
from cogs.helpers import checks
from cogs.helpers.level import get_level

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.context import CustomContext

# from bs4 import BeautifulSoup
# import requests
import aiohttp
import re

with open("credentials.json", "r") as f:
    credentials = json.load(f)
print(credentials)
GOOGLE_API_TOKEN = credentials["google_api_key"]

class Zjednoczeni(commands.Cog):
    def __init__(self, bot: 'BamboBot'):
        self.bot = bot
        self.api = bot.api
        self.live_posted_id = None


    async def has_role(self, ctx: 'CustomContext'):
        async with ctx.typing():
            try:
                role_id = int(await self.bot.settings.get_special(ctx.guild, 'youtube_mod_role_id'))
            except ValueError:
                value = await self.bot.settings.get_special(ctx.guild, 'youtube_mod_role_id')
                await ctx.send_to(f':x: Rola Moderatora YT jest ustawiona niepoprawnie. `{value}` nie wygląda mi na liczbę :thinking:', delete_after=60)
                return False
            else:
                role = discord.utils.get(ctx.guild.roles, id=role_id)
                if role is None:
                    await ctx.send_to(f':x: Nie znaleziono roli o ID `{role_id}`', delete_after=60)
                    return False
                else:
                    all_roles = ctx.author.roles
                    level = await get_level(ctx, ctx.message.author)
                    if role in all_roles:
                        return True
                    elif level >= 2:
                        return True
                    else:
                        await ctx.send_to(':x: Nie posiadasz uprawnień. (Może rola jest źle skonfigurowana? :thinking:)', delete_after=60)
                        return False

    async def get_channel(self, ctx: 'CustomContext'):
        async with ctx.typing():
            try:
                channel_id = int(await self.bot.settings.get_special(ctx.guild, 'livestream_channel_id'))
            except ValueError:
                value = await self.bot.settings.get_special(ctx.guild, 'livestream_channel_id')
                await ctx.send_to(f':x: Kanał livestream\'ów jest źle ustawiony. `{value}` nie wygląda mi na liczbę :thinking:', delete_after=60)
                return False
            else:
                channel = discord.utils.get(ctx.guild.text_channels, id=channel_id)
                if channel is None:
                    await ctx.send_to(f':x: Kanał livestream\'ów jest źle ustawiony. Nie znalazłem kanału tekstowego o ID `{channel_id}`', delete_after=60)
                    return False
                else:
                    return channel

    async def check_link(self, ctx: 'CustomContext'):
        async with ctx.typing():
            pattern = '(?i)(?:https|http)\:\/\/(?:www\.)?youtube\.com\/(?:channel\/)+?([a-zA-Z0-9\-]{1,})'
            channel_link = await self.bot.settings.get_special(ctx.guild, 'youtube_channel_link')
            if len(channel_link) < 10:
                await ctx.send_to(f':x: Zapisany link `{channel_link}` nie wygląda na prawidłowy link. Upewnij się, że podano prawidłowy link na webinterfejsie. \n'
                                  f'Prawidłowy link powiniem wyglądać tak: `https://youtube.com/channel/<id_kanału>`', delete_after=60)
                return False
            if len(channel_link) < 26 or len(channel_link) > 60:
                await ctx.send_to(f':x: Zapisany link `{channel_link}` wydaje się być zbyt krótki lub zbyt długi. Upewnij się, że podano prawidłowy link na webinterfejsie. \n'
                                  f'Prawidłowy link powiniem wyglądać tak: `https://youtube.com/channel/<id_kanału>`', delete_after=60)
                return False
            else:
                match = re.search(pattern, channel_link)
                if not match:
                    await ctx.send_to(f':x: Zapisany link `{channel_link}` nie wygląda na prawidłowy link do kanału. Upewnij się, że podano prawidłowy link na webinterfejsie. \n'
                                      f'Prawidłowy link powiniem wyglądać tak: `https://youtube.com/channel/<id_kanału>`', delete_after=60)
                    return False
                else:
                    if not channel_link.endswith('/'):
                        channel_link = channel_link[-24:]
                    else:
                        channel_link = channel_link[-25:-1]
                return channel_link

    @commands.command()
    @commands.guild_only()
    @checks.bot_have_permissions()
    # @checks.have_required_level(2)
    async def liveon(self, ctx: 'CustomContext'):
        async with ctx.typing():
            msg = await ctx.send('Działam...', delete_after=10)
            if await self.has_role(ctx):
                channel = await self.get_channel(ctx)
                if not channel:
                    return False
                else:
                    youtube_channel = await self.check_link(ctx)
                    if not youtube_channel:
                        return False
                    else:
                        API_URL = f'https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={youtube_channel}&type=video&eventType=live&key={GOOGLE_API_TOKEN}'
                        headers = {'Accept-Language': 'en-US', 'Cache-Control': 'no-cache'}
                        async with aiohttp.ClientSession() as cs:
                            async with cs.get(API_URL, headers=headers) as r:
                                # res = await r.text()
                                # soup = BeautifulSoup(res, 'html.parser')
                                # html = soup.body.find('div', attrs={'class':'yt-lockup clearfix yt-lockup-video yt-lockup-grid vve-check'})
                                # live = soup.body.find('span', attrs={'class':'yt-badge yt-badge-live'})
                                res = await r.json()
                                # print(f'API_URL -> {API_URL}')
                                # print(res)
                                if 'error' in res:
                                    await ctx.send_to(f':x: Wystąpił błąd! Zgłoś go na Serwerze Wsparcia: \n```json{json.dumps(res, indent=2)}```', delete_after=120)
                                    return False
                                if len(res['items']) == 0:
                                    await ctx.send_to(':x: Nie wykryto trwającego live\'a')
                                    return False
                                # if not live:
                                #     await ctx.send_to(':x: Nie wykryto trwającego live\'a')
                                #     return False
                                else:
                                    # live_id = html['data-context-item-id']
                                    live_id = res['items'][0]['id']['videoId']
                                    live_link = f'https://youtube.com/watch?v={live_id}'
                                    if live_id == self.live_posted_id:
                                        await ctx.send_to(':x: Link do liv\'a został już zapostowany')
                                        return False
                                    else:
                                        self.live_posted_id = live_id
                                        message = (f'🔴 @everyone\n'
                                                   f'🔴 **Live Trwa!**\n'
                                                   f'🔴 {live_link}')
                                        avatar = await ctx.author.avatar_url.read()
                                        try:
                                            webhook = await channel.create_webhook(name=ctx.author.display_name, avatar=avatar, reason=f'{ctx.author.name} postuje link do live\'a')
                                        except discord.Forbidden:
                                            await channel.send(message)
                                        else:
                                            await webhook.send(message)
                                            await webhook.delete()
                                        await ctx.send_to(':ok_hand: Link został zapostowany!')
            else:
                return False


def setup(bot: 'BamboBot'):
    bot.add_cog(Zjednoczeni(bot))

'''
Changes by me:
(1) Added this special Cog mainly to handle posting a link to a YouTube Livestream
=====
Moje zmiany:
(1) Dodano ten specjalny 'trybik' głównie do wysyłania linku do live'a na YouTube'ie
'''
