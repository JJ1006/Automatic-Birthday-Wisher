import os
import datetime
import smtplib
import pandas as pd

# Use env vars provided by GitHub Actions secrets (or your local shell)
GMAIL_ID = os.environ["GMAIL_ID"]
GMAIL_PSWD = os.environ["GMAIL_APP_PASSWORD"]  # Gmail App Password (2FA required)

def sendEmail(to, sub, msg):
    print(f"Email to {to} sent with subject: {sub}")
    s = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
    s.starttls()
    s.login(GMAIL_ID, GMAIL_PSWD)
    s.sendmail(GMAIL_ID, to, f"Subject: {sub}\n\n{msg}")
    s.quit()

if __name__ == "__main__":
    # Expect data.xlsx in the repo root (no chdir needed on Actions)
    df = pd.read_excel("data.xlsx")

    today = datetime.datetime.now().strftime("%d-%m")
    yearNow = datetime.datetime.now().strftime("%Y")

    writeInd = []
    for index, item in df.iterrows():
        bday = item['Birthday'].strftime("%d-%m")
        if (today == bday) and (yearNow not in str(item['Year'])):
            sendEmail(item['Email'], "Happy Birthday", item['Dialogue'])
            writeInd.append(index)

    # Update the Year column for rows we just processed
    for i in writeInd:
        yr = str(df.loc[i, 'Year']).strip()
        df.loc[i, 'Year'] = (yr + ', ' if yr and yr.lower() != 'nan' else '') + yearNow

    # Save back to the same file
    df.to_excel('data.xlsx', index=False)
    print(f"Updated rows: {writeInd}")
