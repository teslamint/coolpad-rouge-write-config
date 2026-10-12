"""Restricted fastboot transport; PyUSB is loaded only for execution."""

from __future__ import annotations

import time

from ._plan import PRODUCT, build_command, confirmation_is_valid

USB_VENDOR = 0x1EBF


class ExecutionError(Exception):
    def __init__(self, code: int, status: str, message: str, executed: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.executed = executed


def execute(serial: str, value: int) -> None:
    command = build_command(value)
    try:
        import usb.core
        import usb.util
    except ImportError as error:
        raise ExecutionError(5, "failed", "PyUSB is not available") from error

    device = None
    interface = None
    claimed = False
    write_started = False
    opened = []

    def exchange(text: str, out_endpoint, in_endpoint) -> str:
        nonlocal write_started
        data = text.encode("ascii")
        if len(data) > 64:
            raise ExecutionError(5, "failed", "command exceeds fastboot limit")
        deadline = time.monotonic() + 5.0
        if text == command:
            # A failed USB write can still have reached the device. Never retry it.
            write_started = True
        if out_endpoint.write(data, timeout=5000) != len(data):
            raise ValueError("short command transfer")
        for _ in range(64):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("fastboot response deadline exceeded")
            packet = bytes(in_endpoint.read(64, timeout=max(1, int(remaining * 1000))))
            if not 4 <= len(packet) <= 64:
                raise ValueError("invalid fastboot packet length")
            response = packet.decode("ascii")
            prefix, payload = response[:4], response[4:]
            if prefix == "INFO":
                continue
            if prefix == "OKAY":
                return payload
            if prefix == "FAIL":
                if write_started:
                    raise ExecutionError(
                        6,
                        "indeterminate",
                        "write command failed after transmission",
                        True,
                    )
                raise ExecutionError(4, "rejected", "fastboot rejected command", write_started)
            raise ValueError("unexpected fastboot response")
        raise ValueError("too many INFO responses")

    def endpoints(candidate):
        bulk = [endpoint for endpoint in candidate
                if usb.util.endpoint_type(endpoint.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK]
        incoming = [endpoint for endpoint in bulk
                    if usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_IN]
        outgoing = [endpoint for endpoint in bulk
                    if usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_OUT]
        if len(incoming) != 1 or len(outgoing) != 1:
            return None
        return outgoing[0], incoming[0]

    def is_fastboot(candidate):
        return (candidate.bInterfaceClass, candidate.bInterfaceSubClass,
                candidate.bInterfaceProtocol) == (0xFF, 0x42, 0x03)

    try:
        matches = []
        for candidate in usb.core.find(find_all=True):
            if candidate.idVendor != USB_VENDOR:
                continue
            opened.append(candidate)
            if not candidate.iSerialNumber:
                continue
            if usb.util.get_string(candidate, candidate.iSerialNumber) != serial:
                continue
            for configuration in candidate:
                for candidate_interface in configuration:
                    if is_fastboot(candidate_interface) and endpoints(candidate_interface) is not None:
                        matches.append((candidate, candidate_interface))
        if len(matches) != 1:
            raise ExecutionError(3, "failed", "expected exactly one matching fastboot interface")
        device, selected = matches[0]
        device.set_configuration()
        active = [candidate for candidate in device.get_active_configuration()
                  if is_fastboot(candidate) and endpoints(candidate) is not None]
        if len(active) != 1 or active[0].bInterfaceNumber != selected.bInterfaceNumber:
            raise ExecutionError(3, "failed", "matching fastboot interface is not active")
        interface = active[0]
        out_endpoint, in_endpoint = endpoints(interface)
        usb.util.claim_interface(device, interface.bInterfaceNumber)
        claimed = True
        if exchange("getvar:product", out_endpoint, in_endpoint) != PRODUCT:
            raise ExecutionError(3, "failed", "fastboot product does not match 3320A")
        if exchange("getvar:serialno", out_endpoint, in_endpoint) != serial:
            raise ExecutionError(3, "failed", "fastboot serial does not match requested serial")
        confirmation = exchange(command, out_endpoint, in_endpoint)
        if not confirmation_is_valid(confirmation, value):
            raise ExecutionError(6, "indeterminate", "write confirmation is invalid", True)
    except (usb.core.USBError, ValueError) as error:
        if write_started:
            raise ExecutionError(6, "indeterminate", "write confirmation is absent or invalid", True) from error
        raise ExecutionError(5, "failed", "USB transport or fastboot protocol failed") from error
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, interface.bInterfaceNumber)
            except usb.core.USBError:
                pass
        for candidate in opened:
            try:
                usb.util.dispose_resources(candidate)
            except usb.core.USBError:
                pass
