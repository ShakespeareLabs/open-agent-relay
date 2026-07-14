from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class ExampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = Path(__file__).parents[1] / "examples" / "read-only-campaign-report" / "report.py"

    def run_report(self, request: str) -> str:
        completed = subprocess.run(
            [sys.executable, str(self.report)],
            input=request,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout

    def test_campaign_report_summarizes_all_rows(self) -> None:
        output = self.run_report("Summarize all campaigns")
        self.assertIn("Spend: $3,600.00", output)
        self.assertIn("Revenue: $9,300.00", output)
        self.assertIn("ROAS: 2.58x", output)

    def test_campaign_report_filters_exact_campaign_name(self) -> None:
        output = self.run_report("Summarize Launch Retargeting")
        self.assertIn("Campaigns: Launch Retargeting", output)
        self.assertIn("ROAS: 1.60x", output)
        self.assertNotIn("Brand Search", output)


if __name__ == "__main__":
    unittest.main()
