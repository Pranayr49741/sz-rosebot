import asyncio
import importlib
import re
from contextlib import closing, suppress
from uvloop import install
from pyrogram import filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from Rose.menu import *
from Rose import *
from Rose.plugins import ALL_MODULES
from Rose.utils import paginate_modules
from lang import get_command
from Rose.utils.lang import *
from Rose.utils.commands import *
from Rose.mongo.rulesdb import *
from Rose.utils.start import *
from Rose.mongo.usersdb import *
from Rose.mongo.restart import *
from Rose.mongo.chatsdb import *
from Rose.plugins.fsub import ForceSub
import random
import json
import re

from pyrogram import Client, filters

import functions as func
import raid_dynamax as raid

app = Client(
    session_name='Rotomgram'
)

texts = json.load(open('src/texts.json', 'r'))
data = json.load(open('src/pkmn.json', 'r'))
stats = json.load(open('src/stats.json', 'r'))

usage_dict = {'vgc': None}
raid_dict = {}


# ===== Stats =====
@app.on_message(Filters.private & Filters.create(lambda _, message: str(message.chat.id) not in stats['users']))
@app.on_message(Filters.group & Filters.create(lambda _, message: str(message.chat.id) not in stats['groups']))
def get_bot_data(app, message):
    cid = str(message.chat.id)
    if message.chat.type == 'private':
        stats['users'][cid] = {}
        name = message.chat.first_name
        try:
            name = message.chat.first_name + ' ' + message.chat.last_name
        except TypeError:
            name = message.chat.first_name
        stats['users'][cid]['name'] = name
        try:
            stats['users'][cid]['username'] = message.chat.username
        except AttributeError:
            pass

    elif message.chat.type in ['group', 'supergroup']:
        stats['groups'][cid] = {}
        stats['groups'][cid]['title'] = message.chat.title
        try:
            stats['groups'][cid]['username'] = message.chat.username
        except AttributeError:
            pass
        stats['groups'][cid]['members'] = app.get_chat(cid).members_count

    json.dump(stats, open('src/stats.json', 'w'), indent=4)
    print(stats)
    print('\n\n')
    message.continue_propagation()


@app.on_message(Filters.command(['stats', 'stats@RotomgramBot']))
def get_stats(app, message):
    if message.from_user.id == 312012637:
        members = 0
        for group in stats['groups']:
            members += stats['groups'][group]['members']
        text = texts['stats'].format(
            len(stats['users']),
            len(stats['groups']),
            members
        )
        app.send_message(
            chat_id=message.chat.id,
            text=text
        )


# ===== Home =====
@app.on_message(Filters.command(['start', 'start@RotomgramBot']))
def start(app, message):
    app.send_message(
        chat_id=message.chat.id,
        text=texts['start_message'],
        parse_mode='HTML'
    )


# ===== Data command =====
@app.on_callback_query(Filters.create(lambda _, query: 'basic_infos' in query.data))
@app.on_message(Filters.command(['data', 'data@RotomgramBot']))
def pkmn_search(app, message):
    try:
        if message.text == '/data' or message.text == '/data@RotomgramBot':
            app.send_message(message.chat.id, texts['error1'], parse_mode='HTML')
            return None
        pkmn = func.find_name(message.text)
        result = func.check_name(pkmn, data)

        if type(result) == str:
            app.send_message(message.chat.id, result)
            return None
        elif type(result) == list:
            best_matches(app, message, result)
            return None
        else:
            pkmn = result['pkmn']
            form = result['form']
    except AttributeError:
        pkmn = re.split('/', message.data)[1]
        form = re.split('/', message.data)[2]


    if pkmn in form:
        text = func.set_message(data[pkmn][form], reduced=True)
    else:
        base_form = re.sub('_', ' ', pkmn.title())
        name = base_form + ' (' + data[pkmn][form]['name'] + ')'
        text = func.set_message(data[pkmn][form], name, reduced=True)

    markup_list = [[
        InlineKeyboardButton(
            text='➕ Expand',
            callback_data='all_infos/'+pkmn+'/'+form
        )
    ],
    [
        InlineKeyboardButton(
            text='⚔️ Moveset',
            callback_data='moveset/'+pkmn+'/'+form
        ),
        InlineKeyboardButton(
            text='🏠 Locations',
            callback_data='locations/'+pkmn+'/'+form
        )
    ]]
    for alt_form in data[pkmn]:
        if alt_form != form:
            markup_list.append([
                InlineKeyboardButton(
                    text=data[pkmn][alt_form]['name'],
                    callback_data='basic_infos/'+pkmn+'/'+alt_form
                )
            ])
    markup = InlineKeyboardMarkup(markup_list)

    func.bot_action(app, message, text, markup)


def best_matches(app, message, result):
    text = texts['results']
    emoji_list = ['1️⃣', '2️⃣', '3️⃣']
    index = 0
    for dictt in result:
        pkmn = dictt['pkmn']
        form = dictt['form']
        percentage = dictt['percentage']
        form_name = data[pkmn][form]['name']
        name = func.form_name(pkmn.title(), form_name)
        text += '\n{} <b>{}</b> (<i>{}</i>)'.format(
            emoji_list[index],
            name,
            percentage
        )
        if index == 0:
            text += ' [<b>⭐️ Top result</b>]'
        index += 1
    app.send_message(message.chat.id, text, parse_mode='HTML')


@app.on_callback_query(Filters.create(lambda _, query: 'all_infos' in query.data))
def all_infos(app, call):
    pkmn = re.split('/', call.data)[1]
    form = re.split('/', call.data)[2]
    
    if pkmn in form:
        text = func.set_message(data[pkmn][form], reduced=False)
    else:
        base_form = re.sub('_', ' ', pkmn.title())
        name = base_form + ' (' + data[pkmn][form]['name'] + ')'
        text = func.set_message(data[pkmn][form], name, reduced=False)

    markup_list = [[
        InlineKeyboardButton(
            text='➖ Reduce',
            callback_data='basic_infos/'+pkmn+'/'+form
        )
    ],
    [
        InlineKeyboardButton(
            text='⚔️ Moveset',
            callback_data='moveset/'+pkmn+'/'+form
        ),
        InlineKeyboardButton(
            text='🏠 Locations',
            callback_data='locations/'+pkmn+'/'+form
        )
    ]]
    for alt_form in data[pkmn]:
        if alt_form != form:
            markup_list.append([
                InlineKeyboardButton(
                    text=data[pkmn][alt_form]['name'],
                    callback_data='basic_infos/'+pkmn+'/'+alt_form
                )
            ])
    markup = InlineKeyboardMarkup(markup_list)

    func.bot_action(app, call, text, markup)


@app.on_callback_query(Filters.create(lambda _, query: 'moveset' in query.data))
def moveset(app, call):
    pkmn = re.split('/', call.data)[1]
    form = re.split('/', call.data)[2]
    if len(re.split('/', call.data)) == 4:
        page = int(re.split('/', call.data)[3])
    else:
        page = 1
    dictt = func.set_moveset(pkmn, form, page)

    func.bot_action(app, call, dictt['text'], dictt['markup'])


@app.on_callback_query(Filters.create(lambda _, query: 'locations' in query.data))
def locations(app, call):
    pkmn = re.split('/', call.data)[1]
    form = re.split('/', call.data)[2]

    text = func.get_locations(data, pkmn)

    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text='⚔️ Moveset',
            callback_data='moveset/'+pkmn+'/'+form
        )
    ],
    [
        InlineKeyboardButton(
            text='🔙 Back to basic infos',
            callback_data='basic_infos/'+pkmn+'/'+form
        )
    ]])

    func.bot_action(app, call, text, markup)


# ===== Usage command =====
@app.on_callback_query(Filters.create(lambda _, query: 'usage' in query.data))
@app.on_message(Filters.command(['usage', 'usage@RotomgramBot']))
def usage(app, message):
    try:
        page = int(re.split('/', message.data)[1])
        dictt = func.get_usage_vgc(int(page), usage_dict['vgc'])
    except AttributeError:
        page = 1
        text = '<i>Connecting to Pokémon Showdown database...</i>'
        message = app.send_message(message.chat.id, text, parse_mode='HTML')
        dictt = func.get_usage_vgc(int(page))
        usage_dict['vgc'] = dictt['vgc_usage']

    leaderboard = dictt['leaderboard']
    base_text = texts['usage']
    text = ''
    for i in range(15):
        pkmn = leaderboard[i]
        text += base_text.format(
            pkmn['rank'],
            pkmn['pokemon'],
            pkmn['usage'],
        )
    markup = dictt['markup']

    func.bot_action(app, message, text, markup)


# ===== FAQ command =====
@app.on_message(Filters.command(['faq', 'faq@RotomgramBot']))
def faq(app, message):
    text = texts['faq']
    app.send_message(
        chat_id=message.chat.id,
        text=text, 
        parse_mode='HTML',
        disable_web_page_preview=True
    )



# ===== About command =====
@app.on_message(Filters.command(['about', 'about@RotomgramBot']))
def about(app, message):
    text = texts['about']
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text='Github',
            url='https://github.com/alessiocelentano/rotomgram'
        )
    ]])

    app.send_message(
        chat_id=message.chat.id,
        text=text, 
        reply_markup=markup,
        disable_web_page_preview=True
    )


# ===== Raid commands =====
@app.on_message(Filters.command(['addcode', 'addcode@RotomgramBot']))
def call_add_fc(app, message):
    raid.add_fc(app, message, texts)

@app.on_message(Filters.command(['mycode', 'mycode@RotomgramBot']))
def call_show_my_fc(app, message):
    raid.show_my_fc(app, message, texts)

@app.on_message(Filters.command(['newraid', 'newraid@RotomgramBot']))
def call_new_raid(app, message):
    raid.new_raid(app, message, texts)

@app.on_callback_query(Filters.create(lambda _, query: 'stars' in query.data))
def call_stars(app, message):
    raid.stars(app, message, texts)

@app.on_callback_query(Filters.create(lambda _, query: 'join' in query.data))
def call_join(app, message):
    raid.join(app, message, texts)

@app.on_callback_query(Filters.create(lambda _, query: 'done' in query.data))
def call_done(app, message):
    raid.done(app, message, texts)

@app.on_callback_query(Filters.create(lambda _, query: 'yes' in query.data))
def call_confirm(app, message):
    raid.confirm(app, message, texts)

@app.on_callback_query(Filters.create(lambda _, query: 'no' in query.data))
def call_back(app, message):
    raid.back(app, message, texts)

@app.on_callback_query(Filters.create(lambda _, query: 'pin' in query.data))
def call_pin(app, message):
    raid.pin(app, message, texts)


# ===== Presentation =====
@app.on_message(Filters.create(lambda _, message: message.new_chat_members))
def bot_added(app, message):
    for new_member in message.new_chat_members:
        if new_member.id == 932107343:
            text = texts['added']
            app.send_message(
                chat_id=message.chat.id,
                text=text
            )

loop = asyncio.get_event_loop()
flood = {}
START_COMMAND = get_command("START_COMMAND")
HELP_COMMAND = get_command("HELP_COMMAND")
HELPABLE = {}

async def start_bot():
    global HELPABLE
    for module in ALL_MODULES:
        imported_module = importlib.import_module("Rose.plugins." + module)
        if (
            hasattr(imported_module, "__MODULE__")
            and imported_module.__MODULE__
        ):
            imported_module.__MODULE__ = imported_module.__MODULE__
            if (
                hasattr(imported_module, "__HELP__")
                and imported_module.__HELP__
            ):
                HELPABLE[
                    imported_module.__MODULE__.replace(" ", "_").lower()
                ] = imported_module
    all_module = ""
    j = 1
    for i in ALL_MODULES:
        if j == 1:
            all_module += "•≫ Successfully imported:{:<15}.py\n".format(i)
            j = 0
        else:
            all_module += "•≫ Successfully imported:{:<15}.py".format(i)
        j += 1           
    restart_data = await clean_restart_stage()
    try:
        if restart_data:
            await app.edit_message_text(
                restart_data["chat_id"],
                restart_data["message_id"],
                "**Restarted Successfully**",
            )

        else:
            await app.send_message(LOG_GROUP_ID, "Bot started!")
    except Exception:
        pass
    print(f"{all_module}")
    print("""
 _____________________________________________   
|                                             |  
|          Deployed Successfully              |  
|         (C) 2021-2022 by @szteambots        | 
|          Greetings from supun  :)           |
|_____________________________________________|  
                                                                                               
    """)
    await idle()

    await aiohttpsession.close()
    await app.stop()
    for task in asyncio.all_tasks():
        task.cancel() 



home_keyboard_pm = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                text="Offcial Beta Channel",
                url=f"https://t.me/betagang",
            )
        ],
        [
            InlineKeyboardButton(
                text="click here to join beta",
                url=f"https://t.me/BetaRegistration_Bot",
            ),
            InlineKeyboardButton(
                text="click here to join beta",
                url=f"https://t.me/BetaRegistration_Bot",
            )
        ],
    ]
)


IMG = ["https://telegra.ph/file/c8f5c1dd990ca9a3d8516.jpg",
       "https://telegra.ph/file/77cc3154b752ce822fd52.jpg",
       "https://telegra.ph/file/e72fb0b6a7fba177cf4c7.jpg",
       "https://telegra.ph/file/8738a478904238e367939.jpg",
       "https://telegra.ph/file/68d7830ba72820f44bda0.jpg"
]

@app.on_message(filters.command(START_COMMAND))
@language
async def start(client, message: Message, _):
    FSub = await ForceSub(bot, message)
    if FSub == 400:
        return
    chat_id = message.chat.id
    if message.sender_chat:
        return
    if message.chat.type != "private":
        await message.reply(
            _["main2"], reply_markup=keyboard)
        await adds_served_user(message.from_user.id)     
        return await add_served_chat(message.chat.id) 
    if len(message.text.split()) > 1:
        name = (message.text.split(None, 1)[1]).lower()
        if name.startswith("rules"):
                await get_private_rules(app, message, name)
                return     
        if name.startswith("learn"):
                await get_learn(app, message, name)
                return     
        elif "_" in name:
            module = name.split("_", 1)[1]
            text = (_["main6"].format({HELPABLE[module].__MODULE__}
                + HELPABLE[module].__HELP__)
            )
            await message.reply(text, disable_web_page_preview=True)
        elif name == "help":
            text, keyb = await help_parser(message.from_user.first_name)
            await message.reply(
                _["main5"],
                reply_markup=keyb,
                disable_web_page_preview=True,
            )
        elif name == "connections":
            await message.reply("Run /connections to view or disconnect from groups!")
    else:
        served_chats = len(await get_served_chats())
        served_chats = []
        chats = await get_served_chats()
        for chat in chats:
           served_chats.append(int(chat["chat_id"]))
        served_users = len(await get_served_users())
        served_users = []
        users = await get_served_users()
        for user in users:
          served_users.append(int(user["bot_users"]))
        await message.reply(f"""
[👋]({random.choice(IMG)}) Hey there {message.from_user.mention}, 

✪ Hey, I'm Team Beta Bot!
I'm a group management bot and i will help you with the information related to Beta!
✪ Must read the ABOUT Section Below


⚒ Send Me /help For Get Commands. 
👨‍💻Dᴇᴠᴇʟᴏᴘᴇʀ : @bunny_2021
""",
            reply_markup=home_keyboard_pm,
        )
        return await add_served_user(message.from_user.id) 


@app.on_message(filters.command(HELP_COMMAND))
@language
async def help_command(client, message: Message, _):
    FSub = await ForceSub(bot, message)
    if FSub == 400:
        return
    if message.chat.type != "private":
        if len(message.command) >= 2:
            name = (message.text.split(None, 1)[1]).replace(" ", "_").lower()
            if str(name) in HELPABLE:
                key = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=_["main3"],
                                url=f"t.me/{BOT_USERNAME}?start=help_{name}",
                            )
                        ],
                    ]
                )
                await message.reply(
                    _["main4"],
                    reply_markup=key,
                )
            else:
                await message.reply(
                    _["main2"], reply_markup=keyboard
                )
        else:
            await message.reply(
                _["main2"], reply_markup=keyboard
            )
    else:
        if len(message.command) >= 2:
            name = (message.text.split(None, 1)[1]).replace(" ", "_").lower()
            if str(name) in HELPABLE:
                text = (_["main6"].format({HELPABLE[name].__MODULE__}
                + HELPABLE[name].__HELP__)
                )
                if hasattr(HELPABLE[name], "__helpbtns__"):
                       button = (HELPABLE[name].__helpbtns__) + [[InlineKeyboardButton("« Back", callback_data="bot_commands")]]
                if not hasattr(HELPABLE[name], "__helpbtns__"): button = [[InlineKeyboardButton("« Back", callback_data="bot_commands")]]
                await message.reply(text,
                           reply_markup=InlineKeyboardMarkup(button),
                           disable_web_page_preview=True)
            else:
                text, help_keyboard = await help_parser(
                    message.from_user.first_name
                )
                await message.reply(
                    _["main5"],
                    reply_markup=help_keyboard,
                    disable_web_page_preview=True,
                )
        else:
            text, help_keyboard = await help_parser(
                message.from_user.first_name
            )
            await message.reply(
                text, reply_markup=help_keyboard, disable_web_page_preview=True
            )
    return

@app.on_callback_query(filters.regex("startcq"))
@languageCB
async def startcq(client,CallbackQuery, _):
    served_chats = len(await get_served_chats())
    served_chats = []
    chats = await get_served_chats()
    for chat in chats:
        served_chats.append(int(chat["chat_id"]))
    served_users = len(await get_served_users())
    served_users = []
    users = await get_served_users()
    for user in users:
        served_users.append(int(user["bot_users"]))
    await CallbackQuery.message.edit(
            text=f"""
👋 Hey there {CallbackQuery.from_user.mention}, 

   ✪ Hey, I'm Team Beta Bot!
I'm a group management bot and i will help you with the information related to Beta!
✪ Must read the ABOUT Section Below


⚒ Send Me /help For Get Commands. 
👨‍💻Dᴇᴠᴇʟᴏᴘᴇʀ : @bunny_2021
""",
            disable_web_page_preview=True,
            reply_markup=home_keyboard_pm)


async def help_parser(name, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    return (
"""
**Welcome to help menu**
I'm a group management bot of TEAM BETA with some useful features.
You can choose an option below, by clicking a button.
If you have any bugs or questions on how to use me, 
have a look at my [Docs](https://szsupunma.gitbook.io/rose-bot/), or head to @szteambots.
**All commands can be used with the following: / **""",
        keyboard,
    )

@app.on_callback_query(filters.regex("bot_commands"))
@languageCB
async def commands_callbacc(client,CallbackQuery, _):
    text ,keyboard = await help_parser(CallbackQuery.from_user.mention)
    await app.send_message(
        CallbackQuery.message.chat.id,
        text=_["main5"],
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )
    await CallbackQuery.message.delete()

@app.on_callback_query(filters.regex(r"help_(.*?)"))
@languageCB
async def help_button(client, query, _):
    home_match = re.match(r"help_home\((.+?)\)", query.data)
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    create_match = re.match(r"help_create", query.data)
    top_text = _["main5"]
    if mod_match:
        module = (mod_match.group(1)).replace(" ", "_")
        text = (
            "{} **{}**:\n".format(
                "Here is the help for", HELPABLE[module].__MODULE__
            )
            + HELPABLE[module].__HELP__
            + "\n👨‍💻Dᴇᴠᴇʟᴏᴘᴇʀ : @bunny_2021"
        )
        if hasattr(HELPABLE[module], "__helpbtns__"):
                       button = (HELPABLE[module].__helpbtns__) + [[InlineKeyboardButton("« Back", callback_data="bot_commands")]]
        if not hasattr(HELPABLE[module], "__helpbtns__"): button = [[InlineKeyboardButton("« Back", callback_data="bot_commands")]]
        await query.message.edit(
            text=text,
            reply_markup=InlineKeyboardMarkup(button),
            disable_web_page_preview=True,
        )
        await query.answer(f"Here is the help for {module}")
    elif home_match:
        await app.send_message(
            query.from_user.id,
            text= _["main2"],
            reply_markup=home_keyboard_pm,
        )
        await query.message.delete()
    elif prev_match:
        curr_page = int(prev_match.group(1))
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(curr_page - 1, HELPABLE, "help")
            ),
            disable_web_page_preview=True,
        )

    elif next_match:
        next_page = int(next_match.group(1))
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(next_page + 1, HELPABLE, "help")
            ),
            disable_web_page_preview=True,
        )

    elif back_match:
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(0, HELPABLE, "help")
            ),
            disable_web_page_preview=True,
        )

    elif create_match:
        text, keyboard = await help_parser(query)
        await query.message.edit(
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

    return await client.answer_callback_query(query.id)

if __name__ == "__main__":
    install()
    with closing(loop):
        with suppress(asyncio.exceptions.CancelledError):
            loop.run_until_complete(start_bot())
        loop.run_until_complete(asyncio.sleep(3.0)) 

app.run()
