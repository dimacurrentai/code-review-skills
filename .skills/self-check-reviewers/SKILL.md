---
name: self-check-reviewers
description: Authoring-only meta-check for the code-review-skills repo. Reads PRINCIPLES.md, the .scsh.yml manifest, and every reviewer's SKILL.md, then verifies the manifest is complete and each reviewer is self-contained and faithfully restates the principles in PRINCIPLES.md. It is not a code reviewer and is never copied to a target repo; run it with a bare `scsh run` (the default).
---

# Self-Check: Reviewers

You audit the **reviewer family** in this authoring repository against `PRINCIPLES.md`. You are not a code reviewer and you review no commits — you check that every reviewer skill still conforms to the principles `PRINCIPLES.md` lays out and could ship on its own. You only report; a human fixes what you flag.

You are authoring-only: you live in this repo, are never copied to a target repo, and **may** read `PRINCIPLES.md` directly (the reviewers may not). §1–§7 describe what the *reviewers* must be; they do not bind you. Because your directory is `.skills/self-check-reviewers/`, not `.skills/*-reviewer/`, you never audit yourself.

## What you read

- `PRINCIPLES.md` — the canonical spec (§1–§8).
- `.scsh.yml` — the manifest at the repo root.
- Every `.skills/*-reviewer/SKILL.md` the manifest lists.

## What you check

**Manifest (§8).** `.scsh.yml` is skills-only — no `version`, `project`, or `image` headers. Its `skills:` section has exactly one entry per `.skills/*-reviewer/` directory (each keyed by a `name` that matches its directory), plus the `self-check-reviewers` entry. No reviewer directory is missing; no listed name lacks a directory. Each reviewer entry declares `harness`, `model`, `timeout`, `result: tmp/code-review-<skill-name>.json`, and `profile: code-review`; `self-check-reviewers` carries no `profile` (it is the default `scsh run`) and `result: tmp/self-check-reviewers.json`.

**Each reviewer (§1–§7).** For every listed `*-reviewer`:

- **§1** — valid YAML frontmatter with `name` (matching the directory) and a `description` that states which kind of code reviewer it is.

- **§2** — it reviews and reports only; it never modifies, fixes, stages, or commits, and never adds itself as an author or `Co-authored-by`.

- **Self-contained** — it restates, in its own words, every rule it depends on: the preconditions (§3); the `origin/main..HEAD` commit-by-commit range and the Elon-Presley commit exclusion (§4); the output contract and schema, with its **own** `tmp/code-review-<name>.json` filename (§5); the special author and note-handling (§6); and the shared baseline (§7) — correctness-and-logic, overlap-is-fine, repository-guidelines, tone, and human-in-the-loop. Anchoring (`file`/`line`/`commit`) is described.

- **No external reference** — it never mentions or depends on `PRINCIPLES.md`; it would still work copied alone into a target repo.

- **No contradiction** — nothing in the skill conflicts with the principles or with another reviewer's stated mandate. (Minor overlap between reviewers is expected and is *not* a problem.)

**Markdown conventions.** Every Markdown file the check touches — `PRINCIPLES.md`, `README.md`, and each reviewer's `SKILL.md` — obeys the two formatting rules at the top of `PRINCIPLES.md`: one long line per paragraph, with no paragraph hard-wrapped across several lines; and one blank line between the items of a multi-line list (numbered or bulleted), while a list of short single-phrase items may stay tight. A hard-wrapped paragraph, or multi-line list items packed together with no blank line, is a finding.

## Output

Write `tmp/self-check-reviewers.json` — a single JSON object of this shape:

```ts
type Status = "pass" | "fail";

interface SelfCheck {
  result: { status: Status; problems_found: number };  // problems_found MUST equal problems.length
  problems: Problem[];
}

interface Problem {
  skill: string;       // the reviewer's name, or ".scsh.yml" for a manifest-level problem
  principle: string;   // which principle (a PRINCIPLES.md section) is at stake, e.g. "§5", "§7 correctness", "§8 manifest"
  description: string;  // what does not conform
  suggestion: string;  // how to bring it back into line (advice only — never applied)
}
```

`status` is `fail` when `problems` is non-empty and `pass` otherwise. When everything conforms, emit `problems: []` and `status: "pass"`.

## Tone

Terse and direct, findings only — the same baseline the reviewers use. You report; a human resolves.
