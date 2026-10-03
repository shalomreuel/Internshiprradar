# Zero-cost AI Internship Radar v3

India + remote worldwide. Focus: AI/ML, GenAI, computer vision, NLP, robotics and applied research.

## Why v3
The earlier workflow completed successfully but returned zero because the source set was small and the matching rules were too strict. v3:
- Adds Remotive's public remote-jobs API.
- Keeps Remote OK and Arbeitnow.
- Supports Greenhouse, Lever and Ashby board slugs.
- Looks for internship/student/research signals across the whole posting, not only the title.
- Writes `data/discovery_debug.json` so you can see what each source did.
- Writes public GitHub referral signals.

## Setup
1. Replace the files in your repository with the contents of this folder.
2. Open **Actions → Daily internship discovery → Run workflow**.
3. Wait for the green check.
4. Open `data/daily_digest.md` and `data/discovery_debug.json`.
5. Scheduled runs happen daily at 08:00 IST.

## Company boards
Add Greenhouse board tokens, Lever site slugs, or Ashby board names to `config.json`.

## Safety
This is discovery, not auto-application. Verify each role on the employer's official page. Never put passwords, OTPs, PAN or banking details in this repository.
