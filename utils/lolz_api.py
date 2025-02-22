import aiohttp
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from config import FORUM_API_TOKEN


class ChatAPI:
    BASE_URL = "https://api.zelenka.guru"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {FORUM_API_TOKEN}",
            "Content-Type": "application/json"
        }
        self.last_request_time = datetime.now()
        self.interval = 3

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
            print(f"Ошибка запроса: {e}")
            return None
        finally:
            self.last_request_time = datetime.now()

    async def get_messages(self, room_id: int, before_message: Optional[int] = None) -> Optional[Dict[str, Any]]:
        params = {'room_id': room_id}
        if before_message:
            params['before_message'] = before_message
        return await self._make_request('get', '/chatbox/messages', params=params)

    async def create_message(self, room_id: int, message: str) -> Optional[Dict[str, Any]]:
        params = {'room_id': room_id}
        data = {'message': message}
        return await self._make_request('post', '/chatbox/message', params=params, json=data)

    async def delete_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        params = {'message_id': message_id}
        return await self._make_request('delete', '/chatbox/message', params=params)