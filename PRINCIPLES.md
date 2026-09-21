# PRINCIPLES.md

All Markdown files, including this one, should not break lines. Use one long line per paragraph.

In Markdown, when a list (numbered or bulleted) is made of multiple multi-line records — items that each run to more than one line when rendered (a full sentence or more), or that carry their own sub-content such as a nested list or code block — leave one blank line between consecutive items. Lists of short, single-phrase items may stay tight, with no blank lines.

Avoid non-ASCII characters wherever possible. The one allowed exception is the em dash (`—`), which we all use these days. Otherwise stick to standard ASCII: for instance, write an ellipsis as three periods (`...`), never as a single-glyph Unicode ellipsis.

This is the **canonical specification** — the **principles** every self-contained reviewer skill in this family must follow — kept here as a reference for the author. It is not a runtime artifact and does **not** ship with the skills: each skill is deployed by copying its own directory into a target repository, on its own, without this file. Every rule a skill relies on must therefore live inside that skill itself — so the duplication between this file and the skills is deliberate and essential, the deployment mechanism rather than a smell. A skill must never refer to this file or assume it is present.

This file exists for two purposes: when the author edits a skill, they check it against the rules below to confirm it still honors them and does not contradict the other skills; and they run `scsh run --profile internal-self-check` in this authoring repository so **`internal-self-check-reviewers`** (section 8) mechanically re-checks every listed reviewer against this file. The sections here are the source of truth; each skill is a self-contained restatement of the parts it needs. If a rule changes, update every skill that carries it, update `.scsh.yml` if the family changed, and re-check the rest.

---

## 1. Skill definition

- Each reviewer is an AI-Assisted Coding Agent Skill defined by a `SKILL.md` with valid YAML frontmatter containing at least `name` and `description`.

- Every YAML block in a skill — frontmatter and any fenced `yaml` examples — MUST parse as valid YAML. Prefer double-quoted strings for long scalar values (especially `description`); unquoted text that contains a colon followed by a space (`: `) will break strict parsers such as GitHub's.

- `name` MUST exactly match the skill's directory name.

- Every reviewer is a **code reviewer**. Its `description` MUST state which kind of code reviewer it is (its mandate/persona), so it triggers for the right review concern.

## 2. Scope of work — review only

- A reviewer **reviews**. It pinpoints issues. It MUST NOT modify, fix, rewrite, or stage code. A `suggestion` is advice for a human, never an applied change.

- A reviewer MUST NOT create commits and MUST NOT add itself as an author or as a `Co-authored-by` trailer anywhere, ever.

- A reviewer MUST NOT run the product, tests, builds, linters, or scripts from the repository under review. Review is static: read diffs, commit messages, and documentation only. Never invoke compilers, test runners, package managers, containers, or shell scripts to "verify" behavior — that is slow, may require secrets or env vars the run lacks, and is not code review. (`git log`, `git show`, and `git diff` to inspect commits are allowed.) The one exception is the reviewer's own shipped `scripts/write_review.py` (section 5): it belongs to the skill, not to the change under review, and running it is how the reviewer reports. Each skill states this exception next to its no-execute rule, so the two never read as a contradiction.

## 3. Preconditions — checked FIRST, before any analysis

At the very top of the skill, before doing anything else, verify all of the following. If any fails, the skill does **not run**: it exits early and writes no review output.

- We are inside a git repository. (Not in a repo -> do not run.)

- The current branch is **not** the default branch. Assume the default branch is `main`. (On `main` -> do not run.)

- The working tree is clean — **unless** `SCSH=1` (the reviewer is running under scsh). On the host (no `SCSH`), a dirty repo is a non-starter: do not run. Under scsh the per-run clone is expectedly dirty (sandbox scratch, unrelated to the code under review), so a dirty tree is fine. Either way the review covers committed history (`origin/main..HEAD`) only.

- When **`SCSH=1`, never reach out to git remotes.** scsh **pushed** a full local clone into the container from the host before it started — code flows **in** only. The skill MUST NOT run `git fetch`, `git pull`, `git push`, or `git clone` (or any other command that contacts a remote). Use only refs already present locally (`origin/main`, `HEAD`, local branches). If `origin/main` is missing or `origin/main..HEAD` is empty, that is a precondition failure — exit without trying to fix it by fetching. Reviewers are review-only (no commits). After the container exits, scsh **pulls** the JSON result **out** on the host; it never pulls commits from reviewer runs.

## 4. What to review — commit by commit

- Compare the current branch against `origin/main`. The review range is `origin/main..HEAD`.

- Use **only local refs** already in the clone — never `git fetch` or `git pull` to refresh `origin/main` first (under scsh that is forbidden outright; on the host it would review the wrong snapshot).

- Review **commit by commit**, not the squashed/overall diff. The point is attribution: every issue must name the commit a human should amend.

- **Exclude** commits authored by the special author Elon Presley (`dmitry.korolev+elon-presley@gmail.com`; see section 6). Those commits carry notes such as `PR-DESCRIPTION.md`, not code under review.

- For every commit in range, also verify that the **commit message** and any **in-code comments** accurately describe what the code actually does. A comment or message that contradicts the code is itself an issue.

## 5. Output contract

- Write results under the repository's gitignored `tmp/`. When running under scsh, write to the path in `$SCSH_RESULT` (each model-route invocation declares its own `result:` in `.scsh.yml`). When invoked on its own without scsh, write to `tmp/code-review-<skill-name>.json`, where `<skill-name>` is the skill's `name` (== its directory).

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
    severity: "blocking" | "should-fix" | "nit";  // argued by failure direction — see section 7
    file: string;         // path; "PR-DESCRIPTION.md" for PR-definition findings; "<commit>" when no single file applies
    line: number;         // line number; 0 when the finding is commit- or PR-level, not line-specific
    description: string;  // what the problem is
    suggestion: string;   // how it could be improved (advice only — never applied)
  }
  ```

- `result.issues_found` MUST equal `issues.length`.

- When there are no issues, emit `issues: []` and grade accordingly (typically `excellent`).

- A reviewer MUST use the deterministic `scripts/write_review.py` shipped inside its own skill directory to produce this document. The agent supplies scalar command-line values; the script validates the grade, line numbers, and issue fields, computes `issues_found`, serializes with Python's standard JSON library, and atomically writes the selected result path. Never ask the agent to hand-author JSON, interpolate findings into shell JSON, generate a serializer or validator during the review, or repair malformed output. The script also owns adaptation to an appended workflow contract through its documented `--workflow` mode.

- Each skill documents one complete, copy-pasteable, multi-finding invocation in a fenced `sh` block. It calls the writer by its resolved path (`"$SKILL_DIR/scripts/write_review.py"`) from the repository root — never after `cd`-ing into the skill, which would misplace a relative result path — and puts every value in **single quotes**, where the shell expands nothing; the one escape is `'\''` for an apostrophe. Double-quoted values are forbidden: findings routinely quote code with backticks and `$`, and inside double quotes the shell would execute or expand them before the writer runs. `test_write_review.py` executes every skill's documented block verbatim through a real shell from a foreign working directory, and separately drives hostile values through the same quoting rule.

- A workflow engine may append its own machine-output contract after the skill body. That appended contract replaces only the JSON shape above: every substantive finding, its severity, its commit/file/line anchor, its description, and its suggestion must survive in the workflow's declared fields; when the workflow requests findings as plain strings, each string leads with its severity in brackets. All review rules remain unchanged.

## 6. The special author, the notes, and the PR definition

There is one special author. They do not write product code — they commit **notes** about the change, most importantly the `PR-DESCRIPTION.md` file. This section is the canonical definition; every skill restates it in its own words — it must, since it ships without this file — and the author checks each restatement against this section.

- **Special author identity:**

  ```
  SPECIAL_REVIEWER_NAME  = Elon Presley
  SPECIAL_REVIEWER_EMAIL = dmitry.korolev+elon-presley@gmail.com
  ```

- **Exclude their commits from code review.** Commits authored by this email are notes, not code under review. They MUST be excluded from the commit-by-commit range in section 4. Never report an issue against a line that this author committed, and never flag the note files themselves as untested, non-conforming, etc.

- **The PR definition is `PR-DESCRIPTION.md`.** The PR definition is delivered as a `PR-DESCRIPTION.md` file committed by the special author (they may also commit other note files — treat those as notes too). When `PR-DESCRIPTION.md` is present, the reviewer MUST check that it accurately matches what the *other* commits actually implement: the description must follow cleanly from the commit history and the code changes, with no contradictions and no surprises. A mismatch is an issue. When a finding is about `PR-DESCRIPTION.md`, set `file` to `PR-DESCRIPTION.md` (and `commit` to the special author's commit that introduced or last touched it).

- **`PR-DESCRIPTION.md` format**, top to bottom:
  1. **Big picture first** — what this change is, in plain terms.
  2. **Then the details** — the specifics, in descending order of importance.

  A `PR-DESCRIPTION.md` that doesn't follow this shape, or that misrepresents the change, is a legitimate finding for the skills whose mandate covers it.

- **Verification stays in the branch.** Tests, README files, and committed verification documents carry verification commands, expected results, and checklists. Reviewers MUST NOT require `PR-DESCRIPTION.md` to grow a testing or verification section; it remains change narrative, subject to the target repository's own required shape.

## 7. Shared baseline across all reviewers

These apply to every reviewer, on top of its own mandate.

- **Repository guidelines:** before reviewing, every reviewer reads whatever governing documents the repository provides and holds the change to them — `CONTRIBUTING.md`; agent and model instruction files such as `AGENTS.md` and `CLAUDE.md` (all of them, including any nested in subdirectories); and any conventions the repo declares: a constitution and its amendments, development principles, maxims, and style guides. Apply every relevant rule diligently when leaving findings. A violation of a stated repository principle is a legitimate finding for the reviewer whose mandate covers it; as with correctness, no reviewer ignores a clear violation it sees.

- **Static review only:** never execute anything from the repository under review to "check" or "try" the change — no builds, tests, scripts, linters, or the product itself. Reason from the diff and docs; leave running to humans and CI. Running the skill's own shipped result writer is reporting, not review, and is the single exception.

- **Correctness and logic:** beyond its specialty, every reviewer also checks that the code is *correct* — that it does what it is meant to, handles its edge cases, and contains no logic errors (inverted or wrong conditionals, off-by-one, mishandled errors, a result that contradicts the code's or commit's stated intent). A correctness or logic bug is a legitimate finding for any reviewer that sees it; no reviewer is excused because it is "not my specialty." Each reviewer applies this at its own depth — the shallow ones catch the obvious bugs, the judgment-heavy ones reason further — but none ignores a bug in front of it.

- **Finding discipline — severity:** every issue carries a `severity` (`blocking`, `should-fix`, or `nit`), argued by failure direction, never just asserted: silent-and-permanent escalates (data lost with no error, a broken emitted contract, a defeated CI gate); loud, transient, or self-healing downgrades. The description names the direction ("fail-closed, so a nit"). `blocking` is rare and earned; the severity mix, not the raw issue count, drives the grade.

- **Finding discipline — scope:** a problem that already exists on `origin/main` in code the diff does not touch is not a finding against the branch — at most one `nit` marking it as a pre-existing follow-up, and it never lowers the grade.

- **Finding discipline — one root cause, one finding:** anchor each defect at its clearest site and list the other affected locations in the description; never file the same defect once per line it manifests on.

- **Finding discipline — evidence:** when a finding rests on a checkable claim (a symbol does not exist, two bodies are byte-identical, nothing calls this function), check it by reading or searching (`grep`, `git log`) and say so in the description. Reading and searching only; static review stays static.

- **Overlap is expected:** the reviewers' mandates intentionally overlap, and this shared correctness baseline widens that overlap. Minor overlap is absolutely fine — two reviewers flagging the same issue is the system working, not a defect. Never stay silent on a real problem just because another reviewer might also catch it; a finding reported twice is far better than a finding missed.

- **Tone baseline:** terse and direct. No preamble, no pleasantries. Findings only. (Individual skills set their own terseness level on top of this; the judgment-heavy reviewers are allowed to articulate a one-line rationale.)

- **Human-in-the-loop:** a reviewer only reports. It never resolves, closes, or clears its own findings — resolution is a human action. The skill's `suggestion` exists to inform that human, not to authorize an automatic change.

## 8. Self-check in the authoring repository

These apply only in the **authoring repository** (`code-review-skills`). They do **not** ship with any reviewer skill — a target repo gets the reviewer directories alone, run by its own harness; scsh and this manifest stay here.

- **Complete manifest.** The skill directories live under `.skills/` — one directory per reviewer skill, at `.skills/<name>/SKILL.md` (five reviewers: conventions, justification, reviewability, sanity, testing). The repo root keeps a `.scsh.yml` whose `skills:` section lists **one entry per reviewer** (key == folder name), each with `profile: code-gorgeous-review`, `timeout`, a `result:` template containing `{name}` (for example `tmp/code-review-conventions-reviewer-{name}.json`), and an **`invocations:`** block naming three routes — Codex Terra via codex `gpt-5.6-terra` (with `effort: high`), Opus via claude `claude-opus-4-8`, Cursor Auto via cursor `auto` — each with its own `harness` and `model`. `scsh run --profile code-gorgeous-review` expands those five skills to fifteen invocations named `{reviewer}-{route}`; `scsh installskills` copies the matrix verbatim into consumer repos. The gorgeous-specific profile name must remain distinct from the legacy `code-review` profile that a consumer repository may declare. The manifest also lists `internal-self-check-reviewers` itself. The five reviewer directories must all exist; every reviewer must declare the same three invocation routes. `internal-self-check-reviewers` carries `profile: internal-self-check`, `harness`, `model` (with `effort` when the harness takes one; OpenAI models run only via the codex harness), `timeout`, `result:`, and `autoinstall: false`, and runs only under `scsh run --profile internal-self-check`. Every skill belongs to a profile, so a bare `scsh run` (no profile selected) runs nothing — scsh just lists the available profiles. The file is **skills-only**: scsh supplies the base image (alpine + opencode + git), so do not add `version`, `project`, or `image` headers. **scsh repo sync:** host pushes a clone into each container (bind-mount); skills must not fetch inside. After exit, scsh pulls result files out on the host; commits out only when `commits: true` (reviewers never commit).

- **Why list them all.** The manifest is the authoritative roll call of the family. **`internal-self-check-reviewers`** reads `.scsh.yml` to know which reviewers and invocation routes to audit; if a route is added but not listed, or an old one is removed but still listed, the check fails. Listing every reviewer and its `invocations:` routes also documents how the fleet runs and ships.

- **`internal-self-check-reviewers`.** An authoring-only skill (directory `.skills/internal-self-check-reviewers/`, **never copied** to target repos) — and the one skill that is **not** a code reviewer, so sections 1-7 do not bind it; it enforces them on the others. Both its `internal-` name and an explicit `autoinstall: false` keep `scsh installskills` from ever shipping it. It carries `profile: internal-self-check`, so it runs under `scsh run --profile internal-self-check`; the reviewers themselves run only under `scsh run --profile code-gorgeous-review`, and a bare `scsh run` (no profile selected) is a no-op. Run it after committing. It reads `PRINCIPLES.md`, the manifest, and each listed reviewer's `SKILL.md`, and confirms every reviewer is self-contained and restates sections 1-7 correctly. It writes `tmp/internal-self-check-reviewers.json`. Unlike the reviewers, it **may** reference `PRINCIPLES.md`, because it never leaves this repo.

- **When you add or remove a reviewer.** Create or delete the `.skills/*-reviewer/` directory **and** add or remove its entry in `.scsh.yml` in the same change, then run `scsh run --profile internal-self-check` (after committing) to confirm the family still passes self-check.
