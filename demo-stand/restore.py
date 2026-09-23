from __future__ import annotations

import argparse
from typing import Any

from bitrix import BitrixClient


def find_last_openline_chat(client: BitrixClient) -> dict[str, Any]:
    """Find the latest Open Line chat through the documented CRM method."""
    result = client.call(
        "crm.item.list",
        {
            "entityTypeId": 2,
            "select": ["id", "title", "categoryId", "stageId"],
            "order": {"id": "DESC"},
            "start": 0,
        },
    ) or {}

    deals = result.get("items") or []
    print(f"Checking last Open Line chat for {len(deals[:30])} recent deals")

    for deal in deals[:30]:
        deal_id = int(deal["id"])
        try:
            chat_id = client.call(
                "imopenlines.crm.chat.getLastId",
                {
                    "CRM_ENTITY_TYPE": "deal",
                    "CRM_ENTITY": deal_id,
                },
            )
        except Exception:
            continue

        if chat_id:
            print(
                f"Found Open Line chat: deal={deal_id}, "
                f"CHAT_ID={chat_id}, title={deal.get('title')!r}"
            )
            return {
                "chat_id": int(chat_id),
                "deal_id": deal_id,
                "deal": deal,
            }

    raise RuntimeError("No Open Line chat found on recent deals")


def get_dialog(client: BitrixClient, chat_id: int) -> dict[str, Any]:
    return client.call("imopenlines.dialog.get", {"CHAT_ID": chat_id})


def get_history(client: BitrixClient, chat_id: int) -> dict[str, Any]:
    return client.call(
        "imopenlines.session.history.get",
        {"CHAT_ID": chat_id},
    )


def print_diagnostic(
    chat: dict[str, Any],
    dialog: dict[str, Any],
    history: dict[str, Any],
) -> None:
    chat_id = chat["chat_id"]
    deal_id = chat["deal_id"]

    print("\n=== OPEN LINE DIAGNOSTIC ===")
    print(f"CRM deal:       {deal_id}")
    print(f"CRM title:      {chat['deal'].get('title')}")
    print(f"CHAT_ID:        {chat_id}")
    print(f"USER_CODE:      {dialog.get('entity_id')}")
    print(f"ENTITY_DATA_1:  {dialog.get('entity_data_1')}")
    print(f"ENTITY_DATA_2:  {dialog.get('entity_data_2')}")
    print(f"ENTITY_DATA_3:  {dialog.get('entity_data_3')}")

    messages = history.get("message", {}) or {}
    ordered = sorted(
        messages.values(),
        key=lambda item: (item.get("date") or "", int(item.get("id", 0))),
    )

    print(f"HISTORY MESSAGES: {len(ordered)}")
    for item in ordered:
        text = str(item.get("textlegacy") or item.get("text") or "").strip()
        if text:
            print(
                f"  [{item.get('date')}] "
                f"sender={item.get('senderid')}: {text}"
            )

    print("============================\n")


def run(client: BitrixClient) -> None:
    chat = find_last_openline_chat(client)
    dialog = get_dialog(client, chat["chat_id"])
    history = get_history(client, chat["chat_id"])
    print_diagnostic(chat, dialog, history)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Диагностика Telegram/Open Line через Bitrix REST"
    )
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Показать CHAT_ID, USER_CODE, CRM binding и историю",
    )
    args = parser.parse_args()

    from config import get_settings

    client = BitrixClient(get_settings().webhook)
    run(client)


if __name__ == "__main__":
    main()
