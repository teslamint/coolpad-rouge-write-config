"""Deterministic fake objects for command-line end-to-end tests."""

from __future__ import annotations

import json
import os
from pathlib import Path


class USBError(Exception):
    pass


class NoBackendError(USBError):
    pass


def _touch_import_marker() -> None:
    marker = os.environ.get("FAKE_USB_IMPORT_MARKER")
    if marker:
        Path(marker).write_text("imported\n", encoding="utf-8")


def _load_scenario() -> dict:
    path = os.environ.get("FAKE_USB_SCENARIO")
    if not path:
        raise USBError("FAKE_USB_SCENARIO is not set")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _append_transcript(event: dict) -> None:
    path = os.environ.get("FAKE_USB_TRANSCRIPT")
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    events = []
    if target.exists():
        events = json.loads(target.read_text(encoding="utf-8"))
    events.append(event)
    target.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")


_touch_import_marker()


class Endpoint:
    def __init__(self, address: int, device: "Device") -> None:
        self.bEndpointAddress = address
        self.bmAttributes = 2
        self._device = device

    def write(self, data: bytes, timeout: int | None = None) -> int:
        command = bytes(data).decode("ascii")
        self._device.select_response(command)
        _append_transcript({"event": "write", "command": command})
        return len(data)

    def read(self, size: int, timeout: int | None = None) -> bytes:
        response = self._device.next_response()
        if response == "__TIMEOUT__":
            raise USBError("timed out")
        _append_transcript({"event": "read", "response": response})
        return response.encode("ascii")


class Interface:
    bInterfaceClass = 0xFF
    bInterfaceSubClass = 0x42
    bInterfaceProtocol = 0x03
    bInterfaceNumber = 0

    def __init__(self, device: "Device") -> None:
        self._endpoints = [Endpoint(0x01, device), Endpoint(0x81, device)]

    def __iter__(self):
        return iter(self._endpoints)


class Configuration:
    def __init__(self, device: "Device") -> None:
        self._interfaces = [Interface(device)]

    def __iter__(self):
        return iter(self._interfaces)


class Device:
    iSerialNumber = 1

    def __init__(self, spec: dict) -> None:
        self.serial = spec["serial"]
        self.idVendor = spec.get("vendor_id", 0x1EBF)
        self.responses = spec.get("responses", {})
        self._pending: list[str] = []
        self._configuration = Configuration(self)

    def __iter__(self):
        return iter([self._configuration])

    def set_configuration(self) -> None:
        return None

    def get_active_configuration(self) -> Configuration:
        return self._configuration

    def is_kernel_driver_active(self, interface_number: int) -> bool:
        return False

    def select_response(self, command: str) -> None:
        responses = self.responses.get(command)
        if responses is None:
            responses = ["FAILunexpected command"]
        self._pending = list(responses)

    def next_response(self) -> str:
        if not self._pending:
            raise USBError("no pending response")
        return self._pending.pop(0)


def find(*, find_all: bool = False, custom_match=None):
    scenario = _load_scenario()
    if scenario.get("backend_error"):
        raise NoBackendError("fake backend unavailable")
    devices = [Device(spec) for spec in scenario.get("devices", [])]
    if custom_match is not None:
        devices = [device for device in devices if custom_match(device)]
    if find_all:
        return iter(devices)
    return devices[0] if devices else None
