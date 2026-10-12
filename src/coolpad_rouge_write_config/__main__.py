from __future__ import annotations

import argparse
import json
import sys

from ._plan import (
    PRODUCT,
    UsageError,
    parse_value,
    plan,
    validate_serial,
    verify_acknowledgement,
)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)

    def print_help(self, file=None) -> None:
        print(json.dumps({
            "command": None, "executed": False, "product": PRODUCT,
            "serial": None, "value": None, "status": "help",
            "usage": self.format_help(),
        }, sort_keys=True), file=file)


def main() -> int:
    parser = Parser(prog="coolpad-rouge-write-config", allow_abbrev=False)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--value", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge")
    output = {
        "command": None, "executed": False, "product": PRODUCT,
        "serial": None, "status": "invalid", "value": None,
    }
    code = 0
    message = None
    try:
        arguments = parser.parse_args()
        serial = validate_serial(arguments.serial)
        value = parse_value(arguments.value)
        output = plan(serial, value)
        if arguments.execute:
            verify_acknowledgement(arguments.acknowledge, serial, value)
            from ._usb import ExecutionError, execute

            try:
                execute(serial, value)
            except ExecutionError as error:
                code = error.code
                output["status"] = error.status
                output["executed"] = error.executed
                message = str(error)
            else:
                output["status"] = "accepted"
                output["executed"] = True
    except UsageError as error:
        code = 2
        output["status"] = "invalid"
        message = str(error)
    print(json.dumps(output, sort_keys=True))
    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
