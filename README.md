# ProofPath

Upload your CV. Get one title. Prove it in a week — before you commit a year.

A career-discovery tool for Myanmar students and graduates. Built as an educational project.

## What it does
1. You paste or upload your CV text
2. The app matches it against 991 real job titles (TF-IDF, no AI/API needed)
3. You get one concrete job title with evidence from your own words
4. You work through a 7-day hands-on sprint for that title
5. You self-report: fit or no-fit

## Tech stack
- **Backend:** Python 3.11+, FastAPI, Pydantic, NumPy — managed with `uv`
- **Frontend:** Vanilla HTML/CSS/JS, no build step, served by FastAPI

## How to run locally

### 1. Install dependencies
```bash
uv sync