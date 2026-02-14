import logging
import random
import re
from dataclasses import dataclass
from typing import List, Optional, Union
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from backend.database import DBModel

logger = logging.getLogger(__name__)

COOKIE_FILENAME = "cookies.json"


@dataclass
class TwoFactorRequired:
    """Результат, когда требуется двухфакторная аутентификация."""

    session_cookies: dict
    otp_action_url: str
    credential_id: str
    message: str = "Требуется ввод TOTP кода"
    otp_credentials: List[dict] = None  # Список доступных 2FA методов


@dataclass
class CookiesResult:
    """Успешный результат получения cookies."""

    cookies: List[dict]


@dataclass
class AuthError:
    """Ошибка авторизации."""

    message: str


def generate_random_mobile_user_agent() -> str:
    """
    Генерирует случайный User-Agent мобильного устройства.

    Возвращает:
    str: Строка User-Agent для мобильного браузера.
    """
    # Список популярных мобильных браузеров
    mobile_browsers = [
        # Android browsers
        "Mozilla/5.0 (Linux; Android {android_ver}; {device}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Mobile Safari/537.36",
        "Mozilla/5.0 (Android {android_ver}; Mobile; rv:{firefox_ver}) Gecko/{gecko_ver} Firefox/{firefox_ver}",
        "Mozilla/5.0 (Linux; Android {android_ver}; {device}) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/{samsung_ver} Chrome/{chrome_ver} Mobile Safari/537.36",
        # iOS browsers
        "Mozilla/5.0 (iPhone; CPU iPhone OS {ios_ver} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_ver} Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS {ios_ver} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/{chrome_ver} Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS {ios_ver} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/{firefox_ver} Mobile/15E148 Safari/605.1.15",
    ]

    # Популярные Android устройства
    android_devices = [
        "SM-G991B",
        "SM-A526B",
        "SM-S901U",
        "Pixel 7",
        "Pixel 6a",
        "Redmi Note 10 Pro",
        "OnePlus 9",
        "Xiaomi 12",
        "Moto G Power",
        "SAMSUNG SM-A515F",
    ]

    # Версии
    android_versions = ["10", "11", "12", "13", "14"]
    ios_versions = ["15_6", "16_0", "16_5", "17_0", "17_3"]
    chrome_versions = [
        "110.0.5481.153",
        "112.0.5615.48",
        "114.0.5735.90",
        "116.0.5845.92",
        "118.0.5993.89",
    ]
    firefox_versions = ["110.1", "111.0", "112.1", "113.0", "114.2"]
    safari_versions = ["15.6", "16.0", "16.5", "17.0", "17.3"]
    samsung_versions = ["17.0", "18.0", "19.0", "20.0", "21.0"]
    gecko_versions = ["20100101", "20220227", "20230812"]

    # Выбираем случайный шаблон UA
    ua_template = random.choice(mobile_browsers)

    # Заполняем шаблон случайными значениями
    if "Android" in ua_template:
        android_ver = random.choice(android_versions)
        device = random.choice(android_devices)
        chrome_ver = random.choice(chrome_versions)
        firefox_ver = random.choice(firefox_versions)
        gecko_ver = random.choice(gecko_versions)
        samsung_ver = random.choice(samsung_versions)

        ua = ua_template.format(
            android_ver=android_ver,
            device=device,
            chrome_ver=chrome_ver,
            firefox_ver=firefox_ver,
            gecko_ver=gecko_ver,
            samsung_ver=samsung_ver,
        )
    else:  # iOS
        ios_ver = random.choice(ios_versions)
        safari_ver = random.choice(safari_versions)
        chrome_ver = random.choice(chrome_versions)
        firefox_ver = random.choice(firefox_versions)

        ua = ua_template.format(
            ios_ver=ios_ver,
            safari_ver=safari_ver,
            chrome_ver=chrome_ver,
            firefox_ver=firefox_ver,
        )

    return ua


def _extract_session_cookies(session) -> dict:
    """Извлекает cookies из сессии в виде словаря."""
    cookies = {}
    for domain, domain_cookies in session.cookie_jar._cookies.items():
        for cookie_name, morsel in domain_cookies.items():
            cookies[morsel.key] = {
                "value": morsel.value,
                "domain": domain,
                "path": morsel.get("path", "/"),
            }
    return cookies


def _extract_cookies_list(session) -> list:
    """Извлекает cookies из сессии в виде списка словарей."""
    cookies = []
    for domain, domain_cookies in session.cookie_jar._cookies.items():
        for cookie_name, morsel in domain_cookies.items():
            cookie = {
                "name": morsel.key,
                "value": morsel.value,
                "domain": domain,
                "path": morsel.get("path", "/"),
                "secure": morsel.get("secure", False),
            }
            if morsel.get("expires"):
                cookie["expiry"] = morsel.get("expires")
            cookies.append(cookie)
    return cookies


def _is_otp_page(page_text: str) -> bool:
    """Проверяет, является ли страница формой ввода OTP кода."""
    # Keycloak OTP страница содержит поле otp и специфичные маркеры
    return (
        '"otpLogin"' in page_text
        or 'name="otp"' in page_text
        or "selectedCredentialId" in page_text
        or "totp" in page_text.lower()
    )


def _extract_otp_form_data(page_text: str, current_url: str) -> Optional[dict]:
    """Извлекает данные формы OTP из страницы Keycloak."""
    logger.info(f"Extracting OTP form data, page length: {len(page_text)}")

    otp_action_url = None

    # Способ 1: Ищем loginAction URL в kcContext.url.loginAction (новый Keycloak с React)
    login_action_match = re.search(r'"loginAction":\s*"([^"]*)"', page_text)
    if login_action_match:
        otp_action_url = login_action_match.group(1).encode().decode("unicode-escape")
        logger.info(f"Found loginAction URL: {otp_action_url}")

    # Способ 2: Ищем форму напрямую в HTML
    if not otp_action_url:
        soup = BeautifulSoup(page_text, "html.parser")
        form = soup.find("form", id="kc-otp-login-form") or soup.find("form")
        if form and form.get("action"):
            otp_action_url = form["action"].replace("&amp;", "&")
            logger.info(f"Found form action: {otp_action_url}")
            if not otp_action_url.startswith("http"):
                parsed = urlparse(current_url)
                otp_action_url = f"{parsed.scheme}://{parsed.netloc}{otp_action_url}"

    if not otp_action_url:
        logger.error(f"No OTP action URL found. Page preview: {page_text[:3000]}")
        return None

    # Извлекаем список всех доступных credentials
    otp_credentials = []
    credentials_match = re.search(
        r'"userOtpCredentials":\s*\[(.*?)\]', page_text, re.DOTALL
    )
    if credentials_match:
        credentials_json = credentials_match.group(1)
        # Парсим каждый credential
        for cred_match in re.finditer(
            r'\{\s*[^}]*"userLabel":\s*"([^"]*)"[^}]*"id":\s*"([^"]*)"[^}]*\}|'
            r'\{\s*[^}]*"id":\s*"([^"]*)"[^}]*"userLabel":\s*"([^"]*)"[^}]*\}',
            credentials_json
        ):
            if cred_match.group(1) and cred_match.group(2):
                otp_credentials.append({
                    "userLabel": cred_match.group(1),
                    "id": cred_match.group(2)
                })
            elif cred_match.group(3) and cred_match.group(4):
                otp_credentials.append({
                    "userLabel": cred_match.group(4),
                    "id": cred_match.group(3)
                })
        logger.info(f"Found {len(otp_credentials)} OTP credentials: {otp_credentials}")

    # Ищем selectedCredentialId в нескольких местах
    credential_id = ""

    # Способ 1: В kcContext.otpLogin.selectedCredentialId
    credential_match = re.search(r'"selectedCredentialId":\s*"([^"]*)"', page_text)
    if credential_match:
        credential_id = credential_match.group(1)
        logger.info(f"Found selectedCredentialId in JSON: {credential_id}")

    # Способ 2: В hidden input
    if not credential_id:
        credential_match = re.search(
            r'name="selectedCredentialId"\s+value="([^"]*)"', page_text
        )
        if credential_match:
            credential_id = credential_match.group(1)
            logger.info(f"Found selectedCredentialId in hidden input: {credential_id}")

    return {
        "otp_action_url": otp_action_url,
        "credential_id": credential_id,
        "otp_credentials": otp_credentials
    }


async def get_cookies(
    user_login: str,
    password: str,
    user_agent: str = None,
    tg_user_id: int = None,
    db: DBModel = None,
) -> Union[list, TwoFactorRequired]:
    """
    Асинхронно выполняет авторизацию на https://attendance.mirea.ru через Keycloak SSO
    и возвращает куки в виде списка словарей или TwoFactorRequired если нужен OTP.

    Аргументы:
    user_login (str): Логин пользователя (email).
    password (str): Пароль пользователя.
    user_agent (str): User-Agent для запросов (опционально).
    tg_user_id (int): Telegram ID пользователя для логирования.
    db (DBModel): Объект базы данных.

    Возвращает:
    list: [cookies] при успешной авторизации
    TwoFactorRequired: если требуется ввод TOTP кода
    """
    logger.info(f"Получаю новые куки для пользователя {tg_user_id}")
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Получаем страницу авторизации (будет редирект на Keycloak SSO)
            initial_url = (
                "https://attendance.mirea.ru/api/auth/login"
                "?redirectUri=https%3A%2F%2Fattendance-app.mirea.ru%2Fservices"
                "&rememberMe=True"
            )

            # Генерируем случайный мобильный User-Agent
            random_mobile_ua = (
                user_agent
                if user_agent is not None
                else generate_random_mobile_user_agent()
            )
            initial_headers = {
                "User-Agent": random_mobile_ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            logger.info("Переход на страницу логина...")
            async with session.get(
                initial_url,
                headers=initial_headers,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    raise Exception(
                        f"Ошибка при получении страницы авторизации. Код: {response.status}"
                    )

                final_url = str(response.url)
                logger.info(f"Получена страница Keycloak: {final_url}")

                page_text = await response.text()

            # 2. Извлекаем loginAction из Keycloak (используется для React-формы)
            # Keycloak использует React, ищем loginAction в JavaScript
            login_action_match = re.search(r'"loginAction":\s*"([^"]*)"', page_text)
            if not login_action_match:
                logger.warning("Не найден loginAction, пробуем альтернативный метод")
                # Пробуем найти форму
                soup = BeautifulSoup(page_text, "html.parser")
                form = soup.find("form")
                if form and form.get("action"):
                    form_action = form["action"].replace("&amp;", "&")
                    if not form_action.startswith("http"):
                        parsed_url = urlparse(final_url)
                        form_action = (
                            f"{parsed_url.scheme}://{parsed_url.netloc}{form_action}"
                        )
                else:
                    raise Exception(
                        "Не удалось найти форму авторизации на странице Keycloak"
                    )
            else:
                form_action = login_action_match.group(1)
                # Декодируем unicode escape sequences
                form_action = form_action.encode().decode("unicode-escape")

            logger.info(f"URL для авторизации: {form_action}")

            # 3. Отправляем данные логина в Keycloak
            login_data = {
                "username": user_login,
                "password": password,
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": final_url,
                "Origin": f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}",
                "User-Agent": random_mobile_ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            }

            logger.info("Отправка данных авторизации...")
            async with session.post(
                form_action,
                data=login_data,
                headers=headers,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as post_response:
                final_redirect_url = str(post_response.url)
                response_text = await post_response.text()
                logger.info(
                    f"Статус: {post_response.status}, Конечный URL: {final_redirect_url}"
                )

                # Проверяем, не требуется ли OTP
                if post_response.status == 200 and _is_otp_page(response_text):
                    logger.info(
                        f"Обнаружена страница 2FA для пользователя {tg_user_id}"
                    )
                    otp_data = _extract_otp_form_data(response_text, final_redirect_url)

                    if otp_data:
                        session_cookies = _extract_session_cookies(session)
                        return TwoFactorRequired(
                            session_cookies=session_cookies,
                            otp_action_url=otp_data["otp_action_url"],
                            credential_id=otp_data["credential_id"],
                            otp_credentials=otp_data.get("otp_credentials", []),
                        )
                    else:
                        raise Exception(
                            "Обнаружена 2FA, но не удалось извлечь данные формы OTP"
                        )

                # Проверяем успешность авторизации
                if post_response.status != 200:
                    raise Exception(f"Ошибка авторизации. Код: {post_response.status}")

                # Проверяем, что мы попали на attendance-app
                if (
                    "attendance-app.mirea.ru" not in final_redirect_url
                    and "error" in response_text.lower()
                ):
                    raise Exception("Неправильный логин или пароль")

            # 4. Извлекаем куки из cookie_jar
            cookies = _extract_cookies_list(session)

            # Проверяем наличие важных cookies
            aspnet_cookie = any(c["name"] == ".AspNetCore.Cookies" for c in cookies)
            if (
                not aspnet_cookie
                and "attendance-app.mirea.ru" not in final_redirect_url
            ):
                raise Exception(
                    "Не удалось получить cookie авторизации. Проверьте логин и пароль."
                )

            logger.info(f"Авторизация успешна! Получено {len(cookies)} cookies")
            return [cookies]

    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети для пользователя {tg_user_id}: {str(e)}")
        raise Exception(f"Ошибка подключения к серверу: {str(e)}")

    except Exception as e:
        logger.error(f"Неожиданная ошибка для пользователя {tg_user_id}: {str(e)}")
        # Проверяем, не является ли это ошибкой авторизации
        if (
            "логин" in str(e).lower()
            or "пароль" in str(e).lower()
            or "авторизац" in str(e).lower()
        ):
            raise
        raise Exception(f"Ошибка при получении cookies: {str(e)}")


async def submit_otp_code(
    otp_code: str,
    otp_action_url: str,
    credential_id: str,
    session_cookies: dict,
    user_agent: str = None,
    tg_user_id: int = None,
) -> Union[list, TwoFactorRequired]:
    """
    Отправляет OTP код для завершения двухфакторной аутентификации.

    Аргументы:
    otp_code (str): 6-значный TOTP код.
    otp_action_url (str): URL для отправки OTP.
    credential_id (str): ID credential из формы.
    session_cookies (dict): Cookies сессии Keycloak.
    user_agent (str): User-Agent для запросов.
    tg_user_id (int): Telegram ID пользователя для логирования.

    Возвращает:
    list: [cookies] при успешной авторизации
    TwoFactorRequired: если код неверный и нужно повторить ввод
    """
    logger.info(f"Отправка OTP кода для пользователя {tg_user_id}")

    try:
        # Создаём cookie jar с сохранёнными cookies
        jar = aiohttp.CookieJar()

        async with aiohttp.ClientSession(cookie_jar=jar) as session:
            # Восстанавливаем cookies в сессию
            for name, cookie_data in session_cookies.items():
                # Обрабатываем domain - может быть строкой, списком или кортежем
                domain = cookie_data.get("domain", "sso.mirea.ru")
                if isinstance(domain, (list, tuple)):
                    domain = domain[0] if domain and domain[0] else "sso.mirea.ru"
                # Убираем точку в начале домена, если есть
                if domain.startswith("."):
                    domain = domain[1:]

                jar.update_cookies(
                    {name: cookie_data["value"]},
                    response_url=aiohttp.client.URL(f"https://{domain}"),
                )

            random_mobile_ua = (
                user_agent
                if user_agent is not None
                else generate_random_mobile_user_agent()
            )

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": random_mobile_ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            }

            otp_data = {
                "otp": otp_code,
                "login": "Вход",
            }
            if credential_id:
                otp_data["selectedCredentialId"] = credential_id

            logger.info(f"Отправка OTP на URL: {otp_action_url}")

            async with session.post(
                otp_action_url,
                data=otp_data,
                headers=headers,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                final_url = str(response.url)
                response_text = await response.text()
                logger.info(f"OTP ответ: статус={response.status}, URL={final_url}")

                # Проверяем, нужно ли повторить ввод OTP (неверный код)
                if response.status == 200 and _is_otp_page(response_text):
                    logger.warning(f"Неверный OTP код для пользователя {tg_user_id}")
                    otp_form_data = _extract_otp_form_data(response_text, final_url)

                    if otp_form_data:
                        new_session_cookies = _extract_session_cookies(session)
                        return TwoFactorRequired(
                            session_cookies=new_session_cookies,
                            otp_action_url=otp_form_data["otp_action_url"],
                            credential_id=otp_form_data["credential_id"],
                            message="Неверный код. Попробуйте снова.",
                            otp_credentials=otp_form_data.get("otp_credentials", []),
                        )
                    else:
                        raise Exception("Неверный OTP код")

                # Проверяем успешный редирект (302 -> attendance-app)
                if response.status == 200 or response.status == 302:
                    if "attendance-app.mirea.ru" in final_url or response.status == 302:
                        # Успешная авторизация
                        cookies = _extract_cookies_list(session)
                        logger.info(
                            f"2FA успешна для пользователя {tg_user_id}! "
                            f"Получено {len(cookies)} cookies"
                        )
                        return [cookies]

                raise Exception(
                    f"Неожиданный ответ при проверке OTP: {response.status}"
                )

    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети при отправке OTP для {tg_user_id}: {str(e)}")
        raise Exception(f"Ошибка подключения: {str(e)}")

    except Exception as e:
        logger.error(f"Ошибка при отправке OTP для {tg_user_id}: {str(e)}")
        raise
