#!/usr/bin/env python3
"""Regression tests for the reviewer-owned JSON writer."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parent
SKILLS = sorted((ROOT / ".skills").glob("*-reviewer"))


class WriteReviewTest(unittest.TestCase):
    def run_writer(self, *arguments):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "nested" / "result.json"
            environment = os.environ.copy()
            environment["SCSH_RESULT"] = str(result)
            subprocess.run(
                ["python3", str(SKILLS[0] / "scripts" / "write_review.py"), *arguments],
                check=True,
                env=environment,
            )
            text = result.read_text(encoding="utf-8")
            return text, json.loads(text)

    def test_all_reviewers_ship_the_identical_writer(self):
        bodies = [(skill / "scripts" / "write_review.py").read_bytes() for skill in SKILLS]
        self.assertEqual(len(SKILLS), 5)
        self.assertTrue(all(body == bodies[0] for body in bodies))

    def test_documented_multi_issue_command_preserves_escaped_quotes(self):
        command = (
            'python3 scripts/write_review.py --grade="good" '
            '--issue --commit="abc123" --severity="should-fix" '
            '--file="src/parser.py" --line="17" '
            '--description="The parser returns \\"ok\\" before validation." '
            '--suggestion="Validate before returning the \\"ok\\" result." '
            '--issue --commit="def456" --severity="nit" '
            '--file="README.md" --line="9" '
            '--description="Document the \\"strict\\" mode." '
            '--suggestion="Add one example."'
        )
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "result.json"
            environment = os.environ.copy()
            environment["SCSH_RESULT"] = str(result)
            subprocess.run(
                command,
                check=True,
                cwd=SKILLS[0],
                env=environment,
                shell=True,
            )
            document = json.loads(result.read_text(encoding="utf-8"))

        self.assertEqual(document["result"]["issues_found"], 2)
        self.assertEqual(
            document["issues"][0]["description"],
            'The parser returns "ok" before validation.',
        )
        self.assertEqual(
            document["issues"][1]["description"],
            'Document the "strict" mode.',
        )

    def test_default_result_serializes_hostile_scalar_values(self):
        description = 'A "quote", a backslash \\, a newline\n雪, `$HOME`, and $(touch nope)'
        text, document = self.run_writer(
            "--grade=good", "--issue", "--commit=abc123", "--severity=blocking",
            "--file=path with spaces.py", "--line=17", f"--description={description}",
            "--suggestion=Keep `value` and use json.dump().",
        )
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(document["result"], {"grade": "good", "issues_found": 1})
        self.assertEqual(document["issues"][0]["description"], description)
        self.assertEqual(document["issues"][0]["severity"], "blocking")

    def test_workflow_mode_and_empty_review(self):
        _, empty = self.run_writer("--workflow", "--grade", "excellent")
        self.assertEqual(empty, {"grade": "excellent", "comments": []})
        _, populated = self.run_writer(
            "--workflow", "--grade=average", "--issue", "--commit=c0ffee",
            "--severity=should-fix", "--file=src/main.rs", "--line=0", "--description=Two paragraphs.\n\nStill quoted: `x`.",
            "--suggestion=Split it.",
        )
        self.assertEqual(populated["grade"], "average")
        self.assertIn("Still quoted: `x`.", populated["comments"][0])

    def test_bad_values_fail_without_a_result(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "result.json"
            environment = os.environ.copy()
            environment["SCSH_RESULT"] = str(result)
            completed = subprocess.run(
                ["python3", str(SKILLS[0] / "scripts" / "write_review.py"), "--grade=great"],
                env=environment, capture_output=True, text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("--grade must be one of", completed.stderr)
            self.assertFalse(result.exists())


if __name__ == "__main__":
    unittest.main()
