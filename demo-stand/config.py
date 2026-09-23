from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    webhook: str


def get_settings() -> Settings:
    webhook = os.getenv("BITRIX_WEBHOOK", "").strip().rstrip("/")
    if not webhook:
        raise RuntimeError("BITRIX_WEBHOOK is not configured. Copy .env.example to .env.")
    return Settings(webhook=webhook)
