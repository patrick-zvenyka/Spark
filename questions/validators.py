"""
Validators that help keep personal details out of anonymous questions.

The goal is to protect students from accidentally identifying themselves
(names, registration numbers, phone numbers, emails, class/group details).
"""
import re

from django.conf import settings
from django.core.exceptions import ValidationError

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\s-]?){9,}(?!\w)")
# Registration / student numbers such as R201234A, H180123B, CS12345.
STUDENT_ID_RE = re.compile(r"\b[A-Za-z]{1,3}\d{5,}[A-Za-z]?\b")
SELF_IDENTIFY_RE = re.compile(
    r"\b(my name is|i am called|i'm called|my surname is|"
    r"reg(istration)?\.? ?(no|num|number)|student (no|num|number|id)|"
    r"(my|our) (class|group|stream|cohort) (is|number|no)|i am in (class|group))\b",
    re.IGNORECASE,
)

PROBLEMS = [
    (EMAIL_RE, "email addresses"),
    (PHONE_RE, "phone numbers"),
    (STUDENT_ID_RE, "registration or student numbers"),
    (SELF_IDENTIFY_RE, "your name, class or group details"),
]


def find_personal_info(value: str) -> list[str]:
    found = [label for pattern, label in PROBLEMS if pattern.search(value or "")]
    return found


def validate_no_personal_info(value):
    found = find_personal_info(value)
    if found:
        raise ValidationError(
            "To protect your anonymity, please remove %(items)s.",
            code="personal_info",
            params={"items": ", ".join(found)},
        )


def validate_no_blocked_words(value):
    lowered = (value or "").lower()
    blocked = [w for w in settings.SB_BLOCKED_WORDS if w.lower() in lowered]
    if blocked:
        raise ValidationError(
            "Your text contains language that is not allowed. Please read the community rules.",
            code="blocked_words",
        )
