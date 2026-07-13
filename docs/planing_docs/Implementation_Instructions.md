# Implementation Instructions

## PART 1 — IMPLEMENT THE APP CODE

- Build it according to @engineering.md (stack, file structure)
- Match the UI described in @ui.md
- Use the patterns in @reference/ as guidance for code style
- Backend: use Python with uv for dependency management
- If your chosen stack requires Node.js and it isn't installed on my
  system, install it via claude co-work (use brew/winget/apt) — ask
  permission first
- DO NOT start any dev servers — that's a later section

## PART 2 — APPLY THE TEST-GATE SKILL

After the code is written, apply the test-driven-dev skill from
`.agent/skills/skills-garden/eng-skills/test-driven-dev.md`.

Use the "Testing strategy" section in @engineering.md as the test plan.

**IMPORTANT:** Mock the Sonnet 4.6 API calls in tests — use a stub that returns
fake response data. The real API key isn't set up yet, and tests should
be deterministic and free anyway (best practice).

The skill should:

1. Write the tests described in the Testing strategy
2. Run them (use pytest for Python, Vitest or Jest for JS)
3. If any fail, fix the CODE (not the tests) and re-run
4. Up to 3 retry attempts max
5. If still failing after 3 tries, STOP and tell me what's broken

When Claude co-work asks permission to run commands (uv sync, uv pip
install, pytest, etc.), click Allow.

Report results when both parts are done.
