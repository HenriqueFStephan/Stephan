"""Check digits for CNPJ and CPF. The API rejects a registration number that fails them."""


def only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _digit(base: str, factors: list[int]) -> int:
    total = sum(int(digit) * factor for digit, factor in zip(base, factors))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def is_cnpj(value: str) -> bool:
    digits = only_digits(value)
    if len(digits) != 14 or len(set(digits)) == 1:
        return False
    first = _digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = _digit(digits[:12] + str(first), [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digits.endswith(f"{first}{second}")


def is_cpf(value: str) -> bool:
    digits = only_digits(value)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    first = _digit(digits[:9], [10, 9, 8, 7, 6, 5, 4, 3, 2])
    second = _digit(digits[:9] + str(first), [11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
    return digits.endswith(f"{first}{second}")
