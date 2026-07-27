def normalize_phone(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    return digits[-10:]
