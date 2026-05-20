import os
import logging
import datetime
from email.message import EmailMessage
import smtplib
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

GMAIL_ID = os.environ["GMAIL_ID"]
GMAIL_PSWD = os.environ["GMAIL_APP_PASSWORD"]
DATA_FILE = "data.yaml"

# Interactive flags set by workflow_dispatch inputs (or local env vars)
DRY_RUN      = os.environ.get("DRY_RUN", "false").lower() == "true"
OVERRIDE_DATE = os.environ.get("OVERRIDE_DATE", "").strip()   # MM-DD, e.g. "07-19"
FORCE_RESEND  = os.environ.get("FORCE_RESEND", "false").lower() == "true"

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Georgia,'Times New Roman',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,0.08);max-width:600px;">
        <tr>
          <td style="background:linear-gradient(135deg,#667eea,#764ba2);
                     padding:48px 40px;text-align:center;">
            <div style="font-size:64px;margin-bottom:12px;">&#x1F382;</div>
            <h1 style="color:#fff;font-size:34px;margin:0;font-weight:700;
                       letter-spacing:-0.5px;">Happy Birthday, {name}!</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:40px;">
            <p style="font-size:16px;color:#444;line-height:1.8;margin:0 0 24px;">{message}</p>
            <div style="background:#f8f7ff;border-left:4px solid #764ba2;
                        padding:16px 20px;border-radius:0 8px 8px 0;margin:0 0 16px;">
              <p style="margin:0;font-size:14px;color:#5a4a8a;font-style:italic;">
                "May this special day bring you joy, laughter, and all the happiness
                your heart can hold!"
              </p>
            </div>
          </td>
        </tr>
        <tr>
          <td style="background:#f8f7ff;padding:20px 40px;text-align:center;
                     border-top:1px solid #eee;">
            <p style="margin:0;font-size:12px;color:#999;">
              Sent with love by your Birthday Wisher
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def send_email(to: str, name: str, message: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"Happy Birthday, {name}! \U0001f382"
    msg["From"] = GMAIL_ID
    msg["To"] = to
    msg.set_content(
        f"Happy Birthday, {name}!\n\n{message}\n\nSent with love by your Birthday Wisher"
    )
    msg.add_alternative(_HTML.format(name=name, message=message), subtype="html")

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(GMAIL_ID, GMAIL_PSWD)
        smtp.send_message(msg)


def write_summary(lines: list[str]) -> None:
    """Write markdown to the GitHub Actions job summary if available."""
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    with open(DATA_FILE, encoding="utf-8") as f:
        contacts: list[dict] = yaml.safe_load(f)

    now = datetime.datetime.now(datetime.timezone.utc)
    today = OVERRIDE_DATE if OVERRIDE_DATE else now.strftime("%m-%d")
    year_now = int(now.strftime("%Y"))

    mode_label = []
    if DRY_RUN:
        mode_label.append("dry-run")
    if OVERRIDE_DATE:
        mode_label.append(f"date={OVERRIDE_DATE}")
    if FORCE_RESEND:
        mode_label.append("force-resend")

    log.info("Starting — date=%s year=%d mode=[%s]", today, year_now,
             ", ".join(mode_label) if mode_label else "normal")

    sent_rows:    list[dict] = []
    skipped_rows: list[dict] = []
    failed_rows:  list[dict] = []

    for contact in contacts:
        if contact["birthday"] != today:
            continue
        years_sent: list[int] = contact.get("years_sent") or []
        if year_now in years_sent and not FORCE_RESEND:
            log.info("SKIP  %s — already wished in %d", contact["name"], year_now)
            skipped_rows.append(contact)
            continue
        if DRY_RUN:
            log.info("DRY   %s <%s>", contact["name"], contact["email"])
            sent_rows.append(contact)
            continue
        try:
            send_email(
                to=contact["email"],
                name=contact["name"],
                message=contact.get("message", f"Wishing you a wonderful birthday, {contact['name']}!"),
            )
            log.info("SENT  %s <%s>", contact["name"], contact["email"])
            years_sent.append(year_now)
            contact["years_sent"] = sorted(set(years_sent))
            sent_rows.append(contact)
        except Exception:
            log.exception("FAIL  %s <%s>", contact["name"], contact["email"])
            failed_rows.append(contact)

    # Persist updated years_sent (skip if dry-run so data stays clean)
    if not DRY_RUN:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            yaml.dump(contacts, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    log.info("Done. sent=%d skipped=%d failed=%d",
             len(sent_rows), len(skipped_rows), len(failed_rows))

    # ── GitHub Actions job summary ────────────────────────────────────────────
    summary: list[str] = []
    summary.append("## 🎂 Birthday Wisher Summary")
    summary.append("")
    summary.append(f"| | |")
    summary.append(f"|---|---|")
    summary.append(f"| **Date checked** | `{today}` |")
    summary.append(f"| **Mode** | {'🔍 Dry run' if DRY_RUN else '📧 Live'}{' · force-resend' if FORCE_RESEND else ''} |")
    summary.append(f"| **Total contacts** | {len(contacts)} |")
    summary.append("")

    if sent_rows:
        verb = "Would send" if DRY_RUN else "Sent"
        summary.append(f"### ✅ {verb} ({len(sent_rows)})")
        summary.append("| Name | Email |")
        summary.append("|---|---|")
        for c in sent_rows:
            summary.append(f"| {c['name']} | {c['email']} |")
        summary.append("")

    if skipped_rows:
        summary.append(f"### ⏭️ Skipped — already wished this year ({len(skipped_rows)})")
        summary.append("| Name | Email |")
        summary.append("|---|---|")
        for c in skipped_rows:
            summary.append(f"| {c['name']} | {c['email']} |")
        summary.append("")

    if failed_rows:
        summary.append(f"### ❌ Failed ({len(failed_rows)})")
        summary.append("| Name | Email |")
        summary.append("|---|---|")
        for c in failed_rows:
            summary.append(f"| {c['name']} | {c['email']} |")
        summary.append("")

    if not sent_rows and not skipped_rows and not failed_rows:
        summary.append(f"_No birthdays on {today}._")

    write_summary(summary)
