from datetime import date, timedelta

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from einsatzbereit.models import (
    Certification,
    CertificationKind,
    Completion,
    Member,
    PasswordResetToken,
    RefreshToken,
    User,
    ValidityMode,
)
from einsatzbereit.routers.overview import describe_filter
from einsatzbereit.security import create_jwt, decode_jwt, hash_opaque_token, now_utc
from einsatzbereit.services.export import cell_text
from einsatzbereit.services.status import (
    Cell,
    CellStatus,
    MatrixFilter,
    MatrixRow,
    build_matrix,
    expiry_date,
)
from tests.conftest import ADMIN, USER, login

CERT = {"name": "EH", "kind": "training", "validity_mode": "unlimited"}


def _user_id(db: Session, email: str) -> int:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user.id


class TestAuth:
    def test_inactive_and_locked_users_cannot_log_in(self, client: TestClient, db: Session) -> None:
        db.execute(update(User).where(User.email == USER[0]).values(is_active=False))
        db.commit()
        r = client.post("/api/auth/login", json={"login": USER[0], "password": USER[1]})
        assert r.status_code == 401

    def test_unknown_user(self, client: TestClient) -> None:
        r = client.post("/api/auth/login", json={"login": "x@example.org", "password": "whatever"})
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid credentials"

    def test_refresh_edge_cases(self, client: TestClient, db: Session) -> None:
        assert client.post("/api/auth/refresh").status_code == 401
        client.cookies.set("eb_refresh", "garbage", path="/api/auth")
        assert client.post("/api/auth/refresh").status_code == 401

        login(client, USER)
        db.execute(update(RefreshToken).values(expires_at=now_utc() - timedelta(minutes=1)))
        db.commit()
        assert client.post("/api/auth/refresh").status_code == 401

        login(client, USER)
        db.execute(update(User).where(User.email == USER[0]).values(is_active=False))
        db.commit()
        assert client.post("/api/auth/refresh").status_code == 401

    def test_locked_user_cannot_log_in(self, client: TestClient, db: Session) -> None:
        db.execute(
            update(User)
            .where(User.email == USER[0])
            .values(locked_until=now_utc() + timedelta(minutes=5))
        )
        db.commit()
        r = client.post("/api/auth/login", json={"login": USER[0], "password": USER[1]})
        assert r.status_code == 401

    def test_logout_without_cookie(self, client: TestClient) -> None:
        assert client.post("/api/auth/logout").status_code == 204

    def test_mfa_token_edge_cases(self, client: TestClient, db: Session) -> None:
        uid = _user_id(db, USER[0])
        body = {"code": "123456"}
        assert (
            client.post("/api/auth/login/mfa", json={**body, "mfa_token": "nope"}).status_code
            == 401
        )
        access = create_jwt(uid, "access", 0)
        assert (
            client.post("/api/auth/login/mfa", json={**body, "mfa_token": access}).status_code
            == 401
        )
        stale = create_jwt(uid, "mfa", 99)
        assert (
            client.post("/api/auth/login/mfa", json={**body, "mfa_token": stale}).status_code == 401
        )
        valid_but_no_2fa = create_jwt(uid, "mfa", 0)
        r = client.post("/api/auth/login/mfa", json={**body, "mfa_token": valid_but_no_2fa})
        assert r.status_code == 401
        unknown = create_jwt(9999, "mfa", 0)
        assert (
            client.post("/api/auth/login/mfa", json={**body, "mfa_token": unknown}).status_code
            == 401
        )

    def test_decode_rejects_tampered_tokens(self) -> None:
        token = create_jwt(1, "access", 0)
        assert decode_jwt(token, "access") == (1, 0)
        assert decode_jwt(token[:-2] + "xx", "access") is None
        assert decode_jwt(token, "mfa") is None

    def test_bearer_token_edge_cases(self, client: TestClient) -> None:
        assert client.get("/api/me", headers={"Authorization": "Bearer nope"}).status_code == 401
        token = create_jwt(9999, "access", 0)
        assert (
            client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
        )

    def test_expired_reset_token_and_inactive_user(self, client: TestClient, db: Session) -> None:
        uid = _user_id(db, USER[0])
        now = now_utc()
        db.add_all(
            [
                PasswordResetToken(
                    user_id=uid,
                    token_hash=hash_opaque_token("old"),
                    expires_at=now - timedelta(minutes=1),
                    created_at=now,
                ),
                PasswordResetToken(
                    user_id=uid,
                    token_hash=hash_opaque_token("fresh"),
                    expires_at=now + timedelta(minutes=10),
                    created_at=now,
                ),
            ]
        )
        db.execute(update(User).where(User.id == uid).values(is_active=False))
        db.commit()
        for token in ("old", "fresh", "unknown"):
            r = client.post(
                "/api/auth/password-reset/confirm", json={"token": token, "new_password": "x" * 12}
            )
            assert r.status_code == 400
        r = client.post("/api/auth/password-reset/request", json={"email": USER[0]})
        assert r.status_code == 202


class TestMe:
    def test_change_password(self, client: TestClient) -> None:
        headers = login(client, USER)
        wrong = {"current_password": "nope", "new_password": "another-password-1"}
        assert client.post("/api/me/password", headers=headers, json=wrong).status_code == 400
        ok = {"current_password": USER[1], "new_password": "another-password-1"}
        assert client.post("/api/me/password", headers=headers, json=ok).status_code == 204
        assert client.get("/api/me", headers=headers).status_code == 401
        login(client, (USER[0], "another-password-1"))

    def test_totp_state_machine(self, client: TestClient) -> None:
        headers = login(client, USER)
        code = {"code": "123456"}
        assert client.post("/api/me/totp/enable", headers=headers, json=code).status_code == 409
        assert (
            client.post(
                "/api/me/totp/disable", headers=headers, json={"password": USER[1], **code}
            ).status_code
            == 409
        )

        secret = client.post("/api/me/totp/setup", headers=headers).json()["secret"]
        client.post("/api/me/totp/enable", headers=headers, json={"code": pyotp.TOTP(secret).now()})
        assert client.post("/api/me/totp/setup", headers=headers).status_code == 409
        assert client.post("/api/me/totp/enable", headers=headers, json=code).status_code == 409

        wrong_pw = {"password": "nope", "code": pyotp.TOTP(secret).now()}
        assert (
            client.post("/api/me/totp/disable", headers=headers, json=wrong_pw).status_code == 400
        )
        wrong_code = {"password": USER[1], "code": "000000"}
        assert (
            client.post("/api/me/totp/disable", headers=headers, json=wrong_code).status_code == 400
        )
        ok = {"password": USER[1], "code": pyotp.TOTP(secret).now()}
        r = client.post("/api/me/totp/disable", headers=headers, json=ok)
        assert r.status_code == 200 and r.json()["totp_enabled"] is False


class TestUsers:
    def test_user_admin_edge_cases(
        self, client: TestClient, admin_headers: dict[str, str], db: Session
    ) -> None:
        uid = _user_id(db, USER[0])
        dup_mail = {
            "username": "neu",
            "email": USER[0].upper(),
            "display_name": "X",
            "password": "password-123",
        }
        assert client.post("/api/users", headers=admin_headers, json=dup_mail).status_code == 409
        dup_name = {**dup_mail, "username": "Anwender", "email": "neu@example.org"}
        assert client.post("/api/users", headers=admin_headers, json=dup_name).status_code == 409
        bad_name = {**dup_mail, "username": "mit leerzeichen", "email": "neu@example.org"}
        assert client.post("/api/users", headers=admin_headers, json=bad_name).status_code == 422
        assert client.patch("/api/users/9999", headers=admin_headers, json={}).status_code == 404
        assert client.post("/api/users/9999/reset-2fa", headers=admin_headers).status_code == 404

        users = client.get("/api/users", headers=admin_headers).json()
        assert {u["email"] for u in users} == {ADMIN[0], USER[0]}

        user_headers = login(client, USER)
        r = client.post(f"/api/users/{uid}/reset-2fa", headers=admin_headers)
        assert r.status_code == 200 and r.json()["totp_enabled"] is False
        assert client.get("/api/me", headers=user_headers).status_code == 401

        client.patch(f"/api/users/{uid}", headers=admin_headers, json={"is_active": False})
        assert (
            client.post(f"/api/users/{uid}/send-password-reset", headers=admin_headers).status_code
            == 409
        )

    def test_admin_can_be_removed_when_another_admin_exists(
        self, client: TestClient, admin_headers: dict[str, str], db: Session
    ) -> None:
        uid = _user_id(db, USER[0])
        client.patch(f"/api/users/{uid}", headers=admin_headers, json={"role": "admin"})
        admin_id = _user_id(db, ADMIN[0])
        r = client.patch(f"/api/users/{admin_id}", headers=admin_headers, json={"is_active": False})
        assert r.status_code == 200
        assert client.get("/api/me", headers=admin_headers).status_code == 401


class TestCatalog:
    def test_not_found_and_conflicts(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        h = admin_headers
        assert client.put("/api/certifications/9999", headers=h, json=CERT).status_code == 404
        assert client.delete("/api/certifications/9999", headers=h).status_code == 404
        assert client.put("/api/positions/9999", headers=h, json={"name": "X"}).status_code == 404
        assert client.delete("/api/positions/9999", headers=h).status_code == 404

        first = client.post("/api/certifications", headers=h, json=CERT).json()
        assert client.post("/api/certifications", headers=h, json=CERT).status_code == 409
        other = client.post("/api/certifications", headers=h, json={**CERT, "name": "UVV"}).json()
        assert (
            client.put(f"/api/certifications/{other['id']}", headers=h, json=CERT).status_code
            == 409
        )

        agt = client.post("/api/positions", headers=h, json={"name": "AGT"}).json()["id"]
        assert client.post("/api/positions", headers=h, json={"name": "AGT"}).status_code == 409
        ma = client.post("/api/positions", headers=h, json={"name": "MA"}).json()["id"]
        rename = {"name": "AGT", "certification_ids": [first["id"]]}
        assert client.put(f"/api/positions/{ma}", headers=h, json=rename).status_code == 409
        assert (
            client.put(
                f"/api/positions/{agt}",
                headers=h,
                json={"name": "AGT", "certification_ids": [9999]},
            ).status_code
            == 422
        )
        bad = {"name": "FST", "certification_ids": [first["id"], 9999]}
        assert client.post("/api/positions", headers=h, json=bad).status_code == 422

    def test_manual_mode_drops_months(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        body = {**CERT, "validity_mode": "manual", "validity_months": 12}
        assert (
            client.post("/api/certifications", headers=admin_headers, json=body).json()[
                "validity_months"
            ]
            is None
        )


class TestMembers:
    def test_member_edge_cases(self, client: TestClient, user_headers: dict[str, str]) -> None:
        h = user_headers
        body = {"number": "1", "last_name": "A", "first_name": "B"}
        assert (
            client.post(
                "/api/members", headers=h, json={**body, "position_ids": [9999]}
            ).status_code
            == 422
        )
        assert client.put("/api/members/9999", headers=h, json=body).status_code == 404
        assert client.get("/api/members/9999", headers=h).status_code == 404
        first = client.post("/api/members", headers=h, json=body).json()["id"]
        second = client.post("/api/members", headers=h, json={**body, "number": "2"}).json()["id"]
        assert client.put(f"/api/members/{second}", headers=h, json=body).status_code == 409
        client.put(f"/api/members/{first}", headers=h, json={**body, "is_active": False})
        assert [m["id"] for m in client.get("/api/members", headers=h).json()] == [second]
        assert len(client.get("/api/members?include_inactive=true", headers=h).json()) == 2

    def test_completion_edge_cases(
        self, client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str]
    ) -> None:
        cert = client.post("/api/certifications", headers=admin_headers, json=CERT).json()["id"]
        member = client.post(
            "/api/members",
            headers=user_headers,
            json={"number": "1", "last_name": "A", "first_name": "B"},
        ).json()["id"]
        today = date.today().isoformat()
        base = {"member_id": member, "certification_id": cert, "completed_on": today}
        assert (
            client.post(
                "/api/completions", headers=user_headers, json={**base, "member_id": 9999}
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/completions", headers=user_headers, json={**base, "certification_id": 9999}
            ).status_code
            == 404
        )
        before = {**base, "manual_expires_on": (date.today() - timedelta(days=1)).isoformat()}
        assert client.post("/api/completions", headers=user_headers, json=before).status_code == 422
        created = client.post(
            "/api/completions",
            headers=user_headers,
            json={**base, "manual_expires_on": "2030-01-01"},
        )
        assert created.json()["expires_on"] is None
        assert client.delete("/api/completions/9999", headers=user_headers).status_code == 404
        cid = created.json()["id"]
        assert client.delete(f"/api/completions/{cid}", headers=user_headers).status_code == 204
        bulk = {
            "certification_id": cert,
            "member_ids": [member],
            "completed_on": today,
            "manual_expires_on": "2020-01-01",
        }
        assert (
            client.post("/api/completions/bulk", headers=user_headers, json=bulk).status_code == 422
        )


class TestOverview:
    def test_search_and_describe_filter(
        self, client: TestClient, admin_headers: dict[str, str], db: Session
    ) -> None:
        cert = client.post("/api/certifications", headers=admin_headers, json=CERT).json()["id"]
        pos = client.post(
            "/api/positions",
            headers=admin_headers,
            json={"name": "AGT", "certification_ids": [cert]},
        )
        pos_id = pos.json()["id"]
        for n, name in ((1, "Albers"), (2, "Brandt")):
            client.post(
                "/api/members",
                headers=admin_headers,
                json={
                    "number": str(n),
                    "last_name": name,
                    "first_name": "X",
                    "position_ids": [pos_id],
                },
            )
        rows = client.get("/api/overview?q=  alb ", headers=admin_headers).json()["rows"]
        assert [r["member"]["last_name"] for r in rows] == ["Albers"]
        assert client.get("/api/overview?status=valid", headers=admin_headers).json()["rows"] == []
        rows = client.get("/api/overview?q=2", headers=admin_headers).json()["rows"]
        assert [r["member"]["last_name"] for r in rows] == ["Brandt"]

        flt = MatrixFilter(
            statuses={CellStatus.MISSING, CellStatus.VALID},
            position_id=pos_id,
            certification_id=cert,
            query=" Alb ",
            include_inactive=True,
            only_open=True,
        )
        assert describe_filter(db, flt) == (
            "Filter: nur offene; Status: fehlt, gültig; Funktion: AGT; Nachweis: EH; Suche: Alb; inkl. inaktive"
        )
        assert describe_filter(db, MatrixFilter(position_id=9999)) == "Filter: keiner"

        xlsx = client.get(
            f"/api/exports/xlsx?status=missing&position_id={pos_id}&certification_id={cert}&q=a&include_inactive=true",
            headers=admin_headers,
        )
        assert xlsx.status_code == 200


class TestStatusAndExport:
    def test_missing_months_means_no_expiry(self) -> None:
        for mode in (ValidityMode.FIXED_DURATION, ValidityMode.END_OF_YEAR):
            cert = Certification(
                name="x", kind=CertificationKind.TEST, validity_mode=mode, validity_months=None
            )
            assert expiry_date(cert, Completion(completed_on=date(2026, 1, 1))) is None

    def test_worst_status_of_empty_row(self) -> None:
        row = MatrixRow(member=Member(number="1", last_name="A", first_name="B"), cells=[])
        assert row.worst_status == CellStatus.NOT_REQUIRED
        assert row.open_count == 0

    @pytest.mark.parametrize(
        ("status", "expires", "text"),
        [
            (CellStatus.MISSING, None, "fehlt"),
            (CellStatus.NOT_REQUIRED, None, ""),
            (CellStatus.NOT_REQUIRED, date(2026, 5, 1), "(01.05.2026)"),
            (CellStatus.VALID, None, "unbefristet"),
            (CellStatus.EXPIRED, date(2026, 5, 1), "01.05.2026"),
        ],
    )
    def test_cell_text(self, status: CellStatus, expires: date | None, text: str) -> None:
        assert cell_text(Cell(1, status != CellStatus.NOT_REQUIRED, status, None, expires)) == text

    def test_empty_matrix(self, db: Session) -> None:
        matrix = build_matrix(db, MatrixFilter(only_open=True), today=date(2026, 1, 1))
        assert matrix.rows == [] and matrix.certifications == []
        assert set(matrix.counts().values()) == {0}
