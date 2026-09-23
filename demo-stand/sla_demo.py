from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bitrix import BitrixClient
from schema import DEAL_FIELD_CODES

DEMO_COMMENT = "Синтетические SLA-демо-данные для тестовой презентации."

# Four fixed SLA checkpoints for the demo stand:
# +3h -> Не срочно, +1h30m -> Скоро, +30m -> Сейчас, -10m -> Просрочено.
CASES = [
    ("Иван Петров", "Водитель", "Высокий", 180),
    ("Марина Соколова", "Кладовщик", "Высокий", 90),
    ("Дмитрий Волков", "Курьер", "Средний", 30),
    ("Ольга Морозова", "Оператор", "Высокий", -10),
]


def stage_map(client: BitrixClient, category_id: int) -> dict[str, str]:
    return {x["NAME"]: x["STATUS_ID"] for x in client.list_stages(category_id)}


def clear_sla_demo(client: BitrixClient, category_id: int) -> int:
    removed = 0
    while True:
        data = client.call("crm.item.list", {
            "entityTypeId": 2,
            "select": ["id", "comments"],
            "filter": {"categoryId": category_id},
        })
        items = data.get("items", [])
        if not items:
            break

        found = False
        for item in items:
            if item.get("comments") == DEMO_COMMENT:
                client.delete_deal(int(item["id"]))
                removed += 1
                found = True

        if not found:
            break

    return removed


def run(client: BitrixClient, category_id: int, user_id: int) -> None:
    stages = stage_map(client, category_id)
    stage_id = stages.get("Новый кандидат")
    if not stage_id:
        raise RuntimeError("Stage not found: Новый кандидат")

    now = datetime.now(timezone.utc)
    print("Creating 4 SLA demo candidates...")

    for person, vacancy, priority, deadline_delta in CASES:
        deadline = now + timedelta(minutes=deadline_delta)
        inbound = deadline - timedelta(hours=2)

        first, last = person.split(" ", 1)
        fields = {
            DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: first,
            DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: last,
            DEAL_FIELD_CODES["CANDIDATE_PHONE"]: f"+7900{1000000 + len(person) * 137}",
            DEAL_FIELD_CODES["DESIRED_POSITION"]: vacancy,
            DEAL_FIELD_CODES["VACANCY"]: vacancy,
            DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "Другое",
            DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["PRIORITY"]: priority,
            DEAL_FIELD_CODES["BLOCKER"]: "Нужно ответить",
            DEAL_FIELD_CODES["NEXT_STEP"]: "Ответить кандидату",
            DEAL_FIELD_CODES["NEXT_ACTION_AT"]: now.isoformat(timespec="seconds"),
        }

        deal_id = client.add_deal(
            title=f"{person} · {vacancy}",
            category_id=category_id,
            stage_id=stage_id,
            assigned_by_id=user_id,
            comments=DEMO_COMMENT,
            fields=fields,
        )
        client.add_timeline_comment(
            deal_id,
            f"[SLA DEMO] Новый кандидат: интересуется вакансией «{vacancy}».",
        )

        print(
            f"{deal_id}: {person} | {vacancy} | "
            f"deadline {deadline.isoformat(timespec='minutes')} | "
            f"delta {deadline_delta:+d}m"
        )
