from aiogram import Router
from .admin import router as admin_router
from .start import router as start_router
from .profile import router as profile_router
from .tasks import router as tasks_router
from .token import router as token_router
from .language import router as language_router
from .webapp import router as webapp_router

# Combine all handler routers.
# Admin router is placed first so its specific messages take precedence.
main_router = Router()
main_router.include_routers(
    admin_router,
    start_router,
    profile_router,
    tasks_router,
    token_router,
    language_router,
    webapp_router
)
