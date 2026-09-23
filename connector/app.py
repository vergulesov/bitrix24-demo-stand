from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import os
import time
import uuid
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests


# ============================================================
# ENV
# ============================================================

CONNECTOR_ID = "staffflow_test"
HANDLER_URL = "https://195-19-195-13.sslip.io/bitrix/app"

# GigaChat
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "").strip()

GIGACHAT_OAUTH_URL = (
    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
)

GIGACHAT_CHAT_URL = (
    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
)

# Bitrix CRM
PIPELINE_NAME = "Подбор персонала"


# ============================================================
# CRM FIELD CODES
# ============================================================

CANDIDATE_FIRST_NAME = "UF_CRM_CANDIDATE_FIRST_NAME"
CANDIDATE_LAST_NAME = "UF_CRM_CANDIDATE_LAST_NAME"
CANDIDATE_PHONE = "UF_CRM_CANDIDATE_PHONE"
CANDIDATE_TELEGRAM = "UF_CRM_CANDIDATE_TELEGRAM"
CANDIDATE_WHATSAPP = "UF_CRM_CANDIDATE_WHATSAPP"
CANDIDATE_MAX = "UF_CRM_CANDIDATE_MAX"

DESIRED_POSITION_FIELD = "UF_CRM_DESIRED_POSITION"
DIRECTION_FIELD = "UF_CRM_DIRECTION"
VACANCY_FIELD = "UF_CRM_VACANCY"
CLIENT_COMPANY_FIELD = "UF_CRM_CLIENT_COMPANY"
CANDIDATE_SOURCE_FIELD = "UF_CRM_CANDIDATE_SOURCE"

LAST_INBOUND_FIELD = "UF_CRM_LAST_INBOUND_AT"
LAST_RESPONSE_FIELD = "UF_CRM_LAST_RESPONSE_AT"
RESPONSE_DEADLINE_FIELD = "UF_CRM_RESPONSE_DEADLINE"
SLA_STATUS_FIELD = "UF_CRM_SLA_STATUS"
PRIORITY_FIELD = "UF_CRM_PRIORITY"
URGENCY_FIELD = "UF_CRM_URGENCY"
BLOCKER_FIELD = "UF_CRM_BLOCKER"
NEXT_STEP_FIELD = "UF_CRM_NEXT_STEP"
NEXT_ACTION_AT_FIELD = "UF_CRM_NEXT_ACTION_AT"


# ============================================================
# GLOBAL BITRIX AUTH
# ============================================================

LAST_AUTH = None
LAST_DOMAIN = None


# ============================================================
# BITRIX REST
# ============================================================

def bitrix_call(server_endpoint, method, auth, params=None):
    url = server_endpoint.rstrip("/") + "/" + method

    data = dict(params or {})
    data["auth"] = auth

    encoded = json.dumps(
        data,
        ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().decode(
            "utf-8",
            errors="replace"
        )

        print()
        print("=" * 80)
        print("BITRIX CALL:", method)
        print("HTTP STATUS:", response.status)
        print("RESPONSE:", raw[:10000])
        print("=" * 80)
        print()

        try:
            return json.loads(raw)

        except json.JSONDecodeError:
            raise RuntimeError(
                f"Bitrix вернул не-JSON ответ для {method}: "
                f"{raw[:2000]!r}"
            )


# ============================================================
# GIGACHAT
# ============================================================

def get_gigachat_token():
    """
    Получает OAuth-токен GigaChat.
    """

    if not GIGACHAT_AUTH_KEY:
        raise RuntimeError(
            "GIGACHAT_AUTH_KEY не найден в окружении systemd."
        )

    rq_uid = str(uuid.uuid4())

    response = requests.post(
        GIGACHAT_OAUTH_URL,
        headers={
            "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
            "RqUID": rq_uid,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "scope": "GIGACHAT_API_PERS",
        },
        verify=False,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    token = data.get("access_token")

    if not token:
        raise RuntimeError(
            f"GigaChat не вернул access_token: {data}"
        )

    return token


def recognize_position(text):
    """
    Распознаёт желаемую должность кандидата
    из входящего сообщения.
    """

    if not text:
        return None

    token = get_gigachat_token()

    prompt = """
Ты помощник кадрового агентства.

Определи желаемую должность кандидата из входящего сообщения.

Верни ТОЛЬКО название должности.
Без пояснений.
Без кавычек.
Без точек в конце.

Если указана конкретизация должности, сохрани её.

Примеры:

"Ищу работу водителем категории C"
→ Водитель категории C

"Здравствуйте, хочу устроиться менеджером по продажам"
→ Менеджер по продажам

"Нужна работа оператором станка ЧПУ"
→ Оператор станка ЧПУ

"Ищу работу бухгалтером"
→ Бухгалтер

Если должность определить невозможно, верни:
Не определено
""".strip()

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
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
        },
        verify=False,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    try:
        result = (
            data["choices"][0]["message"]["content"]
            .strip()
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ):
        raise RuntimeError(
            f"Неожиданный ответ GigaChat: {data}"
        )

    result = result.strip(
        " \n\t\"'`.,;:!?"
    )

    if not result:
        return None

    if result.lower() == "не определено":
        return None

    return result


# ============================================================
# BITRIX CRM HELPERS
# ============================================================

def get_pipeline():
    """
    Находит воронку "Подбор персонала".
    """

    if not LAST_AUTH or not LAST_DOMAIN:
        raise RuntimeError(
            "Bitrix authorization is not initialized."
        )

    endpoint = (
        "https://" +
        LAST_DOMAIN +
        "/rest/"
    )

    result = bitrix_call(
        endpoint,
        "crm.category.list",
        LAST_AUTH,
        {
            "entityTypeId": 2,
        },
    )

    categories = (
        result.get("result", {})
        .get("categories", [])
    )

    for category in categories:
        if category.get("name") == PIPELINE_NAME:
            return category

    return None


def get_pipeline_stages(category_id):
    """
    Получает стадии конкретной воронки.
    """

    endpoint = (
        "https://" +
        LAST_DOMAIN +
        "/rest/"
    )

    result = bitrix_call(
        endpoint,
        "crm.dealcategory.stage.list",
        LAST_AUTH,
        {
            "id": category_id,
        },
    )

    return result.get("result", [])


def get_first_stage(category_id):
    """
    Возвращает первую стадию воронки.
    """

    stages = get_pipeline_stages(
        category_id
    )

    if not stages:
        return None

    return stages[0]


# ============================================================
# UPDATE EXISTING CRM DEAL
# ============================================================

def update_deal_position(
    deal_id,
    position,
    inbound_text=None,
    user_name=None,
):
    """
    Обновляет существующую CRM-сделку после AI.

    AI:
      Желаемая должность = position

    В этом сценарии:
      Вакансия = пусто

    Название сделки:
      имя кандидата без должности

    Остальные SLA-поля НЕ трогаем.
    """

    endpoint = (
        "https://" +
        LAST_DOMAIN +
        "/rest/"
    )

    title = (
        user_name.strip()
        if user_name and user_name.strip()
        else "Новый кандидат"
    )

    fields = {
        # Убираем должность из названия сделки.
        "TITLE": title,

        # AI → Желаемая должность.
        DESIRED_POSITION_FIELD: position,

        # В AI-демо вакансия неизвестна,
        # поэтому поле оставляем пустым.
        VACANCY_FIELD: "",
    }

    if inbound_text:
        fields["COMMENTS"] = (
            "AI-квалификация\n\n"
            f"Входящее сообщение:\n"
            f"{inbound_text}\n\n"
            f"AI определил должность: "
            f"{position}"
        )

    result = bitrix_call(
        endpoint,
        "crm.deal.update",
        LAST_AUTH,
        {
            "id": int(deal_id),
            "fields": fields,
        },
    )

    print()
    print("=" * 80)
    print("🤖 AI → CRM")
    print(f"Сделка #{deal_id}")
    print(f"Название: {title}")
    print(f"Желаемая должность: {position}")
    print("Вакансия: пусто")
    print("=" * 80)
    print()

    return result


# ============================================================
# CREATE CRM DEAL IF NEEDED
# ============================================================

def create_ai_deal(
    position,
    inbound_text,
    user_name="Кандидат",
):
    """
    Создаёт CRM-сделку, если Bitrix
    ещё не создал её автоматически.
    """

    pipeline = get_pipeline()

    if not pipeline:
        raise RuntimeError(
            f'Воронка "{PIPELINE_NAME}" не найдена.'
        )

    category_id = pipeline.get("id")

    stage = get_first_stage(
        category_id
    )

    if not stage:
        raise RuntimeError(
            "Не удалось получить стадии воронки."
        )

    stage_id = stage.get("STATUS_ID")

    endpoint = (
        "https://" +
        LAST_DOMAIN +
        "/rest/"
    )

    title = (
        user_name.strip()
        if user_name and user_name.strip()
        else "Новый кандидат"
    )

    fields = {
        "TITLE": title,

        "CATEGORY_ID": category_id,

        "STAGE_ID": stage_id,

        # AI → Желаемая должность.
        DESIRED_POSITION_FIELD: position,

        # Вакансия не определялась.
        VACANCY_FIELD: "",

        "COMMENTS": (
            "AI-квалификация кандидата\n\n"
            f"Кандидат: {user_name}\n\n"
            f"Входящее сообщение:\n"
            f"{inbound_text}\n\n"
            f"Распознано AI:\n"
            f"{position}"
        ),
    }

    result = bitrix_call(
        endpoint,
        "crm.deal.add",
        LAST_AUTH,
        {
            "fields": fields,
        },
    )

    deal_id = result.get(
        "result"
    )

    print()
    print("=" * 80)
    print("🤖 AI → CRM")
    print(f"Создана сделка #{deal_id}")
    print(f"Название: {title}")
    print(f"Желаемая должность: {position}")
    print("Вакансия: пусто")
    print("=" * 80)
    print()

    return deal_id


# ============================================================
# REGISTER CONNECTOR
# ============================================================

def register_and_list(data):
    global LAST_AUTH, LAST_DOMAIN

    auth = data["AUTH_ID"]

    endpoint = (
        "https://" +
        data["DOMAIN"] +
        "/rest/"
    )

    LAST_AUTH = auth
    LAST_DOMAIN = data["DOMAIN"]

    icon = {
        "DATA_IMAGE": (
            "data:image/svg+xml,%3Csvg%20"
            "xmlns%3D%22http://www.w3.org/2000/svg%22/%3E"
        ),
        "COLOR": "#69acc0",
        "SIZE": "90%",
        "POSITION": "center",
    }

    result = bitrix_call(
        endpoint,
        "imconnector.register",
        auth,
        {
            "ID": CONNECTOR_ID,
            "NAME": "StaffFlow Test",
            "ICON": icon,
            "PLACEMENT_HANDLER": HANDLER_URL,
            "CHAT_GROUP": False,
        },
    )

    print(
        "REGISTER RESULT:",
        json.dumps(
            result,
            ensure_ascii=False
        )
    )

    activate = bitrix_call(
        endpoint,
        "imconnector.activate",
        auth,
        {
            "CONNECTOR": CONNECTOR_ID,
            "LINE": 1,
            "ACTIVE": "1",
        },
    )

    print(
        "ACTIVATE RESULT:",
        json.dumps(
            activate,
            ensure_ascii=False
        )
    )

    connector_data = bitrix_call(
        endpoint,
        "imconnector.connector.data.set",
        auth,
        {
            "CONNECTOR": CONNECTOR_ID,
            "LINE": 1,
            "DATA": {
                "ID": "staffflow_test_line_1",
                "URL": HANDLER_URL,
                "URL_IM": HANDLER_URL,
                "NAME": "StaffFlow Test",
            },
        },
    )

    print(
        "DATA SET RESULT:",
        json.dumps(
            connector_data,
            ensure_ascii=False
        )
    )

    status = bitrix_call(
        endpoint,
        "imconnector.status",
        auth,
        {
            "CONNECTOR": CONNECTOR_ID,
            "LINE": 1,
        },
    )

    print(
        "STATUS RESULT:",
        json.dumps(
            status,
            ensure_ascii=False
        )
    )


# ============================================================
# OPEN CHANNEL DIAGNOSTICS
# ============================================================

def get_dialog_by_chat_id(chat_id):

    if not LAST_AUTH or not LAST_DOMAIN:
        raise RuntimeError(
            "Bitrix authorization is not initialized."
        )

    if not chat_id:
        return None

    endpoint = (
        "https://" +
        LAST_DOMAIN +
        "/rest/"
    )

    result = bitrix_call(
        endpoint,
        "imopenlines.dialog.get",
        LAST_AUTH,
        {
            "CHAT_ID": int(chat_id),
        },
    )

    return result.get("result")


def extract_session(send_result):

    if not isinstance(
        send_result,
        dict
    ):
        return None

    result = send_result.get(
        "result"
    )

    if not isinstance(
        result,
        dict
    ):
        return None

    session = result.get(
        "session"
    )

    if isinstance(
        session,
        dict
    ):
        return session

    return None


def build_diagnostic(
    send_result,
    payload,
):

    session = extract_session(
        send_result
    )

    diagnostic = {
        "external": {
            "connector": CONNECTOR_ID,
            "line": 1,
            "user_id": payload.get(
                "user_id"
            ),
            "chat_id": payload.get(
                "chat_id"
            ),
            "message_id": payload.get(
                "message_id"
            ),
        },

        "session": session,

        "dialog": None,

        "crm": {
            "entity_id": None,
            "entity_data_1": None,
            "entity_data_2": None,
            "entity_data_3": None,

            "deal_id": None,
            "lead_id": None,
            "contact_id": None,
            "company_id": None,
        },
    }

    if not session:
        return diagnostic

    bitrix_chat_id = session.get(
        "CHAT_ID"
    )

    if bitrix_chat_id is None:
        bitrix_chat_id = session.get(
            "chat_id"
        )

    if bitrix_chat_id is None:
        return diagnostic

    try:

        dialog = get_dialog_by_chat_id(
            bitrix_chat_id
        )

    except Exception as error:

        diagnostic["dialog_error"] = repr(
            error
        )

        return diagnostic

    diagnostic["dialog"] = dialog

    if not isinstance(
        dialog,
        dict
    ):
        return diagnostic

    entity_data_2 = str(
        dialog.get(
            "entity_data_2"
        ) or ""
    )

    diagnostic["crm"][
        "entity_id"
    ] = dialog.get(
        "entity_id"
    )

    diagnostic["crm"][
        "entity_data_1"
    ] = dialog.get(
        "entity_data_1"
    )

    diagnostic["crm"][
        "entity_data_2"
    ] = entity_data_2

    diagnostic["crm"][
        "entity_data_3"
    ] = dialog.get(
        "entity_data_3"
    )

    parts = entity_data_2.split("|")

    for index in range(
        0,
        len(parts) - 1,
        2,
    ):

        entity_type = parts[index]
        entity_id = parts[index + 1]

        if entity_type == "DEAL":

            diagnostic["crm"][
                "deal_id"
            ] = (
                int(entity_id)
                if entity_id.isdigit()
                else entity_id
            )

        elif entity_type == "LEAD":

            diagnostic["crm"][
                "lead_id"
            ] = (
                int(entity_id)
                if entity_id.isdigit()
                else entity_id
            )

        elif entity_type == "CONTACT":

            diagnostic["crm"][
                "contact_id"
            ] = (
                int(entity_id)
                if entity_id.isdigit()
                else entity_id
            )

        elif entity_type == "COMPANY":

            diagnostic["crm"][
                "company_id"
            ] = (
                int(entity_id)
                if entity_id.isdigit()
                else entity_id
            )

    return diagnostic


# ============================================================
# SEND EXTERNAL MESSAGE
# ============================================================

def send_external_message(payload):

    if not LAST_AUTH or not LAST_DOMAIN:
        raise RuntimeError(
            "Bitrix authorization is not initialized. "
            "Open the Bitrix app first."
        )

    token_path = (
        "/root/bitrix_connector/.send_token"
    )

    expected_token = (
        Path(token_path)
        .read_text()
        .strip()
    )

    token = payload.get(
        "token",
        "",
    )

    if token != expected_token:
        raise PermissionError(
            "Invalid send token."
        )

    user_id = payload.get(
        "user_id",
        "demo-user-001",
    )

    user_name = payload.get(
        "user_name",
        "Гость",
    )

    message_id = payload.get(
        "message_id",
        "demo-msg-001",
    )

    chat_id = payload.get(
        "chat_id",
        "demo-chat-001",
    )

    chat_name = payload.get(
        "chat_name",
        f"StaffFlow Test — {user_name}",
    )

    text = payload.get(
        "text",
        "Здравствуйте! Хочу узнать насчёт вакансии.",
    )

    # ========================================================
    # AI QUALIFICATION
    # ========================================================

    ai_position = None
    ai_error = None

    try:

        print()
        print("=" * 80)
        print("🤖 AI QUALIFICATION")
        print("Входящее сообщение:")
        print(text)
        print("=" * 80)

        ai_position = recognize_position(
            text
        )

        if ai_position:

            print(
                f"✅ AI определил должность: "
                f"{ai_position}"
            )

        else:

            print(
                "⚠️ AI не смог определить должность."
            )

    except Exception as error:

        ai_error = repr(error)

        print()
        print(
            "⚠️ AI ERROR:",
            ai_error
        )

        # Ошибка AI не ломает коннектор.
        # Сообщение всё равно отправляется в Bitrix.

    # ========================================================
    # SEND MESSAGE TO BITRIX OPEN CHANNEL
    # ========================================================

    endpoint = (
        "https://" +
        LAST_DOMAIN +
        "/rest/"
    )

    send_result = bitrix_call(
        endpoint,
        "imconnector.send.messages",
        LAST_AUTH,
        {
            "CONNECTOR": CONNECTOR_ID,
            "LINE": 1,

            "MESSAGES": [
                {
                    "user": {
                        "id": user_id,
                        "name": user_name,
                    },

                    "message": {
                        "id": message_id,
                        "date": int(
                            time.time()
                        ),
                        "text": text,
                    },

                    "chat": {
                        "id": chat_id,
                        "name": chat_name,
                        "url": HANDLER_URL,
                    },
                }
            ],
        },
    )