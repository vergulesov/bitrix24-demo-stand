from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from bitrix import BitrixClient
from schema import DEAL_FIELD_CODES


DEMO_COMMENT = "Синтетические демо-данные для тестовой презентации."

MALE_LAST_NAMES = [
    "Петров", "Кузнецов", "Волков", "Орлов", "Васильев", "Иванов",
]

FEMALE_LAST_NAMES = [
    "Соколова", "Морозова", "Лебедева", "Фёдорова", "Смирнова", "Попова",
]

MALE_FIRST_NAMES = [
    "Василий", "Пётр", "Сергей", "Дмитрий", "Андрей", "Александр",
    "Максим", "Артём", "Виктор", "Роман",
]

FEMALE_FIRST_NAMES = [
    "Анна", "Ольга", "Екатерина", "Наталья", "Марина", "Ирина",
    "Елена", "Виктория", "Юлия",
]

VACANCIES = [
    "Водитель", "Курьер", "Оператор", "Менеджер по продажам",
    "Кладовщик", "Комплектовщик", "Администратор", "Водитель-экспедитор",
]

DIRECTIONS = {
    "Водитель": "Логистика",
    "Курьер": "Логистика",
    "Водитель-экспедитор": "Логистика",
    "Кладовщик": "Логистика",
    "Комплектовщик": "Производство",
    "Оператор": "Административный персонал",
    "Администратор": "Административный персонал",
    "Менеджер по продажам": "Продажи",
}

SOURCES = ["HH.ru", "Telegram", "Сайт", "Рекомендация"]

STAGES = [
    "Новый кандидат",
    "Квалификация",
    "Интервью",
    "Ожидаем решение",
    "Документы",
    "Передан заказчику",
    "Выход на работу",
    "Отказ",
]

CLIENTS = [
    "ООО «Стандарт»",
    "ООО «Вектор»",
    "ООО «Логистик Плюс»",
    "ООО «Север»",
]

SCENARIOS = {
    "Новый кандидат": [
        ("Нужно ответить", "Связаться"),
        ("Нужно ответить", "Ответить кандидату"),
    ],
    "Квалификация": [
        ("Не хватает информации", "Уточнить опыт"),
        ("Назначить интервью", "Назначить интервью"),
    ],
    "Интервью": [
        ("Ждём кандидата", "Провести интервью"),
        ("Назначить интервью", "Согласовать время интервью"),
    ],
    "Ожидаем решение": [
        ("Ждём кандидата", "Получить подтверждение кандидата"),
        ("Ждём заказчика", "Уточнить решение заказчика"),
    ],
    "Документы": [
        ("Ждём кандидата", "Получить комплект документов"),
        ("Не хватает информации", "Проверить документы"),
    ],
    "Передан заказчику": [
        ("Ждём заказчика", "Получить обратную связь"),
    ],
    "Выход на работу": [
        ("Другое", "Контроль выхода"),
    ],
    "Отказ": [
        ("Другое", "Зафиксировать причину отказа"),
    ],
}


def stage_by_name(client: BitrixClient, category_id: int) -> dict[str, str]:
    return {item["NAME"]: item["STATUS_ID"] for item in client.list_stages(category_id)}


def reset_demo(client: BitrixClient, category_id: int) -> int:
    deals = client.list_deals(category_id)
    removed = 0

    for deal in deals:
        if deal.get("comments") == DEMO_COMMENT:
            client.delete_deal(int(deal["id"]))
            removed += 1

    print(f"Removed demo deals: {removed}")
    return removed


def random_candidate() -> tuple[str, str, str, str | None, str | None, str | None, str | None, str | None]:
    is_male = random.random() < 0.55
    first = random.choice(MALE_FIRST_NAMES if is_male else FEMALE_FIRST_NAMES)
    surname = random.choice(MALE_LAST_NAMES if is_male else FEMALE_LAST_NAMES) if random.random() < 0.7 else None

    if surname:
        person = f"{first} {surname}"
    else:
        person = first

    vacancy = random.choice(VACANCIES)

    # Contacts are intentionally incomplete in the demo.
    phone = f"+7 9{random.randint(10, 99)} {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}" if random.random() < 0.75 else None
    telegram = f"@{first.lower()}_{random.randint(100, 999)}" if random.random() < 0.65 else None

    whatsapp = phone if phone and random.random() < 0.8 else None
    max_contact = f"@{first.lower()}_{random.randint(100, 999)}" if random.random() < 0.45 else None

    return person, vacancy, first, surname, phone, telegram, whatsapp, max_contact


def demo_timestamps(stage_name: str) -> tuple[str, str | None, str]:
    now = datetime.now(timezone.utc)

    if stage_name == "Новый кандидат":
        age_minutes = random.choice([8, 18, 35, 65, 125, 210])
        inbound = now - timedelta(minutes=age_minutes)
        deadline = inbound + timedelta(hours=2)
        response = None
        return inbound.isoformat(timespec="seconds"), response, deadline.isoformat(timespec="seconds")

    if stage_name in {"Квалификация", "Интервью"}:
        age_hours = random.choice([3, 6, 12, 24, 36])
    else:
        age_hours = random.choice([12, 24, 36, 48, 72, 120])

    inbound = now - timedelta(hours=age_hours)
    response = inbound + timedelta(minutes=random.choice([20, 45, 90]))
    deadline = inbound + timedelta(hours=2)
    return inbound.isoformat(timespec="seconds"), response.isoformat(timespec="seconds"), deadline.isoformat(timespec="seconds")


def seed_demo(
    client: BitrixClient,
    category_id: int,
    user_id: int,
    count: int = 30,
) -> None:
    stages = stage_by_name(client, category_id)

    for _ in range(count):
        person, vacancy, first, surname, phone, telegram, whatsapp, max_contact = random_candidate()
        stage_name = random.choice(STAGES)
        stage_id = stages.get(stage_name)

        if not stage_id:
            raise RuntimeError(f"Stage not found: {stage_name}")

        blocker, next_step = random.choice(SCENARIOS[stage_name])
        inbound_at, response_at, deadline_at = demo_timestamps(stage_name)

        fields = {
            DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: first,
            DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: surname or "",
            DEAL_FIELD_CODES["CANDIDATE_PHONE"]: phone or "",
            DEAL_FIELD_CODES["CANDIDATE_TELEGRAM"]: telegram or "",
            DEAL_FIELD_CODES["CANDIDATE_WHATSAPP"]: whatsapp or "",
            DEAL_FIELD_CODES["CANDIDATE_MAX"]: max_contact or "",
            DEAL_FIELD_CODES["DESIRED_POSITION"]: vacancy,
            DEAL_FIELD_CODES["DIRECTION"]: DIRECTIONS[vacancy],
            DEAL_FIELD_CODES["VACANCY"]: vacancy,
            DEAL_FIELD_CODES["CLIENT_COMPANY"]: random.choice(CLIENTS),
            DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: random.choice(SOURCES),
            DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound_at,
            DEAL_FIELD_CODES["LAST_RESPONSE_AT"]: response_at or "",
            DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline_at,
            DEAL_FIELD_CODES["PRIORITY"]: random.choice(["Высокий", "Средний", "Низкий"]),
            DEAL_FIELD_CODES["BLOCKER"]: blocker,
            DEAL_FIELD_CODES["NEXT_STEP"]: next_step,
            DEAL_FIELD_CODES["NEXT_ACTION_AT"]: (
                (datetime.now(timezone.utc) + timedelta(minutes=random.choice([30, 60, 120, 240]))).isoformat(timespec="seconds")
            ),
        }

        identifier = (
            phone.replace("+7 ", "")
            if phone
            else telegram
            or max_contact
            or f"КАН-{random.randint(10000, 99999)}"
        )
        deal_id = client.add_deal(
            title=f"{person} · {identifier}",
            category_id=category_id,
            stage_id=stage_id,
            assigned_by_id=user_id,
            comments=DEMO_COMMENT,
            fields=fields,
        )

        add_demo_timeline(client, deal_id, person, vacancy, stage_name, inbound_at, response_at)

        print(
            f"Created: {person} — {vacancy} — {stage_name}"
            f" | phone={'yes' if phone else 'no'}"
            f" | tg={'yes' if telegram else 'no'}"
            f" | wa={'yes' if whatsapp else 'no'}"
            f" | max={'yes' if max_contact else 'no'}"
            f" | blocker={blocker}"
        )


def add_demo_timeline(
    client: BitrixClient,
    deal_id: int,
    person: str,
    vacancy: str,
    stage_name: str,
    inbound_at: str,
    response_at: str | None,
) -> None:
    messages = [
        f"[{inbound_at}] Кандидат: «Здравствуйте! Подскажите, пожалуйста, вакансия «{vacancy}» ещё актуальна?»",
    ]

    if response_at:
        messages.append(
            f"[{response_at}] Рекрутер: «Здравствуйте, {person.split()[0]}! Да, вакансия актуальна. Давайте уточним несколько деталей.»"
        )

    if stage_name in {"Квалификация", "Интервью", "Ожидаем решение", "Документы", "Передан заказчику", "Выход на работу", "Отказ"}:
        messages.append(
            f"[сегодня] Кандидат: «Да, готов продолжить. Когда можем обсудить следующий шаг?»"
        )

    if stage_name == "Документы":
        messages.append("[сегодня] Рекрутер: «Отлично. Тогда жду комплект документов для оформления.»")
    elif stage_name == "Передан заказчику":
        messages.append("[сегодня] Рекрутер: «Передал ваш профиль заказчику. Вернусь с обратной связью.»")
    elif stage_name == "Выход на работу":
        messages.append("[сегодня] Рекрутер: «Выход подтверждён. Остаёмся на связи.»")
    elif stage_name == "Отказ":
        messages.append("[сегодня] Рекрутер: «Спасибо за обратную связь. Зафиксировал результат.»")

    for message in messages:
        client.add_timeline_comment(deal_id, message)


def run(
    client: BitrixClient,
    category_id: int,
    user_id: int,
    count: int = 30,
) -> None:
    reset_demo(client, category_id)
    seed_demo(client, category_id, user_id, count=count)


def clear(client: BitrixClient, category_id: int) -> None:
    reset_demo(client, category_id)
