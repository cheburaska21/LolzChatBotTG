import aiohttp
import asyncio
import json
import websockets
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from config import FORUM_API_TOKEN, XF_TOKEN


class ChatAPI:
    BASE_URL = "https://api.zelenka.guru"
    WS_URL = "wss://lolz.live/socket/"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {FORUM_API_TOKEN}",
            "Content-Type": "application/json"
        }
        self.ws_headers = {
            "Cookie": f"xf_user={XF_TOKEN}"
        }
        self.last_request_time = datetime.now()
        self.interval = 3
        self.ws = None
        self.message_callback = None
        self.next_id = 1
        self.client_id = None
        self.chat_epoch = None
        self.chat_offset = None

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Any]:
        now = datetime.now()
        time_since_last = (now - self.last_request_time).total_seconds()
        if time_since_last < self.interval:
            await asyncio.sleep(self.interval - time_since_last)

        try:
            async with aiohttp.ClientSession() as session:
                async with getattr(session, method)(
                        f"{self.BASE_URL}{endpoint}",
                        headers=self.headers,
                        **kwargs
                ) as response:
                    if response.status == 429:
                        await asyncio.sleep(3)
                        return await self._make_request(method, endpoint, **kwargs)

                    if response.status == 200:
                        return await response.json()
                    return None

        except Exception as e:
            print(f"Ошибк: {e}")
            return None
        finally:
            self.last_request_time = datetime.now()

    def get_next_id(self) -> int:
        current_id = self.next_id
        self.next_id += 1
        return current_id

    async def connect_websocket(self, message_callback: Callable):
        self.message_callback = message_callback

        while True:
            try:
                async with websockets.connect(self.WS_URL, additional_headers=self.ws_headers) as websocket:
                    self.ws = websocket

                    connect_id = self.get_next_id()
                    await websocket.send(json.dumps({
                        "connect": {"name": "chat_in_tg"},
                        "id": connect_id
                    }))

                    response = await websocket.recv()
                    data = json.loads(response)
                    if 'id' in data and data['id'] == connect_id and 'connect' in data:
                        self.client_id = data['connect']['client']
                        print(f"WebSocket подключен: {self.client_id}")

                        chat_id = self.get_next_id()
                        await websocket.send(json.dumps({
                            "subscribe": {"channel": "chat:1"},
                            "id": chat_id
                        }))

                        async def process_messages():
                            async for message in websocket:
                                try:
                                    data = json.loads(message)

                                    if data == {}:
                                        await websocket.send(json.dumps({}))
                                        continue

                                    if 'id' in data and data['id'] == chat_id and 'subscribe' in data:
                                        self.chat_epoch = data['subscribe']['epoch']
                                        self.chat_offset = data['subscribe']['offset']

                                        history_id = self.get_next_id()
                                        await websocket.send(json.dumps({
                                            "history": {
                                                "channel": "chat:1",
                                                "since": {
                                                    "offset": self.chat_offset - 20,
                                                    "epoch": self.chat_epoch
                                                },
                                                "limit": 20
                                            },
                                            "id": history_id
                                        }))

                                    elif 'push' in data and data['push']['channel'] == 'chat:1':
                                        try:
                                            pub_data = data['push']['pub']['data']['input']
                                            input_data = json.loads(pub_data)

                                            if input_data['type'] == 'newMessage':
                                                msg = input_data['message']
                                                formatted_message = {
                                                    "message_id": msg["id"],
                                                    "user_id": msg["userId"],
                                                    "username": msg["username"],
                                                    "username_html": msg["usernameHtml"],
                                                    "plain_message": msg["messagePlain"],
                                                    "message": msg["message"],
                                                    "message_date": msg["time"],
                                                    "is_curator_message": msg.get("isCuratorMessage", False)
                                                }
                                                await self.message_callback(formatted_message)
                                        except Exception as e:
                                            print(f"Ошибка обработки сообщения: {e}")
                                except json.JSONDecodeError:
                                    print(f"Ошибка: {message}")
                                except Exception as e:
                                    print(f"Общая ошибка вебсокет: {e}")
                                    raise

                        await process_messages()
                    else:
                        print("Не удалось установить вебсокет соединение")

            except Exception as e:
                print(f"Ошибка вебсокет: {e}")
                self.ws = None
                await asyncio.sleep(5)

    async def create_message(self, room_id: int, message: str) -> Optional[Dict[str, Any]]:
        params = {'room_id': room_id}
        data = {'message': message}
        return await self._make_request('post', '/chatbox/message', params=params, json=data)

    async def send_typing(self, room_id: int):
        if self.ws:
            try:
                typing_id = self.get_next_id()
                await self.ws.send(json.dumps({
                    "publish": {
                        "channel": f"chat:{room_id}",
                        "data": {
                            "input": json.dumps({
                                "type": "typing"
                            })
                        }
                    },
                    "id": typing_id
                }))
                return True
            except:
                pass
        return False