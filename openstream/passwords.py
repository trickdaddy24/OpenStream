"""Password complexity validation and strength checking."""

import re
import string
from dataclasses import dataclass, field


@dataclass
class PasswordPolicy:
    """Configurable password complexity requirements."""

    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_characters: str = string.punctuation  # !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~
    min_unique_chars: int = 4
    disallowed_passwords: list[str] = field(default_factory=lambda: [
        "admin", "password", "123456", "12345678", "qwerty", "letmein",
        "welcome", "monkey", "master", "dragon", "login", "abc123",
        "passw0rd", "shadow", "openstream",
    ])


# Default policy — used everywhere unless overridden
default_policy = PasswordPolicy()


@dataclass
class ValidationResult:
    """Result of password validation with per-rule feedback."""

    valid: bool
    errors: list[str]
    score: int  # 0-100 strength score
    strength: str  # "weak" | "fair" | "good" | "strong"


def validate_password(
    password: str,
    *,
    username: str | None = None,
    policy: PasswordPolicy | None = None,
) -> ValidationResult:
    """Validate a password against the complexity policy.

    Returns a ValidationResult with per-rule error messages and a strength score.
    """
    pol = policy or default_policy
    errors: list[str] = []

    # ---------- Length ----------
    if len(password) < pol.min_length:
        errors.append(f"Must be at least {pol.min_length} characters")
    if len(password) > pol.max_length:
        errors.append(f"Must be at most {pol.max_length} characters")

    # ---------- Character classes ----------
    if pol.require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Must contain at least one uppercase letter (A-Z)")

    if pol.require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Must contain at least one lowercase letter (a-z)")

    if pol.require_digit and not re.search(r"\d", password):
        errors.append("Must contain at least one digit (0-9)")

    if pol.require_special:
        escaped = re.escape(pol.special_characters)
        if not re.search(f"[{escaped}]", password):
            errors.append("Must contain at least one special character (!@#$%^&* etc.)")

    # ---------- Unique characters ----------
    if len(set(password)) < pol.min_unique_chars:
        errors.append(f"Must contain at least {pol.min_unique_chars} unique characters")

    # ---------- Disallowed / obvious passwords ----------
    if password.lower() in [p.lower() for p in pol.disallowed_passwords]:
        errors.append("This password is too common — choose something more unique")

    # ---------- Username in password ----------
    if username and len(username) >= 3 and username.lower() in password.lower():
        errors.append("Password must not contain your username")

    # ---------- Strength score ----------
    score = _calculate_strength(password, pol)
    strength = _score_to_label(score)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        score=score,
        strength=strength,
    )


def get_policy_rules(policy: PasswordPolicy | None = None) -> list[dict]:
    """Return a human-readable list of the policy rules (for UI display)."""
    pol = policy or default_policy
    rules = [
        {"rule": f"At least {pol.min_length} characters", "key": "min_length"},
    ]
    if pol.require_uppercase:
        rules.append({"rule": "At least one uppercase letter (A-Z)", "key": "uppercase"})
    if pol.require_lowercase:
        rules.append({"rule": "At least one lowercase letter (a-z)", "key": "lowercase"})
    if pol.require_digit:
        rules.append({"rule": "At least one digit (0-9)", "key": "digit"})
    if pol.require_special:
        rules.append({"rule": "At least one special character (!@#$%^&*)", "key": "special"})
    if pol.min_unique_chars > 1:
        rules.append({"rule": f"At least {pol.min_unique_chars} unique characters", "key": "unique"})
    return rules


def _calculate_strength(password: str, policy: PasswordPolicy) -> int:
    """Calculate a 0-100 strength score based on entropy-like heuristics."""
    if not password:
        return 0

    score = 0

    # Length contribution (up to 30 points)
    score += min(30, len(password) * 2)

    # Character variety (up to 40 points — 10 per class)
    if re.search(r"[a-z]", password):
        score += 10
    if re.search(r"[A-Z]", password):
        score += 10
    if re.search(r"\d", password):
        score += 10
    if re.search(f"[{re.escape(policy.special_characters)}]", password):
        score += 10

    # Unique character ratio (up to 20 points)
    unique_ratio = len(set(password)) / max(len(password), 1)
    score += int(unique_ratio * 20)

    # Penalty for common patterns
    lower = password.lower()
    if re.search(r"(.)\1{2,}", lower):  # repeated chars (aaa, 111)
        score -= 10
    if re.search(r"(012|123|234|345|456|567|678|789|890)", lower):
        score -= 5
    if re.search(r"(abc|bcd|cde|def|efg|fgh|ghi|hij|qwe|wer|ert)", lower):
        score -= 5

    return max(0, min(100, score))


def _score_to_label(score: int) -> str:
    """Convert numeric strength score to human-readable label."""
    if score < 30:
        return "weak"
    if score < 55:
        return "fair"
    if score < 80:
        return "good"
    return "strong"
