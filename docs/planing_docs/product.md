# ProofPath — Product Design Doc

**Author:** TBD
**Status:** Draft v0.1
**Last updated:** 2026-06-23
**One-liner:** Upload your CV, get one concrete job title, then prove in a week whether it actually fits.

---

## 1. The user & the moment

- **Who:** A Myanmar student or recent grad navigating a career transition abroad — someone who can name a broad field (social science, data science, governance) but is carrying three or four half-considered job titles and has committed to none of them.
- **When:** They've just tailored another CV for another vague direction, or finished another conversation with a teacher, cousin, or mentor that didn't resolve anything. Nine interviews confirmed the conversation alone rarely closes the gap — P7, the person with the most mentoring exposure of anyone interviewed, says directly: "meeting a mentor alone does not automatically solve career problems."
- **Why now:** Real income and legal pressure, named directly by P2 (in Thailand to avoid conscription, current job doesn't cover visa costs), P3 ("working just for survival"), and P4 ("I feel I waste my time because there is no income coming immediately"). Every month spent undecided between titles is a month not building proof in any of them.

## 2. The contract (I/O)

- **Input:** The CV(s) or cover letter(s) the user already has — pasted as text or uploaded as a file. No intake form, no "tell us about yourself" essay box. This automates the workaround P4 already does by hand: rereading her own CVs and cover letters to find her own pattern.
- **Output:** One concrete job title — never a ranked list — pulled from the pattern across their materials, with a "why this title" explanation that quotes the matched evidence back at them, 2–3 example paths of people who started from a similar pattern, and a single 1-week try-it sprint: a day-by-day trial task simulating a slice of that job's real work.
- **The loop:** One-shot per CV, but not one-shot per title. Paste/upload → get one job title + evidence + example paths → start the 1-week sprint → check off the daily tasks → finish and get a skills-and-timeline checklist → self-report fit or no-fit. On "no fit," the product automatically advances to the next-best matching title from the *same* CV — no re-upload, no re-explaining — and the sprint repeats. The loop ends when the user gets a fit, or runs out of matched titles for that CV.

## 3. The magical moment

> "I didn't have to talk to anyone or guess — I tried the actual work for a week, and it held up."

## 4. Scope: what we ARE building (v1)

- CV / cover letter input — paste text or upload a single file
- Pattern extraction that surfaces ONE concrete job title per pass — never a list
- A "why this title" explanation grounded in quoted fragments of their own materials, plus 2–3 real example paths of people who started from a similar pattern
- One structured 1-week try-it sprint tied to that title, with a day-by-day task checklist
- A skills-and-timeline checklist delivered at the end of the sprint, regardless of verdict
- A fit / no-fit self-report at sprint's end that automatically advances to the next-best title (same CV, no re-upload) on "no fit"

## 5. Scope: what we are NOT building

- **No multi-month structured mentoring program** — the coach's screened, 4–6 month model has the strongest proof point in the research (11 of 13 placed), but it's an operational service, not a v1 product bet
- **No mentor/peer directory or matching** — a real, named bottleneck (Opportunity 2 in the OST), but a separate cold-start problem; this product proves fit before anyone needs to be matched to a person
- **No ranked list of titles shown to the user** — internally we may know several plausible titles, but the user only ever sees one at a time; surfacing a list up front just reintroduces the indecision we're trying to kill
- **No accounts or login** — nothing needs to persist across visits or devices in v1
- **No AI coordinator, scheduling, or multilingual assistant** — a real pain point the coach named (Notion AI doesn't support Burmese), but it's a tool for an existing mentoring relationship, which doesn't exist in this product
- **No general "explore careers" browsing mode** — every entry point starts from an uploaded CV, never from browsing a catalog

## 6. The signature detail

The "why this title" box quotes back fragments of the user's own CV and cover letters as evidence — "we found 'governance' (3x) and 'monitoring' (2x) across what you pasted, that's a pattern, not a coincidence" — instead of a generic "based on your skills." It's the diagnostic mirror P4 built for herself by hand, made automatic. It should feel less like a recommendation engine and more like someone who read them more carefully than they read themselves. A working click-through of this exact mechanic already exists and is the part worth protecting most carefully as the product evolves past keyword matching — it's the only piece of the experience that has to feel earned rather than arbitrary.

## 7. Success: how we know it worked

- **Primary:** % of users who, after receiving their job title, complete the full 1-week try-it sprint. A title nobody tries is just another list.
- **Secondary (max 2):** % of completed sprints that end in a clear fit / no-fit verdict rather than stalling out mid-sprint; among "no fit" verdicts, % who continue to the next-best title rather than abandoning.
- **What we're NOT measuring:** Total signups, number of distinct job titles surfaced, time-on-app.

## 8. Open questions

- [ ] Is keyword/pattern matching against a small, hand-curated set of fields specific enough to act on at pilot scale, or does match quality degrade too fast outside the first handful of fields to be trustworthy?
- [ ] What's the right field library to launch with — keep it narrow and deep, or accept thinner coverage across more fields?
- [ ] How do we phrase the fit/no-fit prompt so people answer honestly instead of defaulting to "fit" out of sunk cost after a week of effort?
- [ ] Does cycling through multiple "no fit" titles in a row need its own framing (e.g., showing how many matches remain) so it doesn't start to feel like rejection rather than progress?

## 9. Handoff

- **For UX:** Cycling through a second or third "no fit" title without it feeling like a punishing trial-and-error loop is the hardest design question — each pass has to feel like it ruled something out, not like the product is guessing.
- **For Eng:** Turning raw CV text into one defensible title without quietly falling back to a generic list — and deciding how long a hand-curated keyword approach can hold up before it needs something smarter — is the hardest technical question.
