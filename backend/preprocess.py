import re
import nltk
from nltk.corpus import stopwords

# Ensure stopwords are available
try:
    stop_words = set(stopwords.words("english"))
except Exception:
    nltk.download("stopwords")
    stop_words = set(stopwords.words("english"))

def clean_email(text, strip_urls=True):
    text = str(text).lower()
    if strip_urls:
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"www\.\S+", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    words = [w for w in text.split() if w not in stop_words]
    return " ".join(words).strip()
