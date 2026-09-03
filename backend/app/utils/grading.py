"""Grade banding for O-Level and A-Level.

Bands are held in one place so the CSV ingest, the correction workflow and the
report card generator all derive the same grade from the same mark.
"""

from decimal import Decimal
from typing import List, Optional, Tuple, Union

from app.models.enums import EducationLevel

Number = Union[int, float, Decimal]

# (minimum percentage inclusive, grade symbol, remark)
O_LEVEL_BANDS: List[Tuple[int, str, str]] = [
    (75, "A", "Distinction"),
    (70, "B", "Merit"),
    (60, "C", "Credit"),
    (50, "D", "Pass"),
    (40, "E", "Pass"),
    (0, "U", "Ungraded"),
]

A_LEVEL_BANDS: List[Tuple[int, str, str]] = [
    (80, "A", "Excellent"),
    (70, "B", "Very good"),
    (60, "C", "Good"),
    (50, "D", "Satisfactory"),
    (40, "E", "Marginal pass"),
    (35, "O", "Subsidiary pass"),
    (0, "F", "Fail"),
]

# Remarks this module used to generate, before the scale moved into the
# database. Recalculation needs to recognise them as system-written so it can
# replace them; without this a result keeps a remark from a retired scale.
LEGACY_REMARKS = {
    remark
    for bands in (O_LEVEL_BANDS, A_LEVEL_BANDS)
    for _, _, remark in bands
}

BANDS_BY_LEVEL = {
    EducationLevel.O_LEVEL: O_LEVEL_BANDS,
    EducationLevel.A_LEVEL: A_LEVEL_BANDS,
}

# The lowest symbol at each level that still counts as a pass.
PASSING_GRADES = {
    EducationLevel.O_LEVEL: {"A", "B", "C", "D", "E"},
    EducationLevel.A_LEVEL: {"A", "B", "C", "D", "E"},
}


def score_to_grade(
    marks: Number,
    level: EducationLevel,
    max_marks: Number = 100,
) -> Tuple[str, str]:
    """Convert a raw mark to a (grade, remark) pair for the given level.

    Marks are normalised to a percentage first, so a school marking out of 50
    or 200 grades on the same bands as one marking out of 100.
    """
    if max_marks is None or Decimal(str(max_marks)) <= 0:
        raise ValueError("max_marks must be greater than zero.")

    bands = BANDS_BY_LEVEL.get(level)
    if bands is None:
        raise ValueError(f"No grade bands defined for level {level}.")

    percentage = (Decimal(str(marks)) / Decimal(str(max_marks))) * 100

    for minimum, grade, remark in bands:
        if percentage >= minimum:
            return grade, remark

    # The final band starts at zero, so this is only reached for a negative mark.
    lowest = bands[-1]
    return lowest[1], lowest[2]


def is_pass(grade: Optional[str], level: EducationLevel) -> bool:
    """Whether a grade symbol counts as a pass at the given level."""
    if not grade:
        return False
    return grade.upper() in PASSING_GRADES.get(level, set())


def grade_symbols(level: EducationLevel) -> List[str]:
    """Every grade symbol used at a level, best first. Useful for report keys."""
    return [grade for _, grade, _ in BANDS_BY_LEVEL[level]]
