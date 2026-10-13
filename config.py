import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://cloud-api.yandex.net/v1/disk"
TOKEN = os.getenv("YANDEX_DISK_TOKEN")
HEADERS = {
    "Authorization": f"OAuth {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}