from aiogram import Router

from handlers.user import users_router

main_router = Router()


main_router.include_routers(
    users_router
)
