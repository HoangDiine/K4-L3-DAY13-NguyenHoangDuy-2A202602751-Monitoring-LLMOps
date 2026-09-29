from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
        "+84901234567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    cccds = (
        "001099012345",
        "079201001234",
    )
    for cccd in cccds:
        out = scrub_text(f"CCCD is {cccd}")
        assert cccd not in out
        assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    cards = (
        "4111 2222 3333 4444",
        "4111-2222-3333-4444",
        "4111222233334444",
    )
    for card in cards:
        out = scrub_text(f"Payment card: {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_mixed_pii() -> None:
    text = "Student student@vinuni.edu.vn with phone 0901234567, CCCD 001099012345, card 4111 1111 1111 1111"
    out = scrub_text(text)
    assert "student@vinuni.edu.vn" not in out
    assert "0901234567" not in out
    assert "001099012345" not in out
    assert "4111 1111 1111 1111" not in out
    assert "REDACTED_EMAIL" in out
    assert "REDACTED_PHONE_VN" in out
    assert "REDACTED_CCCD" in out
    assert "REDACTED_CREDIT_CARD" in out


def test_scrub_passport() -> None:
    passports = ("B1234567", "C87654321")
    for passport in passports:
        out = scrub_text(f"My passport is {passport}")
        assert passport not in out
        assert "REDACTED_PASSPORT" in out

