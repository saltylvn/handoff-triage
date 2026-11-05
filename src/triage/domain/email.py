import re

_FREE_MAIL = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "outlook.com",
        "hotmail.com",
        "icloud.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
    }
)
_LABEL = r"(?!-)[a-z0-9-]{1,63}(?<!-)"
_SAFE_DOMAIN = re.compile(rf"^{_LABEL}(\.{_LABEL})+$")


def email_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower()


def is_free_mail(domain: str) -> bool:
    return domain in _FREE_MAIL


def is_lookup_safe_domain(domain: str) -> bool:
    """Only plain domain names may reach a lookup URL: blocks path tricks like x/../admin."""
    return len(domain) <= 253 and _SAFE_DOMAIN.fullmatch(domain) is not None
