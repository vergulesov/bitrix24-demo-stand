import base64
import os
import uuid
from datetime import datetime

import requests
from dotenv import load_dotenv

from schema import DEAL_FIELD_CODES

load_dotenv()

BITRIX_WEBHOOK = (os.getenv("BITRIX_WEBHOOK_URL") or os.getenv("BITRIX_WEBHOOK") or "").rstrip("/")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "").strip()

PIPELINE_NAME = "Подбор персонала"
ENTITY_TYPE_ID = 2
GIGACHAT_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"


def bitrix(method, params=None):
    response = requests.post(
        f"{BITRIX_WEBHOOK}/{method}.json",
        json=params or {},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Bitrix: {data['error']} — {data.get('error_description', '')}")
    return data.get("result")


def get_pipeline_id():
    result = bitrix("crm.category.list", {"entityTypeId": ENTITY_TYPE_ID})
    for category in result.get("categories", []):
        if category.get("name") == PIPELINE_NAME:
            return int(category["id"])
    raise RuntimeError(f"Не найдена воронка «{PIPELINE_NAME}».")


def get_stage_id(category_id):
    result = bitrix(
        "crm.status.list",
        {
            "filter": {"ENTITY_ID": f"DEAL_STAGE_{category_id}"},
            "order": {"SORT": "ASC"},
        },
    )
    for stage in result or []:
        if stage.get("NAME") == "Новый кандидат":
            return stage["STATUS_ID"]
    raise RuntimeError("Не найдена стадия «Новый кандидат».")


def gigachat_token():
    if not GIGACHAT_AUTH_KEY:
        raise RuntimeError("Не задан GIGACHAT_AUTH_KEY в .env")

    response = requests.post(
        GIGACHAT_OAUTH_URL,
        headers={
            "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"scope": "GIGACHAT_API_PERS"},
        timeout=20,
        verify=False,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def recognize_position(text):
    token = gigachat_token()

    prompt = (
        "Ты помощник кадрового агентства. "
        "Определи желаемую должность кандидата из входящего сообщения. "
        "Верни только название должности, без пояснений, кавычек и знаков препинания. "
        "Если указана конкретизация, сохрани её. Например: "
        "«водитель категории C» -> «Водитель категории C»."
    )

    response = requests.post(
        GIGACHAT_CHAT_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "model": "GigaChat",
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        },
        timeout=30,
        verify=False,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def create_demo_candidate(text, position):
    category_id = get_pipeline_id()
    stage_id = get_stage_id(category_id)

    now = datetime.now().isoformat(timespec="seconds")

    result = bitrix(
        "crm.item.add",
        {
            "entityTypeId": ENTITY_TYPE_ID,
            "useOriginalUfNames": "Y",
            "fields": {
                "title": f"[AI DEMO] Новый кандидат · {position}",
                "categoryId": category_id,
                "stageId": stage_id,
                "comments": f"Входящее сообщение:\n{text}\n\nAI распознал должность: {position}",
                DEAL_FIELD_CODES["DESIRED_POSITION"]: position,
                DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "Telegram",
                DEAL_FIELD_CODES["LAST_INBOUND_AT"]: now,
                DEAL_FIELD_CODES["NEXT_STEP"]: "Ответить кандидату",
                DEAL_FIELD_CODES["BLOCKER"]: "Нужно ответить",
            },
        },
    )
    return int(result["item"]["id"])


def main():
    if not BITRIX_WEBHOOK:
        raise SystemExit("Не найден BITRIX_WEBHOOK_URL / BITRIX_WEBHOOK в .env")

    text = input(
        "Входящее сообщение кандидата:\n"
        "> "
    ).strip()

    if not text:
        raise SystemExit("Пустое сообщение.")

    print("\n🤖 AI распознаёт должность...")
    position = recognize_position(text)
    print(f"✅ Должность: {position}")

    deal_id = create_demo_candidate(text, position)
    print(f"✅ Создана демо-сделка #{deal_id}")
    print("   Поле «Желаемая должность» заполнено автоматически.")


if __name__ == "__main__":
    main()
