from __future__ import annotations

import sys

from bitrix import BitrixClient
from config import get_settings
from demo import clear as clear_demo
from demo import run as run_demo
from setup import ensure_pipeline, setup
from restore import run as restore_test
from sla_demo import run as run_sla_demo


def make_client() -> BitrixClient:
    return BitrixClient(get_settings().webhook)


def check() -> None:
    client = make_client()
    me = client.get_current_user()
    print("REST OK")
    print(f"User: {me.get('NAME', '')} {me.get('LAST_NAME', '')}")
    print(f"ID: {me.get('ID')}")


def demo(count: int = 30) -> None:
    client = make_client()
    me = client.get_current_user()
    pipeline_id = ensure_pipeline(client, "Подбор персонала")
    run_demo(client, pipeline_id, int(me["ID"]), count=count)


def clear() -> None:
    client = make_client()
    pipeline_id = ensure_pipeline(client, "Подбор персонала")
    clear_demo(client, pipeline_id)




def cleanup_old_test() -> None:
    """Удалить старые ручные тестовые CRM-сущности, не затрагивая Open Line deal 423."""
    client = make_client()

    try:
        result = client.call(
            "crm.item.delete",
            {"entityTypeId": 2, "id": 419},
        )
        print(f"Deleted old test deal 419: {result}")
    except Exception as exc:
        print(f"Deal 419: {exc}")

    try:
        result = client.call(
            "crm.item.delete",
            {"entityTypeId": 3, "id": 3},
        )
        print(f"Deleted old test contact 3: {result}")
    except Exception as exc:
        print(f"Contact 3: {exc}")

def sla_demo() -> None:
    client = make_client()
    me = client.get_current_user()
    pipeline_id = ensure_pipeline(client, "Подбор персонала")
    run_sla_demo(client, pipeline_id, int(me["ID"]))


def inspect() -> None:
    client = make_client()
    categories = client.list_categories()

    print("CRM deal pipelines:")
    for category in categories:
        category_id = int(category["id"])
        name = category.get("name", "")
        print(f"\n[{category_id}] {name}")

        for stage in client.list_stages(category_id):
            print(
                f"  {stage.get('SORT'):>4} | "
                f"{stage.get('STATUS_ID')} | "
                f"{stage.get('NAME')} | "
                f"semantics={stage.get('SEMANTICS', '')}"
            )

def usage() -> None:
    print("Usage: python main.py [check|setup|demo|demo-new N|demo-clear|sla-demo|restore-test|cleanup-old-test|inspect]")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""

    if command == "check":
        check()
    elif command == "setup":
        setup()
    elif command == "demo":
        demo()
    elif command == "demo-new":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        demo(count=count)
    elif command == "sla-demo":
        sla_demo()
    elif command == "demo-clear":
        clear()
    elif command == "restore-test":
        restore_test(make_client())
    elif command == "cleanup-old-test":
        cleanup_old_test()
    elif command == "inspect":
        inspect()
    else:
        usage()
