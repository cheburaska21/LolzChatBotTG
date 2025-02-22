from aiogram import Router

from handlers.user.chat_router import chat_router

users_router = Router()

users_router.include_routers(
    chat_router
)