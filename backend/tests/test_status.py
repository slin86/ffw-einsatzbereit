from datetime import date

import pytest

from einsatzbereit.models import Certification, CertificationKind, Completion, ValidityMode
from einsatzbereit.services.status import CellStatus, add_months, evaluate, expiry_date


def cert(mode: ValidityMode, months: int | None = None, warn: int = 30) -> Certification:
    return Certification(
        id=1,
        name="x",
        kind=CertificationKind.TEST,
        validity_mode=mode,
        validity_months=months,
        warn_days=warn,
        is_active=True,
    )


def comp(done: date, manual: date | None = None, cid: int = 1) -> Completion:
    return Completion(id=cid, certification_id=1, completed_on=done, manual_expires_on=manual)


@pytest.mark.parametrize(
    ("start", "months", "expected"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2024, 1, 31), 1, date(2024, 2, 29)),
        (date(2026, 11, 15), 3, date(2027, 2, 15)),
        (date(2026, 5, 1), 36, date(2029, 5, 1)),
    ],
)
def test_add_months(start: date, months: int, expected: date) -> None:
    assert add_months(start, months) == expected


def test_fixed_duration_expires_day_before_anniversary() -> None:
    assert expiry_date(cert(ValidityMode.FIXED_DURATION, 12), comp(date(2026, 3, 10))) == date(
        2027, 3, 9
    )


def test_end_of_year() -> None:
    assert expiry_date(cert(ValidityMode.END_OF_YEAR, 12), comp(date(2026, 3, 10))) == date(
        2027, 12, 31
    )


def test_manual_and_unlimited() -> None:
    assert expiry_date(cert(ValidityMode.MANUAL), comp(date(2026, 1, 1), date(2026, 6, 1))) == date(
        2026, 6, 1
    )
    assert expiry_date(cert(ValidityMode.UNLIMITED), comp(date(2000, 1, 1))) is None


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 12, 1), CellStatus.VALID),
        (date(2027, 2, 7), CellStatus.EXPIRING),
        (date(2027, 3, 9), CellStatus.EXPIRING),
        (date(2027, 3, 10), CellStatus.EXPIRED),
    ],
)
def test_evaluate_required(today: date, expected: CellStatus) -> None:
    status, _ = evaluate(
        cert(ValidityMode.FIXED_DURATION, 12), comp(date(2026, 3, 10)), True, today
    )
    assert status == expected


def test_missing_vs_not_required() -> None:
    c = cert(ValidityMode.UNLIMITED)
    assert evaluate(c, None, True, date(2026, 1, 1))[0] == CellStatus.MISSING
    assert evaluate(c, None, False, date(2026, 1, 1))[0] == CellStatus.NOT_REQUIRED


def test_optional_expired_is_not_open() -> None:
    status, expires = evaluate(
        cert(ValidityMode.FIXED_DURATION, 12), comp(date(2020, 1, 1)), False, date(2026, 1, 1)
    )
    assert status == CellStatus.NOT_REQUIRED
    assert expires == date(2020, 12, 31)
