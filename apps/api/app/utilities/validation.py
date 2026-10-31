import re
from urllib.parse import urlsplit


def normalize_phone(value: str) -> str:
    phone = re.sub(r"[\s()-]", "", value)
    if phone.startswith("01"):
        phone = "+88" + phone
    elif phone.startswith("880"):
        phone = "+" + phone
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        raise ValueError("Use a phone number with country code, e.g. +8801712345678")
    return phone


def image_link(value: str) -> str:
    if re.fullmatch(r"/media/[a-f0-9]{32}\.(?:jpg|png|webp)", value):
        return value
    url = urlsplit(value)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("Image links must use HTTPS without embedded credentials")
    return value
