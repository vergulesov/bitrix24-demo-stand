from __future__ import annotations

from typing import Any

import requests


class BitrixClient:
    def __init__(self, webhook: str, timeout: int = 30) -> None:
        self.webhook = webhook.rstrip("/")
        self.timeout = timeout

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.webhook}/{method}"
        response = requests.post(
            url,
            json=params or {},
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )

        try:
            payload = response.json()
        except ValueError:
            response.raise_for_status()
            raise RuntimeError(f"{method}: Bitrix returned a non-JSON response")

        if not response.ok:
            error = payload.get("error", response.status_code)
            description = payload.get("error_description", response.text)
            raise RuntimeError(f"{method}: {error} — {description}")

        if "error" in payload:
            raise RuntimeError(
                f"{method}: {payload.get('error')} — "
                f"{payload.get('error_description', '')}"
            )

        return payload.get("result")

    def get_current_user(self) -> dict[str, Any]:
        return self.call("user.current")

    def list_users(self, limit: int = 50) -> list[dict[str, Any]]:
        result = self.call(
            "user.get",
            {"FILTER": {}, "SORT": "ID", "ORDER": "ASC"},
        )
        return (result or [])[:limit]

    def list_departments(self) -> list[dict[str, Any]]:
        result = self.call("department.get", {})
        return result or []

    def add_department(
        self,
        name: str,
        parent: int = 0,
        head_id: int | None = None,
    ) -> int:
        fields: dict[str, Any] = {
            "NAME": name,
            "PARENT": parent,
        }
        if head_id is not None:
            fields["UF_HEAD"] = head_id
        result = self.call("department.add", fields)
        return int(result)

    def add_user(
        self,
        email: str,
        name: str,
        last_name: str,
        department_id: int,
    ) -> int:
        result = self.call(
            "user.add",
            {
                "EMAIL": email,
                "NAME": name,
                "LAST_NAME": last_name,
                "UF_DEPARTMENT": [department_id],
            },
        )
        return int(result)

    def list_categories(self, entity_type_id: int = 2) -> list[dict[str, Any]]:
        result = self.call(
            "crm.category.list",
            {"entityTypeId": entity_type_id},
        )
        return (result or {}).get("categories", [])

    def add_category(self, name: str, entity_type_id: int = 2) -> int:
        result = self.call(
            "crm.category.add",
            {
                "entityTypeId": entity_type_id,
                "fields": {"name": name},
            },
        )
        return int(result["category"]["id"])

    def list_stages(self, category_id: int) -> list[dict[str, Any]]:
        entity_id = "DEAL_STAGE" if category_id == 0 else f"DEAL_STAGE_{category_id}"
        result = self.call(
            "crm.status.list",
            {
                "filter": {"ENTITY_ID": entity_id},
                "order": {"SORT": "ASC"},
            },
        )
        return result or []

    def update_status(self, status_id: int, fields: dict[str, Any]) -> Any:
        return self.call(
            "crm.status.update",
            {"id": status_id, "fields": fields},
        )

    def delete_status(self, status_id: int, forced: bool = False) -> Any:
        params: dict[str, Any] = {"id": status_id}
        if forced:
            params["params"] = {"FORCED": "Y"}
        return self.call("crm.status.delete", params)

    def add_stage(
        self,
        category_id: int,
        name: str,
        status_id: str,
        sort: int,
        semantics: str = "",
    ) -> Any:
        entity_id = "DEAL_STAGE" if category_id == 0 else f"DEAL_STAGE_{category_id}"
        return self.call(
            "crm.status.add",
            {
                "fields": {
                    "ENTITY_ID": entity_id,
                    "STATUS_ID": status_id,
                    "NAME": name,
                    "SORT": sort,
                    "SEMANTICS": semantics,
                }
            },
        )

    def list_deal_userfields(self) -> list[dict[str, Any]]:
        result = self.call(
            "crm.deal.userfield.list",
            {
                "filter": {},
                "order": {"SORT": "ASC", "ID": "ASC"},
            },
        )
        return result or []

    def add_deal_userfield(self, fields: dict[str, Any]) -> int:
        result = self.call(
            "crm.deal.userfield.add",
            {"fields": fields},
        )
        return int(result)

    def update_deal_userfield(
        self,
        field_id: int,
        fields: dict[str, Any],
    ) -> Any:
        return self.call(
            "crm.deal.userfield.update",
            {"id": field_id, "fields": fields},
        )

    def set_deal_card_configuration(
        self,
        category_id: int,
        data: list[dict[str, Any]],
    ) -> Any:
        return self.call(
            "crm.item.details.configuration.set",
            {
                "entityTypeId": 2,
                "scope": "C",
                "extras": {"dealCategoryId": category_id},
                "data": data,
            },
        )

    def list_deals(self, category_id: int | None = None) -> list[dict[str, Any]]:
        filter_data: dict[str, Any] = {}
        if category_id is not None:
            filter_data["categoryId"] = category_id

        result = self.call(
            "crm.item.list",
            {
                "entityTypeId": 2,
                "select": ["id", "title", "categoryId", "stageId", "comments"],
                "filter": filter_data,
            },
        )
        return (result or {}).get("items", [])

    def add_timeline_comment(self, deal_id: int, comment: str) -> Any:
        return self.call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT": comment,
                }
            },
        )

    def update_deal_stage(self, deal_id: int, stage_id: str) -> Any:
        return self.call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "fields": {"stageId": stage_id},
            },
        )

    def delete_deal(self, deal_id: int) -> Any:
        return self.call(
            "crm.item.delete",
            {
                "entityTypeId": 2,
                "id": deal_id,
            },
        )

    def add_deal(
        self,
        title: str,
        category_id: int,
        stage_id: str,
        assigned_by_id: int,
        comments: str = "",
        fields: dict[str, Any] | None = None,
    ) -> int:
        deal_fields: dict[str, Any] = {
            "title": title,
            "categoryId": category_id,
            "stageId": stage_id,
            "assignedById": assigned_by_id,
            "opened": "Y",
            "closed": "N",
            "comments": comments,
        }
        if fields:
            deal_fields.update(fields)

        result = self.call(
            "crm.item.add",
            {
                "entityTypeId": 2,
                "fields": deal_fields,
                "useOriginalUfNames": "Y",
            },
        )
        return int(result["item"]["id"])
