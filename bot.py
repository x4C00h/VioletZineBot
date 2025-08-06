from typing import Final, Coroutine, Dict, Any
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.async_telebot import types, AsyncTeleBot
import asyncio
import yaml
import os
import database



# GLOBAL VARS
TOKEN       : Final[str]    = None # BOT TOKEN HERE 
bot         : AsyncTeleBot  = AsyncTeleBot(TOKEN)
sizeof32MB  : int           = 33554432

with open("text.yml", "r", encoding="utf-8") as file:
    localization_file   : Dict[str, Any]  = yaml.safe_load(file)
    commands            : Dict[str, Any]  = localization_file["commands"]
    buttons             : Dict[str, Any]  = localization_file["buttons"]
    text                : Dict[str, Any]  = localization_file["text"]
    del localization_file

keyboard_registration = InlineKeyboardMarkup()
button_registration = InlineKeyboardButton(buttons["participate"], callback_data="participate")
keyboard_registration.add(button_registration)

waiting_for_name = []
waiting_for_file = []



# EXPORT FUNCTION
async def run_bot():
    try:
        os.mkdir("works")
    except PermissionError as e:
        print("Permission denied (folder ./works creation): {e}")
    except Exception as e:
        pass

    await setup_commands()
    await bot.delete_webhook()
    await bot.polling()



# LOCAL FUNCTIONS
def setup_commands() -> Coroutine[Any, Any, bool]:
    global commands
    cmds_list = [
        types.BotCommand(command, commands[command]) for command in commands
    ]
    return bot.set_my_commands(cmds_list, types.BotCommandScopeDefault())



# HANDLES
@bot.message_handler(["start"])
async def handle_start(user_message: types.Message) -> None:
    await bot.send_message(
        user_message.chat.id,
        text["start"],
        reply_markup=keyboard_registration
    )


@bot.message_handler(["help"])
async def handle_help(user_message: types.Message) -> None:
    await bot.send_message(
        user_message.chat.id,
        text["help"]
    )


async def participate_handler(chat_id: int, user_id: int) -> None:
    if await database.is_user_registred(user_id):
        waiting_for_file.append(user_id)
        await bot.send_message(chat_id, text["send_file"])
        return
    
    # else if user isn't registred
    waiting_for_name.append(user_id)
    await bot.send_message(chat_id, text["send_name"])


@bot.callback_query_handler(func=lambda call: call.data == "participate")
async def handle_button_callback_participate(call: types.CallbackQuery) -> None:
    await bot.answer_callback_query(call.id)
    await participate_handler(call.message.chat.id, call.from_user.id)


@bot.message_handler(["participate"])
async def handle_participate(user_message: types.Message) -> None:
    await participate_handler(user_message.chat.id, user_message.from_user.id)


# TODO: errors for content_types=['text', 'photo', 'document', 'audio', 'video', 'voice']
@bot.message_handler(func=lambda msg: msg.from_user.id in waiting_for_name,)
async def handle_users_realname(user_message: types.Message):
    chat_id = user_message.chat.id
    waiting_for_name.remove(user_message.from_user.id)
    waiting_for_file.append((user_message.from_user.id))

    registration_task = asyncio.create_task(
        database.register_user(user_message)
    )

    await bot.send_message(chat_id, text["successful_registration"])
    await bot.send_message(chat_id, text["send_file"])
    await registration_task


@bot.message_handler(
    func=lambda msg: msg.from_user.id in waiting_for_file,
    content_types=['document']
)
async def handle_users_works(user_message: types.Message):
    waiting_for_file.remove(user_message.from_user.id)
    chat_id = user_message.chat.id

    allowed_file_extensions = (".docx", ".doc")
    user_filename = user_message.document.file_name.lower()
    if (not user_filename.endswith(allowed_file_extensions)):
        response_msg = text["error_file_ext2"].format(user_filename.split(".")[-1]) if '.' in user_filename else text["error_file_ext"]
        await bot.send_message(chat_id, response_msg)
        return
    
    if (user_message.document.file_size > sizeof32MB):
        await bot.send_message(chat_id, text["error_file_too_large"])
        return

    work_id = await database.register_work(user_message)
    
    try:
        file_info = await bot.get_file(user_message.document.file_id)
        file = await bot.download_file(file_info.file_path)
        with open(f"works/{work_id}.doc", "+wb") as new_file:
            new_file.write(file)
    except Exception as e:
        await bot.send_message(chat_id, text["error_file_processing"])
        print(f"ERROR with file processig from user {getattr(user_message, 'from_user.username', user_message.from_user.full_name)} with {file_info.file_path}: {e}")
    
    await bot.send_message(chat_id, text["successful_participated"])



@bot.message_handler(
    func=lambda msg: msg.from_user.id not in waiting_for_file,
    content_types=['document']
)
async def handle_users_file(user_message: types.Message):
    await bot.send_message(
        user_message.chat.id,
        text["error_file_unexpected"]
    )


def get_plural(n, forms) -> str:
    n = abs(n) % 100
    n1 = n % 10

    if 10 < n < 20:
        return forms[2]
    elif 1 < n1 < 5:
        return forms[1]
    elif n1 == 1:
        return forms[0]
    
    return forms[2]


@bot.message_handler(["am_i_participate"])
async def handle_am_i_participate(user_message: types.Message) -> None:
    chat_id = user_message.chat.id

    works = await database.get_user_works(user_message)

    if len(works) == 0:
        await bot.send_message(chat_id, text["work_statistics_empty"])
        return
    
    work_number = len(works)
    works_list = "\n".join(f"{work[1]} — {work[2] if work[2] is not None else text["no_comment_to_work"]}" for work in works)
    
    await bot.send_message(
        chat_id,
        text["am_i_participate"].format(
            work_number,
            get_plural(work_number, ("текст", "текста", "текстов")), 
            works_list
        )
    )
