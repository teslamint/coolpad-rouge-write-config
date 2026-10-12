"""Pure planning and validation for the write-config client.

This module never touches the USB backend; importing it must not import PyUSB.
"""

from __future__ import annotations

import re

PRODUCT = "3320A"
SERIAL_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")
CONFIRMATION_PATTERN = re.compile(r"sz:524288, arg:0, tag:(48|49)\Z")
ACKNOWLEDGE_TEMPLATE = "WRITE-CONFIG:{product}:{serial}:{value}"


class UsageError(ValueError):
    """The command-line input is invalid."""


def parse_value(text: str) -> int:
    if text == "0":
        return 0
    if text == "1":
        return 1
    raise UsageError("value must be 0 or 1")


def validate_serial(serial: str) -> str:
    if not SERIAL_PATTERN.fullmatch(serial):
        raise UsageError("serial must match [A-Za-z0-9._-]{1,64}")
    return serial


def build_command(value: int) -> str:
    """Generate the only two commands this client can send."""
    if type(value) is not int or value not in (0, 1):
        raise UsageError("value must be 0 or 1")
    return f"write-config:{value}"


def acknowledge_token(serial: str, value: int) -> str:
    return ACKNOWLEDGE_TEMPLATE.format(product=PRODUCT, serial=serial, value=value)


def verify_acknowledgement(token: str | None, serial: str, value: int) -> None:
    if token is None:
        raise UsageError("execution requires --acknowledge with the exact token")
    expected = acknowledge_token(serial, value)
    if token != expected:
        raise UsageError(f"acknowledgement must be exactly: {expected}")


def plan(serial: str, value: int) -> dict:
    return {
        "command": build_command(value),
        "executed": False,
        "product": PRODUCT,
        "serial": serial,
        "status": "planned",
        "value": value,
    }


def confirmation_is_valid(payload: str, value: int) -> bool:
    match = CONFIRMATION_PATTERN.fullmatch(payload)
    if match is None:
        return False
    return int(match.group(1)) == ord(str(value))
