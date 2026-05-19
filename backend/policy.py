import re
from urllib.parse import urlparse

from backend.config import get_env


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [p.strip().strip('"\'').lower() for p in value.split(",")]
    return [p for p in parts if p]

def extract_email_address(sender: str | None) -> str | None:
    if not sender:
        return None
    m = re.search(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", sender, re.IGNORECASE)
    return m.group(1).lower() if m else None

def is_trusted_sender(sender: str | None) -> bool:
    addr = extract_email_address(sender)
    if not addr:
        return False

    trusted_senders = set(_split_csv(get_env("PHISHGUARD_TRUSTED_SENDERS")))
    trusted_domains = set(_split_csv(get_env("PHISHGUARD_TRUSTED_SENDER_DOMAINS")))

    if addr in trusted_senders:
        return True

    domain = addr.split("@", 1)[-1]
    return domain in trusted_domains

def extract_link_domains(text: str | None) -> set[str]:
    if not text:
        return set()
    domains: set[str] = set()
    for m in re.finditer(r"https?://[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}[^\s<>()]*", text, re.IGNORECASE):
        try:
            url = m.group(0)
            url = re.sub(r"[.,!?;:...]+$", "", url)
            u = urlparse(url)
            host = (u.hostname or "").lower()
            if host:
                domains.add(host)
        except Exception:
            continue
    return domains

def are_links_trusted(text: str | None, sender: str | None = None) -> bool:
    link_domains = extract_link_domains(text)
    if not link_domains:
        return True

    trusted = set(_split_csv(get_env("PHISHGUARD_TRUSTED_LINK_DOMAINS")))
    sender_addr = extract_email_address(sender)
    
    if sender_addr:
        sender_domain = sender_addr.split("@", 1)[-1]
        sender_parts = sender_domain.split(".")
        parent_domain = ".".join(sender_parts[-2:]) if len(sender_parts) >= 2 else sender_domain

        remaining_links = set()
        for link_domain in link_domains:
            if (link_domain == sender_domain or 
                link_domain.endswith(f".{sender_domain}") or 
                link_domain == parent_domain or 
                link_domain.endswith(f".{parent_domain}")):
                continue
            remaining_links.add(link_domain)
        
        if not remaining_links:
            return True
        link_domains = remaining_links

    # If no trusted list is configured, return True (neutral/safe default)
    # instead of False, to avoid penalizing emails unnecessarily.
    if not trusted:
        return True
        
    return link_domains.issubset(trusted)

