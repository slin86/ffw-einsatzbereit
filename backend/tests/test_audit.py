from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from einsatzbereit.services.audit import diff


def test_diff_only_changed_fields() -> None:
    assert diff({"a": 1, "b": [1]}, {"a": 1, "b": [1, 2], "c": None}) == {"b": [[1], [1, 2]]}


def _entries(client: TestClient, headers: dict[str, str], query: str = "") -> list[dict[str, Any]]:
    r = client.get(f"/api/audit{query}", headers=headers)
    assert r.status_code == 200, r.text
    entries: list[dict[str, Any]] = r.json()["entries"]
    return entries


def test_member_and_completion_changes_are_logged(
    client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str]
) -> None:
    cert = client.post(
        "/api/certifications",
        headers=admin_headers,
        json={
            "name": "Erste Hilfe",
            "kind": "training",
            "validity_mode": "fixed_duration",
            "validity_months": 24,
        },
    ).json()["id"]
    pos = client.post(
        "/api/positions", headers=admin_headers, json={"name": "Basis", "certification_ids": [cert]}
    ).json()["id"]
    member = client.post(
        "/api/members",
        headers=user_headers,
        json={"number": "7", "last_name": "Voß", "first_name": "Ida", "position_ids": [pos]},
    ).json()["id"]

    same = {"number": "7", "last_name": "Voß", "first_name": "Ida", "position_ids": [pos]}
    client.put(f"/api/members/{member}", headers=user_headers, json=same)
    client.put(
        f"/api/members/{member}",
        headers=user_headers,
        json={**same, "first_name": "Ina", "is_active": False, "position_ids": []},
    )

    comp = client.post(
        "/api/completions",
        headers=user_headers,
        json={
            "member_id": member,
            "certification_id": cert,
            "completed_on": date.today().isoformat(),
            "note": "Kurs DRK",
        },
    ).json()["id"]
    client.post(
        "/api/completions/bulk",
        headers=user_headers,
        json={"certification_id": cert, "member_ids": [member], "completed_on": "2025-01-10"},
    )
    client.delete(f"/api/completions/{comp}", headers=user_headers)

    page = client.get(f"/api/members/{member}/audit", headers=user_headers).json()
    entries = page["entries"]
    assert [(e["entity_type"], e["action"]) for e in entries] == [
        ("completion", "delete"),
        ("completion", "create"),
        ("completion", "create"),
        ("member", "update"),
        ("member", "create"),
    ]
    assert all(e["user_name"] == "Anwender" for e in entries)
    update = entries[3]
    assert update["changes"] == {
        "first_name": ["Ida", "Ina"],
        "is_active": [True, False],
        "positions": [["Basis"], []],
    }
    assert update["entity_label"] == "Voß, Ina (7)"
    assert entries[0]["changes"]["note"] == "Kurs DRK"
    assert entries[0]["entity_label"] == "Voß, Ina (7): Erste Hilfe"
    assert entries[1]["changes"]["completed_on"] == "2025-01-10"


def test_catalog_and_user_changes_are_logged(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    cert = client.post(
        "/api/certifications",
        headers=admin_headers,
        json={
            "name": "UVV",
            "kind": "seminar",
            "validity_mode": "end_of_year",
            "validity_months": 12,
        },
    ).json()
    client.put(
        f"/api/certifications/{cert['id']}", headers=admin_headers, json={**cert, "warn_days": 30}
    )
    pos = client.post("/api/positions", headers=admin_headers, json={"name": "AGT"}).json()
    client.put(
        f"/api/positions/{pos['id']}",
        headers=admin_headers,
        json={"name": "AGT", "certification_ids": [cert["id"]]},
    )
    client.delete(f"/api/positions/{pos['id']}", headers=admin_headers)
    client.delete(f"/api/certifications/{cert['id']}", headers=admin_headers)
    user = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "username": "neu",
            "email": "neu@example.org",
            "display_name": "Neu",
            "password": "secret-password-1",
        },
    ).json()
    client.patch(f"/api/users/{user['id']}", headers=admin_headers, json={"role": "admin"})

    entries = _entries(client, admin_headers)
    summary = [(e["entity_type"], e["action"]) for e in entries]
    assert summary == [
        ("user", "update"),
        ("user", "create"),
        ("certification", "delete"),
        ("position", "delete"),
        ("position", "update"),
        ("position", "create"),
        ("certification", "update"),
        ("certification", "create"),
    ]
    assert entries[0]["changes"] == {"role": ["user", "admin"]}
    assert entries[4]["changes"] == {"certifications": [[], ["UVV"]]}
    assert entries[6]["changes"] == {"warn_days": [60, 30]}
    assert set(entries[1]["changes"]) == {
        "username",
        "email",
        "display_name",
        "role",
        "is_active",
        "totp_enabled",
    }
    assert "secret-password" not in str(entries)

    only_pos = _entries(client, admin_headers, "?entity_type=position")
    assert {e["entity_type"] for e in only_pos} == {"position"}
    assert _entries(client, admin_headers, "?q=uvv")
    assert all("UVV" in e["entity_label"] for e in _entries(client, admin_headers, "?q=uvv"))


def test_audit_paging_and_permissions(
    client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str]
) -> None:
    for n in range(5):
        client.post("/api/positions", headers=admin_headers, json={"name": f"P{n}"})
    first = client.get("/api/audit?limit=2", headers=admin_headers).json()
    assert len(first["entries"]) == 2 and first["next_before_id"] is not None
    second = client.get(
        f"/api/audit?limit=2&before_id={first['next_before_id']}", headers=admin_headers
    ).json()
    assert second["entries"][0]["id"] < first["entries"][-1]["id"]
    last = client.get(
        f"/api/audit?limit=10&before_id={second['next_before_id']}", headers=admin_headers
    ).json()
    assert len(last["entries"]) == 1 and last["next_before_id"] is None

    assert client.get("/api/audit", headers=user_headers).status_code == 403
    assert client.get("/api/members/999/audit", headers=user_headers).status_code == 404
