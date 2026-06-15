# PRINCIPLES.md

All Markdown files, including this one, should not break lines. Use one long line per paragraph.

In Markdown, when a list (numbered or bulleted) is made of multiple multi-line records — items that each run to more than one line when rendered (a full sentence or more), or that carry their own sub-content such as a nested list or code block — leave one blank line between consecutive items. Lists of short, single-phrase items may stay tight, with no blank lines.

This is the **canonical specification** — the **principles** every self-contained reviewer skill in this family must follow — kept here as a reference for the author. It is not a runtime artifact and does **not** ship with the skills: each skill is deployed by copying its own directory into a target repository, on its own, without this file. Every rule a skill relies on must therefore live inside that skill itself — so the duplication between this file and the skills is deliberate and essential, the deployment mechanism rather than a smell. A skill must never refer to this file or assume it is present.

This file exists for two purposes: when the author edits a skill, they check it against the rules below to confirm it still honors them and does not contradict the other skills; and they run `scsh run` in this authoring repository so **`self-check-reviewers`** (§8) mechanically re-checks every listed reviewer against this file. The sections here are the source of truth; each skill is a self-contained restatement of the parts it needs. If a rule changes, update every skill that carries it, update `.scsh.yml` if the family changed, and re-check the rest.

---

## 1. Skill definition

- Each reviewer is an AI-Assisted Coding Agent Skill defined by a `SKILL.md` with valid YAML frontmatter containing at least `name` and `description`.

- `name` MUST exactly match the skill's directory name.

- Every reviewer is a **code reviewer**. Its `description` MUST state which kind of code reviewer it is (its mandate/persona), so it triggers for the right review concern.

## 2. Scope of work — review only

- A reviewer **reviews**. It pinpoints issues. It MUST NOT modify, fix, rewrite, or stage code. A `suggestion` is advice for a human, never an applied change.

- A reviewer MUST NOT create commits and MUST NOT add itself as an author or as a `Co-authored-by` trailer anywhere, ever.

## 3. Preconditions — checked FIRST, before any analysis

At the very top of the skill, before doing anything else, verify all of the following. If any fails, the skill does **not run**: it exits early and writes no review output.

- We are inside a git repository. (Not in a repo → do not run.)

- The current branch is **not** the default branch. Assume the default branch is `main`. (On `main` → do not run.)

- The working tree is clean. (Dirty repo → do not run.)

## 4. What to review — commit by commit

- Compare the current branch against `origin/main`. The review range is `origin/main..HEAD`.

- Review **commit by commit**, not the squashed/overall diff. The point is attribution: every issue must name the commit a human should amend.

- **Exclude** commits authored by the special author Elon Presley (`dmitry.korolev+elon-presley@gmail.com`; see §6). Those commits carry notes such as `PR-DESCRIPTION.md`, not code under review.

- For every commit in range, also verify that the **commit message** and any **in-code comments** accurately describe what the code actually does. A comment or message that contradicts the code is itself an issue.

## 5. Output contract

- Write results to the repository root in a file named:

  ```
  tmp/code-review-<skill-name>.json
  ```

  where `<skill-name>` is the skill's `name` (== its directory).

- The file MUST be a single, strongly typed JSON object matching this schema:

  ```ts
  type Grade = "excellent" | "good" | "average" | "poor";

  interface Review {
    result: {
      grade: Grade;          // overall assessment
      issues_found: number;  // MUST equal issues.length
    };
    issues: Issue[];
  }

  interface Issue {
    commit: string;       // SHA of the commit where this should be addressed
    file: string;         // path; "PR-DESCRIPTION.md" for PR-definition findings; "<commit>" when no single file applies
    line: number;         // line number; 0 when the finding is commit- or PR-level, not line-specific
    description: string;  // what the problem is
    suggestion: string;   // how it could be improved (advice only — never applied)
  }
  ```

- `result.issues_found` MUST equal `issues.length`.

- When there are no issues, emit `issues: []` and grade accordingly (typically `excellent`).

## 6. The special author, the notes, and the PR definition

There is one special author. They do not write product code — they commit **notes** about the change, most importantly the `PR-DESCRIPTION.md` file. This section is the canonical definition; every skill restates it in its own words — it must, since it ships without this file — and the author checks each restatement against this section.

- **Special author identity:**

  ```
  SPECIAL_REVIEWER_NAME  = Elon Presley
  SPECIAL_REVIEWER_EMAIL = dmitry.korolev+elon-presley@gmail.com
  ```

- **Exclude their commits from code review.** Commits authored by this email are notes, not code under review. They MUST be excluded from the commit-by-commit range in §4. Never report an issue against a line that this author committed, and never flag the note files themselves as untested, non-conforming, etc.

- **The PR definition is `PR-DESCRIPTION.md`.** The PR definition is delivered as a `PR-DESCRIPTION.md` file committed by the special author (they may also commit other note files — treat those as notes too). When `PR-DESCRIPTION.md` is present, the reviewer MUST check that it accurately matches what the *other* commits actually implement: the description must follow cleanly from the commit history and the code changes, with no contradictions and no surprises. A mismatch is an issue. When a finding is about `PR-DESCRIPTION.md`, set `file` to `PR-DESCRIPTION.md` (and `commit` to the special author's commit that introduced or last touched it).

- **`PR-DESCRIPTION.md` format**, top to bottom:
  1. **Big picture first** — what this change is, in plain terms.
  2. **Then the details** — the specifics, in descending order of importance.

  A `PR-DESCRIPTION.md` that doesn't follow this shape, or that misrepresents the change, is a legitimate finding for the skills whose mandate covers it.

## 7. Shared baseline across all reviewers

These apply to every reviewer, on top of its own mandate.

- **Repository guidelines:** before reviewing, every reviewer reads whatever governing documents the repository provides and holds the change to them — `CONTRIBUTING.md`; agent and model instruction files such as `AGENTS.md` and `CLAUDE.md` (all of them, including any nested in subdirectories); and any conventions the repo declares: a constitution and its amendments, development principles, maxims, and style guides. Apply every relevant rule diligently when leaving findings. A violation of a stated repository principle is a legitimate finding for the reviewer whose mandate covers it; as with correctness, no reviewer ignores a clear violation it sees.

- **Correctness and logic:** beyond its specialty, every reviewer also checks that the code is *correct* — that it does what it is meant to, handles its edge cases, and contains no logic errors (inverted or wrong conditionals, off-by-one, mishandled errors, a result that contradicts the code's or commit's stated intent). A correctness or logic bug is a legitimate finding for any reviewer that sees it; no reviewer is excused because it is "not my specialty." Each reviewer applies this at its own depth — the shallow ones catch the obvious bugs, the judgment-heavy ones reason further — but none ignores a bug in front of it.

- **Overlap is expected:** the reviewers' mandates intentionally overlap, and this shared correctness baseline widens that overlap. Minor overlap is absolutely fine — two reviewers flagging the same issue is the system working, not a defect. Never stay silent on a real problem just because another reviewer might also catch it; a finding reported twice is far better than a finding missed.

- **Tone baseline:** terse and direct. No preamble, no pleasantries. Findings only. (Individual skills set their own terseness level on top of this; the judgment-heavy reviewers are allowed to articulate a one-line rationale.)

- **Human-in-the-loop:** a reviewer only reports. It never resolves, closes, or clears its own findings — resolution is a human action. The skill's `suggestion` exists to inform that human, not to authorize an automatic change.

## 8. Self-check in the authoring repository

These apply only in the **authoring repository** (`code-review-skills`). They do **not** ship with any reviewer skill — a target repo gets the reviewer directories alone, run by its own harness; scsh and this manifest stay here.

- **Complete manifest.** The skill directories live under `.skills/` — one directory per skill, at `.skills/<name>/SKILL.md`. The repo root keeps a `.scsh.yml` whose `skills:` section lists **every** reviewer skill — one entry per `.skills/*-reviewer/` directory, keyed by the skill's `name` (matching the directory) — plus the `self-check-reviewers` entry itself. The manifest must be complete: no reviewer omitted, no extra name without a matching directory. Each reviewer entry declares `harness`, `model`, `timeout`, `result: tmp/code-review-<skill-name>.json` matching §5, and `profile: code-review` — the reviewers run only under that profile, while `self-check-reviewers` carries no profile and is what a bare `scsh run` runs. The file is **skills-only**: scsh supplies the base image (alpine + opencode + git), so do not add `version`, `project`, or `image` headers.

- **Why list them all.** The manifest is the authoritative roll call of the family. **`self-check-reviewers`** reads `.scsh.yml` to know which reviewers to audit; if a new reviewer is added but not listed, or an old one is removed but still listed, the check fails. Listing every reviewer also documents how the family runs together under `scsh run` in this repo.

- **`self-check-reviewers`.** An authoring-only skill (directory `.skills/self-check-reviewers/`, **never copied** to target repos) — and the one skill that is **not** a code reviewer, so §1–§7 do not bind it; it enforces them on the others. It carries no `profile`, so a bare `scsh run` runs it (the default); the reviewers themselves run only under `scsh run --profile code-review`. Run it after committing. It reads `PRINCIPLES.md`, the manifest, and each listed reviewer's `SKILL.md`, and confirms every reviewer is self-contained and restates §1–§7 correctly. It writes `tmp/self-check-reviewers.json`. Unlike the reviewers, it **may** reference `PRINCIPLES.md`, because it never leaves this repo.

- **When you add or remove a reviewer.** Create or delete the `.skills/*-reviewer/` directory **and** add or remove its entry in `.scsh.yml` in the same change, then run `scsh run` (after committing) to confirm the family still passes self-check.
