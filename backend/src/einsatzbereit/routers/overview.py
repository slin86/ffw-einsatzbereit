from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from einsatzbereit.deps import CurrentUser, DbSession
from einsatzbereit.models import Certification, Position
from einsatzbereit.schemas import (
    CellOut,
    CertificationOut,
    MatrixRowOut,
    MemberOut,
    OverviewOut,
)
from einsatzbereit.services import export
from einsatzbereit.services.status import CellStatus, MatrixFilter, build_matrix

router = APIRouter(prefix="/api", tags=["overview"])


def matrix_filter(
    status: Annotated[list[CellStatus] | None, Query()] = None,
    position_id: int | None = None,
    certification_id: int | None = None,
    q: str = "",
    include_inactive: bool = False,
    only_open: bool = False,
) -> MatrixFilter:
    return MatrixFilter(
        statuses=set(status or ()),
        position_id=position_id,
        certification_id=certification_id,
        query=q,
        include_inactive=include_inactive,
        only_open=only_open,
    )


Filter = Annotated[MatrixFilter, Depends(matrix_filter)]


def describe_filter(db: Session, flt: MatrixFilter) -> str:
    """
    Describes the active filter in German for the header of exported files. Unknown position or
    certification ids are left out.
    """
    parts: list[str] = []
    if flt.only_open:
        parts.append("nur offene")
    if flt.statuses:
        parts.append(
            "Status: " + ", ".join(sorted(export.STATUS_LABEL[s] or s for s in flt.statuses))
        )
    if flt.position_id and (pos := db.get(Position, flt.position_id)):
        parts.append(f"Funktion: {pos.name}")
    if flt.certification_id and (cert := db.get(Certification, flt.certification_id)):
        parts.append(f"Nachweis: {cert.name}")
    if flt.query.strip():
        parts.append(f"Suche: {flt.query.strip()}")
    if flt.include_inactive:
        parts.append("inkl. inaktive")
    return "Filter: " + ("; ".join(parts) if parts else "keiner")


@router.get("/overview", response_model=OverviewOut)
def overview(_: CurrentUser, db: DbSession, flt: Filter) -> OverviewOut:
    matrix = build_matrix(db, flt)
    return OverviewOut(
        today=matrix.today,
        certifications=[CertificationOut.model_validate(c) for c in matrix.certifications],
        rows=[
            MatrixRowOut(
                member=MemberOut.model_validate(r.member),
                worst_status=r.worst_status,
                open_count=r.open_count,
                cells=[CellOut.model_validate(c, from_attributes=True) for c in r.cells],
            )
            for r in matrix.rows
        ],
        counts=matrix.counts(),
    )


_MEDIA = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


@router.get("/exports/{fmt}")
def export_matrix(
    fmt: Literal["csv", "xlsx", "pdf"], _: CurrentUser, db: DbSession, flt: Filter
) -> Response:
    """
    Exports the status matrix as CSV, Excel or PDF with exactly the same filter parameters as the
    overview.
    """
    matrix = build_matrix(db, flt)
    description = describe_filter(db, flt)
    if fmt == "csv":
        content = export.to_csv(matrix)
    elif fmt == "xlsx":
        content = export.to_xlsx(matrix, description)
    else:
        content = export.to_pdf(matrix, description)
    filename = f"einsatzbereit-{date.today().isoformat()}.{fmt}"
    return Response(
        content,
        media_type=_MEDIA[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
