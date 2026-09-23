import os
import random
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

from schema import DEAL_FIELD_CODES

load_dotenv()

WEBHOOK = os.getenv("BITRIX_WEBHOOK_URL") or os.getenv("BITRIX_WEBHOOK")
if not WEBHOOK:
    raise SystemExit("Не найден BITRIX_WEBHOOK_URL / BITRIX_WEBHOOK в .env")

PIPELINE_NAME = "Подбор персонала"
DEMO_COMMENT = "SLA DEMO DATA"
CONNECTOR_URL = os.getenv("STAFFFLOW_CONNECTOR_URL", "https://195-19-195-13.sslip.io/bitrix/app")
CONNECTOR_TOKEN = os.getenv("STAFFFLOW_SEND_TOKEN", "")
CONNECTOR_ID = "staffflow_test"
OPEN_LINE_ID = 1
SLA_MINUTES = 120

WORKDAY_SCENARIO = [
    {"name":"Алексей","vacancy":"Водитель","priority":"Высокий","stage":"Новый кандидат","delta":-90,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. SLA уже просрочен."},
    {"name":"Марина","vacancy":"Кладовщик","priority":"Высокий","stage":"Новый кандидат","delta":-40,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. SLA уже просрочен."},
    {"name":"Дмитрий","vacancy":"Курьер","priority":"Высокий","stage":"Новый кандидат","delta":-15,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. SLA почти на границе."},
    {"name":"Ольга","vacancy":"Оператор","priority":"Высокий","stage":"Новый кандидат","delta":15,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. До SLA 15 минут."},
    {"name":"Сергей","vacancy":"Комплектовщик","priority":"Средний","stage":"Новый кандидат","delta":30,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. До SLA 30 минут."},
    {"name":"Ирина","vacancy":"Менеджер по продажам","priority":"Средний","stage":"Новый кандидат","delta":60,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. До SLA 1 часа."},

    {"name":"Артём","vacancy":"Водитель","priority":"Высокий","stage":"Квалификация","delta":-30,"answered":True,"next":"Написать кандидату","blocker":"Не отвечает","comment":"Кандидат не выходит на связь после первого контакта."},
    {"name":"Елена","vacancy":"Курьер","priority":"Средний","stage":"Квалификация","delta":-10,"answered":True,"next":"Позвонить кандидату","blocker":"Не отвечает","comment":"Нужно повторно связаться с кандидатом."},
    {"name":"Павел","vacancy":"Администратор","priority":"Средний","stage":"Квалификация","delta":20,"answered":True,"next":"Проверить квалификацию","blocker":"Не хватает данных","comment":"Нужно уточнить опыт и доступность."},
    {"name":"Анна","vacancy":"Кладовщик","priority":"Высокий","stage":"Квалификация","delta":45,"answered":True,"next":"Проверить квалификацию","blocker":"Не хватает данных","comment":"Нужно уточнить график и зарплатные ожидания."},

    {"name":"Максим","vacancy":"Водитель-экспедитор","priority":"Высокий","stage":"Интервью","delta":-20,"answered":True,"next":"Провести интервью","blocker":"Интервью сегодня","comment":"Время интервью уже наступило."},
    {"name":"Юлия","vacancy":"Администратор","priority":"Высокий","stage":"Интервью","delta":30,"answered":True,"next":"Провести интервью","blocker":"Интервью сегодня","comment":"Интервью запланировано в ближайшие 30 минут."},
    {"name":"Виктор","vacancy":"Менеджер по продажам","priority":"Средний","stage":"Интервью","delta":90,"answered":True,"next":"Подтвердить интервью","blocker":"Интервью сегодня","comment":"Нужно подтвердить время с кандидатом."},
    {"name":"Роман","vacancy":"Водитель","priority":"Средний","stage":"Интервью","delta":180,"answered":True,"next":"Провести интервью","blocker":"Интервью сегодня","comment":"Интервью запланировано на сегодня."},

    {"name":"Наталья","vacancy":"Кладовщик","priority":"Высокий","stage":"Документы","delta":-45,"answered":True,"next":"Запросить документы","blocker":"Документы не получены","comment":"Кандидат обещал прислать документы, срок уже прошёл."},
    {"name":"Александр","vacancy":"Комплектовщик","priority":"Высокий","stage":"Документы","delta":15,"answered":True,"next":"Проверить документы","blocker":"Ждём документы","comment":"Документы должны прийти в ближайшее время."},
    {"name":"Екатерина","vacancy":"Оператор","priority":"Средний","stage":"Документы","delta":60,"answered":True,"next":"Проверить документы","blocker":"Ждём документы","comment":"Кандидат собирает пакет документов."},
    {"name":"Андрей","vacancy":"Курьер","priority":"Низкий","stage":"Документы","delta":120,"answered":True,"next":"Проверить документы","blocker":"Ждём документы","comment":"Документы в работе у кандидата."},

    {"name":"Денис","vacancy":"Водитель","priority":"Высокий","stage":"Передан заказчику","delta":-30,"answered":True,"next":"Запросить обратную связь","blocker":"Нет ответа заказчика","comment":"Кандидат передан заказчику, обратная связь просрочена."},
    {"name":"Кирилл","vacancy":"Кладовщик","priority":"Высокий","stage":"Передан заказчику","delta":30,"answered":True,"next":"Запросить обратную связь","blocker":"Ждём заказчика","comment":"Нужно получить решение заказчика."},
    {"name":"Михаил","vacancy":"Курьер","priority":"Средний","stage":"Передан заказчику","delta":90,"answered":True,"next":"Проверить статус у заказчика","blocker":"Ждём заказчика","comment":"Кандидат на рассмотрении у заказчика."},
    {"name":"Илья","vacancy":"Оператор","priority":"Средний","stage":"Передан заказчику","delta":180,"answered":True,"next":"Проверить статус у заказчика","blocker":"Ждём заказчика","comment":"Нужно проконтролировать обратную связь."},

    {"name":"Николай","vacancy":"Водитель","priority":"Высокий","stage":"Выход на работу","delta":-20,"answered":True,"next":"Подтвердить выход","blocker":"Выход сегодня","comment":"Сегодня день выхода. Нужно подтвердить готовность."},
    {"name":"Павел","vacancy":"Кладовщик","priority":"Высокий","stage":"Выход на работу","delta":45,"answered":True,"next":"Подтвердить выход","blocker":"Выход сегодня","comment":"Выход запланирован на сегодня."},
    {"name":"Владислав","vacancy":"Комплектовщик","priority":"Средний","stage":"Выход на работу","delta":180,"answered":True,"next":"Напомнить кандидату","blocker":"Выход сегодня","comment":"Нужно подтвердить выход кандидата."},

    {"name":"Глеб","vacancy":"Администратор","priority":"Средний","stage":"Ожидаем решение","delta":-15,"answered":True,"next":"Запросить решение","blocker":"Нет решения","comment":"После интервью решение не получено в ожидаемый срок."},
    {"name":"Егор","vacancy":"Менеджер по продажам","priority":"Высокий","stage":"Ожидаем решение","delta":45,"answered":True,"next":"Запросить решение","blocker":"Нет решения","comment":"Нужно получить решение по кандидату."},
    {"name":"Степан","vacancy":"Водитель","priority":"Средний","stage":"Ожидаем решение","delta":120,"answered":True,"next":"Проверить статус","blocker":"Ждём решение","comment":"Решение ожидается сегодня."},
    {"name":"Тимур","vacancy":"Курьер","priority":"Низкий","stage":"Ожидаем решение","delta":240,"answered":True,"next":"Проверить статус","blocker":"Ждём решение","comment":"Кандидат на финальном согласовании."},
]



# Восемь контрольных точек SLA: по две на каждое состояние.
# +3ч -> Не срочно, +1ч30м -> Скоро, +30м -> Сейчас, -10м -> Просрочено.
SLA_PRESENTATION_SCENARIO = [
    # По две контрольные точки на каждое состояние SLA.
    {"name": "Иван", "surname": "Петров", "vacancy": "Водитель", "priority": "Высокий", "delta": 180},
    {"name": "Сергей", "surname": "Петров", "vacancy": "Водитель", "priority": "Средний", "delta": 180},
    {"name": "Марина", "surname": "Соколова", "vacancy": "Кладовщик", "priority": "Высокий", "delta": 90},
    {"name": "Анна", "surname": "Соколова", "vacancy": "Кладовщик", "priority": "Средний", "delta": 90},
    {"name": "Дмитрий", "surname": "Волков", "vacancy": "Курьер", "priority": "Средний", "delta": 30},
    {"name": "Андрей", "surname": "Волков", "vacancy": "Курьер", "priority": "Высокий", "delta": 30},
    {"name": "Ольга", "surname": "Морозова", "vacancy": "Оператор", "priority": "Высокий", "delta": -10},
    {"name": "Елена", "surname": "Морозова", "vacancy": "Оператор", "priority": "Средний", "delta": -10},
]

def create_sla_presentation(category_id, user_id, stages):
    """Специальный SLA-стенд: четыре фиксированных контрольных состояния."""
    stage_id = stages.get("Новый кандидат")
    if not stage_id:
        raise RuntimeError("Не найдена стадия «Новый кандидат».")

    now = datetime.now()
    created = []

    for case in SLA_PRESENTATION_SCENARIO:
        deadline = now + timedelta(minutes=case["delta"])
        inbound = deadline - timedelta(minutes=SLA_MINUTES)

        # КРИТИЧНО: сделка сразу создаётся в «Новый кандидат»
        # и сразу получает «Срок реакции». Это штатный запуск SLA-БП.
        # «Срочность» здесь НЕ заполняем — её пишет сам БП.
        fields = {
            DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: case["name"],
            DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: case["surname"],
            DEAL_FIELD_CODES["CANDIDATE_PHONE"]: f"+79000000{100 + len(created)}",
            # SLA-сделка не получает должность: здесь нет входящего текста.
            # «Желаемую должность» заполняет только AI по реальному сообщению.
            DEAL_FIELD_CODES["VACANCY"]: "",
            DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "StaffFlow SLA Demo",
            DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["PRIORITY"]: case["priority"],
            DEAL_FIELD_CODES["BLOCKER"]: "Нужно ответить",
            DEAL_FIELD_CODES["NEXT_STEP"]: "Ответить кандидату",
            DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
        }

        result = call(
            "crm.item.add",
            {
                "entityTypeId": 2,
                "useOriginalUfNames": "Y",
                "fields": {
                    "title": f'{case["name"]} {case["surname"]}',
                    "categoryId": category_id,
                    "stageId": stage_id,
                    "assignedById": user_id,
                    "comments": DEMO_COMMENT,
                    **fields,
                },
            },
        )
        deal_id = int(result["item"]["id"])

        # Сделка сразу создаётся в «Новый кандидат» — это штатный триггер SLA БП.
        created.append(deal_id)

        call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT": (
                        f'[SLA DEMO] Контрольная точка: '
                        f'{case["delta"]:+d} мин. '
                        "Срочность рассчитывает SLA-БП."
                    ),
                }
            },
        )

    return created




PRESENTATION_SCENARIO = [
    {"name": "Сергей", "surname": "Кузнецов", "vacancy": "Водитель", "stage": "Новый кандидат",
     "priority": "Высокий", "delta": 45, "next": "Ответить кандидату", "blocker": "Нужно ответить"},
    {"name": "Павел", "surname": "Смирнов", "vacancy": "Кладовщик", "stage": "Квалификация",
     "priority": "Высокий", "delta": 60, "next": "Уточнить опыт", "blocker": "Не хватает данных"},
    {"name": "Юлия", "surname": "Орлова", "vacancy": "Администратор", "stage": "Интервью",
     "priority": "Высокий", "delta": 30, "next": "Провести интервью", "blocker": "Интервью сегодня"},
    {"name": "Глеб", "surname": "Морозов", "vacancy": "Менеджер", "stage": "Ожидаем решение",
     "priority": "Средний", "delta": 45, "next": "Запросить решение", "blocker": "Нет решения"},
    {"name": "Наталья", "surname": "Волкова", "vacancy": "Кладовщик", "stage": "Документы",
     "priority": "Высокий", "delta": -20, "next": "Запросить документы", "blocker": "Документы не получены"},
    {"name": "Денис", "surname": "Иванов", "vacancy": "Водитель", "stage": "Передан заказчику",
     "priority": "Высокий", "delta": 30, "next": "Запросить обратную связь", "blocker": "Ждём заказчика"},
    {"name": "Николай", "surname": "Соколов", "vacancy": "Комплектовщик", "stage": "Выход на работу",
     "priority": "Высокий", "delta": -10, "next": "Подтвердить выход", "blocker": "Выход сегодня"},
]

WORK_STAGES = [
    "Новый кандидат",
    "Квалификация",
    "Интервью",
    "Ожидаем решение",
    "Документы",
    "Передан заказчику",
    "Выход на работу",
]

# Расширенный демонстрационный набор: всего 50 кандидатов.

def call(method, params=None):
    response = requests.post(
        f"{WEBHOOK.rstrip('/')}/{method}.json",
        json=params or {},
        timeout=20,
    )
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            f"Bitrix REST вернул не-JSON ответ (HTTP {response.status_code}): {response.text!r}"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Bitrix REST вернул неожиданный ответ: {data!r} "
            f"(HTTP {response.status_code})"
        )

    if "error" in data:
        raise RuntimeError(
            f"{data['error']}: {data.get('error_description', '')}"
        )
    return data.get("result")


def get_pipeline():
    result = call("crm.category.list", {"entityTypeId": 2})
    categories = result.get("categories", []) if isinstance(result, dict) else []
    for category in categories:
        if category.get("name") == PIPELINE_NAME:
            return int(category["id"])
    raise RuntimeError(f"Не найдена воронка «{PIPELINE_NAME}».")


def get_stages(category_id):
    return call(
        "crm.status.list",
        {
            "filter": {"ENTITY_ID": f"DEAL_STAGE_{category_id}"},
            "order": {"SORT": "ASC"},
        },
    ) or []


def get_current_user_id():
    return int(call("user.current")["ID"])


def check_connector():
    response = requests.get(CONNECTOR_URL.rstrip("/"), timeout=8)
    response.raise_for_status()
    return True


def check_openline():
    # imconnector.status is an application-context method and cannot be
    # checked through the personal webhook used by this simulator.
    return {
        "CONFIGURED": None,
        "STATUS": None,
        "NOTE": "Проверка фактической доставки выполняется через /send + CRM."
    }


def send_openline_test():
    if not CONNECTOR_TOKEN:
        raise RuntimeError(
            "Не задан STAFFFLOW_SEND_TOKEN в .env. "
            "Добавь локально токен /send с VPS; в чат его не присылай."
        )

    stamp = int(time.time())
    payload = {
        "token": CONNECTOR_TOKEN,
        "user_id": f"health-user-{stamp}",
        "user_name": "StaffFlow Health Check",
        "message_id": f"health-msg-{stamp}",
        "chat_id": f"health-chat-{stamp}",
        "chat_name": "StaffFlow Health Check",
        "text": "StaffFlow health-check: входящее тестовое сообщение.",
    }
    send_url = CONNECTOR_URL.rstrip("/") + "/send"
    response = requests.post(
        send_url,
        json=payload,
        timeout=20,
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(
            f"Connector /send вернул HTTP {response.status_code}: "
            f"{response.text!r}"
        )
    # Connector может вернуть пустой/null body при успешном HTTP 2xx.
    # Для симулятора важен сам факт успешной доставки запроса.
    try:
        data = response.json()
    except ValueError:
        data = None

    if isinstance(data, dict) and data.get("ok") is False:
        raise RuntimeError(f"Connector /send вернул ошибку: {data!r}")
    return data or {"ok": True, "status_code": response.status_code}


def count_pipeline_deals(category_id):
    data = call(
        "crm.item.list",
        {
            "entityTypeId": 2,
            "select": ["id", "title"],
            "filter": {"categoryId": category_id},
        },
    )
    return len(data.get("items", []))


def wait_for_new_pipeline_deal(category_id, before_count, timeout=12):
    deadline = time.time() + timeout
    while time.time() < deadline:
        count = count_pipeline_deals(category_id)
        if count > before_count:
            return count
        time.sleep(1)
    return count_pipeline_deals(category_id)


def stage_map(category_id):
    return {
        item["NAME"]: item["STATUS_ID"]
        for item in get_stages(category_id)
        if item.get("NAME")
    }


def send_openline_message(name, vacancy, text, external_user_id=None, external_chat_id=None, message_prefix="workday"):
    """Отправляет сообщение во внешний чат. Одинаковые user/chat IDs продолжают существующий диалог."""
    if not CONNECTOR_TOKEN:
        raise RuntimeError("Для входящего демо не задан STAFFFLOW_SEND_TOKEN в .env.")

    stamp = int(time.time() * 1000)
    user_id = external_user_id or f"{message_prefix}-user-{stamp}"
    chat_id = external_chat_id or f"{message_prefix}-chat-{stamp}"
    message_id = f"{message_prefix}-msg-{stamp}"

    payload = {
        "token": CONNECTOR_TOKEN,
        "user_id": user_id,
        "user_name": name,
        "message_id": message_id,
        "chat_id": chat_id,
        # Не передаём должность в имя чата: Bitrix может использовать chat_name
        # при автоматическом названии CRM-сделки. Должность должен определить AI.
        "chat_name": name,
        "text": text,
    }
    response = requests.post(
        CONNECTOR_URL.rstrip("/") + "/send",
        json=payload,
        timeout=20,
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(
            f"Connector /send вернул HTTP {response.status_code}: "
            f"{response.text!r}"
        )

    try:
        data = response.json()
    except ValueError:
        data = None

    if isinstance(data, dict) and data.get("ok") is False:
        raise RuntimeError(f"Connector /send вернул ошибку: {data!r}")

    return {
        "ok": True,
        "status_code": response.status_code,
        "user_id": user_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "response": data,
    }


def send_workday_incoming(name, vacancy, index):
    """Создаёт настоящее новое входящее сообщение через Open Channel."""
    return send_openline_message(
        name=name,
        vacancy=vacancy,
        text=f"Здравствуйте! Интересует вакансия «{vacancy}». Подскажите, пожалуйста, условия и график.",
        message_prefix=f"workday-demo-{index + 1}",
    )



def find_recent_deal(category_id, name, timeout=15, before_count=None):
    """Ждём новую CRM-сделку после реального incoming."""
    deadline = time.time() + timeout
    last_items = []

    while time.time() < deadline:
        data = call(
            "crm.item.list",
            {
                "entityTypeId": 2,
                "select": ["id", "title", "categoryId", "stageId", "contactIds", "createdTime"],
                "filter": {"categoryId": category_id},
                "order": {"id": "DESC"},
            },
        )
        last_items = (data or {}).get("items", [])

        if last_items:
            if before_count is None or len(last_items) > before_count:
                return last_items[0]
        time.sleep(1)

    if last_items:
        # Даже если пагинация/фильтр не дал корректный count, берём последнюю сделку.
        return last_items[0]

    raise RuntimeError(
        f"Open Channel отправил сообщение для «{name}», "
        f"но CRM-сделка за {timeout} сек не появилась."
    )


def sla_status_text(deadline: datetime, now: datetime | None = None) -> str:
    """Человеческий статус SLA, рассчитанный от фактического дедлайна."""
    now = now or datetime.now()
    delta_minutes = round((deadline - now).total_seconds() / 60)
    if delta_minutes < 0:
        return f"🔴 ПРОСРОЧЕНО · {abs(delta_minutes)} мин"
    return f"🟢 ОСТАЛОСЬ · {delta_minutes} мин"


def urgency_level(deadline: datetime, now: datetime | None = None) -> str:
    """Возвращает демонстрационную срочность по времени до SLA."""
    now = now or datetime.now()
    delta_minutes = round((deadline - now).total_seconds() / 60)
    if delta_minutes < 0:
        return "Просрочено"
    if delta_minutes <= 30:
        return "Сейчас"
    if delta_minutes <= 120:
        return "Скоро"
    return "Не срочно"


_SLA_FIELD_CODE = None

def create_sla_candidate(category_id, user_id, stages, index):
    scenario = WORKDAY_SCENARIO[index]
    name = scenario["name"]
    vacancy = scenario["vacancy"]
    priority = scenario["priority"]
    deadline_delta = scenario["delta"]
    answered = scenario["answered"]
    scenario_stage = scenario["stage"]
    next_step = scenario["next"]
    blocker = scenario["blocker"]
    scenario_comment = scenario["comment"]

    # delta — только демо-смещение относительно текущего момента.
    # Источник SLA всё равно строится по правильной цепочке:
    # LAST_INBOUND_AT + SLA_MINUTES = RESPONSE_DEADLINE.
    now = datetime.now()
    inbound = now - timedelta(minutes=SLA_MINUTES - deadline_delta)
    deadline = inbound + timedelta(minutes=SLA_MINUTES)
    response = inbound + timedelta(minutes=35) if answered else None

    stage_name = scenario_stage
    stage_id = stages[stage_name]

    action_priority = urgency_level(deadline, now)

    fields = {
        DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: name,
        DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: "Демо",
        DEAL_FIELD_CODES["CANDIDATE_PHONE"]: f"+7900{1000000 + index * 731}",
        DEAL_FIELD_CODES["DESIRED_POSITION"]: vacancy,
        DEAL_FIELD_CODES["VACANCY"]: "",
        DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "StaffFlow Demo",
        DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound.isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["LAST_RESPONSE_AT"]: response.isoformat(timespec="seconds") if response else "",
        DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["PRIORITY"]: priority,
        DEAL_FIELD_CODES["BLOCKER"]: blocker,
        DEAL_FIELD_CODES["NEXT_STEP"]: next_step,
        # Для рабочего дня это время следующего действия.
        DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
    }

    # Для первых шести кандидатов сначала создаём сделку вне «Новый кандидат».
    # Так демо-SLA записывается ДО входа в стадию, где срабатывает робот.
    create_stage_id = stages["Квалификация"] if stage_name == "Новый кандидат" else stage_id

    if stage_name == "Новый кандидат":
        # Для входящего кандидата не рисуем сделку через REST:
        # сообщение реально проходит Telegram → Connector → Open Channel → CRM.
        send_workday_incoming(name, vacancy, index)
        recent = find_recent_deal(category_id, name)
        deal_id = int(recent["id"])

        # Open Channel мог автоматически создать/привязать контакт.
        # Помечаем его тем же демо-маркером, чтобы «Удалить демо-день»
        # чистил и контакты, созданные реальным incoming-потоком.
        contact_ids = recent.get("contactIds", []) or []
        for contact_id in contact_ids:
            call(
                "crm.item.update",
                {
                    "entityTypeId": 3,
                    "id": int(contact_id),
                    "useOriginalUfNames": "Y",
                    "fields": {
                        "comments": "[DEMO] SLA simulator contact",
                    },
                },
            )

        # Open Channel уже создал сделку и запустил штатные роботы.
        # После этого накладываем демо-состояние рабочего дня поверх реального входящего.
        call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "useOriginalUfNames": "Y",
                "fields": {
                    "comments": DEMO_COMMENT,
                    DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: name,
                    # Должность определяет AI из входящего сообщения.
                    # Поле «Вакансия» в этом сценарии намеренно не заполняем.
                    DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound.isoformat(timespec="seconds"),
                    DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
                    DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
                    DEAL_FIELD_CODES["PRIORITY"]: priority,
                    DEAL_FIELD_CODES["URGENCY"]: action_priority,
                    DEAL_FIELD_CODES["BLOCKER"]: blocker,
                    DEAL_FIELD_CODES["NEXT_STEP"]: next_step,
                },
            },
        )
    else:
        deal = call(
            "crm.item.add",
            {
                "entityTypeId": 2,
                "useOriginalUfNames": "Y",
                "fields": {
                    "title": name,
                    "categoryId": category_id,
                    "stageId": create_stage_id,
                    "assignedById": user_id,
                    "comments": DEMO_COMMENT,
                    **{k: v for k, v in fields.items() if k != DEAL_FIELD_CODES["CANDIDATE_SOURCE"]},
                },
            },
        )
        deal_id = int(deal["item"]["id"])

        # Сначала записываем демо-SLA в безопасной стадии, затем переводим в «Новый кандидат».
        call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "useOriginalUfNames": "Y",
                "fields": {
                    DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
                    DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
                },
            },
        )

        
        call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "useOriginalUfNames": "Y",
                "fields": {"stageId": stage_id},
            },
        )
    time.sleep(2)


    call(
        "crm.timeline.comment.add",
        {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": (
                    f"[WORKDAY DEMO] {scenario_comment}"
                ),
            }
        },
    )

    return deal_id, stage_name, priority, deadline_delta, answered





def create_presentation_incoming_fallback(category_id, user_id, stages, case, reason):
    """REST-фолбэк: создаёт входящего кандидата, если реальный Connector недоступен."""
    now = datetime.now()
    deadline = now + timedelta(minutes=case["delta"])
    urgency = (
        "Просрочено" if case["delta"] < 0
        else "Сейчас" if case["delta"] <= 30
        else "Скоро" if case["delta"] <= 120
        else "Не срочно"
    )
    deal = call(
        "crm.item.add",
        {
            "entityTypeId": 2,
            "useOriginalUfNames": "Y",
            "fields": {
                "title": f'{case["name"]} {case["surname"]}',
                "categoryId": category_id,
                "stageId": stages["Новый кандидат"],
                "assignedById": user_id,
                "comments": DEMO_COMMENT,
                DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: case["name"],
                DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: case["surname"],
                # Должность приходит из AI. «Вакансия» остаётся пустой.
                DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "Открытая линия",
                DEAL_FIELD_CODES["LAST_INBOUND_AT"]: (
                    deadline - timedelta(minutes=SLA_MINUTES)
                ).isoformat(timespec="seconds"),
                DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
                DEAL_FIELD_CODES["NEXT_ACTION_AT"]: now.isoformat(timespec="seconds"),
                DEAL_FIELD_CODES["PRIORITY"]: "Высокий",
                DEAL_FIELD_CODES["BLOCKER"]: case["blocker"],
                DEAL_FIELD_CODES["NEXT_STEP"]: case["next"],
            },
        },
    )
    deal_id=int(deal["item"]["id"])
    call(
        "crm.timeline.comment.add",
        {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": (
                    f"[PRESENTATION] Входящий кандидат через Открытую линию. "
                    f"Реальный incoming не удалось дождаться: {reason}"
                ),
            }
        },
    )
    return deal_id


def complete_incoming_activities(deal_id):
    """Закрывает только незавершённые активности, пришедшие из входящего канала."""
    data = call(
        "crm.activity.list",
        {
            "filter": {
                "OWNER_TYPE_ID": 2,
                "OWNER_ID": deal_id,
                "COMPLETED": "N",
                "IS_INCOMING_CHANNEL": "Y",
            },
            "select": [
                "ID",
                "TYPE_ID",
                "SUBJECT",
                "COMPLETED",
                "IS_INCOMING_CHANNEL",
            ],
            "order": {"ID": "DESC"},
        },
    ) or []

    completed = 0
    for activity in data:
        call(
            "crm.activity.update",
            {
                "id": int(activity["ID"]),
                "fields": {"COMPLETED": "Y"},
            },
        )
        completed += 1
    return completed


def create_incoming_call(category_id, deal_id, user_id, contact_id=None, subject="Входящий звонок"):
    """Создаёт незавершённый входящий звонок, чтобы он появился в очереди внимания."""
    communications = []
    if contact_id:
        phone = "+79000000999"
        communications.append(
            {
                "VALUE": phone,
                "ENTITY_ID": int(contact_id),
                "ENTITY_TYPE_ID": 3,
            }
        )

    fields = {
        "OWNER_TYPE_ID": 2,
        "OWNER_ID": int(deal_id),
        "TYPE_ID": 2,
        "SUBJECT": subject,
        "START_TIME": datetime.now().isoformat(timespec="seconds"),
        "END_TIME": (datetime.now() + timedelta(minutes=15)).isoformat(timespec="seconds"),
        "COMPLETED": "N",
        "PRIORITY": 2,
        "RESPONSIBLE_ID": int(user_id),
        "DESCRIPTION": "Кандидат просит перезвонить. Требует внимания рекрутёра.",
        "DESCRIPTION_TYPE": 1,
        "DIRECTION": 1,
        "IS_INCOMING_CHANNEL": "Y",
    }
    if communications:
        fields["COMMUNICATIONS"] = communications

    result = call("crm.activity.add", {"fields": fields})
    return int(result)


def create_existing_candidate_with_incoming(
    category_id,
    user_id,
    stages,
    case,
    index,
    make_call=False,
):
    """
    Создаёт кандидата обычным входящим, переводит его на нужную стадию,
    закрывает первое обращение как уже обработанное и затем отправляет
    второе сообщение из того же внешнего чата.

    Результат: это ОДНА существующая сделка, которая снова появилась во
    входящих после нового сообщения.
    """
    initial = send_openline_message(
        name=case["name"],
        vacancy=case["vacancy"],
        text=(
            f"Здравствуйте! Хочу откликнуться на вакансию «{case['vacancy']}». "
            "Готов пройти следующий этап."
        ),
        message_prefix=f"presentation-base-{index}",
    )

    before = count_pipeline_deals(category_id)
    recent = find_recent_deal(
        category_id,
        case["name"],
        timeout=15,
        before_count=before - 1 if before > 0 else None,
    )
    deal_id = int(recent["id"])

    for contact_id in recent.get("contactIds", []) or []:
        try:
            call(
                "crm.item.update",
                {
                    "entityTypeId": 3,
                    "id": int(contact_id),
                    "useOriginalUfNames": "Y",
                    "fields": {"comments": "[DEMO] SLA simulator contact"},
                },
            )
        except Exception:
            pass

    now = datetime.now()
    deadline = now + timedelta(minutes=case.get("delta", 60))
    fields = {
        "comments": DEMO_COMMENT,
        DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: case["name"],
        DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: case["surname"],
        DEAL_FIELD_CODES["CANDIDATE_PHONE"]: f"+7900000{500 + index}",
        # Должность распознаётся AI из первого входящего сообщения.
        # В этом симуляторе ниже фиксируем ожидаемый результат AI,
        # чтобы презентационный стенд показывал уже обработанную карточку.
        DEAL_FIELD_CODES["DESIRED_POSITION"]: case.get("ai_position") or case["vacancy"],
        DEAL_FIELD_CODES["VACANCY"]: "",
        DEAL_FIELD_CODES["DIRECTION"]: case.get("ai_direction", "Другое"),
        DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "Открытая линия",
        DEAL_FIELD_CODES["LAST_INBOUND_AT"]: now.isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["LAST_RESPONSE_AT"]: (now - timedelta(minutes=20)).isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["NEXT_ACTION_AT"]: now.isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["PRIORITY"]: case["priority"],
        DEAL_FIELD_CODES["BLOCKER"]: case["blocker"],
        DEAL_FIELD_CODES["NEXT_STEP"]: case["next"],
    }

    call(
        "crm.item.update",
        {
            "entityTypeId": 2,
            "id": deal_id,
            "useOriginalUfNames": "Y",
            "fields": {
                **fields,
                "stageId": stages[case["stage"]],
            },
        },
    )

    # Первое обращение уже обработано — именно поэтому кандидат сейчас
    # может спокойно находиться в середине воронки.
    complete_incoming_activities(deal_id)

    followup = send_openline_message(
        name=case["name"],
        vacancy=case["vacancy"],
        text=case["message"],
        external_user_id=initial["user_id"],
        external_chat_id=initial["chat_id"],
        message_prefix=f"presentation-followup-{index}",
    )

    time.sleep(1)

    call(
        "crm.timeline.comment.add",
        {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": (
                    f"[PRESENTATION] Существующий кандидат снова написал: "
                    f"«{case['message']}». Стадия не меняется: {case['stage']}."
                ),
            }
        },
    )

    # Показываем результат AI-квалификации именно на той же CRM-сделке.
    ai_position = case.get("ai_position") or case.get("vacancy")
    if ai_position:
        call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT": (
                        "[AI DEMO] Входящее обращение квалифицировано: "
                        f"желаемая должность → {ai_position}; "
                        f"направление → {case.get('ai_direction', 'Другое')}."
                    ),
                }
            },
        )

    activity_id = None
    if make_call:
        contact_id = (recent.get("contactIds") or [None])[0]
        activity_id = create_incoming_call(
            category_id,
            deal_id,
            user_id,
            contact_id=contact_id,
        )

    return {
        "deal_id": deal_id,
        "user_id": followup["user_id"],
        "chat_id": followup["chat_id"],
        "activity_id": activity_id,
    }


def create_new_incoming_candidate(category_id, user_id, stages, case, index):
    """Создаёт нового кандидата реальным входящим сообщением."""
    before = count_pipeline_deals(category_id)
    sent = send_openline_message(
        name=case["name"],
        # Для нового incoming должность НЕ передаём в CRM/чат:
        # она должна определяться из текста сообщения.
        vacancy=case.get("vacancy", ""),
        text=case["message"],
        message_prefix=f"presentation-new-{index}",
    )

    recent = find_recent_deal(
        category_id,
        case["name"],
        timeout=15,
        before_count=before,
    )
    deal_id = int(recent["id"])

    deadline = datetime.now() + timedelta(minutes=case.get("delta", 60))
    fields = {
        "comments": DEMO_COMMENT,
        DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: case["name"],
        DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: case["surname"],
        # Должность в новом обращении приходит из текста сообщения.
        # В демонстрации ниже она появляется как результат AI-квалификации.
        DEAL_FIELD_CODES["DESIRED_POSITION"]: "",
        DEAL_FIELD_CODES["VACANCY"]: "",
        DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "Открытая линия",
        DEAL_FIELD_CODES["LAST_INBOUND_AT"]: datetime.now().isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["NEXT_ACTION_AT"]: datetime.now().isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["PRIORITY"]: case["priority"],
        DEAL_FIELD_CODES["BLOCKER"]: case["blocker"],
        DEAL_FIELD_CODES["NEXT_STEP"]: case["next"],
    }

    # Симуляция результата AI-квалификации: само обращение приходит реально
    # через Open Channel, а затем в CRM появляются поля, которые в боевом
    # сценарии заполняет AI-квалификатор.
    # Симулируем именно результат AI после реального входящего сообщения.
    # Источник должности — текст обращения; в сценарии ожидаемый результат
    # хранится в expected_position, а не передаётся в Open Channel.
    ai_position = case.get("ai_position") or case.get("expected_position")
    if ai_position:
        fields.update({
            DEAL_FIELD_CODES["DESIRED_POSITION"]: ai_position,
            DEAL_FIELD_CODES["DIRECTION"]: case.get("ai_direction", "Логистика"),
        })

    call(
        "crm.item.update",
        {
            "entityTypeId": 2,
            "id": deal_id,
            "useOriginalUfNames": "Y",
            "fields": fields,
        },
    )

    for contact_id in recent.get("contactIds", []) or []:
        try:
            call(
                "crm.item.update",
                {
                    "entityTypeId": 3,
                    "id": int(contact_id),
                    "useOriginalUfNames": "Y",
                    "fields": {"comments": "[DEMO] SLA simulator contact"},
                },
            )
        except Exception:
            pass

    if ai_position:
        call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT": (
                        "[AI DEMO] Входящее сообщение квалифицировано: "
                        f"желаемая должность → {ai_position}; "
                        f"направление → {case.get('ai_direction', 'Логистика')}."
                    ),
                },
            },
        )

    return deal_id


def create_presentation_scenario(category_id, user_id, stages):
    """
    Презентационный стенд: отдельные, визуально понятные рабочие сцены.

    1. SLA — четыре реальные сделки в «Новый кандидат».
       Срочность заполняет штатный SLA-БП.
    2. Входящие — три отдельных реальных Open Channel обращения.
    3. Воронка — четыре обработанных кандидата на разных стадиях.
       Их повторное сообщение возвращает ОДНУ и ту же сделку во входящие.
    4. Ещё две спокойные сделки для заполнения дальнейших стадий.

    Всего: 13 сделок.
    """
    created = []
    created.extend(create_sla_presentation(category_id, user_id, stages))

    # AI-СЦЕНАРИЙ:
    # должность есть только внутри текста входящего сообщения.
    # Поле vacancy здесь не используется для создания CRM-сделки.
    # expected_position — только контрольное значение для сценария,
    # чтобы мы сами понимали, какой ответ ожидаем от AI.
    incoming_cases = [
        {
            "name": "Алексей",
            "surname": "Смирнов",
            "expected_position": "Водитель категории C",
            "message": "Здравствуйте! Ищу работу водителем категории C. Стаж 5 лет, готов выйти со следующей недели.",
            "priority": "Высокий",
            "delta": 30,
            "blocker": "Нужно ответить",
            "next": "Ответить кандидату",
        },
        {
            "name": "Екатерина",
            "surname": "Орлова",
            "expected_position": "Кладовщик",
            "message": "Добрый день! Ищу работу кладовщиком. Есть опыт на складе, могу работать посменно.",
            "priority": "Высокий",
            "delta": 60,
            "blocker": "Нужно ответить",
            "next": "Ответить кандидату",
        },
        {
            "name": "Роман",
            "surname": "Кузнецов",
            "expected_position": "Курьер",
            "message": "Здравствуйте! Хочу устроиться курьером. Есть опыт доставки, могу начать в ближайшее время.",
            "priority": "Средний",
            "delta": 90,
            "blocker": "Нужно ответить",
            "next": "Ответить кандидату",
        },
    ]
    for index, case in enumerate(incoming_cases):
        created.append(create_new_incoming_candidate(category_id, user_id, stages, case, index))

    existing_cases = [
        {"name":"Павел","surname":"Смирнов","vacancy":"Администратор","stage":"Квалификация","priority":"Высокий","delta":60,"blocker":"Новое сообщение","next":"Ответить кандидату","message":"А график работы какой? Могу работать посменно.","make_call":False},
        {"name":"Юлия","surname":"Орлова","vacancy":"Администратор","stage":"Интервью","priority":"Высокий","delta":30,"blocker":"Новое сообщение","next":"Ответить кандидату","message":"Подтвердите, пожалуйста, интервью на сегодня.","make_call":False},
        {"name":"Наталья","surname":"Волкова","vacancy":"Кладовщик","stage":"Документы","priority":"Высокий","delta":90,"blocker":"Новое сообщение","next":"Проверить документы","message":"Документы отправила. Проверьте, пожалуйста, дошли ли они.","make_call":False},
        {"name":"Денис","surname":"Иванов","vacancy":"Водитель","stage":"Передан заказчику","priority":"Высокий","delta":120,"blocker":"Новое сообщение","next":"Ответить кандидату","message":"Есть новости по моей кандидатуре от заказчика?","make_call":False},
    ]
    for index, case in enumerate(existing_cases, start=10):
        result = create_existing_candidate_with_incoming(category_id, user_id, stages, case, index, make_call=case["make_call"])
        created.append(result["deal_id"])

    quiet_cases = [
        {"name":"Глеб","surname":"Морозов","vacancy":"Менеджер","stage":"Ожидаем решение","priority":"Средний","delta":45,"next":"Запросить решение","blocker":"Нет решения"},
        {"name":"Николай","surname":"Соколов","vacancy":"Комплектовщик","stage":"Выход на работу","priority":"Высокий","delta":180,"next":"Подтвердить выход","blocker":"Выход сегодня"},
    ]
    now = datetime.now()
    for case in quiet_cases:
        deadline = now + timedelta(minutes=case["delta"])
        deal = call("crm.item.add", {
            "entityTypeId": 2,
            "useOriginalUfNames": "Y",
            "fields": {
                "title": f'{case["name"]} {case["surname"]}',
                "categoryId": category_id,
                "stageId": stages[case["stage"]],
                "assignedById": user_id,
                "comments": DEMO_COMMENT,
                DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: case["name"],
                DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: case["surname"],
                # Нет входящего текста → AI не заполняет должность.
                DEAL_FIELD_CODES["VACANCY"]: "",
                DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "StaffFlow Presentation",
                DEAL_FIELD_CODES["LAST_INBOUND_AT"]: (deadline - timedelta(minutes=SLA_MINUTES)).isoformat(timespec="seconds"),
                DEAL_FIELD_CODES["LAST_RESPONSE_AT"]: now.isoformat(timespec="seconds"),
                DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
                DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
                DEAL_FIELD_CODES["PRIORITY"]: case["priority"],
                DEAL_FIELD_CODES["BLOCKER"]: case["blocker"],
                DEAL_FIELD_CODES["NEXT_STEP"]: case["next"],
            },
        })
        deal_id = int(deal["item"]["id"])
        created.append(deal_id)
        call("crm.timeline.comment.add", {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": f'[PRESENTATION] Спокойная стадия: {case["stage"]}.',
            }
        })
    return created


def create_pipeline_snapshot(category_id, user_id, stages, count=24):
    """Создаёт плотный рабочий срез по стадиям без имитации входящих."""
    candidates = WORKDAY_SCENARIO[6:]
    created = 0
    for i in range(min(count, len(candidates))):
        scenario = candidates[i]
        name = f"{scenario['name']} — Demo"
        # В срезе используем ту же SLA-модель:
        # LAST_INBOUND_AT + SLA_MINUTES = RESPONSE_DEADLINE.
        now = datetime.now()
        inbound = now - timedelta(minutes=SLA_MINUTES - scenario["delta"])
        deadline = inbound + timedelta(minutes=SLA_MINUTES)
        fields = {
            DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: name,
            DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: "Демо",
            DEAL_FIELD_CODES["DESIRED_POSITION"]: scenario["vacancy"],
            DEAL_FIELD_CODES["VACANCY"]: "",
            DEAL_FIELD_CODES["PRIORITY"]: scenario["priority"],
            DEAL_FIELD_CODES["URGENCY"]: (
                urgency_level(deadline, now)
            ),
            DEAL_FIELD_CODES["BLOCKER"]: scenario["blocker"],
            DEAL_FIELD_CODES["NEXT_STEP"]: scenario["next"],
            DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
        }
        deal = call(
            "crm.item.add",
            {
                "entityTypeId": 2,
                "useOriginalUfNames": "Y",
                "fields": {
                    "title": name,
                    "categoryId": category_id,
                    "stageId": stages[scenario["stage"]],
                    "assignedById": user_id,
                    "comments": DEMO_COMMENT,
                    **fields,
                },
            },
        )
        deal_id = int(deal["item"]["id"])
        call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT": f"[WORKDAY SNAPSHOT] {scenario['comment']}",
                }
            },
        )
        created += 1
    return created


def delete_demo_tasks():
    deleted = 0
    data = call(
        "tasks.task.list",
        {
            "select": ["id", "title", "status"],
            "filter": {},
        },
    )
    tasks = (data or {}).get("tasks", [])
    for task in tasks:
        if task.get("title") == "Ответить кандидату":
            call("tasks.task.delete", {"taskId": int(task["id"])})
            deleted += 1
    return deleted


def delete_demo_contacts():
    deleted = 0
    while True:
        data = call(
            "crm.item.list",
            {
                "entityTypeId": 3,
                "select": ["id", "name", "lastName", "comments"],
                "filter": {"comments": "[DEMO] SLA simulator contact"},
            },
        )
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            call(
                "crm.item.delete",
                {"entityTypeId": 3, "id": item["id"]},
            )
            deleted += 1
    return deleted


def tag_latest_health_check_deal(category_id):
    """Помечает сделку, созданную реальным incoming health-check."""
    data = call(
        "crm.item.list",
        {
            "entityTypeId": 2,
            "select": ["id", "comments", "title", "categoryId"],
            "filter": {"categoryId": category_id},
            "order": {"id": "DESC"},
        },
    )
    items = data.get("items", [])
    if not items:
        raise RuntimeError("Health-check создал сделку, но её не удалось найти в CRM.")

    deal_id = int(items[0]["id"])
    current_comments = str(items[0].get("comments", "") or "")
    marker = "[STAFFFLOW HEALTH CHECK]"
    comments = (
        current_comments
        if marker in current_comments
        else f"{current_comments}\n{marker}".strip()
    )
    if DEMO_COMMENT not in comments:
        comments = f"{comments}\n{DEMO_COMMENT}".strip()

    call(
        "crm.item.update",
        {
            "entityTypeId": 2,
            "id": deal_id,
            "fields": {"comments": comments},
        },
    )
    return deal_id


def clear_demo_unread_dialogs():
    """Сбрасывает unread-счётчик после тестовых incoming-сообщений."""
    call("im.dialog.read.all", {})
    return True


def delete_demo(category_id):
    total = 0

    while True:
        data = call(
            "crm.item.list",
            {
                "entityTypeId": 2,
                "select": ["id", "comments", "title", "contactIds"],
                "filter": {"categoryId": category_id},
            },
        )
        items = data.get("items", [])
        sla_presentation_titles = {
            f'{case["name"]} {case["surname"]} · {case["vacancy"]}'
            for case in SLA_PRESENTATION_SCENARIO
        }
        targets = [
            item for item in items
            if item.get("comments") == DEMO_COMMENT
            or "SLA DEMO" in str(item.get("comments", ""))
            or str(item.get("title", "")).startswith("[DEMO]")
            or str(item.get("title", "")) in sla_presentation_titles
            or "StaffFlow Health Check" in str(item.get("title", ""))

        ]

        if not targets:
            break

        for item in targets:
            # Legacy incoming deals могли остаться без DEMO_COMMENT.
            # Перед удалением сделки сохраняем связанные контакты:
            # так чистим именно хвост Open Channel, а не все контакты CRM.
            for contact_id in item.get("contactIds", []) or []:
                try:
                    call(
                        "crm.item.delete",
                        {"entityTypeId": 3, "id": int(contact_id)},
                    )
                except Exception:
                    pass

            call(
                "crm.item.delete",
                {"entityTypeId": 2, "id": item["id"]},
            )
            total += 1

    return total


class App:
    def __init__(self, root):
        self.root = root
        root.title("StaffFlow — SLA Simulator")
        root.geometry("560x650")
        root.resizable(False, False)

        self.running = False
        self.thread = None
        self.pipeline_id = None
        self.user_id = None
        self.stages = {}
        self.scenario_index = 0
        self.created = 0

        frame = ttk.Frame(root, padding=22)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="STAFFFLOW — WORKDAY DEMO",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(0, 8))

        ttk.Label(
            frame,
            text="Генератор создаёт реальные рабочие ситуации: SLA, звонки, интервью, документы и заказчик",
            font=("Segoe UI", 10),
        ).pack(pady=(0, 18))

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=5)
        ttk.Label(row, text="Интервал между сделками:").pack(side="left")
        self.interval = tk.IntVar(value=15)
        ttk.Entry(row, textvariable=self.interval, width=7).pack(side="left", padx=8)
        ttk.Label(row, text="секунд").pack(side="left")

        ttk.Separator(frame).pack(fill="x", pady=14)

        ttk.Label(
            frame,
            text="Рабочий день рекрутёра",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text=(
                "1–6: входящие и SLA\n"
                "7–30: квалификация → интервью → документы → заказчик → выход"
            ),
            justify="left",
        ).pack(anchor="w", pady=8)

        row = ttk.Frame(frame)
        row.pack(pady=12)

        ttk.Button(
            row,
            text="▶ ЗАПУСТИТЬ РАБОЧИЙ ДЕНЬ",
            command=self.start_scenario,
        ).pack(side="left", padx=5)

        ttk.Button(
            row,
            text="⏸ ПАУЗА",
            command=self.pause,
        ).pack(side="left", padx=5)

        ttk.Button(
            row,
            text="▶ СОЗДАТЬ СЛЕДУЮЩУЮ",
            command=self.create_next,
        ).pack(side="left", padx=5)

        ttk.Separator(frame).pack(fill="x", pady=8)

        ttk.Button(
            frame,
            text="⏱ SLA: 8 КОНТРОЛЬНЫХ СДЕЛОК",
            command=self.create_sla_presentation,
        ).pack(anchor="w", pady=5)

        ttk.Button(
            frame,
            text="🎬 ФИНАЛЬНАЯ ПРЕЗЕНТАЦИЯ: SLA + AI + ВХОДЯЩИЕ + ВОРОНКА",
            command=self.create_presentation_scenario,
        ).pack(anchor="w", pady=5)

        ttk.Button(
            frame,
            text="СОЗДАТЬ СРЕЗ ВОРОНКИ (24 сделки)",
            command=self.create_pipeline_snapshot,
        ).pack(anchor="w", pady=5)
        ttk.Separator(frame).pack(fill="x", pady=14)

        ttk.Label(
            frame,
            text="Статус стенда",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        self.health_status = tk.StringVar(
            value="⚪ Не проверен"
        )
        ttk.Label(
            frame,
            textvariable=self.health_status,
            justify="left",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=6)

        ttk.Button(
            frame,
            text="🔍 ПРОВЕРИТЬ DEMO",
            command=self.health_check,
        ).pack(anchor="w", pady=(0, 10))

        ttk.Separator(frame).pack(fill="x", pady=10)

        ttk.Label(
            frame,
            text="Контроль стенда",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        row = ttk.Frame(frame)
        row.pack(pady=10)

        ttk.Button(
            row,
            text="🗑 УДАЛИТЬ ДЕМО-ДЕНЬ",
            command=self.delete_demo,
        ).pack(side="left", padx=5)

        ttk.Button(
            row,
            text="↻ СБРОСИТЬ СЦЕНАРИЙ",
            command=self.reset_scenario,
        ).pack(side="left", padx=5)

        self.status = tk.StringVar(value="Готов. Кандидатов в сценарии: 0 / 30")
        ttk.Label(
            frame,
            textvariable=self.status,
            font=("Segoe UI", 11),
        ).pack(pady=18)

        self.preview = tk.StringVar(
            value=(
                "Рабочий день:\n"
                "🔴 3 — просроченный SLA\n"
                "🟠 3 — SLA скоро истекает\n"
                "📞 4 — квалификация / нет ответа\n"
                "🎯 4 — интервью сегодня\n"
                "📄 4 — документы\n"
                "🤝 4 — ждём заказчика\n"
                "🚀 3 — выход на работу\n"
                "⏳ 4 — ждём решение"
            )
        )
        ttk.Label(
            frame,
            textvariable=self.preview,
            justify="left",
            font=("Consolas", 10),
        ).pack(anchor="w", pady=5)

    def ensure_ready(self):
        if self.pipeline_id is None:
            self.pipeline_id = get_pipeline()
        if self.user_id is None:
            self.user_id = get_current_user_id()
        if not self.stages:
            self.stages = stage_map(self.pipeline_id)

        missing = [x for x in WORK_STAGES if x not in self.stages]
        if missing:
            raise RuntimeError("Не найдены стадии: " + ", ".join(missing))

    def health_check(self):
        threading.Thread(target=self._health_check_worker, daemon=True).start()

    def _health_check_worker(self):
        results = []
        try:
            self.ensure_ready()
            results.append("🟢 Bitrix REST — OK")
        except Exception as error:
            results.append(f"🔴 Bitrix REST — {error}")

        try:
            check_connector()
            results.append("🟢 Connector /bitrix/app — OK")
        except Exception as error:
            results.append(f"🔴 Connector /bitrix/app — {error}")

        results.append(
            "🟡 Open Channel API status — проверяется не webhook'ом; "
            "реальная проверка ниже."
        )

        if CONNECTOR_TOKEN:
            try:
                before = count_pipeline_deals(self.pipeline_id)
                send_openline_test()
                after = wait_for_new_pipeline_deal(
                    self.pipeline_id,
                    before,
                    timeout=12,
                )
                if after > before:
                    # Health-check создаёт реальную CRM-сделку. Помечаем её
                    # тем же демо-маркером, чтобы кнопка очистки не оставляла
                    # после проверки «висячие» сделки.
                    tag_latest_health_check_deal(self.pipeline_id)
                    results.append(
                        f"🟢 Incoming → Open Channel → CRM — OK "
                        f"(сделок было {before}, стало {after})"
                    )
                else:
                    results.append(
                        "🔴 Incoming → CRM — сообщение отправлено connector'ом, "
                        "но новая CRM-сделка за 12 сек не появилась."
                    )
            except Exception as error:
                results.append(f"🔴 Incoming test — {error}")
        else:
            results.append(
                "🟡 Incoming test — не запущен: нет STAFFFLOW_SEND_TOKEN в .env"
            )

        text = "\n".join(results)
        self.root.after(0, lambda: self.health_status.set(text))

    def create_next(self):
        if self.running:
            return
        threading.Thread(target=self._create_next_worker, daemon=True).start()

    def _create_next_worker(self):
        try:
            self.ensure_ready()
            if self.scenario_index >= len(WORKDAY_SCENARIO):
                self.root.after(0, lambda: self.status.set("Сценарий завершён: 30 / 30"))
                return

            result = create_sla_candidate(
                self.pipeline_id,
                self.user_id,
                self.stages,
                self.scenario_index,
            )
            self.scenario_index += 1
            self.created += 1

            scenario = WORKDAY_SCENARIO[self.scenario_index - 1]
            name = scenario["name"]
            priority = scenario["priority"]
            delta = scenario["delta"]
            answered = scenario["answered"]
            if delta < 0:
                timing = f"просрочено на {abs(delta)} мин"
            elif answered:
                timing = "уже ответили"
            else:
                timing = f"осталось {delta} мин"

            self.root.after(
                0,
                lambda: self.status.set(
                    f"Создано {self.created} / {len(WORKDAY_SCENARIO)}: "
                    f"{name} — {priority} — {timing}"
                ),
            )
        except Exception as error:
            error_text = f"{type(error).__name__}: {error}\n\n{traceback.format_exc()}"
            self.root.after(0, lambda msg=error_text: messagebox.showerror("Ошибка", msg))

    def create_sla_presentation(self):
        threading.Thread(target=self._create_sla_presentation_worker, daemon=True).start()

    def _create_sla_presentation_worker(self):
        try:
            self.ensure_ready()
            created = create_sla_presentation(
                self.pipeline_id,
                self.user_id,
                self.stages,
            )
            self.root.after(
                0,
                lambda: self.status.set(
                    f"SLA-сценарий создан: {len(created)} сделки — 2× каждое состояние"
                ),
            )
        except Exception as error:
            error_text = repr(error)
            self.root.after(0, lambda msg=error_text: messagebox.showerror("Ошибка SLA", msg))

    def create_presentation_scenario(self):
        threading.Thread(target=self._create_presentation_scenario_worker, daemon=True).start()

    def _create_presentation_scenario_worker(self):
        try:
            self.ensure_ready()
            created = create_presentation_scenario(
                self.pipeline_id,
                self.user_id,
                self.stages,
            )
            self.root.after(
                0,
                lambda: self.status.set(
                    f"Презентация создана: {len(created)} кандидатов — SLA + входящие + список/канбан"
                ),
            )
        except Exception as error:
            error_text = repr(error)
            self.root.after(0, lambda msg=error_text: messagebox.showerror("Ошибка презентации", msg))

    def create_pipeline_snapshot(self):
        threading.Thread(target=self._create_pipeline_snapshot_worker, daemon=True).start()

    def _create_pipeline_snapshot_worker(self):
        try:
            self.ensure_ready()
            created = create_pipeline_snapshot(
                self.pipeline_id,
                self.user_id,
                self.stages,
                count=24,
            )
            self.root.after(
                0,
                lambda: self.status.set(
                    f"Создан срез воронки: {created} сделок по рабочим стадиям"
                ),
            )
        except Exception as error:
            error_text = repr(error)
            self.root.after(0, lambda msg=error_text: messagebox.showerror("Ошибка", msg))

    def start_scenario(self):
        if self.running:
            return

        try:
            interval = max(int(self.interval.get()), 1)
        except ValueError:
            messagebox.showerror("Ошибка", "Интервал должен быть целым числом.")
            return

        if self.scenario_index >= len(WORKDAY_SCENARIO):
            messagebox.showinfo("Сценарий", "Сценарий уже завершён. Нажмите «Сбросить сценарий».")
            return

        self.running = True
        self.status.set("Сценарий запущен")
        self.thread = threading.Thread(
            target=self.loop,
            args=(interval,),
            daemon=True,
        )
        self.thread.start()

    def loop(self, interval):
        while self.running and self.scenario_index < len(WORKDAY_SCENARIO):
            self._create_next_worker()
            if self.running and self.scenario_index < len(WORKDAY_SCENARIO):
                time.sleep(interval)

        self.running = False
        self.root.after(
            0,
            lambda: self.status.set(
                f"Сценарий завершён: {self.created} / {len(WORKDAY_SCENARIO)}"
            ),
        )

    def pause(self):
        self.running = False
        self.status.set(f"Пауза: {self.created} / {len(WORKDAY_SCENARIO)}")

    def reset_scenario(self):
        self.pause()
        self.scenario_index = 0
        self.created = 0
        self.status.set("Сценарий сброшен: 0 / 30")

    def delete_demo(self):
        if not messagebox.askyesno(
            "Удалить демо-день",
            "Удалить все тестовые сделки StaffFlow из воронки «Подбор персонала»?",
        ):
            return

        if getattr(self, "_delete_running", False):
            return

        self._delete_running = True
        self.pause()
        self.status.set("Удаление демо-данных…")

        threading.Thread(
            target=self._delete_demo_worker,
            daemon=True,
        ).start()

    def _delete_demo_worker(self):
        try:
            self.ensure_ready()
            deleted = delete_demo(self.pipeline_id)
            deleted_contacts = delete_demo_contacts()
            deleted_tasks = delete_demo_tasks()

            unread_status = "непрочитанные диалоги сброшены"
            try:
                clear_demo_unread_dialogs()
            except Exception as error:
                unread_status = f"непрочитанные диалоги НЕ сброшены: {error}"

            self.scenario_index = 0
            self.created = 0
            self.root.after(
                0,
                lambda: self.status.set(
                    f"Удалено: сделки {deleted}, контакты {deleted_contacts}, "
                    f"задачи «Ответить кандидату» {deleted_tasks}; "
                    f"{unread_status}. Готово к новому запуску."
                ),
            )
        except Exception as error:
            error_text = f"{type(error).__name__}: {error}\n\n{traceback.format_exc()}"
            self.root.after(
                0,
                lambda msg=error_text: messagebox.showerror("Ошибка удаления", msg),
            )
            self.root.after(
                0,
                lambda: self.status.set("Ошибка удаления демо-данных"),
            )
        finally:
            self._delete_running = False


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
