from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from einsatzbereit.models import AuditEntry, Completion, Member

CERT = {"name": "EH", "kind": "training", "validity_mode": "unlimited"}


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def setup_members(
    client: TestClient, admin: dict[str, str], user: dict[str, str]
) -> dict[str, int]:
    cert = client.post("/api/certifications", headers=admin, json=CERT).json()["id"]
    position = client.post(
        "/api/positions", headers=admin, json={"name": "Basis", "certification_ids": [cert]}
    ).json()["id"]
    ids = {}
    for number, name in (("1", "Albers"), ("2", "Brandt"), ("3", "Claußen")):
        member = client.post(
            "/api/members",
            headers=user,
            json={
                "number": number,
                "last_name": name,
                "first_name": "X",
                "position_ids": [position],
            },
        ).json()["id"]
        client.post(
            "/api/completions",
            headers=user,
            json={
                "member_id": member,
                "certification_id": cert,
                "completed_on": date.today().isoformat(),
            },
        )
        ids[name] = member
    return ids


def test_admin_deletes_one_member_with_history(
    client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str], db: Session
) -> None:
    ids = setup_members(client, admin_headers, user_headers)
    victim = ids["Brandt"]

    r = client.delete(f"/api/members/{victim}", headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"deleted": 1}
    assert client.get(f"/api/members/{victim}", headers=user_headers).status_code == 404
    assert count(db, Member) == 2
    assert count(db, Completion) == 2
    assert (
        db.scalar(
            select(func.count()).select_from(AuditEntry).where(AuditEntry.member_id == victim)
        )
        == 0
    )

    entries = client.get("/api/audit", headers=admin_headers).json()["entries"]
    assert entries[0]["action"] == "delete"
    assert entries[0]["entity_label"] == "Brandt, X (2)"
    assert entries[0]["changes"]["number"] == "2"
    assert entries[0]["member_id"] is None
    assert not any(e["member_id"] == victim for e in entries)
    remaining = {
        r["member"]["id"] for r in client.get("/api/overview", headers=user_headers).json()["rows"]
    }
    assert remaining == {ids["Albers"], ids["Claußen"]}


def test_bulk_delete(
    client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str], db: Session
) -> None:
    ids = setup_members(client, admin_headers, user_headers)
    body = {"member_ids": [ids["Albers"], ids["Claußen"]]}
    r = client.post("/api/members/delete", headers=admin_headers, json=body)
    assert r.status_code == 200 and r.json() == {"deleted": 2}
    assert count(db, Member) == 1
    assert count(db, Completion) == 1
    labels = [
        e["entity_label"]
        for e in client.get("/api/audit", headers=admin_headers).json()["entries"][:2]
    ]
    assert sorted(labels) == ["Albers, X (1)", "Claußen, X (3)"]


def test_bulk_delete_is_all_or_nothing(
    client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str], db: Session
) -> None:
    ids = setup_members(client, admin_headers, user_headers)
    body = {"member_ids": [ids["Albers"], 9999]}
    assert client.post("/api/members/delete", headers=admin_headers, json=body).status_code == 422
    assert count(db, Member) == 3
    assert (
        client.post(
            "/api/members/delete", headers=admin_headers, json={"member_ids": []}
        ).status_code
        == 422
    )


def test_only_admins_may_delete(
    client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str], db: Session
) -> None:
    ids = setup_members(client, admin_headers, user_headers)
    assert client.delete(f"/api/members/{ids['Albers']}", headers=user_headers).status_code == 403
    body = {"member_ids": [ids["Albers"]]}
    assert client.post("/api/members/delete", headers=user_headers, json=body).status_code == 403
    assert client.delete(f"/api/members/{ids['Albers']}").status_code == 401
    assert count(db, Member) == 3


def test_delete_unknown_member(client: TestClient, admin_headers: dict[str, str]) -> None:
    assert client.delete("/api/members/9999", headers=admin_headers).status_code == 404
