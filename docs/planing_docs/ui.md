# ProofPath — UX Design Doc

**Designer:** TBD
**Status:** Draft v0.1
**Last updated:** 2026-06-23

---

## 1. The design bet

We're betting that the "why this title" evidence box carries the entire credibility of the product. ProofPath hands someone exactly one job title with no list and no alternatives in sight — that only works if the title feels earned, not arbitrary. So we're spending most of the design effort on making the evidence read like someone studied this person's CV closely, and keeping every other screen plain, fast, and unstyled by comparison. If the evidence box feels generic, the whole one-title bet collapses into "trust us."

## 2. The defining interaction

User pastes their CV text or drops in a file, then taps "Find my title." The button presses down. There's a brief, deliberate pause — long enough to feel like something happened, not so long it feels like a server call — and then the screen swaps: a small pill ("Your match"), a single bold title, and underneath it the evidence sentence, built from their own words: *"We found 'governance' (3x) and 'monitoring' (2x) across what you pasted — that's a pattern, not a coincidence."* Two or three short example paths follow, each one a sentence describing someone who started from a similar mix and tested their way to clarity. Total time: under a second of actual processing, but the screen should hold for ~400–600ms before revealing the result — instant seriously undersells a decision the user is about to spend a week proving or disproving. Feels like: a diagnosis, not a guess.

## 3. Screen inventory

Four screens, each tied to one distinct moment in the week-long loop — this is already one more than the "ideally 1–3" default, but each earns its place because it maps to a moment the user can't skip: handing over the evidence, receiving the verdict, doing the work, and reporting back.

- **Upload** — hand over CV text or file, the only input moment in the whole product
- **Result** — receive the one title, the evidence, and the example paths
- **Sprint** — work through the day-by-day try-it tasks for the current title
- **End** — see the skills/timeline checklist and self-report fit or no-fit

## 4. Screen-by-screen specs

### Upload

**Purpose:** Get CV text into the system with zero friction and zero setup.

**Layout (top to bottom):**
1. Brand header — name and one-line promise ("Upload your CV. Get one title. Prove it in a week — before you commit a year.")
2. A 4-step progress pill row (Upload → Your title → Try-it sprint → Verdict), so the user knows up front this is a short, bounded process, not an open-ended tool
3. A large paste textarea, labeled plainly ("Paste your CV / cover letter text")
4. A secondary file-upload control below it, clearly marked as the alternate path, not the primary one
5. A primary "Find my title" button
6. Two sample-CV buttons below a divider, for someone who wants to see the product work before trusting it with their own materials

**Key interactions:**
- Paste or type into textarea → "Find my title" becomes the obvious next action
- Upload a file → its text fills the same textarea, so the user can see and edit what was extracted before submitting
- Tap a sample button → textarea fills with a pre-written example CV, no commitment required

**States:**
- **Default:** empty textarea, button present but the product doesn't need to disable it aggressively — let the user try, then guide them if the input's too thin.
- **Empty / first-time:** identical to default — there's no separate onboarding screen. The one-line promise in the header does the explaining; no tour, no modal.
- **Loading:** none on this screen — matching happens fast enough that the wait belongs on the transition into Result, not here.
- **Error:** input under roughly a sentence or two of real content shows a direct inline warning ("paste a bit more — at least a few sentences from your background, coursework, or experience") and does not advance. If the text is long enough but matches nothing in the system's field library, a second, distinct warning says so plainly and suggests pasting more or trying a sample — this is the harder error, because it's not the user's mistake, it's a coverage gap, and the copy has to own that rather than implying the user did something wrong.
- **Edge / "too much":** a very long CV (multiple pages pasted) should still scan fully — no truncation — since the evidence quality depends on seeing the whole document, not just the top of it.

### Result

**Purpose:** Deliver the single title and make the evidence behind it legible enough to trust.

**Layout (top to bottom):**
1. A small "Your match" pill — signals this is a verdict, not a menu
2. The job title, large, alone — nothing competes with it visually
3. The evidence box — the quoted-keyword sentence, visually distinct (shaded background) from the rest of the page, because it's the section doing the persuading
4. "People who started from a similar pattern" — 2–3 short example sentences
5. Primary action: "Start my 1-week try-it sprint"
6. Secondary, de-emphasized action: "Upload a different CV"

**Key interactions:**
- Tap "Start my try-it sprint" → advance to Sprint for this title
- Tap "Upload a different CV" → return to Upload, fully reset (this is the manual escape hatch, separate from the automatic no-fit cycling described below)

**States:**
- **Default:** title + evidence + examples as above.
- **Empty / first-time:** not applicable — this screen never renders without a successful match.
- **Loading:** the ~500ms hold described in the defining interaction happens on the way *into* this screen, not on it.
- **Error:** not applicable here — match failures are handled back on Upload.
- **Edge / "too much" — second or third pass on the same CV:** when the user arrives here after a "no fit" on a previous title, the pill and copy should signal continuation, not a fresh restart — e.g. "Your next match" instead of "Your match" — so cycling through titles reads as the product narrowing in, not as it guessing repeatedly.

### Sprint

**Purpose:** Turn the title into a week of real, checkable work instead of more reading or talking.

**Layout (top to bottom):**
1. Pill labeling the current title's sprint
2. A short reminder line: "Check off each day as you go. This is the real test — not another conversation about it."
3. A day-by-day list, each row a checkbox plus a single concrete task
4. Primary action: "Finish sprint & see my results"

**Key interactions:**
- Tap a day's checkbox → marks it done, purely a personal tracking aid, doesn't gate anything
- Tap "Finish sprint" → advances to End regardless of how many days are checked — we don't enforce completion, because forcing it would turn an honesty tool into a compliance tool

**States:**
- **Default:** all days unchecked, full task list visible at once (not gated day-by-day) so the user can see the whole shape of the week up front.
- **Empty / first-time:** identical to default — there's no separate "day 1 only" reveal. Seeing the whole week is part of the proof; a sprint that hides its own shape would feel like a trick.
- **Loading:** none — this is a static checklist with no async behavior.
- **Error:** none — there's nothing to submit or validate on this screen.
- **Edge — returning mid-sprint after closing the tab:** this is the hardest state in the product and v1 does not solve it well. Without any persistence, a closed tab loses all checked days. The UX accepts this honestly for v1 rather than pretending otherwise — see Section 8.

### End

**Purpose:** Close the loop with something useful regardless of the verdict, and capture an honest fit / no-fit signal.

**Layout (top to bottom):**
1. Pill + title recap ("Your checklist: [title]")
2. Skills to build — a row of compact tags
3. Realistic timeline — a few phase blocks (0–3 months, 3–6 months, 6–12 months), each with a short description
4. The verdict prompt: "Did this feel like real work you'd want to keep doing?" with two buttons — "Yes, this fits" and "No, try my next-best title"
5. A closing message that replaces the verdict prompt once answered

**Key interactions:**
- Tap "Yes, this fits" → verdict prompt hides, a closing affirmation message appears, no further action required except an option to start over with a different CV
- Tap "No, try my next-best title" → if another matched title exists for this CV, jump straight back to Result for that title (skipping re-upload entirely); if none remain, show a closing message that frames this as ruling something out, not failing

**States:**
- **Default:** checklist + timeline + active verdict prompt.
- **Empty / first-time:** not applicable — this screen always has content once reached.
- **Loading:** none.
- **Error:** none — there's no input to fail here.
- **Edge / "ran out of titles":** the closing copy has to do real emotional work here — "you now know what this isn't, with proof, not a guess" — because this is the path where the product has, in a sense, failed to find a fit, and the copy is the only thing standing between that and the user feeling like they wasted a week.

## 5. The user journey

A user lands on Upload already holding a CV they've used for three other applications. They paste it in, glance at the sample buttons but don't need them, and tap "Find my title." There's a half-second hold — just long enough to feel like the product looked — and then one title appears, with a sentence quoting two phrases straight out of what they pasted. It feels less like a recommendation and more like being read closely. They skim the two example paths, recognize a bit of themselves in one, and start the sprint.

Over the next week, they check off a task most days — a report read here, a message sent there — treating it less like an app and more like a to-do list that happens to live in a browser tab. At the end, they see a handful of skills they're missing and a three-phase timeline, then answer the one honest question the whole product was built around. If it's a "no," the next title appears immediately, no re-explaining, no new upload — just the next test. If it's a "yes," the closing message tells them, plainly, that this is what proof looks like: they didn't guess, and they didn't need a stranger to tell them.

A second visit, days or weeks later, starts the same way it did the first time — there's no account, no history, no saved state to pick back up. If they're returning to finish an interrupted sprint, they're starting that sprint over from day one, because nothing was saved. If they're returning with a different CV, the experience is identical to a first-time visit, which is intentional: every CV gets the same fresh, careful read.

## 6. Component & visual notes

- **Typography:** plain system sans-serif, generous line height. Nothing here is decorative — the type's job is to disappear so the evidence sentence is the thing that stands out.
- **Color:** a warm, neutral background with one accent color reserved for the primary action and the pill labels, so "this is the next step" is always visually obvious. Color should not be load-bearing for meaning anywhere else (fit/no-fit, day-complete) — those need text or icons too, not color alone.
- **Motion:** minimal. The one motion moment worth designing deliberately is the ~400–600ms hold between "Find my title" and the result appearing — everything else (tab switches, checklist taps) should be instant, no easing, no bounce. This product's personality is steadiness, not playfulness.
- **The signature visual:** the evidence box on the Result screen — visually set apart (shaded panel) from the rest of the page, because it's quoting the user's own words back at them and needs to read as distinct from generated copy.
- **Microcopy voice:** direct, second-person, slightly blunt — closer to a friend leveling with you than a platform congratulating you. "That's a pattern, not a coincidence." "You now know what this isn't — with proof, not a guess." Never "Congratulations!" or "Great job!" — the product's credibility depends on sounding like it's not trying to make anyone feel good, just trying to be useful.

## 7. Accessibility & inclusion

- **Screen readers:** every interactive element (checkboxes, tab-like pills, buttons) needs a real label tied to its control, not just visual styling — the day checklist in particular needs each checkbox programmatically associated with its task text, not just visually adjacent to it.
- **Motor difficulties:** all actions are single taps on generously sized buttons and checkboxes; nothing in this product requires drag, precise gestures, or timed input. The file upload's drag-and-drop is a convenience, not a requirement — the click-to-browse path must always work as the primary path.
- **Low-bandwidth / spotty connectivity:** this is a strength by construction, not an add-on — v1 has no network calls of any kind after the page loads, so connectivity quality is irrelevant once the page is open. This matters concretely for this user base, several of whom described unstable circumstances (visa transitions, displacement).
- **Burmese-language users:** v1 is English-only. This is a deliberate deferral, not an oversight — the coach explicitly named the lack of Burmese-language tooling as a real gap, but the core bet here (does proving-by-doing produce clarity faster than talking) needs to be validated before investing in translation. Revisit after the pilot if English comprehension turns out to be a filter on who can use this at all.

## 8. What we are NOT designing

- **No accounts, login, or saved history screens** — there is nothing to save across sessions in v1; a returning user starts fresh every time, by design
- **No onboarding flow or product tour beyond the header's one-line promise** — if the Upload screen needs more explaining than that, the screen itself isn't clear enough
- **No progress-persistence UI (save/resume) for the sprint** — acknowledged as a real gap (see Open design questions), not solved by design trickery; either it gets a real persistence mechanism from engineering or it stays an honest limitation
- **No settings or customization screens** — there is nothing in this product a user needs to configure
- **No "browse all fields" catalog view** — every path into this product starts from an uploaded CV, never from browsing a list of available titles

## 9. Open design questions

- [ ] Does the "no fit, next title" transition need an explicit counter ("2 of 3 possible matches") so cycling reads as visible progress instead of an open-ended loop?
- [ ] Is a silent, no-persistence sprint acceptable for a real pilot, or does losing checklist progress on tab close undermine trust enough that it needs solving before wider use?
- [ ] Should the sample CVs stay visible permanently, or fade out as a "first-time only" affordance once a user has submitted real input at least once?
- [ ] Does the evidence box need a confidence floor — a different, softer framing when very few keywords matched — so a thin match doesn't get the same confident tone as a strong one?

## 10. Handoff to engineering

The evidence sentence depends entirely on the scorer returning not just a winning category but the specific matched terms and their counts, in ranked order, for every category, not only the top one — engineering needs to expose that full ranked structure so "no fit" can cycle through it without ever asking the user to resubmit anything. Second, and more urgent: the sprint checklist currently has no persistence layer at all, and a 1-week task spread across multiple browser sessions losing its state on tab close is the single biggest gap between this prototype and something a real pilot user could rely on — this needs a decision (even a lightweight one) before the next round of testing.
