"""Digit verbalization for ``textnorm`` (normalization step 7, ``digits_verbalized``).

Public API
----------
``cardinal(n, lang)``          integer -> words (Indian lakh/crore system for Indic,
                                 international thousand/million for ``en``).
``read_digits(digits, lang)``  digit string -> words, one word per digit.
``verbalize_digits(text, lang)`` -> ``(new_text, flags)``: rewrites every ASCII or
                                 native-digit token in ``text``.

Token rules (documented contract, NORMALIZATION_VERSION "1")
------------------------------------------------------------
A numeric token is a maximal run of digits (ASCII 0-9 or any of the nine Indic
digit blocks) in which ``, . : /`` may appear only *between* two digits.

* Plain integer, up to 9 digits -> cardinal. ``0`` -> the word for zero.
* Leading zero (``007``, ``05``) or 10+ digits (phone numbers, ids) -> read
  digit by digit.
* Grouped thousands, Western ``1,234,567`` or Indian ``12,34,567`` -> commas
  dropped, cardinal. Any other comma use (``1,2,3``) is a list: each integer is
  verbalized and the commas are kept.
* Years: exactly 4 digits, no commas.
    - en: 1100-1999 -> "nineteen ninety eight" ("nineteen hundred",
      "nineteen oh five"); 2010-2099 -> "twenty twenty four". Everything else,
      including 2000-2009, is a cardinal ("two thousand five").
    - hi, bn, mr: 1100-1999 -> "<19> sau/sho/she <98>" (उन्नीस सौ अट्ठानवे,
      উনিশশো আটানব্বই, एकोणीसशे अठ्ठ्याण्णव), which is how these numbers are
      read both as years and as quantities.
    - all other languages: plain cardinal.
* Decimal ``3.75`` (exactly one dot): en/hi/bn/ta -> "<int> <point> <digit>
  <digit>" (point / दशमलव / দশমিক / புள்ளி). Other languages: token left
  unchanged, flag ``numeric_unsupported``.
* ``%`` right after a number and ``₹`` right before it: en/hi/bn/ta get the
  word (percent / प्रतिशत / শতাংশ / சதவீதம்; rupees / रुपये / টাকা / ரூபாய்).
  Other languages, and ``$ € £`` in every language: the whole token (symbol
  and digits) is left unchanged, flag ``numeric_unsupported``.
* en only: ordinals ``1st 2nd 3rd 4th 21st`` -> "first second third fourth
  twenty first".
* Times, dates, fractions, versions (``10:30``, ``15/08/2024``,
  ``1.2.3``): left unchanged, flag ``numeric_unsupported``.
* (v4, NORMALIZATION_VERSION "4") Reading conventions, tried ONLY for a token the
  rules above leave unsupported, in ``CONVENTION_LANGS`` (as kn or pa ta); flag
  ``numeric_reading_convention`` (informational). If no convention fits, the
  token stays unchanged and ``numeric_unsupported``.
    - as: date ``dd/mm/yy(yy)`` / ``dd.mm.yyyy`` -> "<day> <month number>
      <year>" (cardinals, leading zeros not read); ``H:30`` before a বজা* word
      -> "চাৰে <H>"; ``H:00`` -> "<H>"; other ``H:MM`` before বজা* -> "<H> বাজি
      <MM> মিনিট" + the case suffix of বজা*; ``H:MM`` with an attached suffix
      (``৬:৪৫-ত``) -> "<H> বাজি <MM> মিনিট"; decimal -> "<int> দশমিক <digits>";
      percent -> "<n> শতাংশ". A colon pair with no বজা* or suffix (a score
      ``১২:১০``) stays unsupported.
    - or: percent -> "<n> ପ୍ରତିଶତ"; decimal -> "<int> ଦଶମିକ <digits>", except
      ``H.MM`` with H <= 12 (decimal or clock time); after ସକାଳ/ସନ୍ଧ୍ୟା/ରାତି/
      ଅପରାହ୍ନ, ``H.30`` -> "ସାଢ଼େ <H>ଟା", ``H.00`` -> "<H>ଟା"; ``ଟ.<n>[.<pp>] [/-]``
      -> "<n> ଟଙ୍କା [<pp> ପଇସା]" (``/-`` dropped).
    - kn: percent -> "ಶೇಕಡ <n>" (word first); ``$<n> [ಮಿಲಿಯನ್|ಬಿಲಿಯನ್]`` ->
      "<n> [scale] ಡಾಲರ್".
    - pa: ``H:30`` / ``H:00`` before ਵਜੇ -> "ਸਾਢੇ <H>" / "<H>"; ``$<n> [ਮਿਲੀਅਨ|
      ਬਿਲੀਅਨ]`` -> "<n> [scale] ਡਾਲਰ".
    - ta: ``dd.mm.yyyy`` / ``dd/mm/yyyy`` -> "<month name> <day>-ஆம் தேதி
      <year>"; ``H:30`` / ``H:00`` before மணி -> "<H>-ரை" (ஆறரை) / "<H>".
  Clock times (iteration 2): hour 0 is never read (unsupported); half past 1 / 2
  use ডেৰ / আঢ়ৈ (as), ਡੇਢ / ਢਾਈ (pa), ଦେଢ଼ଟା / ଅଢ଼େଇଟା (or), ஒன்றரை / இரண்டரை (ta,
  regular); an or ``H:MM`` also needs a time-of-day word; an as ``H.MM`` before
  বজা* is a clock time (never a decimal); an or ``H.MM`` with MM > 59 is a decimal.
  Evidence (same-prompt rows of the other voice, corpus spellings, a duration
  check): .claude/reports/phoneme_frontend/numeric_conventions_v4.md.
* Hyphens/other punctuation are kept as they are (``10-20`` -> दस-बीस).
* Spacing: when a digit token touches a letter, the words are joined to it
  directly if the letter is non-Latin (Indic case suffixes such as ``১৪খন``),
  and separated by a space if it is Latin or ``lang == "en"`` (``480km`` ->
  "... eighty km").

Quality: en, hi, bn, ta are reviewed and tested against hand-checked tables;
as, gu, kn, ml, mr, or, pa, te are best-effort (word tables derived from
AI4Bharat indic_numtowords, see ``_number_tables.py``) and smoke-tested.
All output is NFC, has no ZWJ/ZWNJ, and Assamese output uses ৰ (U+09F0).
"""

from __future__ import annotations

import re
import unicodedata

from . import _number_tables as _t

__all__ = ["cardinal", "read_digits", "verbalize_digits", "DIGIT_CHARS", "MAX_CARDINAL_DIGITS"]

# ASCII + the native decimal digit blocks of our 11 Indic languages.
_DIGIT_BLOCK_ZEROS = (0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66)
DIGIT_CHARS = "0123456789" + "".join(chr(z + i) for z in _DIGIT_BLOCK_ZEROS for i in range(10))
MAX_CARDINAL_DIGITS = 9  # < 100 crore; longer digit strings are read digit by digit

_D = re.escape(DIGIT_CHARS)
_NUM_TOKEN_RE = re.compile(rf"(?P<cur>[₹$€£]\s?)?(?P<body>[{_D}](?:[{_D}]|[,.:/](?=[{_D}]))*)(?P<pct>\s?%)?")
_WESTERN_GROUPS_RE = re.compile(r"\d{1,3}(?:,\d{3})+")
_INDIAN_GROUPS_RE = re.compile(r"\d{1,2}(?:,\d{2})+,\d{3}")
_EN_ORDINAL_RE = re.compile(r"(st|nd|rd|th)(?![A-Za-z])")


def _clean(word: str, lang: str) -> str:
    word = unicodedata.normalize("NFC", word.replace("‌", "").replace("‍", ""))
    return word.replace("র", "ৰ") if lang == "as" else word


# --------------------------------------------------------------------------- English

_EN_ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
_EN_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _en_cardinal(n: int) -> str:
    if n < 20:
        return _EN_ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _EN_TENS[tens] + (f" {_EN_ONES[ones]}" if ones else "")
    words = []
    for value, name in ((10**9, "billion"), (10**6, "million"), (1000, "thousand"), (100, "hundred")):
        if n >= value:
            head, n = divmod(n, value)
            words.append(f"{_en_cardinal(head)} {name}")
    if n:
        words.append(_en_cardinal(n))
    return " ".join(words)


def _en_year(n: int) -> str | None:
    if not (1100 <= n <= 1999 or 2010 <= n <= 2099):
        return None
    high, low = divmod(n, 100)
    if low == 0:
        return f"{_en_cardinal(high)} hundred"
    if low < 10:
        return f"{_en_cardinal(high)} oh {_EN_ONES[low]}"
    return f"{_en_cardinal(high)} {_en_cardinal(low)}"


_EN_ORDINAL_IRREGULAR = {
    "one": "first", "two": "second", "three": "third", "five": "fifth",
    "eight": "eighth", "nine": "ninth", "twelve": "twelfth",
}


def _en_ordinal(n: int) -> str:
    words = _en_cardinal(n).split()
    last = words[-1]
    if last in _EN_ORDINAL_IRREGULAR:
        words[-1] = _EN_ORDINAL_IRREGULAR[last]
    elif last.endswith("y"):
        words[-1] = last[:-1] + "ieth"
    else:
        words[-1] = last + "th"
    return " ".join(words)


# --------------------------------------------------------------------------- Indic units 0-99

def _ta_units() -> tuple[str, ...]:
    base = (
        "பூஜ்ஜியம் ஒன்று இரண்டு மூன்று நான்கு ஐந்து ஆறு ஏழு எட்டு ஒன்பது "
        "பத்து பதினொன்று பன்னிரண்டு பதின்மூன்று பதினான்கு பதினைந்து பதினாறு பதினேழு பதினெட்டு பத்தொன்பது"
    ).split()
    tens = "இருபது முப்பது நாற்பது ஐம்பது அறுபது எழுபது எண்பது தொண்ணூறு".split()
    oblique = "இருபத்து முப்பத்து நாற்பத்து ஐம்பத்து அறுபத்து எழுபத்து எண்பத்து தொண்ணூற்று".split()
    out = list(base)
    for t, o in zip(tens, oblique):
        out.append(t)
        out.extend(f"{o} {base[u]}" for u in range(1, 10))
    return tuple(out)


_ML_VOWEL_SIGN = {"അ": "", "ആ": "ാ", "എ": "െ", "ഏ": "േ", "ഒ": "ൊ"}


def _ml_join(oblique: str, unit: str) -> str:
    """ഇരുപത്തി + ഒന്ന് -> ഇരുപത്തിയൊന്ന്; ഇരുപത്തി + രണ്ട് -> ഇരുപത്തിരണ്ട്."""
    if unit[0] in _ML_VOWEL_SIGN:
        return oblique + "യ" + _ML_VOWEL_SIGN[unit[0]] + unit[1:]
    return oblique + unit


def _ml_units() -> tuple[str, ...]:
    base = (
        "പൂജ്യം ഒന്ന് രണ്ട് മൂന്ന് നാല് അഞ്ച് ആറ് ഏഴ് എട്ട് ഒമ്പത് "
        "പത്ത് പതിനൊന്ന് പന്ത്രണ്ട് പതിമൂന്ന് പതിനാല് പതിനഞ്ച് പതിനാറ് പതിനേഴ് പതിനെട്ട് പത്തൊമ്പത്"
    ).split()
    tens = "ഇരുപത് മുപ്പത് നാല്പത് അമ്പത് അറുപത് എഴുപത് എൺപത് തൊണ്ണൂറ്".split()
    oblique = "ഇരുപത്തി മുപ്പത്തി നാല്പത്തി അമ്പത്തി അറുപത്തി എഴുപത്തി എൺപത്തി തൊണ്ണൂറ്റി".split()
    out = list(base)
    for t, o in zip(tens, oblique):
        out.append(t)
        out.extend(_ml_join(o, base[u]) for u in range(1, 10))
    return tuple(out)


def _te_units() -> tuple[str, ...]:
    base = list(_t._TE_UNITS)  # 0-20
    tens = "ఇరవై ముప్పై నలభై యాభై అరవై డెబ్బై ఎనభై తొంభై".split()
    out = base[:20]
    for t in tens:
        out.append(t)
        out.extend(f"{t} {base[u]}" for u in range(1, 10))
    return tuple(out)


UNITS: dict[str, tuple[str, ...]] = {
    lang: tuple(_clean(w, lang) for w in words)
    for lang, words in {
        "as": _t._AS_UNITS, "bn": _t._BN_UNITS, "gu": _t._GU_UNITS, "hi": _t._HI_UNITS,
        "kn": _t._KN_UNITS, "ml": _ml_units(), "mr": _t._MR_UNITS, "or": _t._OR_UNITS,
        "pa": _t._PA_UNITS, "ta": _ta_units(), "te": _te_units(),
    }.items()
}

# --------------------------------------------------------------------------- Indic hundreds / scales
# Each entry is (final form, non-final form): the non-final form is used when a
# smaller non-zero part follows (Dravidian oblique case: நூறு / நூற்று).


def _same(words):
    return {d: (w, w) for d, w in enumerate(words, start=1)}


def _with_word(lang, word, sep=" "):
    return {d: (f"{UNITS[lang][d]}{sep}{word}",) * 2 for d in range(1, 10)}


_HUNDREDS: dict[str, dict[int, tuple[str, str]]] = {
    "hi": _with_word("hi", "सौ"),
    "bn": _same("একশো দুশো তিনশো চারশো পাঁচশো ছশো সাতশো আটশো নশো".split()),
    "as": _same("এশ দুশ তিনিশ চাৰিশ পাঁচশ ছয়শ সাতশ আঠশ নশ".split()),
    "gu": _with_word("gu", "સો"),
    "mr": {**_with_word("mr", "शे", sep=""), 1: ("शंभर", "एकशे")},
    "or": {**_with_word("or", "ଶହ"), 1: ("ଶହେ", "ଶହେ")},
    "pa": _with_word("pa", "ਸੌ"),
    "ta": dict(enumerate(zip(
        "நூறு இருநூறு முந்நூறு நானூறு ஐநூறு அறுநூறு எழுநூறு எண்ணூறு தொள்ளாயிரம்".split(),
        "நூற்று இருநூற்று முந்நூற்று நானூற்று ஐநூற்று அறுநூற்று எழுநூற்று எண்ணூற்று தொள்ளாயிரத்து".split(),
    ), start=1)),
    "ml": dict(enumerate(zip(
        "നൂറ് ഇരുനൂറ് മുന്നൂറ് നാനൂറ് അഞ്ഞൂറ് അറുനൂറ് എഴുനൂറ് എണ്ണൂറ് തൊള്ളായിരം".split(),
        "നൂറ്റി ഇരുനൂറ്റി മുന്നൂറ്റി നാനൂറ്റി അഞ്ഞൂറ്റി അറുനൂറ്റി എഴുനൂറ്റി എണ്ണൂറ്റി തൊള്ളായിരത്തി".split(),
    ), start=1)),
    "te": {1: ("వంద", "నూట"), **{d: (f"{UNITS['te'][d]} వందలు", f"{UNITS['te'][d]} వందల") for d in range(2, 10)}},
    "kn": dict(enumerate(zip(
        "ನೂರು ಇನ್ನೂರು ಮುನ್ನೂರು ನಾನೂರು ಐನೂರು ಆರುನೂರು ಏಳುನೂರು ಎಂಟುನೂರು ಒಂಬೈನೂರು".split(),
        "ನೂರ ಇನ್ನೂರ ಮುನ್ನೂರ ನಾನೂರ ಐನೂರ ಆರುನೂರ ಏಳುನೂರ ಎಂಟುನೂರ ಒಂಬೈನೂರ".split(),
    ), start=1)),
}

# scale -> (final, non-final) word placed after the multiplier.
_SCALES: dict[str, dict[str, tuple[str, str]]] = {
    "hi": {"thousand": ("हज़ार",) * 2, "lakh": ("लाख",) * 2, "crore": ("करोड़",) * 2},
    "bn": {"thousand": ("হাজার",) * 2, "lakh": ("লাখ",) * 2, "crore": ("কোটি",) * 2},
    "as": {"thousand": ("হাজাৰ",) * 2, "lakh": ("লাখ",) * 2, "crore": ("কোটি",) * 2},
    "gu": {"thousand": ("હજાર",) * 2, "lakh": ("લાખ",) * 2, "crore": ("કરોડ",) * 2},
    "mr": {"thousand": ("हजार",) * 2, "lakh": ("लाख",) * 2, "crore": ("कोटी",) * 2},
    "or": {"thousand": ("ହଜାର",) * 2, "lakh": ("ଲକ୍ଷ",) * 2, "crore": ("କୋଟି",) * 2},
    "pa": {"thousand": ("ਹਜ਼ਾਰ",) * 2, "lakh": ("ਲੱਖ",) * 2, "crore": ("ਕਰੋੜ",) * 2},
    "ta": {"lakh": ("லட்சம்", "லட்சத்து"), "crore": ("கோடி", "கோடியே")},
    "ml": {"lakh": ("ലക്ഷം", "ലക്ഷത്തി"), "crore": ("കോടി", "കോടി")},
    "te": {"thousand": ("వేలు", "వేల"), "lakh": ("లక్షలు", "లక్షల"), "crore": ("కోట్లు", "కోట్ల")},
    "kn": {"thousand": ("ಸಾವಿರ", "ಸಾವಿರದ"), "lakh": ("ಲಕ್ಷ", "ಲಕ್ಷದ"), "crore": ("ಕೋಟಿ", "ಕೋಟಿ")},
}

# Multiplier 1 before lakh/crore is the attributive "one" in the Dravidian languages.
_ONE_ATTRIBUTIVE = {"ta": "ஒரு", "ml": "ഒരു", "te": "ఒక"}
# Telugu singular scale words (ఒక లక్ష, not ఒకటి లక్షలు).
_TE_SINGULAR = {"thousand": ("వెయ్యి", "వెయ్యి"), "lakh": ("ఒక లక్ష", "ఒక లక్ష"), "crore": ("ఒక కోటి", "ఒక కోటి")}

# Fused thousands (Tamil நான்கு -> நான்காயிரம், Malayalam നാല് -> നാലായിരം).
_FUSED_THOUSANDS = {
    "ta": {"strip": "ு", "suffix": ("ாயிரம்", "ாயிரத்து"),
           "special": {1: ("ஆயிரம்", "ஆயிரத்து"), 5: ("ஐயாயிரம்", "ஐயாயிரத்து")}},
    "ml": {"strip": "്", "suffix": ("ായിരം", "ായിരത്തി"),
           "special": {1: ("ആയിരം", "ആയിരത്തി"), 5: ("അയ്യായിരം", "അയ്യായിരത്തി")}},
}

# 1100-1999 read as "<nineteen> hundred <rest>" (see module docstring).
_HUNDRED_YEAR_STYLE = {"hi": " सौ", "bn": "শো", "mr": "शे"}


def _scale_words(lang: str, value: int, scale: str, final: bool) -> str:
    idx = 0 if final else 1
    fused = _FUSED_THOUSANDS.get(lang)
    if scale == "thousand" and fused:
        if value in fused["special"]:
            return fused["special"][value][idx]
        words = UNITS[lang][value]
        assert words.endswith(fused["strip"]), (lang, value)
        return words[: -len(fused["strip"])] + fused["suffix"][idx]
    if lang == "te" and value == 1:
        return _TE_SINGULAR[scale][idx]
    multiplier = _ONE_ATTRIBUTIVE.get(lang, UNITS[lang][1]) if value == 1 else UNITS[lang][value]
    return f"{multiplier} {_SCALES[lang][scale][idx]}"


def _indic_cardinal(n: int, lang: str) -> str:
    units = UNITS[lang]
    if n < 100:
        return units[n]
    crore, rest = divmod(n, 10**7)
    lakh, rest = divmod(rest, 10**5)
    thousand, rest = divmod(rest, 1000)
    hundred, rest = divmod(rest, 100)
    parts = [(crore, "crore"), (lakh, "lakh"), (thousand, "thousand"), (hundred, "hundred"), (rest, None)]
    words = []
    for i, (value, scale) in enumerate(parts):
        if not value:
            continue
        final = not any(v for v, _ in parts[i + 1:])
        if scale is None:
            words.append(units[value])
        elif scale == "hundred":
            words.append(_HUNDREDS[lang][value][0 if final else 1])
        else:
            words.append(_scale_words(lang, value, scale, final))
    return " ".join(words)


# --------------------------------------------------------------------------- public helpers

_SUPPORTED = ("as", "bn", "en", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te")
_POINT = {"en": "point", "hi": "दशमलव", "bn": "দশমিক", "ta": "புள்ளி"}
_PERCENT = {"en": "percent", "hi": "प्रतिशत", "bn": "শতাংশ", "ta": "சதவீதம்"}
_RUPEES = {"en": "rupees", "hi": "रुपये", "bn": "টাকা", "ta": "ரூபாய்"}


def _check_lang(lang: str) -> None:
    if lang not in _SUPPORTED:
        raise ValueError(f"unsupported language {lang!r}; expected one of {_SUPPORTED}")


def _ascii(digits: str) -> str:
    return "".join(str(unicodedata.digit(c)) for c in digits)


def cardinal(n: int, lang: str) -> str:
    """Cardinal words for ``0 <= n < 10**9`` (no year style)."""
    _check_lang(lang)
    if not 0 <= n < 10**MAX_CARDINAL_DIGITS:
        raise ValueError(f"cardinal() supports 0 <= n < 10**{MAX_CARDINAL_DIGITS}, got {n}")
    return _en_cardinal(n) if lang == "en" else _indic_cardinal(n, lang)


def read_digits(digits: str, lang: str) -> str:
    """Digit-by-digit reading of a string of (ASCII or native) digits."""
    _check_lang(lang)
    zero_to_nine = _EN_ONES if lang == "en" else UNITS[lang]
    return " ".join(zero_to_nine[int(d)] for d in _ascii(digits))


def _integer(digits: str, lang: str, year_style: bool) -> str:
    """Words for an integer digit string (ASCII or native, no separators)."""
    ascii_digits = _ascii(digits)
    if (len(ascii_digits) > 1 and ascii_digits[0] == "0") or len(ascii_digits) > MAX_CARDINAL_DIGITS:
        return read_digits(ascii_digits, lang)
    n = int(ascii_digits)
    if year_style and len(ascii_digits) == 4:
        if lang == "en":
            year = _en_year(n)
            if year:
                return year
        elif lang in _HUNDRED_YEAR_STYLE and 1100 <= n <= 1999:
            high, low = divmod(n, 100)
            words = UNITS[lang][high] + _HUNDRED_YEAR_STYLE[lang]
            return f"{words} {UNITS[lang][low]}" if low else words
    return cardinal(n, lang)


def _grouped(body: str) -> str | None:
    """Digits of a valid Western/Indian grouped number, else None."""
    ascii_body = "".join(c if c == "," else str(unicodedata.digit(c)) for c in body)
    if _WESTERN_GROUPS_RE.fullmatch(ascii_body) or _INDIAN_GROUPS_RE.fullmatch(ascii_body):
        return ascii_body.replace(",", "")
    return None


def _body_words(body: str, lang: str, flags: set[str]) -> str | None:
    """Words for a numeric token body, or None to leave it unchanged."""
    if ":" in body or "/" in body or body.count(".") > 1:
        flags.add("numeric_unsupported")
        return None
    if "." in body:
        int_part, frac = body.split(".")
        if lang not in _POINT or "," in frac:  # "5.3,4": a list or a typo, not a decimal (crashed before v4)
            flags.add("numeric_unsupported")
            return None
        int_digits = _grouped(int_part) if "," in int_part else int_part
        if int_digits is None:
            flags.add("numeric_unsupported")
            return None
        return f"{_integer(int_digits, lang, year_style=False)} {_POINT[lang]} {read_digits(frac, lang)}"
    if "," in body:
        digits = _grouped(body)
        if digits is not None:
            return _integer(digits, lang, year_style=False)
        return ",".join(_integer(part, lang, year_style=True) for part in body.split(","))
    return _integer(body, lang, year_style=True)


def _is_latin_letter(ch: str) -> bool:
    return ch.isalpha() and "LATIN" in unicodedata.name(ch, "")


# --------------------------------------------------------------------------- v4 reading conventions
# NORMALIZATION_VERSION "4" (user decision D17). A convention is tried ONLY for a token that the rules
# above leave unchanged (``numeric_unsupported``), so no reading that existed before v4 changes. A token
# read by a convention gets the informational flag ``numeric_reading_convention``: the reading is the
# corpus convention, not verified on the clip. Evidence: .claude/reports/phoneme_frontend/
# numeric_conventions_v4.md (same-prompt rows of the other voice, corpus spellings, a duration check).
# Words are built from code points (``_s``) so that no editor can silently re-normalize them.


def _s(*cps: int) -> str:
    return "".join(map(chr, cps))


CONVENTION_LANGS = ("as", "kn", "or", "pa", "ta")
#: decimal point word (the fraction is read digit by digit, as in the hi/bn/ta rule)
_CONV_POINT = {
    "as": _s(0x09A6, 0x09B6, 0x09AE, 0x09BF, 0x0995),                  # দশমিক
    "or": _s(0x0B26, 0x0B36, 0x0B2E, 0x0B3F, 0x0B15),                  # ଦଶମିକ
}
#: percent word AFTER the number
_CONV_PERCENT_AFTER = {
    "as": _s(0x09B6, 0x09A4, 0x09BE, 0x0982, 0x09B6),                  # শতাংশ
    "or": _s(0x0B2A, 0x0B4D, 0x0B30, 0x0B24, 0x0B3F, 0x0B36, 0x0B24),  # ପ୍ରତିଶତ
}
#: percent word BEFORE the number
_CONV_PERCENT_BEFORE = {"kn": _s(0x0CB6, 0x0CC7, 0x0C95, 0x0CA1)}     # ಶೇಕಡ
#: ``$``: dollar word, placed after a directly following scale word (``$61 million``)
_CONV_DOLLAR = {
    "kn": _s(0x0CA1, 0x0CBE, 0x0CB2, 0x0CB0, 0x0CCD),                  # ಡಾಲರ್
    "pa": _s(0x0A21, 0x0A3E, 0x0A32, 0x0A30),                          # ਡਾਲਰ
}
_CONV_SCALE_WORDS = {
    "kn": (_s(0x0CAE, 0x0CBF, 0x0CB2, 0x0CBF, 0x0CAF, 0x0CA8, 0x0CCD),   # ಮಿಲಿಯನ್
           _s(0x0CAC, 0x0CBF, 0x0CB2, 0x0CBF, 0x0CAF, 0x0CA8, 0x0CCD)),  # ಬಿಲಿಯನ್
    "pa": (_s(0x0A2E, 0x0A3F, 0x0A32, 0x0A40, 0x0A05, 0x0A28),           # ਮਿਲੀਅਨ
           _s(0x0A2C, 0x0A3F, 0x0A32, 0x0A40, 0x0A05, 0x0A28)),          # ਬਿਲੀਅਨ
}
#: or: ``ଟ.<amount>[ /-]`` -> "<n> ଟଙ୍କା [<p> ପଇସା]"
_OR_TAKA_PREFIX = _s(0x0B1F) + "."                                    # ଟ.
_OR_TAKA = _s(0x0B1F, 0x0B19, 0x0B4D, 0x0B15, 0x0B3E)                 # ଟଙ୍କା
_OR_PAISA = _s(0x0B2A, 0x0B07, 0x0B38, 0x0B3E)                        # ପଇସା
_OR_SLASH_DASH_RE = re.compile(r"\s*/-")
# times
_AS_BAJA = _s(0x09AC, 0x099C, 0x09BE)                                 # বজা (বজাত, বজাৰ ...)
_AS_HALF_PAST = _s(0x099A, 0x09BE, 0x09F0, 0x09C7)                    # চাৰে
_AS_HOUR = _s(0x09AC, 0x09BE, 0x099C, 0x09BF)                         # বাজি
_AS_MINUTE = _s(0x09AE, 0x09BF, 0x09A8, 0x09BF, 0x099F)               # মিনিট
_PA_VAJE = _s(0x0A35, 0x0A1C, 0x0A47)                                 # ਵਜੇ
_PA_HALF_PAST = _s(0x0A38, 0x0A3E, 0x0A22, 0x0A47)                    # ਸਾਢੇ
_TA_MANI = _s(0x0BAE, 0x0BA3, 0x0BBF)                                 # மணி
_TA_HALF = _s(0x0BB0, 0x0BC8)                                         # -ரை (ஆறு -> ஆறரை)
_OR_HALF_PAST = _s(0x0B38, 0x0B3E, 0x0B22, 0x0B3C, 0x0B47)            # ସାଢ଼େ (NFC: ଢ + nukta)
_OR_CLASSIFIER = _s(0x0B1F, 0x0B3E)                                   # -ଟା (ଚାରିଟା)
#: half past 1 / 2 have their own words (iteration 2; corpus: ডেৰ 40, আঢ়ৈ 25, ਡੇਢ 31, ਢਾਈ 27, ଦେଢ଼ 31, ଅଢ଼େଇ 12);
#: ta forms them regularly (ஒன்றரை, இரண்டரை) from the -ு stem
_HALF_PAST_1_2 = {
    "as": {1: _s(0x09A1, 0x09C7, 0x09F0), 2: _s(0x0986, 0x09A2, 0x09BC, 0x09C8)},           # ডেৰ, আঢ়ৈ
    "pa": {1: _s(0x0A21, 0x0A47, 0x0A22), 2: _s(0x0A22, 0x0A3E, 0x0A08)},                   # ਡੇਢ, ਢਾਈ
    "or": {1: _s(0x0B26, 0x0B47, 0x0B22, 0x0B3C) + _OR_CLASSIFIER,                          # ଦେଢ଼ଟା
           2: _s(0x0B05, 0x0B22, 0x0B3C, 0x0B47, 0x0B07) + _OR_CLASSIFIER},                 # ଅଢ଼େଇଟା
}
#: or: a ``H.MM`` decimal directly after one of these words is a clock time (``ସକାଳ ୪.୩୦ରେ``)
_OR_TIME_OF_DAY = frozenset({
    _s(0x0B38, 0x0B15, 0x0B3E, 0x0B33),                                # ସକାଳ
    _s(0x0B38, 0x0B28, 0x0B4D, 0x0B27, 0x0B4D, 0x0B5F, 0x0B3E),        # ସନ୍ଧ୍ୟା
    _s(0x0B30, 0x0B3E, 0x0B24, 0x0B3F),                                # ରାତି
    _s(0x0B05, 0x0B2A, 0x0B30, 0x0B3E, 0x0B39, 0x0B4D, 0x0B28),        # ଅପରାହ୍ନ
})
# dates
_TA_MONTHS = (
    _s(0x0B9C, 0x0BA9, 0x0BB5, 0x0BB0, 0x0BBF),                        # ஜனவரி
    _s(0x0BAA, 0x0BBF, 0x0BAA, 0x0BCD, 0x0BB0, 0x0BB5, 0x0BB0, 0x0BBF),  # பிப்ரவரி
    _s(0x0BAE, 0x0BBE, 0x0BB0, 0x0BCD, 0x0B9A, 0x0BCD),                # மார்ச்
    _s(0x0B8F, 0x0BAA, 0x0BCD, 0x0BB0, 0x0BB2, 0x0BCD),                # ஏப்ரல்
    _s(0x0BAE, 0x0BC7),                                                # மே
    _s(0x0B9C, 0x0BC2, 0x0BA9, 0x0BCD),                                # ஜூன்
    _s(0x0B9C, 0x0BC2, 0x0BB2, 0x0BC8),                                # ஜூலை
    _s(0x0B86, 0x0B95, 0x0BB8, 0x0BCD, 0x0B9F, 0x0BCD),                # ஆகஸ்ட்
    _s(0x0B9A, 0x0BC6, 0x0BAA, 0x0BCD, 0x0B9F, 0x0BAE, 0x0BCD, 0x0BAA, 0x0BB0, 0x0BCD),  # செப்டம்பர்
    _s(0x0B85, 0x0B95, 0x0BCD, 0x0B9F, 0x0BCB, 0x0BAA, 0x0BB0, 0x0BCD),  # அக்டோபர்
    _s(0x0BA8, 0x0BB5, 0x0BAE, 0x0BCD, 0x0BAA, 0x0BB0, 0x0BCD),        # நவம்பர்
    _s(0x0B9F, 0x0BBF, 0x0B9A, 0x0BAE, 0x0BCD, 0x0BAA, 0x0BB0, 0x0BCD),  # டிசம்பர்
)
_TA_DATE_WORD = _s(0x0BA4, 0x0BC7, 0x0BA4, 0x0BBF)                    # தேதி
_TA_ORDINAL = _s(0x0BBE, 0x0BAE, 0x0BCD)                              # -ாம் (பத்து -> பத்தாம்)
_TA_U = _s(0x0BC1)                                                    # final -ு

_DATE_RE = re.compile(r"(\d{1,2})([/.])(\d{1,2})\2(\d{4}|\d{2})")
_NEXT_WORD_RE = re.compile(r"\s*(\S+)")


def _ascii_seps(body: str) -> str:
    return "".join(c if c in "/.:," else str(unicodedata.digit(c)) for c in body)


def _drop_final_u(word: str) -> str | None:
    return word[:-1] if word.endswith(_TA_U) else None


def _conv_number(body: str, lang: str) -> str | None:
    """Integer / grouped / decimal body -> words (decimal point word from _CONV_POINT)."""
    if ":" in body or "/" in body or body.count(".") > 1:
        return None
    if "." in body:
        if lang not in _CONV_POINT:
            return None
        int_part, frac = body.split(".")
        int_digits = _grouped(int_part) if "," in int_part else int_part
        if int_digits is None or "," in frac:
            return None
        return f"{_integer(int_digits, lang, year_style=False)} {_CONV_POINT[lang]} {read_digits(frac, lang)}"
    return _body_words(body, lang, set())


def _conv_date(body: str, lang: str) -> str | None:
    m = _DATE_RE.fullmatch(_ascii_seps(body))
    if not m:
        return None
    day, sep, month, year = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4)
    if not (1 <= day <= 31 and 1 <= month <= 12) or (sep == "." and len(year) != 4):
        return None
    if lang == "as":  # "<day> <month number> <year>"; leading zeros are not read (duration check)
        return f"{cardinal(day, lang)} {cardinal(month, lang)} {cardinal(int(year), lang)}"
    if lang == "ta" and len(year) == 4:  # "<month> <day>-ஆம் தேதி <year>"
        stem = _drop_final_u(cardinal(day, lang))
        if stem is None:
            return None
        return f"{_TA_MONTHS[month - 1]} {stem}{_TA_ORDINAL} {_TA_DATE_WORD} {cardinal(int(year), lang)}"
    return None


def _conv_time(hour: int, minute: int, lang: str, text: str, end: int) -> tuple[str, int] | None:
    """Clock time -> (words, end); ``end`` may move past a consumed following word."""
    if not (1 <= hour <= 23 and 0 <= minute <= 59):  # hour 0 has no settled reading: unsupported
        return None
    nxt = _NEXT_WORD_RE.match(text, end)
    nxt_word = nxt.group(1) if nxt else ""
    h = cardinal(hour, lang)
    half = _HALF_PAST_1_2.get(lang, {}).get(hour) if minute == 30 else None
    if lang == "as":
        if nxt_word.startswith(_AS_BAJA):
            if minute == 30:
                return half or f"{_AS_HALF_PAST} {h}", end
            if minute == 0:
                return h, end
            # "৩:১০ বজাত" -> "তিনি বাজি দহ মিনিটত": বজা is replaced, its case suffix stays
            return f"{h} {_AS_HOUR} {cardinal(minute, lang)} {_AS_MINUTE}", nxt.start(1) + len(_AS_BAJA)
        if (text[end:end + 1] == "-" and text[end + 1:end + 2].isalpha()) or text[end:end + 1].isalpha():  # "৬:৪৫-ত"
            return f"{h} {_AS_HOUR} {cardinal(minute, lang)} {_AS_MINUTE}", end
        return None  # e.g. a score "১২:১০ ব্যৱধানত"
    if lang == "pa" and nxt_word.startswith(_PA_VAJE):
        words = {30: half or f"{_PA_HALF_PAST} {h}", 0: h}.get(minute)
        return (words, end) if words else None
    if lang == "ta" and nxt_word.startswith(_TA_MANI):
        if minute == 0:
            return h, end
        stem = _drop_final_u(h)
        return (stem + _TA_HALF, end) if minute == 30 and stem else None
    if lang == "or":  # only called right after a time-of-day word
        words = {30: half or f"{_OR_HALF_PAST} {h}{_OR_CLASSIFIER}", 0: f"{h}{_OR_CLASSIFIER}"}.get(minute)
        return (words, end) if words else None
    return None


def _split_time(body: str, sep: str) -> tuple[int, int] | None:
    hh, mm = body.split(sep)
    if len(mm) != 2 or len(hh) > 2:
        return None
    return int(_ascii(hh)), int(_ascii(mm))


def _convention(text: str, m: re.Match, lang: str) -> tuple[str, int, int] | None:
    """(words, start, end) for a token the default rules leave unsupported, or None (stays unsupported)."""
    if lang not in CONVENTION_LANGS:
        return None
    start, end = m.span()
    body, cur, pct = m.group("body"), m.group("cur"), m.group("pct")
    if cur:
        if pct or cur.strip() != "$" or lang not in _CONV_DOLLAR or "." in body:
            return None
        words = _conv_number(body, lang)
        if words is None:
            return None
        nxt = _NEXT_WORD_RE.match(text, end)
        scale = next((w for w in _CONV_SCALE_WORDS[lang] if nxt and nxt.group(1).startswith(w)
                      and not nxt.group(1)[len(w):len(w) + 1].isalpha()), None)  # "ಮಿಲಿಯನ್." too
        if scale:
            return f"{words} {scale} {_CONV_DOLLAR[lang]}", start, nxt.start(1) + len(scale)
        return f"{words} {_CONV_DOLLAR[lang]}", start, end
    if pct:
        words = _conv_number(body, lang)
        if words is None:
            return None
        if lang in _CONV_PERCENT_AFTER:
            return f"{words} {_CONV_PERCENT_AFTER[lang]}", start, end
        if lang in _CONV_PERCENT_BEFORE:
            return f"{_CONV_PERCENT_BEFORE[lang]} {words}", start, end
        return None
    if lang == "or" and text[max(0, start - 2):start] == _OR_TAKA_PREFIX and not (start >= 3 and unicodedata.category(text[start - 3])[0] in "LM"):
        parts = body.split(".")
        if len(parts) > 2 or any(c in body for c in ",:/") or (len(parts) == 2 and len(parts[1]) != 2):
            return None
        words = f"{_integer(parts[0], lang, year_style=False)} {_OR_TAKA}"
        if len(parts) == 2 and int(_ascii(parts[1])):
            words += f" {cardinal(int(_ascii(parts[1])), lang)} {_OR_PAISA}"
        slash = _OR_SLASH_DASH_RE.match(text, end)
        return words, start - 2, slash.end() if slash else end
    time = None
    prev = text[:start].split()
    or_time_ctx = lang == "or" and bool(prev) and prev[-1] in _OR_TIME_OF_DAY
    if body.count(":") == 1 and not any(c in body for c in "./,"):
        if lang == "or" and not or_time_ctx:  # or colon pairs need a time-of-day word (scores, ratios)
            return None
        time = _split_time(body, ":")
        if time is None:
            return None
    elif lang == "or" and body.count(".") == 1 and "," not in body:
        dot = _split_time(body, ".")
        if or_time_ctx:
            time = dot
            if time is None:
                return None
        elif dot and dot[0] <= 12 and dot[1] <= 59:
            return None  # "୪.୩୦" with no time-of-day word: decimal or clock time, ambiguous
    elif lang == "as" and body.count(".") == 1 and "," not in body:
        nxt = _NEXT_WORD_RE.match(text, end)
        if nxt and nxt.group(1).startswith(_AS_BAJA):  # "৫.৩০ বজাত" is a clock time, never a decimal
            time = _split_time(body, ".")
            if time is None:
                return None
    if time is not None:
        res = _conv_time(*time, lang, text, end)
        return (res[0], start, res[1]) if res else None
    if body.count("/") == 2 or body.count(".") == 2:
        words = _conv_date(body, lang)
        return (words, start, end) if words else None
    words = _conv_number(body, lang)  # decimals (as, or)
    return (words, start, end) if words else None


def verbalize_digits(text: str, lang: str) -> tuple[str, set[str]]:
    """Replace every numeric token in ``text`` by words. Returns (text, flags)."""
    _check_lang(lang)
    flags: set[str] = set()
    out: list[str] = []
    pos = 0
    for m in _NUM_TOKEN_RE.finditer(text):
        start, end = m.span()
        if start < pos:  # inside a span a convention already consumed
            continue
        body = m.group("body")
        cur, pct = m.group("cur"), m.group("pct")
        words = _body_words(body, lang, set())
        if words is None or (pct and lang not in _PERCENT) or (cur and (cur.strip() != "₹" or lang not in _RUPEES)):
            conv = _convention(text, m, lang)  # v4: only tokens the rules above leave unsupported
            if conv is None or conv[1] < pos:
                flags.add("numeric_unsupported")  # leave the whole token unchanged
                continue
            words, start, end = conv
            flags.add("numeric_reading_convention")
        else:
            if lang == "en" and not cur and not pct and body.isdigit() and len(body) <= MAX_CARDINAL_DIGITS:
                ordinal = _EN_ORDINAL_RE.match(text, end)
                if ordinal:
                    words, end = _en_ordinal(int(_ascii(body))), ordinal.end()
            if pct:
                words = f"{words} {_PERCENT[lang]}"
            if cur:
                unit = "rupee" if lang == "en" and words == "one" else _RUPEES[lang]
                words = f"{words} {unit}"
        words = _clean(words, lang)
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        if before.isalpha() and (lang == "en" or _is_latin_letter(before)):
            words = " " + words
        if after.isalpha() and (lang == "en" or _is_latin_letter(after)):
            words = words + " "
        out.append(text[pos:start])
        out.append(words)
        pos = end
    out.append(text[pos:])
    return "".join(out), flags
