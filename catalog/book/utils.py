import re

from ..common.models import IdType


def check_digit_10(isbn):
    assert len(isbn) == 9
    sum = 0
    for i in range(len(isbn)):
        c = int(isbn[i])
        w = i + 1
        sum += w * c
    r = sum % 11
    return "X" if r == 10 else str(r)


def check_digit_13(isbn):
    assert len(isbn) == 12
    sum = 0
    for i in range(len(isbn)):
        c = int(isbn[i])
        w = 3 if i % 2 else 1
        sum += w * c
    r = 10 - (sum % 10)
    return "0" if r == 10 else str(r)


def isbn_10_to_13(isbn):
    if not isbn or len(isbn) != 10:
        return None
    return "978" + isbn[:-1] + check_digit_13("978" + isbn[:-1])


def isbn_13_to_10(isbn):
    if not isbn or len(isbn) != 13 or isbn[:3] != "978":
        return None
    else:
        return isbn[3:12] + check_digit_10(isbn[3:12])


def is_isbn_13(isbn):
    return re.match(r"^\d{13}$", isbn) is not None


def is_isbn_10(isbn):
    return re.match(r"^\d{9}[X0-9]$", isbn) is not None


def is_asin(asin):
    return re.match(r"^B[A-Z0-9]{9}$", asin) is not None


def detect_isbn_asin(s: str) -> tuple[IdType, str] | tuple[None, None]:
    if not s:
        return None, None
    n = re.sub(r"[^0-9A-Z]", "", s.upper())
    if is_isbn_13(n) and check_digit_13(n[:-1]) == n[-1]:
        return IdType.ISBN, n
    if is_isbn_10(n) and check_digit_10(n[:-1]) == n[-1]:
        v = isbn_10_to_13(n)
        return (IdType.ISBN, v) if v else (None, None)
    if is_asin(n):
        return IdType.ASIN, n
    return None, None


def binding_to_format(binding: str | None):
    from .models import Edition

    if not binding:
        return None
    if re.search(r"(Audio|Audible|音频)", binding, flags=re.IGNORECASE):
        return Edition.BookFormat.AUDIOBOOK
    if re.search(
        r"(pub|ebook|e-book|kindle|electronic|电子)", binding, flags=re.IGNORECASE
    ):
        return Edition.BookFormat.HARDCOVER
    if re.search(r"(web|网)", binding, flags=re.IGNORECASE):
        return Edition.BookFormat.WEB
    if re.search(r"(精|Hard)", binding, flags=re.IGNORECASE):
        return Edition.BookFormat.HARDCOVER
    if re.search(r"(平|Paper|Soft)", binding, flags=re.IGNORECASE):
        return Edition.BookFormat.PAPERBACK
    return None
