"""Apply the school's approved A--U grading scale to both academic levels.

Marks and previously issued report cards are intentionally left untouched. The
administrator can reapply a new scale to a selected examination from the
Results page after reviewing the effect.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.models import EducationLevel, Examination, ExaminationStatus, GradeBand, Result  # noqa: E402
from app.services.grading_service import DEFAULT_BANDS  # noqa: E402
from app.services.results_engine import ResultsEngine  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        result_count = db.query(Result).count()
        for level in EducationLevel:
            db.query(GradeBand).filter(GradeBand.level == level).delete(
                synchronize_session=False
            )
            db.add_all(
                GradeBand(
                    level=level,
                    min_marks=minimum,
                    grade=grade,
                    remark=remark,
                    is_pass=is_pass,
                )
                for minimum, grade, remark, is_pass in DEFAULT_BANDS[level]
            )
        db.commit()
        examinations = (
            db.query(Examination)
            .filter(Examination.status != ExaminationStatus.PUBLISHED)
            .all()
        )
        engine = ResultsEngine(db)
        recalculated = sum(engine.recalculate_grades(examination.id) for examination in examinations)
    print(
        "Applied A--U scale to O-Level and A-Level. "
        f"Recalculated {recalculated} grade(s) in unpublished examinations; "
        f"{result_count} recorded mark(s) were preserved."
    )


if __name__ == "__main__":
    main()
