from datetime import date, timedelta

from fastapi.testclient import TestClient

from einsatzbereit.services.status import add_months


def _setup(client: TestClient, admin: dict[str, str]) -> dict[str, int]:
    agt_test = client.post(
        "/api/certifications",
        headers=admin,
        json={
            "name": "Belastungsübung",
            "kind": "exercise",
            "validity_mode": "fixed_duration",
            "validity_months": 12,
            "warn_days": 60,
        },
    ).json()["id"]
    unterweisung = client.post(
        "/api/certifications",
        headers=admin,
        json={
            "name": "Unterweisung",
            "kind": "seminar",
            "validity_mode": "end_of_year",
            "validity_months": 12,
        },
    ).json()["id"]
    agt = client.post(
        "/api/positions",
        headers=admin,
        json={
            "name": "AGT",
            "certification_ids": [agt_test, unterweisung],
        },
    ).json()["id"]
    basis = client.post(
        "/api/positions",
        headers=admin,
        json={
            "name": "Basis",
            "certification_ids": [unterweisung],
        },
    ).json()["id"]
    return {"agt_test": agt_test, "unterweisung": unterweisung, "agt": agt, "basis": basis}


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/api/overview").status_code == 401
    assert client.get("/api/exports/csv").status_code == 401


def test_user_cannot_admin(client: TestClient, user_headers: dict[str, str]) -> None:
    r = client.post(
        "/api/certifications",
        headers=user_headers,
        json={"name": "X", "kind": "test", "validity_mode": "unlimited"},
    )
    assert r.status_code == 403
    assert client.get("/api/users", headers=user_headers).status_code == 403


def test_months_required_for_fixed(client: TestClient, admin_headers: dict[str, str]) -> None:
    r = client.post(
        "/api/certifications",
        headers=admin_headers,
        json={"name": "X", "kind": "test", "validity_mode": "fixed_duration"},
    )
    assert r.status_code == 422


def test_overview_flow(
    client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str]
) -> None:
    ids = _setup(client, admin_headers)
    # Users may maintain members
    anna = client.post(
        "/api/members",
        headers=user_headers,
        json={
            "number": "101",
            "last_name": "Albers",
            "first_name": "Anna",
            "position_ids": [ids["agt"], ids["basis"]],
        },
    ).json()["id"]
    ben = client.post(
        "/api/members",
        headers=user_headers,
        json={
            "number": "102",
            "last_name": "Brandt",
            "first_name": "Ben",
            "position_ids": [ids["basis"]],
        },
    ).json()["id"]
    assert (
        client.post(
            "/api/members",
            headers=user_headers,
            json={"number": "101", "last_name": "Dup", "first_name": "X"},
        ).status_code
        == 409
    )

    today = date.today()
    # Anna: AGT test expiring soon (done ~11.5 months ago), Unterweisung valid
    almost = add_months(today, -12) + timedelta(days=20)
    for cert, done in ((ids["agt_test"], almost), (ids["unterweisung"], today)):
        r = client.post(
            "/api/completions",
            headers=user_headers,
            json={"member_id": anna, "certification_id": cert, "completed_on": done.isoformat()},
        )
        assert r.status_code == 201, r.text
    # Ben: all valid
    client.post(
        "/api/completions",
        headers=user_headers,
        json={
            "member_id": ben,
            "certification_id": ids["unterweisung"],
            "completed_on": today.isoformat(),
        },
    )

    data = client.get("/api/overview", headers=user_headers).json()
    assert len(data["rows"]) == 2
    rows = {r["member"]["id"]: r for r in data["rows"]}
    assert rows[anna]["worst_status"] == "expiring"
    assert rows[ben]["worst_status"] == "valid"
    ben_cells = {c["certification_id"]: c for c in rows[ben]["cells"]}
    assert ben_cells[ids["agt_test"]]["status"] == "not_required"

    open_only = client.get("/api/overview?only_open=true", headers=user_headers).json()
    assert [r["member"]["id"] for r in open_only["rows"]] == [anna]

    by_status = client.get("/api/overview?status=valid&status=missing", headers=user_headers).json()
    assert {r["member"]["id"] for r in by_status["rows"]} == {anna, ben}

    by_pos = client.get(f"/api/overview?position_id={ids['agt']}", headers=user_headers).json()
    assert [r["member"]["id"] for r in by_pos["rows"]] == [anna]

    # History is kept, latest completion wins
    client.post(
        "/api/completions",
        headers=user_headers,
        json={
            "member_id": anna,
            "certification_id": ids["agt_test"],
            "completed_on": today.isoformat(),
        },
    )
    detail = client.get(f"/api/members/{anna}", headers=user_headers).json()
    assert len(detail["history"]) == 3
    assert all(c["status"] == "valid" for c in detail["cells"])
    assert detail["history"][0]["recorded_by"] == "Anwender"

    # Deactivated members disappear unless requested
    client.put(
        f"/api/members/{ben}",
        headers=user_headers,
        json={
            "number": "102",
            "last_name": "Brandt",
            "first_name": "Ben",
            "is_active": False,
            "position_ids": [],
        },
    )
    assert len(client.get("/api/overview", headers=user_headers).json()["rows"]) == 1
    assert (
        len(client.get("/api/overview?include_inactive=true", headers=user_headers).json()["rows"])
        == 2
    )


def test_completion_rules(
    client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str]
) -> None:
    manual = client.post(
        "/api/certifications",
        headers=admin_headers,
        json={"name": "G26.3", "kind": "test", "validity_mode": "manual"},
    ).json()["id"]
    m = client.post(
        "/api/members",
        headers=user_headers,
        json={"number": "1", "last_name": "A", "first_name": "B"},
    ).json()["id"]
    base = {"member_id": m, "certification_id": manual}
    today = date.today().isoformat()
    assert (
        client.post(
            "/api/completions", headers=user_headers, json={**base, "completed_on": today}
        ).status_code
        == 422
    )
    future = (date.today() + timedelta(days=1)).isoformat()
    assert (
        client.post(
            "/api/completions",
            headers=user_headers,
            json={**base, "completed_on": future, "manual_expires_on": future},
        ).status_code
        == 422
    )
    r = client.post(
        "/api/completions",
        headers=admin_headers,
        json={**base, "completed_on": today, "manual_expires_on": "2030-01-01"},
    )
    assert r.json()["expires_on"] == "2030-01-01"
    # a user cannot delete an admin's entry, admin can
    cid = r.json()["id"]
    assert client.delete(f"/api/completions/{cid}", headers=user_headers).status_code == 403
    assert client.delete(f"/api/completions/{cid}", headers=admin_headers).status_code == 204
    # certification with no completions left can be deleted
    assert client.delete(f"/api/certifications/{manual}", headers=admin_headers).status_code == 204


def test_exports(client: TestClient, admin_headers: dict[str, str]) -> None:
    ids = _setup(client, admin_headers)
    client.post(
        "/api/members",
        headers=admin_headers,
        json={
            "number": "7",
            "last_name": "Müller",
            "first_name": "Jörg",
            "position_ids": [ids["agt"]],
        },
    )
    csv = client.get("/api/exports/csv?only_open=true", headers=admin_headers)
    assert csv.status_code == 200
    text = csv.content.decode("utf-8-sig")
    assert "Müller" in text and "fehlt" in text
    xlsx = client.get("/api/exports/xlsx", headers=admin_headers)
    assert xlsx.content[:2] == b"PK"
    pdf = client.get(f"/api/exports/pdf?position_id={ids['agt']}", headers=admin_headers)
    assert pdf.content[:4] == b"%PDF"
    assert "attachment" in pdf.headers["content-disposition"]
    assert client.get("/api/exports/docx", headers=admin_headers).status_code == 422


def test_bulk_completions(
    client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str]
) -> None:
    ids = _setup(client, admin_headers)
    members = [
        client.post(
            "/api/members",
            headers=user_headers,
            json={
                "number": str(n),
                "last_name": f"M{n}",
                "first_name": "X",
                "position_ids": [ids["agt"]],
            },
        ).json()["id"]
        for n in range(1, 5)
    ]
    today = date.today().isoformat()
    body = {
        "certification_id": ids["agt_test"],
        "completed_on": today,
        "member_ids": [*members[:3], members[0]],
    }
    r = client.post("/api/completions/bulk", headers=user_headers, json=body)
    assert r.status_code == 201 and r.json() == {"created": 3}
    # submitting again is idempotent for the same date
    r = client.post(
        "/api/completions/bulk", headers=user_headers, json={**body, "member_ids": members}
    )
    assert r.json() == {"created": 1}

    data = client.get(
        f"/api/overview?certification_id={ids['agt_test']}", headers=user_headers
    ).json()
    assert {r["cells"][0]["status"] for r in data["rows"]} == {"valid"}
    assert (
        client.get(f"/api/members/{members[0]}", headers=user_headers).json()["history"][0][
            "recorded_by"
        ]
        == "Anwender"
    )

    # validation
    assert (
        client.post(
            "/api/completions/bulk", headers=user_headers, json={**body, "member_ids": [9999]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/completions/bulk", headers=user_headers, json={**body, "member_ids": []}
        ).status_code
        == 422
    )
    future = (date.today() + timedelta(days=3)).isoformat()
    assert (
        client.post(
            "/api/completions/bulk", headers=user_headers, json={**body, "completed_on": future}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/completions/bulk", headers=user_headers, json={**body, "certification_id": 9999}
        ).status_code
        == 404
    )
    assert client.post("/api/completions/bulk", json=body).status_code == 401
