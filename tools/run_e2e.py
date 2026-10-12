from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / ".artifacts"


class ArtifactResult(unittest.TextTestResult):
    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)


def main() -> int:
    if ARTIFACT_ROOT.exists():
        shutil.rmtree(ARTIFACT_ROOT)
    ARTIFACT_ROOT.mkdir(parents=True)

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), "test_e2e.py")
    runner = unittest.TextTestRunner(verbosity=2, resultclass=ArtifactResult)
    result = runner.run(suite)
    artifact = {
        "errors": len(result.errors),
        "failures": len(result.failures),
        "successful": result.wasSuccessful(),
        "tests_run": result.testsRun,
    }
    (ARTIFACT_ROOT / "e2e-results.json").write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
