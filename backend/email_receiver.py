import imaplib
import email
from email.utils import parsedate_to_datetime
from datetime import datetime
from typing import Optional

from backend.database import SessionLocal
from backend.database import Email
from backend.config import get_gmail_credentials
from backend.predictor import predict_email

class EmailFetcher:
    def __init__(self, email_address: str, password: str, imap_server: str = "imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.mail: Optional[imaplib.IMAP4_SSL] = None

    def connect(self):
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            self.mail.select("INBOX")  # Try uppercase INBOX
        except Exception as e:
            # Fallback for some servers
            try:
                self.mail.select("inbox")
            except:
                raise e

    def fetch_and_scan(self, limit: int = 500):
        if not self.mail:
            self.connect()
        
        print(f"Searching for emails in {self.email_address}...")
        
        status, messages = self.mail.search(None, "ALL")
        if status != "OK":
            print(f"Search failed for {self.email_address}")
            return
            
        email_ids = messages[0].split()
        total_inbox = len(email_ids)
        scan_count = min(total_inbox, limit)
        print(f"Found {total_inbox} total emails. Scanning latest {scan_count}...")
        
        latest_ids = email_ids[-scan_count:]

        db = SessionLocal()
        
        # 1. Faster Deduplication: Fetch only headers for all candidates first
        print(f"Checking for new messages (Fast Scan)...")
        new_candidates = []
        
        # We can fetch Message-ID for multiple IDs at once
        id_to_msgid = {}
        if latest_ids:
            ids_str = ",".join([id.decode() if isinstance(id, bytes) else str(id) for id in latest_ids])
            status, data = self.mail.fetch(ids_str, "(BODY[HEADER.FIELDS (MESSAGE-ID)])")
            
            if status == "OK":
                for i in range(0, len(data), 2):
                    try:
                        raw_header = data[i][1]
                        msg = email.message_from_bytes(raw_header)
                        msg_id = msg.get("message-id")
                        numeric_id = data[i][0].split()[0]
                        if msg_id:
                            id_to_msgid[numeric_id] = msg_id.strip()
                    except:
                        continue

            # Check DB for existing message IDs
            existing_msg_ids = set()
            if id_to_msgid:
                found = db.query(Email.message_id).filter(Email.message_id.in_(list(id_to_msgid.values()))).all()
                existing_msg_ids = {f[0] for f in found}

            for numeric_id, msg_id in id_to_msgid.items():
                if msg_id not in existing_msg_ids:
                    new_candidates.append(numeric_id)

        print(f"Found {len(new_candidates)} genuinely new emails to process.")

        # 1.1 Deletion Sync: Find local emails that no longer exist in the Gmail latest set
        if latest_ids:
            latest_msg_ids_in_gmail = set(id_to_msgid.values())
            local_emails = db.query(Email).filter(Email.receiver == self.email_address.strip().lower()).all()
            
            to_delete = []
            for le in local_emails:
                if le.message_id and le.message_id not in latest_msg_ids_in_gmail:
                    to_delete.append(le)
            
            if to_delete:
                print(f"Syncing deletions: Removing {len(to_delete)} emails no longer in Gmail.")
                for le in to_delete:
                    db.delete(le)
                db.commit()

        if not new_candidates:
            return

        # 2. Bulk Process New Emails in chunks
        CHUNK_SIZE = 50 # Increased chunk size for faster processing
        count = 0
        try:
            for i in range(0, len(new_candidates), CHUNK_SIZE):
                chunk = new_candidates[i : i + CHUNK_SIZE]
                ids_str = ",".join([id.decode() if isinstance(id, bytes) else str(id) for id in chunk])
                
                status, data = self.mail.fetch(ids_str, "(RFC822)")
                if status != "OK":
                    continue
                
                for j in range(0, len(data), 2):
                    try:
                        raw_email = data[j][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        sender = msg["from"]
                        subject = msg["subject"]
                        message_id = msg.get("message-id")
                        
                        # Extract and parse date
                        date_str = msg.get("date")
                        email_timestamp = datetime.utcnow()
                        if date_str:
                            try:
                                email_timestamp = parsedate_to_datetime(date_str)
                                if email_timestamp.tzinfo:
                                    email_timestamp = email_timestamp.astimezone(None).replace(tzinfo=None)
                            except:
                                pass

                        body = self._extract_body(msg)
                        numeric_id = data[j][0].split()[0]

                        # Prediction
                        prediction_result = predict_email(subject, body, sender=sender)
                        
                        new_email = Email(
                            sender=sender,
                            receiver=self.email_address.strip().lower(),
                            subject=subject,
                            body=body,
                            prediction=prediction_result["label"],
                            risk_score=prediction_result["risk_score"],
                            folder=prediction_result["folder"],
                            message_id=message_id,
                            timestamp=email_timestamp,
                            imap_uid=numeric_id.decode() if isinstance(numeric_id, bytes) else str(numeric_id)
                        )
                        db.add(new_email)
                        count += 1
                    except Exception as e:
                        print(f"Error processing email {j}: {e}")
                        continue
                
                db.commit()
                print(f"Progress: {count}/{len(new_candidates)} saved...")

            print(f"Successfully processed and saved {count} new emails for {self.email_address}")
        except Exception as e:
            print(f"Error in fetch loop for {self.email_address}: {e}")
            db.rollback()
        finally:
            db.close()

    def _process_email(self, email_id, db) -> bool:
        # This method is now legacy as fetch_and_scan handles bulk processing
        return False

    def _extract_body(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")
                    break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors="ignore")
        return body

    def close(self):
        if self.mail:
            try:
                self.mail.logout()
            except:
                pass

def run_default_fetcher():
    """Main entry point for the original script behavior."""
    EMAIL, PASSWORD = get_gmail_credentials()
    if not EMAIL or not PASSWORD:
        print("Missing Gmail credentials. Set PHISHGUARD_GMAIL_EMAIL and PHISHGUARD_GMAIL_APP_PASSWORD in .env")
        return

    fetcher = EmailFetcher(EMAIL, PASSWORD)
    try:
        fetcher.fetch_and_scan()
        print("Emails scanned and imported successfully.")
    finally:
        fetcher.close()

if __name__ == "__main__":
    run_default_fetcher()
