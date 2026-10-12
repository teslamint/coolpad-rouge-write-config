from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / ".artifacts" / "transcripts"
FAKE_USB = ROOT / "tests" / "fake_pyusb"
SOURCE = ROOT / "src"


class CliE2ETest(unittest.TestCase):
    maxDiff = None

    def run_cli(
        self,
        case: str,
        *arguments: str,
        scenario: dict | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], list[dict], Path]:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        transcript = ARTIFACTS / f"{case}.json"
        marker = ARTIFACTS / f"{case}.usb-imported"
        transcript.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)

        with tempfile.TemporaryDirectory() as directory:
            scenario_path = Path(directory) / "scenario.json"
            scenario_path.write_text(
                json.dumps(scenario or {"devices": []}),
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTHONPATH"] = os.pathsep.join((str(SOURCE), str(FAKE_USB)))
            environment["FAKE_USB_SCENARIO"] = str(scenario_path)
            environment["FAKE_USB_TRANSCRIPT"] = str(transcript)
            environment["FAKE_USB_IMPORT_MARKER"] = str(marker)
            result = subprocess.run(
                [sys.executable, "-m", "coolpad_rouge_write_config", *arguments],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )

        events = []
        if transcript.exists():
            events = json.loads(transcript.read_text(encoding="utf-8"))
        return result, events, marker

    @staticmethod
    def output(result: subprocess.CompletedProcess[str]) -> dict:
        return json.loads(result.stdout)

    @staticmethod
    def device(serial: str = "ROUGE123", **responses: list[str]) -> dict:
        mapped = {name.replace("__", ":"): value for name, value in responses.items()}
        return {"serial": serial, "responses": mapped}

    def test_plan_never_imports_usb(self) -> None:
        result, events, marker = self.run_cli(
            "plan",
            "--serial",
            "ROUGE123",
            "--value",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.output(result),
            {
                "command": "write-config:1",
                "executed": False,
                "product": "3320A",
                "serial": "ROUGE123",
                "status": "planned",
                "value": 1,
            },
        )
        self.assertEqual(events, [])
        self.assertFalse(marker.exists())

    def test_invalid_serial_fails_before_usb(self) -> None:
        result, events, marker = self.run_cli(
            "invalid-serial",
            "--serial",
            "bad serial",
            "--value",
            "1",
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(events, [])
        self.assertFalse(marker.exists())

    def test_missing_acknowledgement_fails_before_usb(self) -> None:
        result, events, marker = self.run_cli(
            "missing-ack",
            "--serial",
            "ROUGE123",
            "--value",
            "1",
            "--execute",
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(events, [])
        self.assertFalse(marker.exists())

    def test_duplicate_serial_fails_before_command(self) -> None:
        scenario = {"devices": [self.device(), self.device()]}
        result, events, marker = self.run_cli(
            "duplicate",
            "--serial",
            "ROUGE123",
            "--value",
            "1",
            "--execute",
            "--acknowledge",
            "WRITE-CONFIG:3320A:ROUGE123:1",
            scenario=scenario,
        )
        self.assertEqual(result.returncode, 3)
        self.assertEqual(events, [])
        self.assertTrue(marker.exists())

    def test_wrong_vendor_id_fails_before_command(self) -> None:
        scenario = {"devices": [{"serial": "ROUGE123", "vendor_id": 0x18D1}]}
        result, events, marker = self.run_cli(
            "wrong-vendor",
            "--serial",
            "ROUGE123",
            "--value",
            "1",
            "--execute",
            "--acknowledge",
            "WRITE-CONFIG:3320A:ROUGE123:1",
            scenario=scenario,
        )
        self.assertEqual(result.returncode, 3)
        self.assertEqual(events, [])
        self.assertTrue(marker.exists())

    def test_wrong_product_never_sends_write(self) -> None:
        scenario = {
            "devices": [
                {
                    "serial": "ROUGE123",
                    "responses": {"getvar:product": ["OKAYother"]},
                },
            ]
        }
        result, events, _ = self.run_cli(
            "wrong-product",
            "--serial",
            "ROUGE123",
            "--value",
            "1",
            "--execute",
            "--acknowledge",
            "WRITE-CONFIG:3320A:ROUGE123:1",
            scenario=scenario,
        )
        self.assertEqual(result.returncode, 3)
        self.assertEqual(
            [event.get("command") for event in events if event["event"] == "write"],
            ["getvar:product"],
        )

    def test_wrong_fastboot_serial_never_sends_write_config(self) -> None:
        scenario = {
            "devices": [
                {
                    "serial": "ROUGE123",
                    "responses": {
                        "getvar:product": ["OKAY3320A"],
                        "getvar:serialno": ["OKAYOTHER"],
                    },
                }
            ]
        }
        result, events, _ = self.run_cli(
            "wrong-fastboot-serial",
            "--serial",
            "ROUGE123",
            "--value",
            "1",
            "--execute",
            "--acknowledge",
            "WRITE-CONFIG:3320A:ROUGE123:1",
            scenario=scenario,
        )
        self.assertEqual(result.returncode, 3)
        self.assertEqual(
            [event.get("command") for event in events if event["event"] == "write"],
            ["getvar:product", "getvar:serialno"],
        )

    def test_success_sends_only_fixed_commands(self) -> None:
        scenario = {
            "devices": [
                {
                    "serial": "ROUGE123",
                    "responses": {
                        "getvar:product": ["INFOchecking", "OKAY3320A"],
                        "getvar:serialno": ["OKAYROUGE123"],
                        "write-config:0": ["OKAYsz:524288, arg:0, tag:48"],
                    },
                }
            ]
        }
        result, events, _ = self.run_cli(
            "success",
            "--serial",
            "ROUGE123",
            "--value",
            "0",
            "--execute",
            "--acknowledge",
            "WRITE-CONFIG:3320A:ROUGE123:0",
            scenario=scenario,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output(result)["status"], "accepted")
        self.assertEqual(
            [event.get("command") for event in events if event["event"] == "write"],
            ["getvar:product", "getvar:serialno", "write-config:0"],
        )

    def test_write_fail_is_indeterminate(self) -> None:
        scenario = {
            "devices": [
                {
                    "serial": "ROUGE123",
                    "responses": {
                        "getvar:product": ["OKAY3320A"],
                        "getvar:serialno": ["OKAYROUGE123"],
                        "write-config:1": ["FAILflash write failure"],
                    },
                }
            ]
        }
        result, _, _ = self.run_cli(
            "rejected",
            "--serial",
            "ROUGE123",
            "--value",
            "1",
            "--execute",
            "--acknowledge",
            "WRITE-CONFIG:3320A:ROUGE123:1",
            scenario=scenario,
        )
        self.assertEqual(result.returncode, 6)
        self.assertEqual(self.output(result)["status"], "indeterminate")

    def test_malformed_write_confirmation_is_indeterminate(self) -> None:
        scenario = {
            "devices": [
                {
                    "serial": "ROUGE123",
                    "responses": {
                        "getvar:product": ["OKAY3320A"],
                        "getvar:serialno": ["OKAYROUGE123"],
                        "write-config:1": ["OKAYunexpected"],
                    },
                }
            ]
        }
        result, _, _ = self.run_cli(
            "malformed-confirmation",
            "--serial",
            "ROUGE123",
            "--value",
            "1",
            "--execute",
            "--acknowledge",
            "WRITE-CONFIG:3320A:ROUGE123:1",
            scenario=scenario,
        )
        self.assertEqual(result.returncode, 6)
        self.assertEqual(self.output(result)["status"], "indeterminate")

    def test_write_timeout_is_indeterminate(self) -> None:
        scenario = {
            "devices": [
                {
                    "serial": "ROUGE123",
                    "responses": {
                        "getvar:product": ["OKAY3320A"],
                        "getvar:serialno": ["OKAYROUGE123"],
                        "write-config:1": ["__TIMEOUT__"],
                    },
                }
            ]
        }
        result, _, _ = self.run_cli(
            "write-timeout",
            "--serial",
            "ROUGE123",
            "--value",
            "1",
            "--execute",
            "--acknowledge",
            "WRITE-CONFIG:3320A:ROUGE123:1",
            scenario=scenario,
        )
        self.assertEqual(result.returncode, 6)
        self.assertEqual(self.output(result)["status"], "indeterminate")


if __name__ == "__main__":
    unittest.main()
