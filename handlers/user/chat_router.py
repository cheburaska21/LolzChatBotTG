from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
import asyncio
from utils.lolz_api import ChatAPI
from config import ID
import re
from collections import deque
import time

chat_router = Router()
last_message_id = 0
DEFAULT_ROOM_ID = 1
chat_api = ChatAPI()

message_queue = deque()
last_sender = None
last_sender_time = 0
sent_message_ids = set()
message_mapping = {}


def clean_html(text: str) -> str:
    text = re.sub(r'\[USER=\d+\]@([^\]]+)\[/USER\]', r'@\1', text)
    text = re.sub(r'\[tooltip=\d+\]([^\]]+)\[/tooltip\]', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&quot;', '"') \
        .replace('&amp;', '&') \
        .replace('&lt;', '<') \
        .replace('&gt;', '>') \
        .replace('&nbsp;', ' ') \
        .replace('\n\n\n', '\n\n')
    return text.strip()


def extract_images_from_message(plain_message: str, html_message: str) -> tuple[str, list[str]]:
    images = []

    bb_images = re.findall(r'\[img\](.*?)\[/img\]', plain_message)
    if bb_images:
        images.extend(bb_images)
        plain_message = re.sub(r'\[img\].*?\[/img\]', '', plain_message)

    html_images = re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', html_message)
    if html_images:
        images.extend([img for img in html_images if img not in images])

    return plain_message.strip(), list(set(images))


async def initialize_last_message_id():
    global last_message_id
    try:
        response = await chat_api.get_messages(room_id=DEFAULT_ROOM_ID)
        if response and 'messages' in response:
            messages = response['messages']
            if messages:
                last_message_id = max(msg['message_id'] for msg in messages)
    except Exception as e:
        print(f"Ошибка инициализации last_message_id: {e}")


async def process_message(message: dict, bot: Bot) -> None:
    global last_sender, last_sender_time

    if message['message_id'] in sent_message_ids:
        return
    sent_message_ids.add(message['message_id'])

    clean_message, images = extract_images_from_message(
        message['plain_message'],
        message['message']
    )

    clean_message = clean_html(clean_message)
    current_time = time.time()

    show_author = (
            message['username'] != last_sender or
            current_time - last_sender_time > 300
    )

    if show_author:
        author = f"<a href='https://lolz.live/members/{message['user_id']}'>{message['username']}</a>"
        text = f"<b>{author}</b>\n{clean_message}"
    else:
        text = clean_message

    if images:
        text = f"<a href='{images[0]}'>&#8205;</a>" + text

    try:
        sent_msg = await bot.send_message(
            chat_id=ID,
            text=text,
            disable_web_page_preview=not bool(images)
        )

        message_mapping[sent_msg.message_id] = {
            'username': message['username'],
            'user_id': message['user_id']
        }

        if len(message_mapping) > 100:
            oldest_keys = sorted(message_mapping.keys())[:-100]
            for key in oldest_keys:
                message_mapping.pop(key, None)

        if len(images) > 1:
            for img_url in images[1:]:
                await bot.send_message(
                    chat_id=ID,
                    text=f"<a href='{img_url}'>&#8205;</a>",
                    disable_web_page_preview=False
                )

        last_sender = message['username']
        last_sender_time = current_time

    except Exception as e:
        print(f"Ошибка отправки сообщения в Telegram: {e}")


async def message_processor(bot: Bot):
    while True:
        try:
            if message_queue:
                message = message_queue.popleft()
                await process_message(message, bot)
            else:
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Ошибка в обработчике сообщений: {e}")
            await asyncio.sleep(1)


async def check_new_messages(bot: Bot):
    global last_message_id
    while True:
        try:
            response = await chat_api.get_messages(room_id=DEFAULT_ROOM_ID)
            if response and 'messages' in response:
                new_messages = [
                    msg for msg in response['messages']
                    if msg['message_id'] > last_message_id
                       and msg['message_id'] not in sent_message_ids
                ]

                if new_messages:
                    new_messages.sort(key=lambda x: x['message_id'])
                    for message in new_messages:
                        last_message_id = max(last_message_id, message['message_id'])
                        message_queue.append(message)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Ошибка проверки сообщений: {e}")
            await asyncio.sleep(3)


@chat_router.startup()
async def start_polling(bot: Bot):
    await initialize_last_message_id()
    asyncio.create_task(check_new_messages(bot))
    asyncio.create_task(message_processor(bot))


@chat_router.message(Command("start"))
async def handle_start(message: Message):
    await message.answer("👋 Бот запущен и готов к работе!")


@chat_router.message()
async def handle_message(message: Message):
    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение")
        return

    try:
        text = message.text

        if message.reply_to_message and message.reply_to_message.message_id in message_mapping:
            user_info = message_mapping[message.reply_to_message.message_id]
            text = f"@{user_info['username']}, {text}"

        response = await chat_api.create_message(
            room_id=DEFAULT_ROOM_ID,
            message=text
        )

        if response and 'message' in response:
            sent_message_ids.add(response['message']['message_id'])

    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        await message.answer("❌ Ошибка отправки сообщения")