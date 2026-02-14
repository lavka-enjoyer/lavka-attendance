import logging
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.admin_endpoint_v1.views import router as admin_router
from backend.base_endpoint_v1.views import router as base_router
from backend.config import ADMIN_LEVEL_SUPER, SUPER_ADMIN
from backend.external_auth_endpoint_v1.views import router as external_auth_router
from backend.group_endpoint_v1.views import router as group_router
from backend.markin_endpoint_v1.views import router as markin_router
from backend.middleware import RateLimitMiddleware
from backend.nfc_endpoint_v1.views import router as nfc_router
from backend.points_endpoint_v1.views import router as points_router
from backend.redis_client import redis_client
from backend.schedule_endpoint_v1.views import router as schedule_router
from backend.tg_endpoint_v1.views import router as tg_router
from backend.utils_helper import db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Менеджер жизненного цикла приложения FastAPI.

    Args:
        app: Экземпляр FastAPI приложения

    Yields:
        Контроль выполнения приложению
    """
    try:
        # Connect to DB
        await db.connect()
        await db.init_tables()  # Ensure tables exist

        # Connect to Redis
        try:
            await redis_client.connect()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed (will work without caching): {e}")

        # Check if admin user exists
        admin_user_id = SUPER_ADMIN
        user = await db.get_user_by_id(admin_user_id)

        if not user:
            # Create user with admin privileges if not exists
            logger.info(f"Creating admin user with ID {admin_user_id}")

            await db.pool.execute(
                """
                    INSERT INTO users (tg_userid, admin_lvl, allowConfirm)
                    VALUES ($1, $2, true)
                """,
                admin_user_id,
                ADMIN_LEVEL_SUPER,
            )

            logger.info(f"Admin user {admin_user_id} created successfully")

    except Exception as e:
        logger.error(f"Error during admin user setup: {e}")

    yield

    # Cleanup on shutdown
    await redis_client.disconnect()
    await db.disconnect()


app = FastAPI(
    lifespan=lifespan,
    title="MireApprove API",
    description="API для автоматизации учёта посещаемости МИРЭА",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Единый обработчик HTTP исключений с стандартным форматом ответа."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": f"HTTP_{exc.status_code}"},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Обработчик ошибок валидации."""
    return JSONResponse(
        status_code=400, content={"detail": str(exc), "error_code": "VALIDATION_ERROR"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик общих исключений."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера", "error_code": "INTERNAL_ERROR"},
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Проверка состояния сервиса.

    Returns:
        JSON с информацией о состоянии всех компонентов
    """
    db_ok = await db.check_connection()
    redis_ok = await redis_client.ping()

    status = "healthy" if db_ok else "unhealthy"

    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }


app.include_router(base_router)
app.include_router(tg_router)
app.include_router(group_router)
app.include_router(markin_router)
app.include_router(admin_router)
app.include_router(points_router)
app.include_router(schedule_router)
app.include_router(external_auth_router)
app.include_router(nfc_router)

app.mount("/assets", StaticFiles(directory="/app/static/assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Обработчик для обслуживания фронтенд приложения.

    Args:
        full_path: Полный путь запроса

    Returns:
        FileResponse с index.html для фронтенд маршрутов

    Raises:
        HTTPException: Если запрашивается несуществующий API маршрут
    """
    # Пропускаем API и OpenAPI docs
    if full_path.startswith("api/") or full_path in ("docs", "openapi.json"):
        raise HTTPException(status_code=404)

    # Возвращаем index.html для всех остальных маршрутов
    return FileResponse("/app/static/index.html")


logging.basicConfig(level=logging.DEBUG)
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True, log_level="debug")
