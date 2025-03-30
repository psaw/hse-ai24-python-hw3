from fastapi import APIRouter
from auth.users import auth_backend, fastapi_users
from schemas.user import UserRead, UserCreate

router = APIRouter(prefix="/auth", tags=["Auth"])

# Роутер JWT аутентификации
router.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/jwt")

# Роутер регистрации
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))

# Дополнительные роутеры fastapi_users можно добавить здесь
# например, роутер для восстановления пароля, верификации и т.д.
