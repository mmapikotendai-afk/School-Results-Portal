from decimal import Decimal

import pytest

from app.models.enums import EducationLevel
from app.services.grading_service import DEFAULT_BANDS, GradingService


@pytest.mark.parametrize(
    "mark, expected",
    [
        (100, "A"), (75, "A"), (74, "B"), (65, "B"), (64, "C"),
        (50, "C"), (49, "D"), (40, "D"), (39, "E"), (30, "E"),
        (29, "U"), (0, "U"),
    ],
)
def test_approved_a_to_u_scale_applies_at_boundaries(db, mark, expected):
    grading = GradingService(db)
    for level in EducationLevel:
        grade, _ = grading.grade_for(Decimal(mark), level)
        assert grade == expected


def test_approved_scale_is_the_default_for_each_level():
    expected = [(75, "A"), (65, "B"), (50, "C"), (40, "D"), (30, "E"), (0, "U")]
    for level in EducationLevel:
        assert [(minimum, grade) for minimum, grade, _, _ in DEFAULT_BANDS[level]] == expected
