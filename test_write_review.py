#!/usr/bin/env python3
"""Regression tests for the reviewer-owned JSON writer."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parent
PLACEHOLDER = "<absolute directory of this SKILL.md>"
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

    def documented_command(self, skill):
        """The one fenced sh block each SKILL.md documents for its writer."""
        blocks = re.findall(r"^```sh\n(.*?)^```$", (skill / "SKILL.md").read_text(encoding="utf-8"), re.M | re.S)
        self.assertEqual(len(blocks), 1, skill.name)
        return blocks[0]

    def install(self, skill, home):
        """Copy the skill directory alone to somewhere outside the repository, as a runner may."""
        installed = Path(home).resolve() / "skills" / skill.name
        shutil.copytree(skill, installed)
        return installed

    def environment(self, **overrides):
        environment = {key: value for key, value in os.environ.items() if key != "SCSH_RESULT"}
        environment.update(overrides)
        return environment

    def test_every_documented_command_runs_from_the_repository_root_with_the_skill_installed_elsewhere(self):
        for skill in SKILLS:
            command = self.documented_command(skill)
            self.assertNotIn('="', command, f"{skill.name}: values are single-quoted, never double-quoted")
            self.assertEqual(command.count(f"SKILL_DIR='{PLACEHOLDER}'\n"), 1, f"{skill.name}: no guessed install path")
            for result in [None, "tmp/declared/result.json"]:
                with self.subTest(skill=skill.name, result=result), tempfile.TemporaryDirectory() as repository, \
                        tempfile.TemporaryDirectory() as home:
                    command = self.documented_command(skill).replace(PLACEHOLDER, str(self.install(skill, home)))
                    overrides = {"SCSH_RESULT": result} if result else {}
                    subprocess.run(command, check=True, cwd=repository, env=self.environment(**overrides), shell=True)
                    written = Path(repository) / (result or f"tmp/code-review-{skill.name}.json")
                    document = json.loads(written.read_text(encoding="utf-8"))
                    self.assertEqual(document["result"], {"grade": "good", "issues_found": 2})
                    self.assertEqual(
                        document["issues"][0]["description"],
                        '`parse()` returns "ok" before validating $input, so the caller\'s error is lost.',
                    )
                    self.assertEqual(
                        document["issues"][0]["suggestion"],
                        'Validate first; return "ok" only after `check($input)` passes.',
                    )
                    self.assertEqual(document["issues"][1]["description"], 'Document the "strict" mode.')
                    self.assertEqual(document["issues"][1]["line"], 9)
                    leftovers = sorted(path.name for path in written.parent.iterdir())
                    self.assertEqual(leftovers, [written.name], "no temporary file survives the atomic write")
                    self.assertFalse((Path(home).resolve() / "skills" / skill.name / "tmp").exists(), "nothing lands in the skill")

    def test_single_quoting_carries_hostile_values_through_a_real_shell(self):
        def quote(value):
            return "'" + value.replace("'", "'\\''") + "'"

        description = 'It\'s `touch nope`, $(touch nope), $HOME, "quoted", a backslash \\, !bang,\nand a second line 雪'
        suggestion = "Don't; use `json.dump()`."
        with tempfile.TemporaryDirectory() as repository, tempfile.TemporaryDirectory() as home:
            command = (
                f"SKILL_DIR='{self.install(SKILLS[0], home)}'\n"
                "python3 \"$SKILL_DIR/scripts/write_review.py\" --grade='poor' --issue --commit='abc123' "
                f"--severity='blocking' --file='path with spaces.py' --line='0' "
                f"--description={quote(description)} --suggestion={quote(suggestion)}"
            )
            subprocess.run(command, check=True, cwd=repository, env=self.environment(), shell=True)
            written = Path(repository) / f"tmp/code-review-{SKILLS[0].name}.json"
            issue = json.loads(written.read_text(encoding="utf-8"))["issues"][0]
            self.assertEqual(issue["description"], description)
            self.assertEqual(issue["suggestion"], suggestion)
            self.assertFalse((Path(repository) / "nope").exists(), "nothing inside a value was executed")

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
