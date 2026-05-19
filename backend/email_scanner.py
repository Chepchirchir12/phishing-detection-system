import os
import shutil

from backend.predictor import predict_email

incoming_folder = "emails/incoming"
inbox_folder = "emails/inbox"
spam_folder = "emails/spam"


def scan_incoming_folder() -> int:
    moved = 0
    if not os.path.isdir(incoming_folder):
        return 0

    for name in os.listdir(incoming_folder):
        file_path = os.path.join(incoming_folder, name)
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            email_content = f.read()

        result = predict_email(subject=None, body=email_content, sender=None)
        target = spam_folder if result["label"] == "Phishing" else inbox_folder
        os.makedirs(target, exist_ok=True)
        shutil.move(file_path, os.path.join(target, name))
        moved += 1

    return moved


if __name__ == "__main__":
    count = scan_incoming_folder()
    print(f"Scanned incoming folder, moved {count} emails.")