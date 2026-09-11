"""Unit tests for PII and secret redaction."""

from voxlocal.security.redactor import redact_text


def test_redact_api_keys():
    text = "Use key sk-abcdef1234567890abcdef1234567890 to access the OpenAI endpoint."
    sanitized = redact_text(text)
    assert "sk-" not in sanitized
    assert "[REDACTED_OPENAI_KEY]" in sanitized


def test_redact_github_and_aws_keys():
    text = "Deploy using AKIAIOSFODNN7EXAMPLE and token ghp_1234567890abcdefghijklmnopqrstuvwxyz1234."
    sanitized = redact_text(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
    assert "[REDACTED_AWS_KEY]" in sanitized
    assert "[REDACTED_GITHUB_TOKEN]" in sanitized


def test_redact_pii_emails_and_ips():
    text = "Contact alex@example.com at server 192.168.1.100 for SSH access."
    sanitized = redact_text(text)
    assert "alex@example.com" not in sanitized
    assert "192.168.1.100" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized
    assert "[REDACTED_IPV4_ADDRESS]" in sanitized


def test_redact_passwords():
    text = "The database password is SuperSecretPass123! so make sure you note it."
    sanitized = redact_text(text)
    assert "SuperSecretPass123!" not in sanitized
    assert "[REDACTED_PASSWORD]" in sanitized
