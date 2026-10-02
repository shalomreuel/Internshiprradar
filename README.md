# Zero-cost AI Internship Discovery Engine

A personal job-discovery starter kit for **India + remote worldwide** AI/ML, GenAI, computer vision and applied research internships.

## What it does
- Pulls publicly accessible listings from RemoteOK and Arbeitnow.
- Pulls public company career-board listings from Greenhouse, Lever and Ashby when you add board identifiers.
- Filters for internship/student/research roles, AI keywords and India/remote location signals.
- Deduplicates by job URL, assigns a transparent keyword relevance score, and exports CSV + Markdown.
- Runs daily at 08:00 India Standard Time using GitHub Actions (UTC schedule).

## Cost
No paid API key, subscription or LLM is required. GitHub Actions has usage limits; this lightweight public-repository workflow is designed to fit free usage. Keep the repository public if you want to avoid consuming private-repository included minutes, and never commit personal data.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
Results appear in `data/opportunities.csv` and `data/daily_digest.md`.

## Enable company career pages
Edit `config.json`:
- `greenhouse_boards`: Greenhouse board tokens (the token is usually visible in the company's Greenhouse job-board URL).
- `lever_sites`: Lever site names (usually the slug in `jobs.lever.co/<site>`).
- `ashby_boards`: Ashby job-board names (usually the slug in `jobs.ashbyhq.com/<board>`).

Start with companies you genuinely want to work for. A board slug is not necessarily identical to the company name; test it in a browser/API and remove boards that return 404. Public Greenhouse GET endpoints do not require authentication. Lever publishes public postings through its postings API. Ashby exposes a public job-board postings endpoint for participating boards.

## GitHub Actions setup
1. Create a new GitHub repository and upload these files.
2. In **Settings → Actions → General → Workflow permissions**, allow read and write permissions.
3. Open **Actions → Daily internship discovery → Run workflow** for the first scan.
4. Check `data/daily_digest.md` and `data/opportunities.csv`.
5. The scheduled scan runs daily at 08:00 IST. GitHub scheduled jobs can be delayed, so treat this as a daily check, not an exact alarm.

## How to apply
The system discovers listings; it does not auto-apply, fabricate qualifications, or bypass employer application forms. Verify every role on the employer's own site, check eligibility and closing date, then apply manually. Use a separate spreadsheet to track application status, referral contacts and follow-up dates.

## Important limitations
- Keyword matching can miss relevant jobs or include false positives.
- Public job feeds are not complete and may not include every employer.
- Many remote jobs restrict hiring to particular countries/time zones. "Remote" does not mean worldwide.
- Job feeds can contain expired or duplicated postings; verify on the official page.
- This tool does not scrape logged-in LinkedIn/Handshake pages or bypass rate limits.

## Referral intelligence

The workflow now also creates:
- `data/referral_targets.csv`
- `data/referral_targets.md`

It checks configured **public GitHub organizations** and public profiles for technical relevance to AI/ML roles. It does not scrape private LinkedIn data, bypass login walls, or infer hiring authority.

Add companies in `config.json` like:
```json
{"company": "Example AI", "github_org": "example-org"}
```

GitHub Actions supplies `GITHUB_TOKEN` to the workflow. For local runs, you may optionally set an environment variable named `GITHUB_TOKEN`; no paid service is required.
