# ProofPath — Product Design Doc

**Author:** TBD
**Status:** Draft v0.1
**Last updated:** 2026-06-22
**One-liner:** Upload your CV, get one concrete job title, then prove in a week whether it actually fits.

---

## 1. The user & the moment

- **Who:** A Myanmar student or recent grad (P3, P4, P8's profile) who can name a broad field — social science, data science, governance — but has three or four half-considered job titles in their head and has picked none of them.
- **When:** They're staring at CVs they've tailored for different roles, not because they lack options but because they've never tested any single path against reality. The friend/teacher/mentor conversation they just had didn't resolve it either.
- **Why now:** Real income and time pressure, named directly by P2, P3, and P4 — "I feel I waste my time because there is no income coming immediately." Every month spent undecided between titles is a month not building proof in any of them.

## 2. The contract (I/O)

- **Input:** The CV(s) and cover letter(s) they already have. No new intake form, no "tell us about yourself" essay box — this automates the workaround P4 already does by hand: rereading her own CVs to find her own pattern.
- **Output:** One concrete job title — not a ranked list — pulled from the pattern across their materials, paired with a single 1-2 week try-it micro-sprint: a structured trial task simulating a slice of that job's real work.
- **The loop:** One-shot for v1. Upload CV → get one job title + a 1-2 week trial task → complete the sprint → get a skills-and-timeline checklist plus a fit / no-fit verdict. On "no fit," they re-run for the next-best title.

## 3. The magical moment

> "I didn't have to talk to anyone or guess — I just tried the actual work for a week and I knew this was it."

## 4. Scope: what we ARE building (v1)

- CV / cover letter upload (single or multiple files)
- Pattern extraction that surfaces ONE concrete job title matched to that pattern — never a list
- A "why this title" explanation grounded in their own materials, plus 2-3 real example paths of people who started from a similar pattern
- One structured 1-2 week try-it micro-sprint tied to that title, with a day-by-day task list
- A skills-and-timeline checklist delivered at the end of the sprint, regardless of verdict
- A fit / no-fit self-report at sprint's end that triggers a re-run for the next-best title on "no fit"

## 5. Scope: what we are NOT building

- **No multi-month structured mentoring program** — the coach's screened, 4-6 month model has the strongest proof point in the research, but it's an operational service, not a v1 product bet
- **No mentor/peer directory or matching** — real bottleneck (Opportunity 2), but a separate cold-start problem; this product proves fit before anyone needs to be matched to a person
- **No ranked list of titles** — one title per upload; a list just reintroduces the indecision we're trying to kill
- **No accounts or login** — re-upload a CV each time; nothing needs to persist across sessions in v1
- **No AI coordinator, scheduling, or multilingual assistant** — a real pain point the coach named, but it's a tool for an existing mentoring relationship, not relevant until mentoring exists in this product
- **No general "explore careers" browsing mode** — every entry point starts from an uploaded CV, not from browsing

## 6. The signature detail

The "why this title" explanation quotes back fragments of the user's own CV and cover letters as evidence — "you listed land rights coursework in 2 of your last 3 applications, that's a pattern, not a coincidence" — instead of a generic "based on your skills." It's the diagnostic mirror P4 built for herself by hand, made automatic. It should feel less like a recommendation engine and more like someone who read them more carefully than they read themselves.

## 7. Success: how we know it worked

- **Primary:** % of users who, after receiving their job title, complete the full 1-2 week try-it sprint. A title nobody tries is just another list.
- **Secondary (max 2):** % of completed sprints that end in a clear fit / no-fit verdict rather than "still unsure" (unsure means the sprint design failed); among "no fit" verdicts, % who re-run for a second title rather than abandoning.
- **What we're NOT measuring:** Total signups, number of distinct job titles surfaced, time-on-app.

## 8. Open questions

- [ ] Can CV-only pattern extraction produce a title specific enough to act on, or does it need one short follow-up question?
- [ ] What's the right per-field library of try-it sprints to launch with — 3 fields built deep (social science/governance, data science, IT), or 1 field built deep?
- [ ] How do we phrase the fit/no-fit prompt so people answer honestly instead of defaulting to "fit" out of sunk cost?
- [ ] Does a "no fit" verdict need to feed back into a sharper second title, or is a flat re-upload good enough for v1?

## 9. Handoff

- **For UX:** The no-fit path is the hardest design question — how someone leaves the sprint feeling like they gained something (a checklist, a closed door) rather than like they failed.
- **For Eng:** The try-it sprint content is hand-authored per title, not model-generated — the hardest technical question is turning raw CV text into one defensible title without quietly falling back to a generic list.
