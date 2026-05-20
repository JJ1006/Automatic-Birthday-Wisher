# Automatic Birthday Wisher

Sends personalized HTML birthday emails automatically via Gmail + GitHub Actions. Runs daily, checks `data.yaml` for birthdays matching today's date, sends an email, and records the year to avoid duplicate sends.

## Stack

| Concern | Tool |
|---|---|
| Email transport | Gmail SMTP — Python stdlib `smtplib` + `email.message.EmailMessage` |
| Data storage | `data.yaml` (PyYAML) |
| Package management | [uv](https://github.com/astral-sh/uv) (CI) |
| Scheduling | GitHub Actions cron |

## data.yaml format

```yaml
- name: Tejasvi
  email: you@example.com
  birthday: "07-19"        # MM-DD
  message: Happy Birthday, Tejasvi!
  years_sent:
  - 2024
  - 2025
```

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Recipient's display name |
| `email` | Yes | Recipient's email address |
| `birthday` | Yes | `MM-DD` — day and month only |
| `message` | Yes | Personal message body for the email |
| `years_sent` | Yes | List of years already sent; use `[]` for new entries |

## GitHub Actions setup

1. Go to **Settings → Secrets and variables → Actions** in your repo.
2. Add two repository secrets:
   - `GMAIL_ID` — your Gmail address (e.g. `you@gmail.com`)
   - `GMAIL_APP_PASSWORD` — a [Gmail App Password](https://myaccount.google.com/apppasswords) (requires 2-Step Verification enabled)
3. Push to `main` — the workflow runs daily at 13:00 UTC, or trigger it manually via **Actions → Daily Birthday Wisher → Run workflow**.

## Local setup

```bash
# Install uv  (https://docs.astral.sh/uv/getting-started/installation/)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install dependencies
uv venv
uv pip install -r requirements.txt

# Set env vars
export GMAIL_ID="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"

# Run
uv run python main.py
```

On Windows:

```bat
set GMAIL_ID=you@gmail.com
set GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
python main.py
```

## How it works

1. Reads `data.yaml`.
2. Compares each `birthday` (MM-DD) to today's UTC date.
3. Skips entries where the current year is already in `years_sent`.
4. Sends an HTML email with a plain-text fallback via Gmail SMTP.
5. Appends the current year to `years_sent` and commits `data.yaml` back to the repo.
