import os

from dotenv import load_dotenv

load_dotenv()

# Database
DSN = os.getenv("DSN")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
_super_admin = os.getenv("SUPER_ADMIN")
SUPER_ADMIN = int(_super_admin) if _super_admin else None

# Trusted service API key (for service-to-service auth)
TRUSTED_SERVICE_API_KEY = os.getenv("TRUSTED_SERVICE_API_KEY")

# Database pool settings
DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 7

# Rate limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_PERIOD = "minute"

# Timeouts (seconds)
HTTP_TIMEOUT = 10

# Pagination
DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 100

# Validation
MIN_TEXT_LENGTH = 5

# Admin levels
ADMIN_LEVEL_NONE = 0  # Regular user
ADMIN_LEVEL_BASIC = 1  # Basic admin (can mark others)
ADMIN_LEVEL_MODERATE = 2  # Moderate admin
ADMIN_LEVEL_SUPER = 3  # Super admin (full access)

# URLs
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
NEWS_CHANNEL_URL = os.getenv("NEWS_CHANNEL_URL", "")
DONATE_URL = os.getenv("DONATE_URL", "")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "")
DONATE_BOT_USERNAME = os.getenv("DONATE_BOT_USERNAME", "")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_PREFIX = "mireapprove:"
CACHE_TTL_SECONDS = 300  # 5 minutes
SESSION_TTL_SECONDS = 3600  # 1 hour

# Export
MAX_EXPORT_ROWS = 10000
