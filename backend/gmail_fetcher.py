import imaplib
import email

from backend.config import get_gmail_credentials

EMAIL, PASSWORD = get_gmail_credentials()
if not EMAIL or not PASSWORD:
    raise RuntimeError(
        "Missing Gmail credentials. Set PHISHGUARD_GMAIL_EMAIL and PHISHGUARD_GMAIL_APP_PASSWORD in .env"
    )

mail = imaplib.IMAP4_SSL("imap.gmail.com")

mail.login(EMAIL, PASSWORD)

mail.select("inbox")

status, messages = mail.search(None, "ALL")

email_ids = messages[0].split()

if len(email_ids) == 0:

    print("No emails found.")

else:

    latest_email_id = email_ids[-1]

    status, msg_data = mail.fetch(
        latest_email_id,
        "(RFC822)"
    )

    raw_email = msg_data[0][1]

    msg = email.message_from_bytes(raw_email)

    subject = msg["subject"]

    sender = msg["from"]

    print("\nLATEST EMAIL\n")

    print("Sender:", sender)

    print("Subject:", subject)