"""The grading service: the one place a mark becomes a grade and a remark.

Every path that writes a result goes through here - CSV import, the on-screen
mark sheet, single-mark corrections - so a school that changes its scale
changes it once and every one of them follows.

The scale is read from the grade_bands table. On first use the table is seeded
from DEFAULT_BANDS so a new installation grades sensibly out of the box, but
nothing afterwards depends on those defaults: an administrator can rewrite the
scale entirely and the code never needs to know.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.models.enums import EducationLevel
from app.models.grade_band import GradeBand

# Starting point only, applied once when a level has no bands of its own.
# (minimum percentage inclusive, grade, remark, counts as a pass)
DEFAULT_BANDS: Dict[EducationLevel, List[Tuple[int, str, str, bool]]] = {
    EducationLevel.O_LEVEL: [
        (75, "A", "Excellent", True),
        (70, "B", "Very good", True),
        (60, "C", "Good", True),
        (50, "D", "Satisfactory", True),
        (40, "E", "Needs improvement", True),
        (0, "U", "Ungraded", False),
    ],
    EducationLevel.A_LEVEL: [
        (80, "A", "Excellent", True),
        (70, "B", "Very good", True),
        (60, "C", "Good", True),
        (50, "D", "Satisfactory", True),
        (40, "E", "Marginal pass", True),
        (35, "O", "Subsidiary pass", False),
        (0, "F", "Fail", False),
    ],
}

# Returned when a level somehow has no bands at all, so a mark can always be
# stored rather than the write failing.
UNGRADED = ("-", "Not graded")


class GradingService:
    """Reads the configured scale and applies it.

    Bands are cached on the instance: one request grading a whole class reads
    the scale once rather than once per student.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._cache: Dict[EducationLevel, List[GradeBand]] = {}

    # ------------------------------------------------------- the scale

    def bands_for(self, level: EducationLevel) -> List[GradeBand]:
        """The scale for one level, highest band first."""
        if level in self._cache:
            return self._cache[level]

        bands = (
            self.db.query(GradeBand)
            .filter(GradeBand.level == level)
            .order_by(GradeBand.min_marks.desc())
            .all()
        )
        if not bands:
            bands = self._seed(level)

        self._cache[level] = bands
        return bands

    def _seed(self, level: EducationLevel) -> List[GradeBand]:
        """Populate a level from the defaults, the first time it is needed."""
        created = [
            GradeBand(
                level=level,
                min_marks=Decimal(minimum),
                grade=grade,
                remark=remark,
                is_pass=is_pass,
            )
            for minimum, grade, remark, is_pass in DEFAULT_BANDS.get(level, [])
        ]
        if not created:
            return []

        self.db.add_all(created)
        self.db.commit()
        return sorted(created, key=lambda b: b.min_marks, reverse=True)

    def ensure_defaults(self) -> None:
        """Seed every level, so the settings screen has something to show."""
        for level in EducationLevel:
            self.bands_for(level)

    def replace_scale(
        self, level: EducationLevel, bands: Sequence[dict]
    ) -> List[GradeBand]:
        """Replace a level's scale wholesale.

        Replacing rather than patching row by row means the scale can never be
        left half-edited, with a gap or an overlap between two bands.
        """
        self.db.query(GradeBand).filter(GradeBand.level == level).delete(
            synchronize_session=False
        )
        rows = [
            GradeBand(
                level=level,
                min_marks=Decimal(str(b["min_marks"])),
                grade=b["grade"].strip().upper(),
                remark=b["remark"].strip(),
                is_pass=bool(b.get("is_pass", True)),
            )
            for b in bands
        ]
        self.db.add_all(rows)
        self.db.commit()
        self._cache.pop(level, None)
        return self.bands_for(level)

    # ------------------------------------------------------- grading

    def grade_for(
        self,
        marks: Decimal,
        level: Optional[EducationLevel],
        max_marks: Decimal = Decimal("100"),
    ) -> Tuple[str, str]:
        """Turn a mark into (grade, remark) using the configured scale.

        The mark is normalised to a percentage first, so a subject marked out
        of 50 grades on the same scale as one marked out of 100.
        """
        level = level or EducationLevel.O_LEVEL
        bands = self.bands_for(level)
        if not bands:
            return UNGRADED

        if max_marks <= 0:
            raise ValueError("max_marks must be greater than zero.")

        percentage = (Decimal(str(marks)) / Decimal(str(max_marks))) * 100

        for band in bands:  # already ordered highest first
            if percentage >= band.min_marks:
                return band.grade, band.remark

        # Below every band: the lowest one still describes it.
        lowest = bands[-1]
        return lowest.grade, lowest.remark

    def is_pass(self, grade: Optional[str], level: EducationLevel) -> bool:
        """Whether a grade symbol counts as a pass at this level."""
        if not grade:
            return False
        for band in self.bands_for(level):
            if band.grade.upper() == grade.upper():
                return band.is_pass
        return False

    def symbols(self, level: EducationLevel) -> List[str]:
        """Every symbol in use at a level, best first, for report card keys."""
        return [b.grade for b in self.bands_for(level)]


def validate_scale(bands: Sequence[dict]) -> Optional[str]:
    """Check a proposed scale before it replaces the current one.

    A scale that does not reach zero, repeats a symbol, or repeats a threshold
    would silently misgrade somebody, so it is rejected outright rather than
    stored and discovered later.
    """
    if not bands:
        return "A grading scale needs at least one band."

    thresholds, symbols = [], []
    for band in bands:
        try:
            minimum = Decimal(str(band["min_marks"]))
        except (KeyError, TypeError, ArithmeticError):
            return "Every band needs a numeric minimum mark."

        grade = (band.get("grade") or "").strip()
        if not grade:
            return "Every band needs a grade symbol."
        if not (band.get("remark") or "").strip():
            return f"Grade {grade} needs a remark."
        if minimum < 0 or minimum > 100:
            return f"The minimum for grade {grade} must be between 0 and 100."

        thresholds.append(minimum)
        symbols.append(grade.upper())

    if len(set(symbols)) != len(symbols):
        return "Each grade symbol may only appear once."
    if len(set(thresholds)) != len(thresholds):
        return "Two bands cannot start at the same mark."
    if min(thresholds) != 0:
        return (
            "The lowest band must start at 0, otherwise a very low mark would "
            "fall outside the scale."
        )

    return None
