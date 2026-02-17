import asyncio
from typing import Optional

import asyncpg
from cryptography.fernet import Fernet

from backend.config import (
    ADMIN_LEVEL_BASIC,
    ADMIN_LEVEL_MODERATE,
    ADMIN_LEVEL_SUPER,
    DB_POOL_MAX_SIZE,
    DB_POOL_MIN_SIZE,
)


class DBModel:
    """Модель базы данных PostgreSQL с пулом соединений и шифрованием."""

    def __init__(self, dsn: str, encryption_key: bytes) -> None:
        """
        Инициализирует модель базы данных.

        Args:
            dsn: Строка подключения PostgreSQL
            encryption_key: Ключ шифрования Fernet
        """
        self.dsn = dsn
        self.encryption_key = encryption_key
        self.fernet = Fernet(encryption_key)
        self.pool: Optional[asyncpg.Pool] = None
        self._active_connections: int = 0
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Создаёт пул соединений с базой данных."""
        async with self._lock:
            if self.pool is None or (
                hasattr(self.pool, "_closed") and self.pool._closed
            ):
                self.pool = await asyncpg.create_pool(
                    dsn=self.dsn, min_size=DB_POOL_MIN_SIZE, max_size=DB_POOL_MAX_SIZE
                )
            self._active_connections += 1

    async def disconnect(self):
        """Закрытие пула соединений."""
        async with self._lock:
            if self._active_connections > 0:
                self._active_connections -= 1

            # Закрываем пул только если нет активных соединений
            if (
                self._active_connections == 0
                and self.pool
                and not (hasattr(self.pool, "_closed") and self.pool._closed)
            ):
                await self.pool.close()

    async def init_tables(self):
        """
        Создание таблиц, если они ещё не существуют.
        Название столбца group заменено на group_name, так как group – зарезервированное слово.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    tg_userid BIGINT PRIMARY KEY,
                    group_name TEXT NULL,
                    login TEXT NULL,
                    hashed_password TEXT NULL,
                    allowConfirm BOOLEAN DEFAULT TRUE,
                    admin_lvl INTEGER DEFAULT 0,
                    user_agent TEXT NULL,
                    fio TEXT NULL
                );
            """
            )

            # Добавляем колонку fio если её нет (для существующих БД)
            await conn.execute(
                """
                ALTER TABLE users ADD COLUMN IF NOT EXISTS fio TEXT NULL;
            """
            )

            # Добавляем колонку totp_secret для автоматического ввода 2FA кодов
            await conn.execute(
                """
                ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret TEXT NULL;
            """
            )

            # Добавляем колонку totp_credential_id для хранения ID credential для авто-TOTP
            await conn.execute(
                """
                ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_credential_id TEXT NULL;
            """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approved (
                    tg_userid BIGINT PRIMARY KEY,
                    group_name TEXT,
                    all_users TEXT,
                    approvedCount INT,
                    approved TEXT,
                    notApproved TEXT
                );
             """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cookies (
                    tg_userid BIGINT PRIMARY KEY,
                    cookies TEXT
                );
            """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS status (
                    tg_userid BIGINT,
                    sType TEXT,
                    status TEXT,
                    PRIMARY KEY (tg_userid, sType)
                );
            """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons_cost_cache (
                    group_name TEXT PRIMARY KEY,
                    subjects_data TEXT NOT NULL,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS external_auth_tokens (
                    token TEXT PRIMARY KEY,
                    tg_userid BIGINT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP WITH TIME ZONE NULL,
                    service_name TEXT NULL
                );
            """
            )

            # Разрешаем NULL для expires_at (бессрочные токены)
            await conn.execute(
                """
                ALTER TABLE external_auth_tokens ALTER COLUMN expires_at DROP NOT NULL;
            """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nfc_cards (
                    id SERIAL PRIMARY KEY,
                    card_id BIGINT NOT NULL,
                    tg_userid BIGINT NULL,
                    name TEXT NOT NULL,
                    owner_group TEXT NOT NULL,
                    added_by BIGINT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(card_id, owner_group)
                );
            """
            )

            # Таблица для хранения 2FA сессий
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS totp_sessions (
                    id SERIAL PRIMARY KEY,
                    tg_userid BIGINT NOT NULL,
                    session_cookies TEXT NOT NULL,
                    otp_action_url TEXT NOT NULL,
                    credential_id TEXT,
                    user_agent TEXT,
                    source TEXT DEFAULT 'login',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    last_notification_sent TIMESTAMP WITH TIME ZONE
                );
            """
            )

            # Добавляем колонку otp_credentials для хранения списка доступных 2FA методов
            await conn.execute(
                """
                ALTER TABLE totp_sessions ADD COLUMN IF NOT EXISTS otp_credentials TEXT;
            """
            )

            # Удаляем истекшие 2FA сессии
            await conn.execute(
                """
                DELETE FROM totp_sessions WHERE expires_at < NOW();
            """
            )

            # Таблица для аудит-логов админских действий
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    admin_tg_userid BIGINT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_type TEXT,
                    target_id TEXT,
                    old_value JSONB,
                    new_value JSONB,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """
            )

            # Таблица для логов действий пользователей
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_action_logs (
                    id SERIAL PRIMARY KEY,
                    actor_tg_userid BIGINT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_tg_userid BIGINT,
                    details JSONB,
                    status TEXT DEFAULT 'success',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """
            )

            # Создаём индексы для производительности
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_group ON users(group_name);
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_admin ON users(admin_lvl) WHERE admin_lvl > 0;
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_login ON users(login) WHERE login IS NOT NULL;
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_logs_admin ON audit_logs(admin_tg_userid);
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action_type);
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_logs_actor ON user_action_logs(actor_tg_userid);
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_logs_created ON user_action_logs(created_at DESC);
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_logs_action ON user_action_logs(action_type);
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_nfc_group ON nfc_cards(owner_group);
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ext_tokens_status ON external_auth_tokens(status);
            """
            )

    # Методы для шифрования/дешифрования пароля

    def encrypt_password(self, password: str) -> str:
        """Шифрует пароль с помощью Fernet."""
        return self.fernet.encrypt(password.encode()).decode()

    def decrypt_password(self, encrypted: str) -> str:
        """Дешифрует пароль и возвращает его в нормальном виде."""
        return self.fernet.decrypt(encrypted.encode()).decode()

    # Методы для таблицы users

    async def create_user(
        self,
        tg_userid: int,
        group_name: str,
        login: str,
        password: str,
        allowConfirm: bool = True,
    ):
        """
        Создаёт пользователя. Пароль шифруется перед сохранением.
        При конфликте по tg_userid запись обновляется.
        """
        encrypted_password = self.encrypt_password(password)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (tg_userid, group_name, login, hashed_password, allowConfirm)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (tg_userid) DO UPDATE SET
                    group_name = EXCLUDED.group_name,
                    login = EXCLUDED.login,
                    hashed_password = EXCLUDED.hashed_password,
                    allowConfirm = EXCLUDED.allowConfirm;
            """,
                tg_userid,
                group_name,
                login,
                encrypted_password,
                allowConfirm,
            )

    async def get_user(self, tg_userid: int):
        """
        Возвращает пользователя по tg_userid. Поле с паролем дешифруется перед возвратом.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tg_userid, group_name, login, hashed_password, allowConfirm
                FROM users
                WHERE tg_userid = $1;
            """,
                tg_userid,
            )
            if row:
                user = dict(row)
                user["hashed_password"] = self.decrypt_password(user["hashed_password"])
                return user
            return None

    async def get_user_by_login(self, login: str):
        """
        Возвращает пользователя по tg_userid. Поле с паролем дешифруется перед возвратом.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tg_userid, group_name, login, hashed_password, allowConfirm
                FROM users
                WHERE login = $1;
            """,
                login,
            )
            if row:
                return "User already exists"
            return None

    async def get_user_by_id(self, tg_id: int):
        """
        Возвращает пользователя по tg_userid.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT *
                FROM users
                WHERE tg_userid = $1;
            """,
                tg_id,
            )
            if row:
                return row
            return None

    async def update_user(self, tg_userid: int, **fields):
        """
        Обновляет поля записи пользователя. Поддерживаются следующие ключи:
            - group_name
            - login
            - password (будет зашифрован)
            - allowConfirm
        """
        assert (
            await self.get_user_by_id(tg_userid) is not None
        ), "Ошибка, Такого пользователя не существует"
        updates = []
        values = []
        idx = 1
        if "group_name" in fields:
            updates.append(f"group_name = ${idx}")
            values.append(fields["group_name"])
            idx += 1
        if "login" in fields:
            updates.append(f"login = ${idx}")
            values.append(fields["login"])
            idx += 1
        if "password" in fields and fields["password"]:
            updates.append(f"hashed_password = ${idx}")
            encrypted_password = self.encrypt_password(fields["password"])
            values.append(encrypted_password)
            idx += 1
        if "allowConfirm" in fields:
            updates.append(f"allowConfirm = ${idx}")
            values.append(fields["allowConfirm"])
            idx += 1
        if "user_agent" in fields:
            updates.append(f"user_agent = ${idx}")
            values.append(fields["user_agent"])
            idx += 1

        if not updates:
            return

        set_clause = ", ".join(updates)
        query = f"UPDATE users SET {set_clause} WHERE tg_userid = ${idx}"
        values.append(tg_userid)
        async with self.pool.acquire() as conn:
            await conn.execute(query, *values)
        if "password" in fields and fields["password"]:
            res = await self.get_user(tg_userid)
        else:
            res = await self.get_user_by_id(tg_userid)

        return True if res else False

    async def check_admin_user(self, tg_userid: int, admin_lv: int):
        """
        Проверяет, является ли пользователь администратором с указанным уровнем.

        Args:
            tg_userid: Telegram ID пользователя
            admin_lv: Минимальный требуемый уровень администратора

        Returns:
            Запись пользователя если он является администратором с нужным уровнем, иначе None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT *
                FROM users
                WHERE tg_userid = $1 AND admin_lvl >= $2;
                """,
                tg_userid,
                admin_lv,
            )
            if row:
                return row
            return None

    async def delete_user(self, tg_userid: int):
        """
        Удаляет пользователя из базы данных.

        Args:
            tg_userid: Telegram ID пользователя

        Returns:
            "Успешно" если пользователь был удален, иначе "Такого пользователя нет в бд"
        """
        async with self.pool.acquire() as conn:
            user_exists = await conn.fetchval(
                "SELECT 1 FROM users WHERE tg_userid = $1", tg_userid
            )
            if user_exists:
                await conn.execute(
                    """
                    DELETE FROM users WHERE tg_userid = $1
                    """,
                    tg_userid,
                )
                return "Успешно"

            return "Такого пользователя нет в бд"

    # Методы для таблицы approved

    async def create_approved(
        self,
        tg_userid: int,
        group_name: str,
        all_users: str,
        approvedCount: int,
        approved: str,
        notApproved: str,
    ):
        """
        Создаёт запись в таблице approved.
        При конфликте по tg_userid запись обновляется.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO approved (tg_userid, group_name, all_users, approvedCount, approved, notApproved)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (tg_userid) DO UPDATE SET
                    group_name = EXCLUDED.group_name,
                    all_users = EXCLUDED.all_users,
                    approvedCount = EXCLUDED.approvedCount,
                    approved = EXCLUDED.approved,
                    notApproved = EXCLUDED.notApproved;
            """,
                tg_userid,
                group_name,
                all_users,
                approvedCount,
                approved,
                notApproved,
            )

    async def get_approved(self, tg_userid: int):
        """Возвращает запись из таблицы approved по tg_userid."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tg_userid, group_name, all_users, approvedCount, approved, notApproved
                FROM approved
                WHERE tg_userid = $1;
            """,
                tg_userid,
            )
            return dict(row) if row else None

    async def update_approved(self, tg_userid: int, **fields):
        """
        Обновляет запись в таблице approved.
        Поддерживаются поля:
            - group_name
            - all_users
            - approvedCount
            - approved
            - notApproved
        """
        updates = []
        values = []
        idx = 1
        for key in [
            "group_name",
            "all_users",
            "approvedCount",
            "approved",
            "notApproved",
        ]:
            if key in fields:
                updates.append(f"{key} = ${idx}")
                values.append(fields[key])
                idx += 1
        if not updates:
            return

        set_clause = ", ".join(updates)
        query = f"UPDATE approved SET {set_clause} WHERE tg_userid = ${idx}"
        values.append(tg_userid)
        async with self.pool.acquire() as conn:
            await conn.execute(query, *values)

    # Методы для таблицы cookies

    async def create_cookie(self, tg_userid: int, cookies: str):
        """
        Создаёт запись в таблице cookies.
        При конфликте по tg_userid запись обновляется.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO cookies (tg_userid, cookies)
                VALUES ($1, $2)
                ON CONFLICT (tg_userid) DO UPDATE SET cookies = EXCLUDED.cookies;
            """,
                tg_userid,
                cookies,
            )

    async def get_cookie(self, tg_userid: int):
        """Возвращает запись из таблицы cookies по tg_userid."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tg_userid, cookies
                FROM cookies
                WHERE tg_userid = $1;
            """,
                tg_userid,
            )
            return dict(row) if row else None

    async def update_cookie(self, tg_userid: int, cookies: str):
        """Обновляет поле cookies для заданного tg_userid."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE cookies SET cookies = $1 WHERE tg_userid = $2;
            """,
                cookies,
                tg_userid,
            )

    # Методы для таблицы status

    async def create_status(self, tg_userid: int, sType: str, status: str):
        """
        Создаёт запись в таблице status.
        При конфликте (tg_userid, sType) обновляется статус.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO status (tg_userid, sType, status)
                VALUES ($1, $2, $3)
                ON CONFLICT (tg_userid, sType) DO UPDATE SET status = EXCLUDED.status;
            """,
                tg_userid,
                sType,
                status,
            )

    async def get_status(self, tg_userid: int, sType: str):
        """Возвращает запись из таблицы status для заданного tg_userid и sType."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tg_userid, sType, status
                FROM status
                WHERE tg_userid = $1 AND sType = $2;
            """,
                tg_userid,
                sType,
            )
            return dict(row) if row else None

    async def update_status(self, tg_userid: int, sType: str, status: str):
        """Обновляет поле status для заданного tg_userid и sType."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE status SET status = $1 WHERE tg_userid = $2 AND sType = $3;
            """,
                status,
                tg_userid,
                sType,
            )

    async def get_unique_group_db(self):
        """
        Получает список уникальных названий групп из базы данных.

        Returns:
            Список записей с уникальными названиями групп, отсортированных по алфавиту
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT group_name
                FROM users
                WHERE group_name != ''
                ORDER BY group_name
            """
            )
        return rows

    async def get_users_from_group(self, group_name: str):
        """
        Получает пользователей из указанной группы.

        Args:
            group_name: Название группы

        Returns:
            Список записей пользователей с полями tg_userid и allowConfirm
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tg_userid, allowConfirm
                FROM users
                WHERE group_name=$1
            """,
                group_name,
            )
        return rows

    async def get_all_users_from_group(self, group_name: str):
        """
        Возвращает всех пользователей группы
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tg_userid, group_name, allowConfirm, admin_lvl
                FROM users
                WHERE group_name = $1
            """,
                group_name,
            )
        return rows

    async def get_other_group_users(self, group_name: str):
        """
        Получает пользователей из указанной группы с проверкой существования группы.

        Args:
            group_name: Название группы

        Returns:
            Список записей пользователей с полями tg_userid и allowConfirm

        Raises:
            Exception: Если группа не найдена
        """
        async with self.pool.acquire() as conn:
            # Проверяем, что группа существует
            # Проверяем существование группы
            group_exists = await conn.fetchval(
                """
                SELECT EXISTS(SELECT 1 FROM users WHERE group_name = $1)
            """,
                group_name,
            )

            if not group_exists:
                raise Exception(f"Группа {group_name} не найдена")

            # Получаем всех пользователей в указанной группе
            rows = await conn.fetch(
                """
                SELECT tg_userid, allowConfirm
                FROM users
                WHERE group_name = $1
            """,
                group_name,
            )
        return rows

    async def create_user_simple(
        self,
        tg_userid,
        login=None,
        password=None,
        group=None,
        user_agent=None,
    ):
        """
        Создает пользователя с минимальным набором полей.

        Args:
            tg_userid: Telegram ID пользователя
            login: Логин пользователя (опционально)
            password: Пароль пользователя (опционально, будет зашифрован)
            group: Название группы (опционально)
            user_agent: User agent пользователя (опционально)
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                encrypted_password = (
                    self.encrypt_password(password) if password else None
                )

                await conn.execute(
                    """INSERT INTO users (tg_userid, group_name, login, hashed_password, user_agent)
                VALUES ($1, $2, $3, $4, $5)""",
                    tg_userid,
                    group,
                    login,
                    encrypted_password,
                    user_agent,
                )

    async def get_user_agent(self, tg_userid):
        """
        Получает user agent для указанного пользователя.

        Args:
            tg_userid: Telegram ID пользователя

        Returns:
            User agent пользователя или None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT user_agent FROM users WHERE tg_userid=$1""",
                tg_userid,
            )
            return row["user_agent"] if row else None

    async def update_fio(self, tg_userid: int, fio: str):
        """Обновляет ФИО пользователя."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET fio = $1 WHERE tg_userid = $2;
            """,
                fio,
                tg_userid,
            )

    async def get_fio(self, tg_userid: int):
        """Возвращает ФИО пользователя по tg_userid."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT fio FROM users WHERE tg_userid = $1;
            """,
                tg_userid,
            )

    async def get_fio_bulk(self, tg_userids: list):
        """Возвращает ФИО для списка пользователей."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tg_userid, fio FROM users WHERE tg_userid = ANY($1);
            """,
                tg_userids,
            )
            return {row["tg_userid"]: row["fio"] for row in rows}

    # Методы для TOTP секретов (автоматический ввод 2FA)

    async def set_totp_secret(self, tg_userid: int, secret: str):
        """
        Сохраняет TOTP секрет пользователя (зашифрованный).

        Args:
            tg_userid: Telegram ID пользователя
            secret: TOTP секрет в формате base32
        """
        encrypted_secret = self.fernet.encrypt(secret.encode()).decode()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET totp_secret = $1 WHERE tg_userid = $2;
            """,
                encrypted_secret,
                tg_userid,
            )

    async def get_totp_secret(self, tg_userid: int) -> str | None:
        """
        Возвращает расшифрованный TOTP секрет пользователя.

        Args:
            tg_userid: Telegram ID пользователя

        Returns:
            TOTP секрет в формате base32 или None
        """
        async with self.pool.acquire() as conn:
            encrypted_secret = await conn.fetchval(
                """
                SELECT totp_secret FROM users WHERE tg_userid = $1;
            """,
                tg_userid,
            )
            if encrypted_secret:
                return self.fernet.decrypt(encrypted_secret.encode()).decode()
            return None

    async def delete_totp_secret(self, tg_userid: int):
        """
        Удаляет TOTP секрет и credential_id пользователя.

        Args:
            tg_userid: Telegram ID пользователя
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET totp_secret = NULL, totp_credential_id = NULL WHERE tg_userid = $1;
            """,
                tg_userid,
            )

    async def set_totp_credential_id(self, tg_userid: int, credential_id: str):
        """
        Сохраняет credential_id для авто-TOTP.

        Args:
            tg_userid: Telegram ID пользователя
            credential_id: ID credential из Keycloak
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET totp_credential_id = $1 WHERE tg_userid = $2;
            """,
                credential_id,
                tg_userid,
            )

    async def get_totp_credential_id(self, tg_userid: int) -> str | None:
        """
        Возвращает сохранённый credential_id для авто-TOTP.

        Args:
            tg_userid: Telegram ID пользователя

        Returns:
            credential_id или None
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT totp_credential_id FROM users WHERE tg_userid = $1;
            """,
                tg_userid,
            )

    async def has_totp_secret(self, tg_userid: int) -> bool:
        """
        Проверяет, есть ли у пользователя сохранённый TOTP секрет.

        Args:
            tg_userid: Telegram ID пользователя

        Returns:
            True если секрет есть
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT totp_secret IS NOT NULL FROM users WHERE tg_userid = $1;
            """,
                tg_userid,
            )
            return bool(result)

    async def get_count_us(self):
        """
        Получает общее количество пользователей в базе данных.

        Returns:
            Количество пользователей
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*) FROM users
                """
            )

    async def getter_us(self, tg_userid: int, offset: int, group_name: str = None):
        """
        Получает список пользователей с пагинацией (требуется admin_lvl >= 3).

        Args:
            tg_userid: Telegram ID администратора
            offset: Смещение для пагинации
            group_name: Фильтр по названию группы (опционально)

        Returns:
            Список записей пользователей (максимум 24)

        Raises:
            AssertionError: Если недостаточно прав
        """
        async with self.pool.acquire() as conn:
            assert (
                await conn.fetchval(
                    """SELECT admin_lvl FROM users WHERE tg_userid=$1""", tg_userid
                )
                >= ADMIN_LEVEL_SUPER
            ), "Не достаточно прав"

            if group_name is not None:
                return await conn.fetch(
                    """
                    SELECT tg_userid, login, group_name, admin_lvl
                    FROM users
                    WHERE group_name=$1
                    LIMIT 24
                    OFFSET $2
                """,
                    group_name,
                    offset,
                )

            return await conn.fetch(
                """
            SELECT tg_userid, login, group_name, admin_lvl
            FROM users
            ORDER BY group_name
            LIMIT 24
            OFFSET $1
            """,
                offset,
            )

    async def get_admin(self, tg_userid: int):
        """
        Получает список всех администраторов (требуется admin_lvl >= 1).

        Args:
            tg_userid: Telegram ID пользователя

        Returns:
            Список записей администраторов с полями tg_userid, login, group_name, admin_lvl

        Raises:
            AssertionError: Если недостаточно прав
        """
        async with self.pool.acquire() as conn:
            assert (
                await conn.fetchval(
                    """SELECT admin_lvl FROM users WHERE tg_userid=$1""", tg_userid
                )
                >= ADMIN_LEVEL_BASIC
            ), "Не достаточно прав"
            return await conn.fetch(
                """
                SELECT tg_userid, login, group_name, admin_lvl FROM users WHERE admin_lvl > 0
            """
            )

    async def delete_user_by_admin(self, admin_tg_userid: int, target_tg_userid: int):
        """Удаление пользователя администратором (требуется admin_lvl >= ADMIN_LEVEL_SUPER)"""
        async with self.pool.acquire() as conn:
            admin_lvl = await conn.fetchval(
                """SELECT admin_lvl FROM users WHERE tg_userid=$1""", admin_tg_userid
            )
            if admin_lvl is None or admin_lvl < ADMIN_LEVEL_SUPER:
                raise Exception("Недостаточно прав для удаления пользователей")

            # Проверяем что целевой пользователь существует
            target_exists = await conn.fetchval(
                """SELECT 1 FROM users WHERE tg_userid=$1""", target_tg_userid
            )
            if not target_exists:
                raise Exception("Пользователь не найден")

            # Нельзя удалить себя
            if admin_tg_userid == target_tg_userid:
                raise Exception("Нельзя удалить свой аккаунт через админ-панель")

            # Удаляем связанные данные
            await conn.execute(
                """DELETE FROM cookies WHERE tg_userid = $1""", target_tg_userid
            )
            await conn.execute(
                """DELETE FROM status WHERE tg_userid = $1""", target_tg_userid
            )
            await conn.execute(
                """DELETE FROM approved WHERE tg_userid = $1""", target_tg_userid
            )
            await conn.execute(
                """DELETE FROM users WHERE tg_userid = $1""", target_tg_userid
            )
            return True

    async def set_admin_level(
        self, admin_tg_userid: int, target_tg_userid: int, new_level: int
    ):
        """Изменение уровня админа (требуется admin_lvl >= ADMIN_LEVEL_SUPER)"""
        async with self.pool.acquire() as conn:
            admin_lvl = await conn.fetchval(
                """SELECT admin_lvl FROM users WHERE tg_userid=$1""", admin_tg_userid
            )
            if admin_lvl is None or admin_lvl < ADMIN_LEVEL_SUPER:
                raise Exception("Недостаточно прав для изменения уровня админа")

            # Проверяем целевого пользователя
            target_row = await conn.fetchrow(
                """SELECT admin_lvl FROM users WHERE tg_userid=$1""", target_tg_userid
            )
            if not target_row:
                raise Exception("Пользователь не найден")

            target_current_lvl = target_row["admin_lvl"]

            # Нельзя изменить уровень пользователя с большим или равным уровнем (кроме себя)
            if target_current_lvl >= admin_lvl and admin_tg_userid != target_tg_userid:
                raise Exception(
                    "Нельзя изменить уровень администратора с равным или большим уровнем"
                )

            # Нельзя установить уровень выше своего
            if new_level > admin_lvl:
                raise Exception("Нельзя установить уровень выше своего")

            # Ограничение уровня (0-5)
            new_level = max(0, min(5, new_level))

            await conn.execute(
                """UPDATE users SET admin_lvl = $1 WHERE tg_userid = $2""",
                new_level,
                target_tg_userid,
            )
            return True

    async def search_users(
        self, admin_tg_userid: int, query: str, offset: int = 0, limit: int = 20
    ):
        """Поиск пользователей по логину, группе или ID (требуется admin_lvl >= ADMIN_LEVEL_MODERATE)"""
        async with self.pool.acquire() as conn:
            admin_lvl = await conn.fetchval(
                """SELECT admin_lvl FROM users WHERE tg_userid=$1""", admin_tg_userid
            )
            if admin_lvl is None or admin_lvl < ADMIN_LEVEL_MODERATE:
                raise Exception("Недостаточно прав для поиска пользователей")

            search_pattern = f"%{query}%"

            # Пробуем искать по числовому ID тоже
            try:
                tg_id_search = int(query)
                rows = await conn.fetch(
                    """
                    SELECT tg_userid, login, group_name, admin_lvl, fio
                    FROM users
                    WHERE login ILIKE $1
                       OR group_name ILIKE $1
                       OR fio ILIKE $1
                       OR tg_userid = $4
                    ORDER BY group_name, login
                    LIMIT $2 OFFSET $3
                """,
                    search_pattern,
                    limit,
                    offset,
                    tg_id_search,
                )
            except ValueError:
                rows = await conn.fetch(
                    """
                    SELECT tg_userid, login, group_name, admin_lvl, fio
                    FROM users
                    WHERE login ILIKE $1
                       OR group_name ILIKE $1
                       OR fio ILIKE $1
                    ORDER BY group_name, login
                    LIMIT $2 OFFSET $3
                """,
                    search_pattern,
                    limit,
                    offset,
                )

            return [dict(row) for row in rows]

    async def get_admin_stats(self, admin_tg_userid: int):
        """Получить статистику для админ-панели (требуется admin_lvl >= ADMIN_LEVEL_BASIC)"""
        async with self.pool.acquire() as conn:
            admin_lvl = await conn.fetchval(
                """SELECT admin_lvl FROM users WHERE tg_userid=$1""", admin_tg_userid
            )
            if admin_lvl is None or admin_lvl < ADMIN_LEVEL_BASIC:
                raise Exception("Недостаточно прав")

            total_users = await conn.fetchval("""SELECT COUNT(*) FROM users""")
            total_groups = await conn.fetchval(
                """SELECT COUNT(DISTINCT group_name) FROM users WHERE group_name IS NOT NULL AND group_name != ''"""
            )
            total_admins = await conn.fetchval(
                """SELECT COUNT(*) FROM users WHERE admin_lvl > 0"""
            )
            users_with_login = await conn.fetchval(
                """SELECT COUNT(*) FROM users WHERE login IS NOT NULL AND login != ''"""
            )

            return {
                "total_users": total_users,
                "total_groups": total_groups,
                "total_admins": total_admins,
                "users_with_login": users_with_login,
            }

    # Методы для таблицы external_auth_tokens

    async def create_external_token(
        self, token: str, expires_at, service_name: str = None
    ):
        """
        Создает новый токен для внешней авторизации.
        Статус по умолчанию 'pending'.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO external_auth_tokens (token, expires_at, service_name)
                VALUES ($1, $2, $3)
            """,
                token,
                expires_at,
                service_name,
            )

    async def get_external_token(self, token: str):
        """
        Возвращает информацию о токене.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT token, tg_userid, status, created_at, expires_at, service_name
                FROM external_auth_tokens
                WHERE token = $1
            """,
                token,
            )
            return dict(row) if row else None

    async def approve_external_token(self, token: str, tg_userid: int):
        """
        Подтверждает токен, связывая его с tg_userid и меняя статус на 'approved'.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE external_auth_tokens
                SET tg_userid = $1, status = 'approved'
                WHERE token = $2 AND status = 'pending'
            """,
                tg_userid,
                token,
            )

    async def reject_external_token(self, token: str):
        """
        Отклоняет токен, меняя статус на 'rejected'.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE external_auth_tokens
                SET status = 'rejected'
                WHERE token = $1 AND status = 'pending'
            """,
                token,
            )

    async def delete_expired_tokens(self):
        """
        Удаляет истекшие токены.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM external_auth_tokens
                WHERE expires_at < NOW()
            """
            )

    # Методы для таблицы nfc_cards

    async def create_nfc_card(
        self,
        card_id: int,
        name: str,
        owner_group: str,
        added_by: int,
        tg_userid: int = None,
    ):
        """
        Добавляет NFC карту в базу данных.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO nfc_cards (card_id, tg_userid, name, owner_group, added_by)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (card_id, owner_group) DO UPDATE SET
                    tg_userid = EXCLUDED.tg_userid,
                    name = EXCLUDED.name
            """,
                card_id,
                tg_userid,
                name,
                owner_group,
                added_by,
            )

    async def get_nfc_cards_by_group(self, owner_group: str):
        """
        Возвращает все NFC карты группы.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, card_id, tg_userid, name, owner_group, added_by, created_at
                FROM nfc_cards
                WHERE owner_group = $1
                ORDER BY created_at DESC
            """,
                owner_group,
            )
            return [dict(row) for row in rows]

    async def get_nfc_card_by_id(self, card_id: int, owner_group: str):
        """
        Возвращает NFC карту по card_id и группе.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, card_id, tg_userid, name, owner_group, added_by, created_at
                FROM nfc_cards
                WHERE card_id = $1 AND owner_group = $2
            """,
                card_id,
                owner_group,
            )
            return dict(row) if row else None

    async def delete_nfc_card(self, card_id: int, owner_group: str):
        """
        Удаляет NFC карту.
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM nfc_cards
                WHERE card_id = $1 AND owner_group = $2
            """,
                card_id,
                owner_group,
            )
            return "DELETE 1" in result

    async def get_users_in_group_for_nfc(self, group_name: str):
        """
        Возвращает список пользователей группы для выбора при добавлении NFC карты.
        Включает флаг needs_totp если у пользователя есть активная 2FA сессия.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.tg_userid, u.fio, u.login,
                       (EXISTS(
                           SELECT 1 FROM totp_sessions ts
                           WHERE ts.tg_userid = u.tg_userid AND ts.expires_at > NOW()
                       )) AS needs_totp
                FROM users u
                WHERE u.group_name = $1
            """,
                group_name,
            )
            return [dict(row) for row in rows]

    # Методы для таблицы totp_sessions (2FA)

    async def create_totp_session(
        self,
        tg_userid: int,
        session_cookies: str,
        otp_action_url: str,
        credential_id: str,
        user_agent: str = None,
        source: str = "login",
        expires_minutes: int = 5,
        otp_credentials: str = None,
    ) -> int:
        """
        Создает новую 2FA сессию.

        Args:
            tg_userid: Telegram ID пользователя
            session_cookies: JSON строка с cookies сессии Keycloak
            otp_action_url: URL для отправки OTP кода
            credential_id: ID credential из формы Keycloak
            user_agent: User-Agent для запросов
            source: Источник запроса ('login' или 'refresh')
            expires_minutes: Время жизни сессии в минутах
            otp_credentials: JSON строка со списком доступных 2FA методов

        Returns:
            ID созданной сессии
        """
        async with self.pool.acquire() as conn:
            # Сохраняем last_notification_sent перед удалением старых сессий
            old_notification = await conn.fetchval(
                """
                SELECT last_notification_sent
                FROM totp_sessions
                WHERE tg_userid = $1 AND last_notification_sent IS NOT NULL
                ORDER BY last_notification_sent DESC
                LIMIT 1
                """,
                tg_userid,
            )

            # Удаляем старые сессии для этого пользователя
            await conn.execute(
                """DELETE FROM totp_sessions WHERE tg_userid = $1""",
                tg_userid,
            )

            session_id = await conn.fetchval(
                """
                INSERT INTO totp_sessions
                    (tg_userid, session_cookies, otp_action_url, credential_id, user_agent, source, expires_at, last_notification_sent, otp_credentials)
                VALUES ($1, $2, $3, $4, $5, $6, NOW() + INTERVAL '1 minute' * $7, $8, $9)
                RETURNING id
            """,
                tg_userid,
                session_cookies,
                otp_action_url,
                credential_id,
                user_agent,
                source,
                expires_minutes,
                old_notification,
                otp_credentials,
            )
            return session_id

    async def get_totp_session(self, tg_userid: int):
        """
        Возвращает активную 2FA сессию для пользователя.

        Args:
            tg_userid: Telegram ID пользователя

        Returns:
            dict с данными сессии или None если сессия не найдена/истекла
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, tg_userid, session_cookies, otp_action_url,
                       credential_id, user_agent, source, created_at, expires_at, otp_credentials
                FROM totp_sessions
                WHERE tg_userid = $1 AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
            """,
                tg_userid,
            )
            return dict(row) if row else None

    async def update_totp_session(
        self,
        tg_userid: int,
        session_cookies: str,
        otp_action_url: str,
        credential_id: str,
    ):
        """
        Обновляет данные 2FA сессии (после неверного OTP кода).

        Args:
            tg_userid: Telegram ID пользователя
            session_cookies: Новые cookies сессии
            otp_action_url: Новый URL для OTP
            credential_id: Новый credential ID
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE totp_sessions
                SET session_cookies = $2,
                    otp_action_url = $3,
                    credential_id = $4
                WHERE tg_userid = $1 AND expires_at > NOW()
            """,
                tg_userid,
                session_cookies,
                otp_action_url,
                credential_id,
            )

    async def update_totp_session_credential(self, tg_userid: int, credential_id: str):
        """
        Обновляет только credential_id в 2FA сессии.

        Args:
            tg_userid: Telegram ID пользователя
            credential_id: Новый credential ID
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE totp_sessions
                SET credential_id = $2
                WHERE tg_userid = $1 AND expires_at > NOW()
            """,
                tg_userid,
                credential_id,
            )

    async def delete_totp_session(self, tg_userid: int):
        """
        Удаляет 2FA сессию пользователя.

        Args:
            tg_userid: Telegram ID пользователя
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """DELETE FROM totp_sessions WHERE tg_userid = $1""",
                tg_userid,
            )

    async def cleanup_expired_totp_sessions(self):
        """Удаляет все истекшие 2FA сессии."""
        async with self.pool.acquire() as conn:
            await conn.execute("""DELETE FROM totp_sessions WHERE expires_at < NOW()""")

    async def can_send_2fa_notification(self, tg_userid: int) -> bool:
        """
        Проверяет, можно ли отправить уведомление о 2FA.
        Возвращает True если уведомление не отправлялось сегодня.

        Args:
            tg_userid: Telegram ID пользователя

        Returns:
            True если можно отправить уведомление
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT last_notification_sent
                FROM totp_sessions
                WHERE tg_userid = $1 AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
            """,
                tg_userid,
            )

            if not row or row["last_notification_sent"] is None:
                return True

            # Проверяем, было ли уведомление отправлено сегодня (в течение 24 часов)
            from datetime import datetime, timezone

            last_sent = row["last_notification_sent"]
            now = datetime.now(timezone.utc)

            # Если прошло больше 24 часов, можно отправить снова
            time_diff = now - last_sent
            return time_diff.total_seconds() > 24 * 60 * 60

    async def mark_2fa_notification_sent(self, tg_userid: int):
        """
        Отмечает, что уведомление о 2FA было отправлено.

        Args:
            tg_userid: Telegram ID пользователя
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE totp_sessions
                SET last_notification_sent = NOW()
                WHERE tg_userid = $1 AND expires_at > NOW()
            """,
                tg_userid,
            )

    # Методы для таблицы audit_logs

    async def create_audit_log(
        self,
        admin_tg_userid: int,
        action_type: str,
        target_type: str = None,
        target_id: str = None,
        old_value: dict = None,
        new_value: dict = None,
        ip_address: str = None,
        user_agent: str = None,
    ) -> int:
        """
        Создаёт запись в таблице audit_logs.

        Args:
            admin_tg_userid: Telegram ID администратора
            action_type: Тип действия (delete_user, set_admin, bulk_delete, etc.)
            target_type: Тип объекта (user, nfc_card, etc.)
            target_id: ID объекта
            old_value: Предыдущее значение (JSONB)
            new_value: Новое значение (JSONB)
            ip_address: IP адрес
            user_agent: User Agent

        Returns:
            ID созданной записи
        """
        import json

        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO audit_logs (admin_tg_userid, action_type, target_type, target_id, old_value, new_value, ip_address, user_agent)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """,
                admin_tg_userid,
                action_type,
                target_type,
                target_id,
                json.dumps(old_value) if old_value else None,
                json.dumps(new_value) if new_value else None,
                ip_address,
                user_agent,
            )

    async def get_audit_logs(
        self,
        admin_tg_userid: int = None,
        action_type: str = None,
        target_type: str = None,
        offset: int = 0,
        limit: int = 50,
        date_from=None,
        date_to=None,
    ):
        """
        Получает записи из таблицы audit_logs с фильтрацией.

        Args:
            admin_tg_userid: Фильтр по администратору
            action_type: Фильтр по типу действия
            target_type: Фильтр по типу объекта
            offset: Смещение
            limit: Лимит записей
            date_from: Дата начала периода
            date_to: Дата конца периода

        Returns:
            Список записей аудита
        """
        query = """
            SELECT id, admin_tg_userid, action_type, target_type, target_id,
                   old_value, new_value, ip_address, user_agent, created_at
            FROM audit_logs
            WHERE 1=1
        """
        params = []
        idx = 1

        if admin_tg_userid:
            query += f" AND admin_tg_userid = ${idx}"
            params.append(admin_tg_userid)
            idx += 1

        if action_type:
            query += f" AND action_type = ${idx}"
            params.append(action_type)
            idx += 1

        if target_type:
            query += f" AND target_type = ${idx}"
            params.append(target_type)
            idx += 1

        if date_from:
            query += f" AND created_at >= ${idx}"
            params.append(date_from)
            idx += 1

        if date_to:
            query += f" AND created_at <= ${idx}"
            params.append(date_to)
            idx += 1

        query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
        params.extend([limit, offset])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def get_audit_logs_count(
        self,
        admin_tg_userid: int = None,
        action_type: str = None,
        target_type: str = None,
        date_from=None,
        date_to=None,
    ) -> int:
        """Получает количество записей аудита с учётом фильтров."""
        query = "SELECT COUNT(*) FROM audit_logs WHERE 1=1"
        params = []
        idx = 1

        if admin_tg_userid:
            query += f" AND admin_tg_userid = ${idx}"
            params.append(admin_tg_userid)
            idx += 1

        if action_type:
            query += f" AND action_type = ${idx}"
            params.append(action_type)
            idx += 1

        if target_type:
            query += f" AND target_type = ${idx}"
            params.append(target_type)
            idx += 1

        if date_from:
            query += f" AND created_at >= ${idx}"
            params.append(date_from)
            idx += 1

        if date_to:
            query += f" AND created_at <= ${idx}"
            params.append(date_to)
            idx += 1

        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *params)

    # Методы для таблицы user_action_logs

    async def create_user_action_log(
        self,
        actor_tg_userid: int,
        action_type: str,
        target_tg_userid: int = None,
        details: dict = None,
        status: str = "success",
    ) -> int:
        """
        Создаёт запись в таблице user_action_logs.

        Args:
            actor_tg_userid: Telegram ID пользователя, выполнившего действие
            action_type: Тип действия (mark_self, mark_other, external_auth, login, etc.)
            target_tg_userid: Telegram ID целевого пользователя (для mark_other)
            details: Дополнительные детали (JSONB)
            status: Статус выполнения (success, failure)

        Returns:
            ID созданной записи
        """
        import json

        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO user_action_logs (actor_tg_userid, action_type, target_tg_userid, details, status)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """,
                actor_tg_userid,
                action_type,
                target_tg_userid,
                json.dumps(details) if details else None,
                status,
            )

    async def get_user_action_logs(
        self,
        actor_tg_userid: int = None,
        target_tg_userid: int = None,
        action_type: str = None,
        status: str = None,
        offset: int = 0,
        limit: int = 50,
        date_from=None,
        date_to=None,
    ):
        """
        Получает записи из таблицы user_action_logs с фильтрацией.

        Returns:
            Список записей действий пользователей
        """
        query = """
            SELECT id, actor_tg_userid, action_type, target_tg_userid,
                   details, status, created_at
            FROM user_action_logs
            WHERE 1=1
        """
        params = []
        idx = 1

        if actor_tg_userid:
            query += f" AND actor_tg_userid = ${idx}"
            params.append(actor_tg_userid)
            idx += 1

        if target_tg_userid:
            query += f" AND target_tg_userid = ${idx}"
            params.append(target_tg_userid)
            idx += 1

        if action_type:
            query += f" AND action_type = ${idx}"
            params.append(action_type)
            idx += 1

        if status:
            query += f" AND status = ${idx}"
            params.append(status)
            idx += 1

        if date_from:
            query += f" AND created_at >= ${idx}"
            params.append(date_from)
            idx += 1

        if date_to:
            query += f" AND created_at <= ${idx}"
            params.append(date_to)
            idx += 1

        query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
        params.extend([limit, offset])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def get_user_action_logs_count(
        self,
        actor_tg_userid: int = None,
        target_tg_userid: int = None,
        action_type: str = None,
        status: str = None,
        date_from=None,
        date_to=None,
    ) -> int:
        """Получает количество записей действий с учётом фильтров."""
        query = "SELECT COUNT(*) FROM user_action_logs WHERE 1=1"
        params = []
        idx = 1

        if actor_tg_userid:
            query += f" AND actor_tg_userid = ${idx}"
            params.append(actor_tg_userid)
            idx += 1

        if target_tg_userid:
            query += f" AND target_tg_userid = ${idx}"
            params.append(target_tg_userid)
            idx += 1

        if action_type:
            query += f" AND action_type = ${idx}"
            params.append(action_type)
            idx += 1

        if status:
            query += f" AND status = ${idx}"
            params.append(status)
            idx += 1

        if date_from:
            query += f" AND created_at >= ${idx}"
            params.append(date_from)
            idx += 1

        if date_to:
            query += f" AND created_at <= ${idx}"
            params.append(date_to)
            idx += 1

        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *params)

    async def get_user_action_logs_stats(self) -> dict:
        """
        Получить статистику действий пользователей за сегодня.

        Returns:
            dict с total_today, success_rate, unique_users
        """
        async with self.pool.acquire() as conn:
            # Всего за сегодня
            total_today = await conn.fetchval(
                """
                SELECT COUNT(*) FROM user_action_logs
                WHERE created_at >= CURRENT_DATE
                """
            )

            # Процент успешных
            success_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM user_action_logs
                WHERE created_at >= CURRENT_DATE AND status = 'success'
                """
            )

            success_rate = 0
            if total_today and total_today > 0:
                success_rate = round((success_count / total_today) * 100)

            # Уникальных пользователей за сегодня
            unique_users = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT actor_tg_userid) FROM user_action_logs
                WHERE created_at >= CURRENT_DATE
                """
            )

            return {
                "total_today": total_today or 0,
                "success_rate": success_rate,
                "unique_users": unique_users or 0,
            }

    # Методы для bulk operations

    async def bulk_delete_users(
        self, admin_tg_userid: int, target_tg_userids: list
    ) -> dict:
        """
        Массовое удаление пользователей.

        Args:
            admin_tg_userid: Telegram ID администратора
            target_tg_userids: Список ID пользователей для удаления

        Returns:
            dict с результатами: deleted, failed, errors
        """
        async with self.pool.acquire() as conn:
            admin_lvl = await conn.fetchval(
                """SELECT admin_lvl FROM users WHERE tg_userid=$1""", admin_tg_userid
            )
            if admin_lvl is None or admin_lvl < ADMIN_LEVEL_SUPER:
                raise Exception("Недостаточно прав для удаления пользователей")

            deleted = []
            failed = []
            errors = []

            for target_id in target_tg_userids:
                try:
                    # Нельзя удалить себя
                    if admin_tg_userid == target_id:
                        failed.append(target_id)
                        errors.append(f"{target_id}: Нельзя удалить свой аккаунт")
                        continue

                    # Проверяем существование
                    target_exists = await conn.fetchval(
                        """SELECT 1 FROM users WHERE tg_userid=$1""", target_id
                    )
                    if not target_exists:
                        failed.append(target_id)
                        errors.append(f"{target_id}: Пользователь не найден")
                        continue

                    # Удаляем связанные данные
                    await conn.execute(
                        """DELETE FROM cookies WHERE tg_userid = $1""", target_id
                    )
                    await conn.execute(
                        """DELETE FROM status WHERE tg_userid = $1""", target_id
                    )
                    await conn.execute(
                        """DELETE FROM approved WHERE tg_userid = $1""", target_id
                    )
                    await conn.execute(
                        """DELETE FROM users WHERE tg_userid = $1""", target_id
                    )
                    deleted.append(target_id)
                except Exception as e:
                    failed.append(target_id)
                    errors.append(f"{target_id}: {str(e)}")

            return {"deleted": deleted, "failed": failed, "errors": errors}

    async def bulk_edit_users(
        self, admin_tg_userid: int, target_tg_userids: list, updates: dict
    ) -> dict:
        """
        Массовое редактирование пользователей.

        Args:
            admin_tg_userid: Telegram ID администратора
            target_tg_userids: Список ID пользователей для редактирования
            updates: Словарь с полями для обновления (allowConfirm, admin_lvl, group_name)

        Returns:
            dict с результатами: updated, failed, errors
        """
        async with self.pool.acquire() as conn:
            admin_lvl = await conn.fetchval(
                """SELECT admin_lvl FROM users WHERE tg_userid=$1""", admin_tg_userid
            )
            if admin_lvl is None or admin_lvl < ADMIN_LEVEL_SUPER:
                raise Exception("Недостаточно прав")

            updated = []
            failed = []
            errors = []

            # Проверяем, что не пытаемся установить уровень выше своего
            if "admin_lvl" in updates and updates["admin_lvl"] > admin_lvl:
                raise Exception("Нельзя установить уровень выше своего")

            for target_id in target_tg_userids:
                try:
                    target_exists = await conn.fetchval(
                        """SELECT 1 FROM users WHERE tg_userid=$1""", target_id
                    )
                    if not target_exists:
                        failed.append(target_id)
                        errors.append(f"{target_id}: Пользователь не найден")
                        continue

                    # Строим UPDATE запрос
                    set_parts = []
                    values = []
                    idx = 1

                    if "allowConfirm" in updates:
                        set_parts.append(f"allowConfirm = ${idx}")
                        values.append(updates["allowConfirm"])
                        idx += 1

                    if "admin_lvl" in updates:
                        set_parts.append(f"admin_lvl = ${idx}")
                        values.append(updates["admin_lvl"])
                        idx += 1

                    if "group_name" in updates:
                        set_parts.append(f"group_name = ${idx}")
                        values.append(updates["group_name"])
                        idx += 1

                    if set_parts:
                        query = f"UPDATE users SET {', '.join(set_parts)} WHERE tg_userid = ${idx}"
                        values.append(target_id)
                        await conn.execute(query, *values)
                        updated.append(target_id)
                    else:
                        failed.append(target_id)
                        errors.append(f"{target_id}: Нет полей для обновления")

                except Exception as e:
                    failed.append(target_id)
                    errors.append(f"{target_id}: {str(e)}")

            return {"updated": updated, "failed": failed, "errors": errors}

    async def get_all_users_for_export(self, admin_tg_userid: int) -> list:
        """
        Получает всех пользователей для экспорта.

        Args:
            admin_tg_userid: Telegram ID администратора

        Returns:
            Список всех пользователей
        """
        async with self.pool.acquire() as conn:
            admin_lvl = await conn.fetchval(
                """SELECT admin_lvl FROM users WHERE tg_userid=$1""", admin_tg_userid
            )
            if admin_lvl is None or admin_lvl < ADMIN_LEVEL_SUPER:
                raise Exception("Недостаточно прав для экспорта")

            rows = await conn.fetch(
                """
                SELECT tg_userid, group_name, login, allowConfirm, admin_lvl, fio
                FROM users
                ORDER BY group_name, login
            """
            )
            return [dict(row) for row in rows]

    async def get_analytics_data(self, admin_tg_userid: int, days: int = 30) -> dict:
        """
        Получает данные для аналитического дашборда.

        Args:
            admin_tg_userid: Telegram ID администратора
            days: Количество дней для анализа

        Returns:
            dict с аналитическими данными
        """
        async with self.pool.acquire() as conn:
            admin_lvl = await conn.fetchval(
                """SELECT admin_lvl FROM users WHERE tg_userid=$1""", admin_tg_userid
            )
            if admin_lvl is None or admin_lvl < ADMIN_LEVEL_BASIC:
                raise Exception("Недостаточно прав")

            # Общая статистика
            total_users = await conn.fetchval("""SELECT COUNT(*) FROM users""")
            total_groups = await conn.fetchval(
                """SELECT COUNT(DISTINCT group_name) FROM users WHERE group_name IS NOT NULL AND group_name != ''"""
            )
            total_admins = await conn.fetchval(
                """SELECT COUNT(*) FROM users WHERE admin_lvl > 0"""
            )
            users_with_login = await conn.fetchval(
                """SELECT COUNT(*) FROM users WHERE login IS NOT NULL AND login != ''"""
            )

            # Активность по дням (из user_action_logs)
            activity_by_day = await conn.fetch(
                """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM user_action_logs
                WHERE created_at >= NOW() - INTERVAL '1 day' * $1
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """,
                days,
            )

            # Топ групп по количеству пользователей
            top_groups = await conn.fetch(
                """
                SELECT group_name, COUNT(*) as user_count
                FROM users
                WHERE group_name IS NOT NULL AND group_name != ''
                GROUP BY group_name
                ORDER BY user_count DESC
                LIMIT 10
            """
            )

            # Статистика по типам действий
            actions_stats = await conn.fetch(
                """
                SELECT action_type, COUNT(*) as count
                FROM user_action_logs
                WHERE created_at >= NOW() - INTERVAL '1 day' * $1
                GROUP BY action_type
                ORDER BY count DESC
            """,
                days,
            )

            # Статистика ошибок
            error_stats = await conn.fetch(
                """
                SELECT action_type, COUNT(*) as count
                FROM user_action_logs
                WHERE status = 'failure' AND created_at >= NOW() - INTERVAL '1 day' * $1
                GROUP BY action_type
                ORDER BY count DESC
            """,
                days,
            )

            return {
                "total_users": total_users,
                "total_groups": total_groups,
                "total_admins": total_admins,
                "users_with_login": users_with_login,
                "activity_by_day": [dict(row) for row in activity_by_day],
                "top_groups": [dict(row) for row in top_groups],
                "actions_stats": [dict(row) for row in actions_stats],
                "error_stats": [dict(row) for row in error_stats],
            }

    async def check_connection(self) -> bool:
        """Проверяет соединение с базой данных."""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False
