# -*- coding: utf-8 -*-
import asyncio
import datetime
import typing

import discord
from discord import Color

if typing.TYPE_CHECKING:
    from cogs.helpers.BamboBot import BamboBot

from cogs.helpers.helpful_classes import LikeUser, FakeMember


colours = {'unban': Color.green(),
           'unmute': Color.dark_green(),
           'note': Color.light_grey(),
           'warn': Color.orange(),
           'mute': Color.dark_purple(),
           'kick': Color.dark_orange(),
           'softban': Color.red(),
           'ban': Color.dark_red(),
           'sponsor': Color.green(),
           'rm_sponsor': Color.dark_gold(),
           'donator': Color.blue(),
           'rm_donator': Color.dark_gold(),
           'kodzik': Color.dark_purple(),
           'rm_kodzik': Color.dark_gold()
           }

verbose_names = {
    'mute': 'Mute',
    'unmute': 'UnMute',
    'ban': 'Ban',
    'unban': 'UnBan',
    'warn': 'Ostrzeżenie',
    'kick': 'Wyrzucenie z serwera',
    'softban': 'SoftBan',
    'note': 'Notatka',
    'sponsor': 'Sponsor',
    'rm_sponsor': 'Wygasły Sponsor',
    'donator': 'Donator',
    'rm_donator': 'Wygasły Donator',
    'kodzik': 'Wspierający w Sklepie',
    'rm_kodzik': 'Wygasły Wspierający w Sklepie'
}

async def thresholds_enforcer(bot, victim: discord.Member, action_type: str):
    if not await bot.settings.get(victim.guild, 'thresholds_enable'):
        return False

    reason = "Przekroczono dozwolony próg kar"
    mod_user = LikeUser(did=2, name="ThresholdsEnforcer", guild=victim.guild)

    counters = await bot.api.get_counters(victim.guild, victim)

    if action_type == 'note' or action_type == 'unban':
        return False

    elif action_type == 'warn':
        thresholds_warns_to_kick = await bot.settings.get(victim.guild, 'thresholds_warns_to_kick')
        if thresholds_warns_to_kick and counters['warn'] % thresholds_warns_to_kick == 0:
            logs = (f"Przekroczono próg ostrzeżeń!\n Dozwolona ilość ostrzeżeń przed wyrzuceniem wynosi {thresholds_warns_to_kick - 1} \n"
                    f"Suma {counters['warn']} ostrzeżeń, chcemy aby {counters['warn']}%{thresholds_warns_to_kick} = {counters['warn'] % thresholds_warns_to_kick} = 0 \n"
                    f"Wyrzucam członka z serwera, ponieważ ostrzeżono go {thresholds_warns_to_kick} razy!")
            await full_process(bot, kick, victim, mod_user, reason=reason, automod_logs=logs)

    elif action_type == 'mute':
        thresholds_mutes_to_kick = await bot.settings.get(victim.guild, 'thresholds_mutes_to_kick')
        if thresholds_mutes_to_kick and counters['mute'] % thresholds_mutes_to_kick == 0:
            logs = (f"Przekroczono próg wyciszeń!\n Dozwolona ilość wyciszeń przed wyrzuceniem wynosi {thresholds_mutes_to_kick - 1} \n"
                    f"Suma {counters['mute']} wyciszeń, chcemy aby {counters['mute']}%{thresholds_mutes_to_kick} = {counters['mute'] % thresholds_mutes_to_kick} = 0 \n"
                    f"Wyrzucam członka z serwera, ponieważ wyciszono go {thresholds_mutes_to_kick} razy!")
            await full_process(bot, kick, victim, mod_user, reason=reason, automod_logs=logs)

    elif action_type == 'kick':
        thresholds_kicks_to_bans = await bot.settings.get(victim.guild, 'thresholds_kicks_to_bans')
        if thresholds_kicks_to_bans and counters['kick'] % thresholds_kicks_to_bans == 0:
            logs = (f"Przekroczono próg wyrzuceń!\n Dozwolona ilość wyrzuceń przed banem wynosi {thresholds_mutes_to_kick - 1} \n"
                    f"Suma {counters['kick']} wyrzuceń, chcemy aby {counters['kick']}%{thresholds_kicks_to_bans} = {counters['kick'] % thresholds_kicks_to_bans} = 0 \n"
                    f"Banuję członka z serwera, ponieważ wyrzucono go {thresholds_kicks_to_bans} razy!")
            await full_process(bot, ban, victim, mod_user, reason=reason, automod_logs=logs)

    elif action_type == 'softban':
        thresholds_softbans_to_bans = await bot.settings.get(victim.guild, 'thresholds_softbans_to_bans')
        if thresholds_softbans_to_bans and counters['softban'] % thresholds_softbans_to_bans == 0:
            logs = (f"Przekroczono próg softbanów!\n Dozwolona ilość softbanów przed banem wynosi {thresholds_softbans_to_bans - 1} \n"
                    f"Suma {counters['softban']} softbanów, chcemy aby {counters['kick']}%{thresholds_softbans_to_bans} = {counters['softban'] % thresholds_softbans_to_bans} = 0 \n"
                    f"Banuję członka z serwera, ponieważ zsoftbanowano go {thresholds_softbans_to_bans} razy!")
            await full_process(bot, ban, victim, mod_user, reason=reason, automod_logs=logs)
    else:
        return False

    return True


async def ban(victim: discord.Member, reason: str = None):
    # verbose_name = 'Ban'
    await victim.guild.ban(victim, reason=reason)


async def softban(victim: discord.Member, reason: str = None):
    # verbose_name = 'SoftBan'
    await victim.guild.ban(victim, reason=reason)
    await victim.guild.unban(victim, reason=reason)


async def kick(victim: discord.Member, reason: str = None):
    # verbose_name = "Wyrzucenie z serwera"
    await victim.guild.kick(victim, reason=reason)


async def mute(bot, victim: discord.Member, reason: str = None):
    # setattr(self, 'verbose_name', 'Mute')
    # self.verbose_name = "Mute"
    # muted_role = discord.utils.get(victim.guild.roles, name="GetBeaned_muted")
    ROLE_NAME = int(await bot.settings.get(victim.guild, 'muted_role_id'))
    muted_role = discord.utils.get(victim.guild.roles, id=ROLE_NAME)
    await victim.add_roles(muted_role, reason=reason)

async def unmute(bot, victim: discord.Member, reason: str = None):
    # verbose_name = "UnMute"
    # muted_role = discord.utils.get(victim.guild.roles, name="GetBeaned_muted")
    ROLE_NAME = int(await bot.settings.get(victim.guild, 'muted_role_id'))
    muted_role = discord.utils.get(victim.guild.roles, id=ROLE_NAME)
    await victim.remove_roles(muted_role, reason=reason)


async def warn(victim: discord.Member, reason: str = None):
    # verbose_name = 'Ostrzeżenie'
    pass


async def note(victim: discord.Member, reason: str = None):
    # verbose_name = 'Notatka'
    pass


async def unban(victim: discord.Member, reason: str = None):
    # verbose_name = 'UnBan'
    await victim.guild.unban(victim, reason=reason)


async def sponsor(bot, victim: discord.Member, tier: int, reason: str = None):
    # verbose_name = 'Sponsor'
    ROLE0_id = int(await bot.settings.get_special(victim.guild, 'zjednoczeni_sponsor_00'))
    if tier == 1:
        ROLE1_id = int(await bot.settings.get_special(victim.guild, 'zjednoczeni_sponsor_01'))
    elif tier == 2:
        ROLE1_id = int(await bot.settings.get_special(victim.guild, 'zjednoczeni_sponsor_02'))
    elif tier == 3:
        ROLE1_id = int(await bot.settings.get_special(victim.guild, 'zjednoczeni_sponsor_03'))
    elif tier == 4:
        ROLE1_id = int(await bot.settings.get_special(victim.guild, 'zjednoczeni_sponsor_04'))
    
    ROLE0 = discord.utils.get(victim.guild.roles, id=ROLE0_id)
    ROLE1 = discord.utils.get(victim.guild.roles, id=ROLE1_id)
    roles = victim.roles + [ROLE0, ROLE1]
    await victim.edit(roles=roles, reason=reason)


async def rm_sponsor(bot, victim: discord.Member, reason: str = None):
    all_roles = victim.roles
    roles_to_get = []
    roles_to_remove = []
    x = range(5)
    for i in x:
        roles_to_get.append(int(await bot.settings.get_special(victim.guild, f'zjednoczeni_sponsor_0{i}')))
    for role in roles_to_get:
        roles_to_remove.append(discord.utils.get(victim.guild.roles, id=role))
    for role in roles_to_remove:
        if role in all_roles:
            all_roles.remove(role)
    await victim.edit(roles=all_roles, reason=reason)


async def donator(bot, victim: discord.Member, tier: int, reason: str = None):
    all_roles = victim.roles
    roles_to_get = []
    roles_to_add = []
    for i in range(tier):
        roles_to_get.append(int(await bot.settings.get_special(victim.guild, f'zjednoczeni_donator_0{i}')))
    for role in roles_to_get:
        roles_to_add.append(discord.utils.get(victim.guild.roles, id=role))
    all_roles += roles_to_add
    await victim.edit(roles=all_roles, reason=reason)


async def rm_donator(bot, victim: discord.Member, reason: str = None):
    all_roles = victim.roles
    roles_to_get = []
    roles_to_remove = []
    for i in range(3):
        roles_to_get.append(int(await bot.settings.get_special(victim.guild, f'zjednoczeni_donator_0{i}')))
    for role in roles_to_get:
        roles_to_remove.append(discord.utils.get(victim.guild.roles, id=role))
    for role in roles_to_remove:
        if role in all_roles:
            all_roles.remove(role)
    await victim.edit(roles=all_roles, reason=reason)


async def kodzik(bot, victim: discord.Member, reason: str = None):
    all_roles = victim.roles
    role_to_get = int(await bot.settings.get_special(victim.guild, f'zjednoczeni_kodzik'))
    role_to_add = discord.utils.get(victim.guild.roles, id=role_to_get)
    all_roles.append(role_to_add)
    await victim.edit(roles=all_roles, reason=reason)


async def rm_kodzik(bot, victim: discord.Member, reason: str = None):
    all_roles = victim.roles
    role_to_get = int(await bot.settings.get_special(victim.guild, f'zjednoczeni_kodzik'))
    role_to_remove = discord.utils.get(victim.guild.roles, id=role_to_get)
    all_roles.remove(role_to_remove)
    await victim.edit(roles=all_roles, reason=reason)


async def get_action_log_embed(bot: 'BamboBot', case_number: int, webinterface_url: str, action_type: str, victim: discord.Member, moderator: discord.Member, reason: str = None,
                               attachement_url: str = None,
                               automod_logs: str = None):
    embed = discord.Embed()
    if attachement_url:
        embed.set_image(url=attachement_url)

    action_name = verbose_names[action_type]
    embed.colour = colours[action_type]
    embed.title = f"{action_name} | Sprawa #{case_number}"
    embed.description = reason[:1000]

    embed.add_field(name="Odpowiedzialny Moderator", value=f"`{moderator.name}#{moderator.discriminator}` ({moderator.id})", inline=True)
    embed.add_field(name="Cel", value=f"`{victim.name}#{victim.discriminator}` ({victim.id})", inline=True)
    embed.add_field(name="Więcej informacji na webinterfejsie", value=webinterface_url, inline=False)

    if automod_logs:
        embed.add_field(name="Logi AutoModa", value=automod_logs[:1000], inline=False)

    embed.set_author(name=bot.user.name)

    embed.timestamp = datetime.datetime.now()

    return embed


async def full_process(bot, action_coroutine: typing.Callable[[discord.Member, str], typing.Awaitable], victim: typing.Union[discord.Member, FakeMember],
                       moderator: typing.Union[discord.Member, LikeUser], reason: str = None, tier: int = None, attachement_url: str = None, automod_logs: str = None):
    """
    A little bit of explanation about what's going on there.

    This is the entry point for action-ing on a `victim`. What this function does is first to POST the action to the
    WebInterface API, then give the user the URL the link to the specific action got, and ignore if that part fails.

    We then actually act (ban/kick/what_ever) if needed, and finally check for thresholds enforcement (and this may do
    something else to the user, like kicking/banning him, calling this back).

    Lastly, we try to see if we should log messages to a #mod-log channel, and log if wanted to.
    """
    # self.bot = bot
    # print(f'attachement_url: {attachement_url}')
    action_type = action_coroutine.__name__
    action_name = verbose_names[action_type]

    res = await bot.api.add_action(guild=victim.guild,
                                   user=victim,
                                   action_type=action_type,
                                   reason=reason,
                                   responsible_moderator=moderator,
                                   attachment=attachement_url,
                                   automod_logs=automod_logs,
                                   )

    # url = "https://getbeaned.me" + res['result_url']
    url = "https://bambobot.herokuapp.com" + res['result_url']
    case_number = res['case_number']
    quoted_reason = ''.join(('' + reason).splitlines(True))
    # try:
    #     asyncio.ensure_future(victim.send(f"Wykonano akcję: **{action_name}**, z następującym powodem:\n"
    #                                       f"{quoted_reason}\n\n"
    #                                       f"Więcej informacji na {url}, być może będziesz musiał się zalogować swoim kontem Discord. \n"
    #                                       f"Możesz się odwołać u wybranego moderatora"))
    # except AttributeError:
    #     # LikeUser dosen't have a send attr
    #     pass

    # print(action_coroutine.__name__)
    # print(type(bot))
    # print(bot)
    if action_coroutine.__name__ == 'mute':
        e = discord.Embed(title='Zostałeś wyciszony!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n'
                                      f'Możesz się odwołać u wybranego Moderatora')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data wyciszenia')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(bot, victim, reason[:510])        
    elif action_coroutine.__name__ == 'unmute':
        e = discord.Embed(title='Twoje wyciszenie dobiegło końca!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data zakończenia wyciszenia')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass
 
        await action_coroutine(bot, victim, reason[:510])
    elif action_coroutine.__name__ == 'sponsor':
        e = discord.Embed(title='Witamy w gronie Sponsorów!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(bot, victim, tier, reason[:510])
    elif action_coroutine.__name__ == 'donator':
        e = discord.Embed(title='Witamy w gronie Donatorów!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(bot, victim, tier, reason[:510])
    elif action_coroutine.__name__ == 'rm_sponsor':
        e = discord.Embed(title='Twója ranga Sponsora dobiegła końca!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(bot, victim, reason[:510])
    elif action_coroutine.__name__ == 'rm_donator':
        e = discord.Embed(title='Twója ranga Donatora dobiegła końca!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass
        
        # print(f'action_coroutine: {action_coroutine.__name__}')
        await action_coroutine(bot, victim, reason[:510])
    elif action_coroutine.__name__ == 'kodzik':
        e = discord.Embed(title='Witamy w gronie Wspierających w Sklepie!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(bot, victim, reason[:510])
    elif action_coroutine.__name__ == 'rm_kodzik':
        e = discord.Embed(title='Twója ranga Wspierającego w Sklepie dobiegła końca!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(bot, victim, reason[:510])
    elif action_coroutine.__name__ == 'kick':
        e = discord.Embed(title='Zostałeś wyrzucony z serwera!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n'
                                      f'Możesz się odwołać u wybranego Moderatora')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data wyrzucenia')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(victim, reason[:510])
    elif action_coroutine.__name__ == 'softban':
        e = discord.Embed(title='Zostałeś zsoftbanowany na Serwerze!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n'
                                      f'Możesz się odwołać u wybranego Moderatora')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data softbanu')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(victim, reason[:510])
    elif action_coroutine.__name__ == 'ban':
        e = discord.Embed(title='Zostałeś zbanowany na Serwerze!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n'
                                      f'Możesz się odwołać u wybranego Moderatora')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data banicji')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(victim, reason[:510])
    elif action_coroutine.__name__ == 'warn':
        e = discord.Embed(title='Zostałeś ostrzeżony!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n'
                                      f'Możesz się odwołać u wybranego Moderatora')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data ostrzeżenia')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(victim, reason[:510])
    elif action_coroutine.__name__ == 'note':
        e = discord.Embed(title='Do twojego profilu została dodana notatka',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data notatki')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(victim, reason[:510])
    elif action_coroutine.__name__ == 'unban':
        e = discord.Embed(title='Zostałeś odbanowany!',
                          colour=colours[action_type],
                          url=url,
                          timestamp=datetime.datetime.utcnow(),
                          description=f'**Serwer:** \t `{victim.guild.name}` \n'
                                      f'**Odpowiedzialny Moderator:** \t `{moderator.name}#{moderator.discriminator}` \n'
                                      f'**Powód:** \t {quoted_reason} \n\n'
                                      f'**Więcej informacji:** \t {url} \n')
        e.set_thumbnail(url=str(victim.guild.icon_url))
        e.set_footer(text='Czas i data unbana')
        try:
            await victim.send(content='', embed=e)
        except AttributeError:
            pass
        except discord.HTTPException:
            pass

        await action_coroutine(victim, reason[:510])

    th = await thresholds_enforcer(bot, victim, action_type)

    if await bot.settings.get(victim.guild, 'logs_enable'):
        # Log this to #mod-log or whatever
        # Beware to see if the channel id is actually in the same server (to compare, we will see if the current server
        # owner is the same as the one in the target channel). If yes, even if it's not the same server, we will allow
        # logging there

        channel_id = int(await bot.settings.get(victim.guild, 'logs_moderation_channel_id'))

        if channel_id != 0:
            channel = bot.get_channel(channel_id)

            if not channel:
                bot.logger.warning(f"There is something fishy going on with guild={victim.guild.id}! "
                                   f"Their logs_channel_id={channel_id} can't be found!")
            elif not channel.guild.owner == victim.guild.owner:
                bot.logger.warning(f"There is something fishy going on with guild={victim.guild.id}! "
                                   f"Their logs_channel_id={channel_id} don't belong to them!")
            else:
                if await bot.settings.get(victim.guild, 'logs_as_embed'):
                    embed = await get_action_log_embed(bot,
                                                       case_number,
                                                       url,
                                                       action_type, #action_type
                                                       victim,
                                                       moderator,
                                                       reason=reason,
                                                       attachement_url=attachement_url,
                                                       automod_logs=None)

                    # On "ensure future" pour envoyer le message en arriere plan
                    # Comme ca, logger ne limite pas les thresholds aux ratelimits de discord
                    async def send(embed):
                        try:
                            await channel.send(embed=embed)
                        except discord.errors.Forbidden:
                            pass

                    asyncio.ensure_future(send(embed))
                else:
                    textual_log = f"**{action_name}** #{case_number} " \
                        f"na {victim.name}#{victim.discriminator} (`{victim.id}`)\n" \
                        f"**Powód**: {reason}\n" \
                        f"**Moderator**: `{moderator.name}#{moderator.discriminator}` (`{moderator.id}`)\n" \
                        f"Więcej informacji na {url} "
                    async def send(log):
                        try:
                            await channel.send(log)
                        except discord.errors.Forbidden:
                            pass

                    asyncio.ensure_future(send(textual_log))

    return {"user_informed": None,
            "url": url,
            "thresholds_enforced": th,
            "case_number": case_number}
