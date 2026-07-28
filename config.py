import os

# Config Variables
API_ID = int(os.environ.get("API_ID", "12345678"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

SHORTENER_URL = os.environ.get(
    "SHORTENER_URL", "https://yourshortener.com/api"
)
SHORTENER_API = os.environ.get("SHORTENER_API", "YOUR_SHORTENER_API_KEY")

BOT_USERNAME = os.environ.get("BOT_USERNAME", "YourMovieBot")
MAIN_CHANNEL = os.environ.get(
    "MAIN_CHANNEL", "https://t.me/YourMainChannel"
)
DEV_ADMIN_USERNAME = os.environ.get("DEV_ADMIN_USERNAME", "YourAdminUsername")

START_PHOTO = os.environ.get(
    "START_PHOTO", "https://i.ibb.co/L8xX11d/movie-banner.jpg"
)

# How To Verify Video/Tutorial Link (YouTube ya Telegram Post Link)
HOW_TO_VERIFY_URL = os.environ.get(
    "HOW_TO_VERIFY_URL", "https://t.me/YourMainChannel/123"
)

DB_NAME = "movie_bot.db"
