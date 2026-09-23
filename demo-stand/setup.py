from __future__ import annotations

from typing import Any

from bitrix import BitrixClient
from config import get_settings
from schema import DEAL_FIELD_CODES, DEAL_FIELD_SPECS


PROCESS_STAGES = [
    ("NEW_CANDIDATE", "Новый кандидат"),
    ("QUALIFICATION", "Квалификация"),
    ("INTERVIEW", "Интервью"),
    ("WAITING_DECISION", "Ожидаем решение"),
    ("DOCUMENTS", "Документы"),
    ("SENT_TO_CLIENT", "Передан заказчику"),
]

FINAL_STAGE_NAMES = {"Выход на работу", "Отказ"}

LEGACY_STAGE_NAMES = {
    "Новая",
    "Подготовка документов",
    "Счёт на предоплату",
    "Cчёт на предоплату",
    "Финальный счёт",
    "В работе",
    "Анализ причины провала",
}

LEGACY_STAGE_CODES = {
    "NEW",
    "PREPARATION",
    "PREPAYMENT_INVOICE",
    "FINAL_INVOICE",
    "EXECUTING",
    "APOLOGY",
    "NEEDS_CONTACT",
    "CONTACTED",
}


def find_category(client: BitrixClient, name: str) -> dict | None:
    for category in client.list_categories():
        if category.get("name") == name:
            return category
    return None


def ensure_pipeline(client: BitrixClient, name: str) -> int:
    existing = find_category(client, name)
    if existing:
        return int(existing["id"])
    return client.add_category(name)


def ensure_department(client: BitrixClient, name: str, head_id: int) -> int:
    departments = client.list_departments()

    for department in departments:
        if department.get("NAME") == name:
            return int(department["ID"])

    # Bitrix allows only one top-level department. New departments
    # therefore have to be created under the existing company root.
    root = next(
        (
            department
            for department in departments
            if not department.get("PARENT")
        ),
        None,
    )

    if not root:
        raise RuntimeError(
            "Company root department was not found; cannot create recruitment department."
        )

    return client.add_department(
        name=name,
        parent=int(root["ID"]),
        head_id=head_id,
    )


def ensure_stages(client: BitrixClient, category_id: int) -> None:
    existing = client.list_stages(category_id)

    success = next(
        (
            stage
            for stage in existing
            if stage.get("SEMANTICS") == "S"
            or stage.get("EXTRA", {}).get("SEMANTICS") == "success"
        ),
        None,
    )
    failure = next(
        (
            stage
            for stage in existing
            if stage.get("SEMANTICS") == "F"
            or stage.get("EXTRA", {}).get("SEMANTICS") in ("failure", "apology")
        ),
        None,
    )

    if not success or not failure:
        raise RuntimeError(
            "Bitrix final Success/Failure stages were not found in the pipeline."
        )

    existing_codes = {
        str(stage.get("STATUS_ID", "")).split(":", 1)[-1]
        for stage in existing
    }

    first_final_sort = min(
        int(success.get("SORT", 0) or 0),
        int(failure.get("SORT", 0) or 0),
    )

    missing = [
        item for item in PROCESS_STAGES
        if item[0] not in existing_codes
    ]

    if missing:
        step = max(1, first_final_sort // (len(missing) + 1))
        sort = step

        for status_id, name in missing:
            client.add_stage(
                category_id=category_id,
                name=name,
                status_id=status_id,
                sort=sort,
                semantics="",
            )
            sort += step

    stages = client.list_stages(category_id)

    desired_names = {name for _, name in PROCESS_STAGES} | FINAL_STAGE_NAMES

    # Legacy stages cannot be deleted while deals still reference them.
    # Move those deals into the new first stage, then remove the legacy statuses.
    legacy_ids = {
        str(stage.get("STATUS_ID"))
        for stage in stages
        if stage.get("NAME") in LEGACY_STAGE_NAMES
        or str(stage.get("STATUS_ID", "")).split(":", 1)[-1] in LEGACY_STAGE_CODES
    }
    if legacy_ids:
        deals = client.list_deals(category_id)
        new_stage_id = f"C{category_id}:NEW_CANDIDATE"
        moved = 0
        for deal in deals:
            if str(deal.get("stageId", "")) in legacy_ids:
                client.update_deal_stage(int(deal["id"]), new_stage_id)
                moved += 1
        if moved:
            print(f"Legacy deals moved to Новый кандидат: {moved}")

    for stage in stages:
        code = str(stage.get("STATUS_ID", "")).split(":", 1)[-1]
        if stage.get("NAME") in LEGACY_STAGE_NAMES or code in LEGACY_STAGE_CODES:
            client.delete_status(int(stage["ID"]), forced=True)

    stages = client.list_stages(category_id)

    success = next(
        stage for stage in stages
        if stage.get("SEMANTICS") == "S"
        or stage.get("EXTRA", {}).get("SEMANTICS") == "success"
    )
    failure = next(
        stage for stage in stages
        if stage.get("SEMANTICS") == "F"
        or stage.get("EXTRA", {}).get("SEMANTICS") in ("failure", "apology")
    )

    # Keep the working stages in the exact business order.
    process_by_code = {
        str(stage.get("STATUS_ID", "")).split(":", 1)[-1]: stage
        for stage in stages
    }
    for index, (status_id, _) in enumerate(PROCESS_STAGES, start=1):
        stage = process_by_code.get(status_id)
        if not stage:
            raise RuntimeError(f"Missing process stage: {status_id}")
        client.update_status(
            int(stage["ID"]),
            {"SORT": index * 10},
        )

    client.update_status(int(success["ID"]), {
        "NAME": "Выход на работу",
        "SORT": 70,
    })
    client.update_status(int(failure["ID"]), {
        "NAME": "Отказ",
        "SORT": 80,
    })

    stages = client.list_stages(category_id)
    actual_names = {stage.get("NAME") for stage in stages}
    missing_names = desired_names - actual_names
    if missing_names:
        raise RuntimeError(f"Missing configured stages: {sorted(missing_names)}")


def _field_payload(spec: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "FIELD_NAME": spec["field_name"],
        "USER_TYPE_ID": spec["type"],
        "MULTIPLE": "N",
        "MANDATORY": "N",
        "SHOW_FILTER": "Y",
        "SHOW_IN_LIST": "Y",
        "EDIT_IN_LIST": "Y",
        "IS_SEARCHABLE": "Y" if spec["type"] == "string" else "N",
        "SORT": spec["sort"],
        "EDIT_FORM_LABEL": {"ru": spec["label"]},
        "LIST_COLUMN_LABEL": {"ru": spec["label"]},
        "LIST_FILTER_LABEL": {"ru": spec["label"]},
    }

    if spec["type"] == "enumeration":
        payload["LIST"] = [
            {
                "VALUE": value,
                "SORT": (index + 1) * 100,
                "DEF": "N",
                "XML_ID": f"{spec['field_name']}_{index + 1}",
            }
            for index, value in enumerate(spec["values"])
        ]
        payload["SETTINGS"] = {
            "DISPLAY": "UI",
            "LIST_HEIGHT": 1,
        }
    elif spec["type"] == "string":
        payload["SETTINGS"] = {
            "SIZE": 50,
            "ROWS": 1,
        }

    return payload


def ensure_deal_fields(client: BitrixClient) -> None:
    existing = {
        item.get("FIELD_NAME"): item
        for item in client.list_deal_userfields()
    }

    for spec in DEAL_FIELD_SPECS:
        field_name = f"UF_CRM_{spec['field_name']}"
        if field_name in existing:
            field = existing[field_name]
            update_fields = {
                "SHOW_IN_LIST": "Y" if spec["field_name"] in {
                    "URGENCY",
                    "VACANCY",
                    "RESPONSE_DEADLINE",
                    "NEXT_STEP",
                } else "N",
                "EDIT_FORM_LABEL": {"ru": spec["label"]},
                "LIST_COLUMN_LABEL": {"ru": spec["label"]},
                "LIST_FILTER_LABEL": {"ru": spec["label"]},
            }
            client.update_deal_userfield(int(field["ID"]), update_fields)
            continue

        field_id = client.add_deal_userfield(_field_payload(spec))
        print(f"Deal field: {spec['label']} ({field_name}, ID {field_id})")


def configure_deal_card(
    client: BitrixClient,
    category_id: int,
) -> None:
    fields = DEAL_FIELD_CODES

    data = [
        {
            "name": "candidate",
            "title": "Кандидат",
            "type": "section",
            "elements": [
                {"name": "TITLE", "optionFlags": 1},
                {"name": "CREATED_TIME", "optionFlags": 1},
                {"name": fields["CANDIDATE_FIRST_NAME"], "optionFlags": 1},
                {"name": fields["CANDIDATE_LAST_NAME"], "optionFlags": 1},
                {"name": fields["CANDIDATE_PHONE"], "optionFlags": 1},
                {"name": fields["CANDIDATE_TELEGRAM"], "optionFlags": 1},
                {"name": fields["CANDIDATE_WHATSAPP"], "optionFlags": 1},
                {"name": fields["CANDIDATE_MAX"], "optionFlags": 1},
                {"name": fields["DESIRED_POSITION"], "optionFlags": 1},
                {"name": fields["DIRECTION"], "optionFlags": 1},
                {"name": fields["VACANCY"], "optionFlags": 1},
                {"name": fields["CLIENT_COMPANY"], "optionFlags": 1},
                {"name": fields["CANDIDATE_SOURCE"], "optionFlags": 1},
                {"name": "ASSIGNED_BY_ID", "optionFlags": 1},
                {"name": "STAGE_ID", "optionFlags": 1},
            ],
        },
        {
            "name": "processing",
            "title": "Контроль обработки",
            "type": "section",
            "elements": [
                {"name": fields["LAST_INBOUND_AT"], "optionFlags": 1},
                {"name": fields["RESPONSE_DEADLINE"], "optionFlags": 1},
                {"name": fields["URGENCY"], "optionFlags": 1},
                {"name": fields["NEXT_STEP"], "optionFlags": 1},
            ],
        },
        {
            "name": "comments",
            "title": "История",
            "type": "section",
            "elements": [
                {"name": "COMMENTS"},
            ],
        },
    ]

    client.set_deal_card_configuration(category_id, data)
    print("Deal card: configured")


def setup() -> int:
    settings = get_settings()
    client = BitrixClient(settings.webhook)

    me = client.get_current_user()
    user_id = int(me["ID"])

    print(
        f"Connected as: {me.get('NAME', '')} "
        f"{me.get('LAST_NAME', '')} (ID {user_id})"
    )

    department_id = ensure_department(client, "Подбор персонала", user_id)
    print(f"Department: Подбор персонала (ID {department_id})")

    pipeline_id = ensure_pipeline(client, "Подбор персонала")
    print(f"Pipeline: Подбор персонала (ID {pipeline_id})")

    ensure_stages(client, pipeline_id)
    print("Stages configured: 8")

    ensure_deal_fields(client)
    configure_deal_card(client, pipeline_id)

    return pipeline_id


if __name__ == "__main__":
    setup()
