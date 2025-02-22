from aiogram import Router, Bot
from aiogram.types import Message
import asyncio
from utils.lolz_api import ChatAPI
from config import ID
import re

chat_router = Router()
last_message_id = 0
DEFAULT_ROOM_ID = 1
chat_api = ChatAPI()


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


def extract_username(text: str) -> str:
    try:
        username = text.split()[0].strip("<b>").strip("</b>")
        return username
    except:
        return None


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


async def check_new_messages(bot: Bot):
    global last_message_id
    while True:
        try:
            response = await chat_api.get_messages(room_id=DEFAULT_ROOM_ID)
            if response and 'messages' in response:
                messages = response['messages']
                for message in messages:
                    if message['message_id'] > last_message_id:
                        last_message_id = message['message_id']

                        clean_message, images = extract_images_from_message(
                            message['plain_message'],
                            message['message']
                        )

                        clean_message = clean_html(clean_message)
                        author = f"<a href='https://lolz.live/members/{message['user_id']}'>{message['username']}</a>"

                        text = f"<b>{author}</b>\n{clean_message}"

                        if images:
                            text = f"<a href='{images[0]}'>&#8205;</a>" + text

                        try:
                            await bot.send_message(
                                chat_id=ID,
                                text=text,
                                disable_web_page_preview=not bool(images)
                            )

                            if len(images) > 1:
                                for img_url in images[1:]:
                                    await bot.send_message(
                                        chat_id=ID,
                                        text=f"<a href='{img_url}'>&#8205;</a>",
                                        disable_web_page_preview=False
                                    )

                        except Exception as e:
                            print(f"Ошибка отправки сообщения в Telegram: {e}")
                            simple_text = f"{message['username']}: {clean_message}"
                            await bot.send_message(
                                chat_id=ID,
                                text=simple_text,
                                disable_web_page_preview=True
                            )
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Ошибка проверки сообщений: {e}")
            await asyncio.sleep(3)


@chat_router.startup()
async def start_polling(bot: Bot):
    asyncio.create_task(check_new_messages(bot))


@chat_router.message()
async def handle_message(message: Message):
    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение")
        return

    try:
        text = message.text

        if message.reply_to_message:
            username = extract_username(message.reply_to_message.text)
            if username:
                text = f"@{username}, {text}"

        await chat_api.create_message(
            room_id=DEFAULT_ROOM_ID,
            message=text
        )
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        await message.answer("❌ Ошибка отправки сообщения")