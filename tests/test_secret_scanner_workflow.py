# SPDX-License-Identifier: MPL-2.0
"""Regression checks for the reusable secret-scanner caller in PR #13.

Requires Python 3 and PyYAML. Run from the repository root with:
    python -m unittest discover -s tests -p 'test_secret_scanner_workflow.py'

These configuration tests do not invoke GitHub Actions or the remote scanner.
"""

from pathlib import Path
import unittest

import yaml


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1] / ".github/workflows/secret-scanner.yml"
)


class SecretScannerWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # BaseLoader keeps GitHub's `on` key as text instead of interpreting it
        # as a YAML 1.1 boolean. All scalar assertions below use string values.
        cls.workflow = yaml.load(
            WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
        )
        cls.scan = cls.workflow["jobs"]["scan"]

    def test_caller_does_not_forward_secrets(self):
        # Reject both `inherit` and explicit mappings, including empty ones:
        # removing the key is the contract introduced by this PR.
        self.assertNotIn("secrets", self.scan)

    def test_scanner_keeps_minimum_token_permissions(self):
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})

    def test_job_cannot_override_workflow_permissions(self):
        # A job-level grant can widen the token despite the workflow default.
        self.assertNotIn("permissions", self.scan)

    def test_scan_still_calls_the_reviewed_reusable_workflow(self):
        self.assertEqual(
            self.scan["uses"],
            "hyperpolymath/standards/.github/workflows/"
            "secret-scanner-reusable.yml@"
            "571cc734cd69fb846032ec77a662aa8ee4fc32cd",
        )
        # Preserve the reusable job rather than replacing it with local steps.
        self.assertNotIn("steps", self.scan)
        self.assertNotIn("runs-on", self.scan)

    def test_pull_requests_remain_unfiltered(self):
        events = self.workflow["on"]
        self.assertIn("pull_request", events)
        # No branch/path filters that could silently omit a required PR scan.
        self.assertIn(events["pull_request"], ("", {}))
        self.assertNotIn("if", self.scan)
        self.assertNotIn("continue-on-error", self.scan)

    def test_pushes_to_both_default_branch_names_remain_scanned(self):
        self.assertEqual(
            self.workflow["on"]["push"], {"branches": ["main", "master"]}
        )


if __name__ == "__main__":
    unittest.main()
