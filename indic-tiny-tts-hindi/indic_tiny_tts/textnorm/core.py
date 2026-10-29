"""The two normalization pipelines of ``textnorm`` (contract: package docstring)."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field

from .numbers import verbalize_digits

NORMALIZATION_VERSION = "4"
SUPPORTED_LANGS = ("as", "bn", "en", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te")

ZWJ = "‍"
ZWNJ = "‌"

# --------------------------------------------------------------------------- tables

#: Malayalam legacy ``ന്‍റ`` (NA + virama + ZWJ + RRA) -> conjunct ``ന്റ``. Applied
#: before ML_LEGACY_CHILLU so that it does not become atomic chillu ൻ + റ.
ML_NTA_LEGACY = ("ന്‍റ", "ന്റ")

#: Malayalam legacy chillu (consonant + virama + ZWJ) -> atomic chillu U+0D7A-0D7F.
ML_LEGACY_CHILLU = {
    "ണ്‍": "ൺ",  # ണ് -> ൺ
    "ന്‍": "ൻ",  # ന് -> ൻ
    "ര്‍": "ർ",  # ര് -> ർ
    "ല്‍": "ൽ",  # ല് -> ൽ
    "ള്‍": "ൾ",  # ള് -> ൾ
    "ക്‍": "ൿ",  # ക് -> ൿ
}

#: Assamese: Bengali RA U+09B0 -> Assamese RA U+09F0 (both paths; encoding fix).
AS_RA = ("র", "ৰ")

#: Bengali (v2): Assamese ৰ U+09F0 / ৱ U+09F1 typed inside Bengali text -> র U+09B0 / ব U+09AC
#: (both paths; the mirror of AS_RA). The bn voice reads ৰ/ৱ as letter names.
BN_AS_LETTERS = {"ৰ": "র", "ৱ": "ব"}

#: Invisible format characters removed in all languages (v2): ZERO WIDTH SPACE U+200B,
#: BOM / ZERO WIDTH NO-BREAK SPACE U+FEFF, WORD JOINER U+2060, SOFT HYPHEN U+00AD.
#: (ZWJ / ZWNJ have their own steps.) Removed, not replaced by a space: in the corpus they sit
#: next to a space or inside a word (ta ``சென்ஜுங்கா<ZWSP>வுல``).
INVISIBLE_CHARS = "\u200b\ufeff\u2060\u00ad"

#: Hindi (v2) nukta / vowel-sign repair (both paths). A nukta is kept only directly after one of
#: HI_NUKTA_BASES. A nukta typed after a vowel sign / anusvara of such a consonant moves back to
#: it (``बडे़`` -> ``बड़े``); every other nukta (doubled, after a vowel letter, after another
#: consonant) is dropped. Then legacy two-sign spellings of one vowel (HI_TWO_SIGN_VOWELS:
#: ``ा+ॅ`` -> ``ॉ``, ``े+ा`` -> ``ो``, ``ा+ौ`` -> ``ौ`` ...) are joined, an exactly repeated vowel
#: sign is collapsed (``मेेरे`` -> ``मेरे``), and two confirmed typo pairs keep the first sign
#: (``ीे`` -> ``ी``: ``नहीे``; ``ेै`` -> ``े``: ``फाइनेैंस``). Any OTHER pair of adjacent vowel
#: signs is left unchanged on purpose (the intended vowel is ambiguous); eSpeak then emits the
#: ``ʰχ`` artefact and the row stays blocked (unknown_symbol).
HI_NUKTA_BASES = frozenset("कखगजडढफ")
DEV_NUKTA = "\u093c"
DEV_VOWEL_SIGNS = frozenset(
    [chr(c) for c in (0x093A, 0x093B, *range(0x093E, 0x094D), 0x094E, 0x094F, 0x0955, 0x0956,
                      0x0957, 0x0962, 0x0963)]
)
DEV_MODIFIERS = frozenset("\u0900\u0901\u0902\u0903")  # inverted candrabindu, candrabindu, anusvara, visarga
HI_TWO_SIGN_VOWELS = (
    ("\u093e\u0945", "\u0949"), ("\u0945\u093e", "\u0949"), ("\u093e\u0949", "\u0949"),  # ा+ॅ ॅ+ा ा+ॉ -> ॉ
    ("\u0947\u093e", "\u094b"), ("\u093e\u0947", "\u094b"),                              # े+ा ा+े -> ो
    ("\u0948\u093e", "\u094c"), ("\u093e\u0948", "\u094c"), ("\u093e\u094c", "\u094c"),  # ै+ा ा+ै ा+ौ -> ौ
)
HI_TYPO_SIGN_PAIRS = (("\u0940\u0947", "\u0940"), ("\u0947\u0948", "\u0947"))  # ी+े -> ी, े+ै -> े

# v3 (D16) text-typo repairs. Until v3 they were applied by phonemes/espeak_fixes.py to text_espeak
# only (ESPEAK_FIXES_VERSION <= 3); now text_char gets them too. Voice-specific eSpeak workarounds
# (mr/gu/kn nukta drop, te arasunna, U+02BC quote marks, mr candra vowels, pa loanword overrides)
# stay eSpeak-side. mr (step ``deva_vowel_signs``) gets the vowel-sign part of the hi rule
# (HI_TWO_SIGN_VOWELS, HI_TYPO_SIGN_PAIRS, an exactly repeated sign), not its nukta part.


def _s(*cps: int) -> str:
    """Codepoints -> str (v3 tables use code points so no editor can silently re-normalize them)."""
    return "".join(map(chr, cps))


#: Two-sign typos of one vowel -> the single sign / letter, per language: (step name, pairs).
TYPO_SIGN_PAIRS = {
    "gu": ("gu_two_sign_vowels", ((_s(0x0ABE, 0x0AC5), _s(0x0AC9)),     # AA + candra E -> candra O
                                  (_s(0x0AC5, 0x0ABE), _s(0x0AC9)))),
    "kn": ("kn_long_o_sign", ((_s(0x0CC2, 0x0CD5), _s(0x0CCB)),)),        # UU + length mark -> OO
    "or": ("or_au_sign", ((_s(0x0B4B, 0x0B56), _s(0x0B4C)),)),            # O + AI length mark -> AU
    "ta": ("ta_au_letter", ((_s(0x0B93, 0x0BD7), _s(0x0B94)),)),          # letter OO + AU mark -> AU
    "pa": ("pa_dda_nukta_to_rra", ((_s(0x0A21, 0x0A3C), _s(0x0A5C)),)),   # DDA + nukta -> RRA
}
#: as (step ``as_stray_nukta_dropped``): a Bengali-script nukta U+09BC is kept only right after
#: DDA / DDHA / YA (the decomposed RRA / RHA / YYA); any other nukta is a typo and is dropped.
AS_NUKTA_BASES = frozenset(_s(0x09A1, 0x09A2, 0x09AF))
BENG_NUKTA = _s(0x09BC)
#: Every Indic dependent vowel sign U+0900-0DFF (Unicode 15 names containing "VOWEL SIGN"; frozen
#: so the rule does not depend on the Python's Unicode version). An exactly repeated sign is always
#: a typo (step ``repeated_vowel_sign``, languages REPEATED_SIGN_LANGS).
INDIC_VOWEL_SIGNS = "".join(chr(c) for a, b in (
    (0x093A, 0x093B), (0x093E, 0x094C), (0x094E, 0x094F), (0x0955, 0x0957), (0x0962, 0x0963),
    (0x09BE, 0x09C4), (0x09C7, 0x09C8), (0x09CB, 0x09CC), (0x09E2, 0x09E3),
    (0x0A3E, 0x0A42), (0x0A47, 0x0A48), (0x0A4B, 0x0A4C),
    (0x0ABE, 0x0AC5), (0x0AC7, 0x0AC9), (0x0ACB, 0x0ACC), (0x0AE2, 0x0AE3),
    (0x0B3E, 0x0B44), (0x0B47, 0x0B48), (0x0B4B, 0x0B4C), (0x0B62, 0x0B63),
    (0x0BBE, 0x0BC2), (0x0BC6, 0x0BC8), (0x0BCA, 0x0BCC),
    (0x0C3E, 0x0C44), (0x0C46, 0x0C48), (0x0C4A, 0x0C4C), (0x0C62, 0x0C63),
    (0x0CBE, 0x0CC4), (0x0CC6, 0x0CC8), (0x0CCA, 0x0CCC), (0x0CE2, 0x0CE3),
    (0x0D3E, 0x0D44), (0x0D46, 0x0D48), (0x0D4A, 0x0D4C), (0x0D62, 0x0D63),
    (0x0DCF, 0x0DD4), (0x0DD6, 0x0DD6), (0x0DD8, 0x0DDF), (0x0DF2, 0x0DF3),
) for c in range(a, b + 1))
REPEATED_SIGN_LANGS = ("gu", "te", "kn", "or", "pa", "as")

#: Bracketed non-speech event tags (transcriber annotations, mostly Assamese), removed in ALL
#: languages wherever they occur (v2). Square or round brackets; case-insensitive; any
#: ``[word_word]`` (underscore compound) is also a tag. Collected from the full corpus text.
NONSPEECH_TAGS = frozenset({
    "noise", "uhh", "ugh", "umm", "talking", "horn", "unintelligible", "stammers", "buzz",
    "buzzer", "music", "singing", "popping", "breathing", "inhaling", "laugh",
    "bird_squawk", "throat_clearing", "child_talking", "phone_vibrating",
})

#: Q5 / D13 (user, 2026-10-16): per-language rule for a bracketed Latin gloss after a native word.
#: Evidence: duration check over every gloss row (validation/report.md, gloss_duration_check.json):
#: as 742/801 clips match the NOT-spoken prediction -> strip; pa 7/9 and kn 4/5 match the spoken
#: prediction -> KEEP (the gloss stays in the text as a Latin span, phonemized with en-us + D8,
#: flagged ``latin_gloss_kept``). Languages with no gloss rows (bn gu hi ml mr or ta te) keep the
#: Q5 default (strip). en never strips.
GLOSS_KEEP_LANGS = ("kn", "pa")

#: Precomposed nukta letters that are Unicode composition exclusions: NFC/NFD
#: always decompose them to base + nukta. The character path keeps the
#: decomposed (= NFC) form; the eSpeak path recomposes them.
COMPOSITION_EXCLUSION_CHARS = (
    "क़ख़ग़ज़ड़ढ़फ़य़"  # Devanagari क़ ख़ ग़ ज़ ड़ ढ़ फ़ य़
    "ড়ঢ়য়"                                # Bengali ড় ঢ় য়
    "ਲ਼ਸ਼ਖ਼ਗ਼ਜ਼ਫ਼"              # Gurmukhi ਲ਼ ਸ਼ ਖ਼ ਗ਼ ਜ਼ ਫ਼
    "ଡ଼ଢ଼"                                      # Odia ଡ଼ ଢ଼
)
#: decomposed (base + nukta) -> precomposed codepoint; eSpeak path only.
NUKTA_RECOMPOSE = {unicodedata.normalize("NFD", c): c for c in COMPOSITION_EXCLUSION_CHARS}

#: Assamese eSpeak workaround: precomposed ড় U+09DC / ঢ় U+09DD -> ৰ U+09F0.
AS_ESPEAK_RRA = {"ড়": "ৰ", "ঢ়": "ৰ"}
#: Odia eSpeak workaround: ୱ U+0B71 -> ଵ U+0B35 (eSpeak drops/spells ୱ).
OR_ESPEAK_WA = ("ୱ", "ଵ")

#: Step names, in pipeline order.
CHAR_STEPS = (
    "nfc",                  # NFC + whitespace collapse (= data_prep normalize_text)
    "ml_chillu",            # ml: ന്‍റ -> ന്റ, legacy chillu -> atomic
    "zwj_removed",
    "zwnj_removed",
    "zwsp_bom_removed",     # v2: U+200B U+FEFF U+2060 U+00AD
    "as_ra",                # as: র -> ৰ
    "bn_as_letters",        # v2, bn: ৰ -> র, ৱ -> ব
    "hi_nukta_matra",       # v2, hi: stray/doubled nukta, legacy candra O, doubled vowel signs
    "deva_vowel_signs",     # v3, mr: the vowel-sign part of hi_nukta_matra
    "gu_two_sign_vowels",   # v3, gu: ા+ૅ -> ૉ
    "kn_long_o_sign",       # v3, kn: ೂ+ೕ -> ೋ
    "or_au_sign",           # v3, or: ୋ+ୖ -> ୌ
    "ta_au_letter",         # v3, ta: ஓ+ௗ -> ஔ
    "pa_dda_nukta_to_rra",  # v3, pa: ਡ+਼ -> ੜ
    "as_stray_nukta_dropped",  # v3, as: nukta not after ড ঢ য
    "repeated_vowel_sign",  # v3, gu te kn or pa as: ખૂૂ -> ખૂ
    "nonspeech_tag_removed",  # v2: [noise], [bird_squawk], (laugh) ...
    "latin_gloss_removed",  # "স্মাৰ্টফোন [smart phone]" -> "স্মাৰ্টফোন" (not pa/kn, not en)
    "as_latin_bracket_removed",  # v3, as: other bracketed spans with Latin and no Assamese letter/digit
    "pa_latin_i_danda",     # pa: clause-final Latin "I" -> "।"
    "hi_latin_i_danda",     # v2, hi: same rule for Devanagari ("हैI" -> "है।")
    "or_latin_i_danda",     # v3, or: text-final Latin "I" -> "।"
    "en_ampersand",         # v4, en: "&" -> " and " (J&K -> J and K)
    "digits_verbalized",
)
ESPEAK_STEPS = (
    "nukta_recomposed",
    "as_rra_to_ra",         # as: ড়/ঢ় -> ৰ
    "or_wa_to_va",          # or: ୱ -> ଵ
)
#: Flag names that may appear in ``NormalizationResult.flags``.
#: ``numeric_reading_convention`` (v4) is INFORMATIONAL: a number was read by a per-language corpus
#: convention (date/time/decimal/percent/currency, see ``textnorm.numbers``), not a verified reading.
FLAGS = ("latin_gloss_removed", "numeric_unsupported", "latin_gloss_kept", "nonspeech_tag_removed",
         "numeric_reading_convention")

# --------------------------------------------------------------------------- result


@dataclass
class NormalizationResult:
    """Output of :func:`normalize_for_chars` / :func:`normalize_for_espeak`."""

    text: str
    lang: str
    normalization_applied: list[str] = field(default_factory=list)
    latin_spans: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    @property
    def latin_gloss_removed(self) -> bool:
        return "latin_gloss_removed" in self.flags

    @property
    def latin_gloss_kept(self) -> bool:
        return "latin_gloss_kept" in self.flags

    @property
    def nonspeech_tag_removed(self) -> bool:
        return "nonspeech_tag_removed" in self.flags

    @property
    def numeric_unsupported(self) -> bool:
        return "numeric_unsupported" in self.flags

    @property
    def numeric_reading_convention(self) -> bool:
        return "numeric_reading_convention" in self.flags

    def __str__(self) -> str:
        return self.text


# --------------------------------------------------------------------------- helpers


def nfc_whitespace(text: str) -> str:
    """Byte-identical to ``data_prep.prepare.normalize_text`` on valid input
    (that function additionally rejects empty/oversized/control-char text)."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def _tidy(text: str) -> str:
    # Removing ZW characters or tokens can create composable pairs / double spaces.
    return nfc_whitespace(text)


def _is_indic_word_char(ch: str) -> bool:
    return (
        "ऀ" <= ch <= "෿"
        and unicodedata.category(ch)[0] in "LM"
    )


_LATIN = "A-Za-zÀ-ÖØ-öø-ɏ"
_GLOSS_RE = re.compile(rf"\s*(\[[{_LATIN} .'’&/-]*\]|\([{_LATIN} .'’&/-]*\))")
_HAS_LATIN_RE = re.compile(rf"[{_LATIN}]")
#: not before Latin, ``.``, ``-``, an apostrophe or a digit (Roman numeral, ``I.T.``, ``I-phone``).
_I_DANDA_TAIL = rf"(?=\s*(?:$|[^\s{_LATIN}.\-'’0-9]))"
_PA_I_RE = re.compile(rf"(?<=[਀-੿])(\s*)I{_I_DANDA_TAIL}")
#: hi: only an ``I`` attached to the word (``हैI``; all corpus cases). A spaced ``I`` is ambiguous
#: with a Roman numeral (``विश्व युद्ध I में``) and is left as Latin.
_HI_I_RE = re.compile(rf"(?<=[ऀ-ॿ])()I{_I_DANDA_TAIL}")
#: square brackets: any case; round brackets: lowercase only (``(Horn)`` in prose is a word).
_TAG_RE = re.compile(r"\s*(?:\[\s*([A-Za-z_]+)\s*\]|\(\s*([a-z_]+)\s*\))")
_LATIN_WORD = rf"[{_LATIN}]+(?:['’.-][{_LATIN}]+)*"
_LATIN_SPAN_RE = re.compile(rf"{_LATIN_WORD}(?:\s+{_LATIN_WORD})*")
#: or (v3): a text-final Latin ``I`` after an Odia letter is a danda typed as I (else read as
#: English "I"); only text-final (the 2 corpus rows), like the former eSpeak-side rule.
_OR_I_RE = re.compile("(?<=[" + _s(0x0B00) + "-" + _s(0x0B7F) + r"])(\s*)I(?=\s*$)")
#: as (v3): a bracketed span with a Latin letter that the gloss rule did not remove (``+``,
#: digits, after punctuation, row-initial). Q5: as glosses are not spoken (742/801 clips), so
#: the span is removed if it has no Bengali-script letter or digit as written in the source
#: (this step runs before digits_verbalized, so ``[18+ years]`` is removed and ``(৫ km)`` kept).
_AS_LATIN_BRACKET_RE = re.compile(r"\s*(?:\[[^\[\]]*[A-Za-z][^\[\]]*\]|\([^()]*[A-Za-z][^()]*\))")
_REPEATED_VOWEL_SIGN_RE = re.compile("([" + INDIC_VOWEL_SIGNS + r"])\1+")
#: en (v4, R6): ``&`` is read "and" (``J&K``, ``HIV & AIDS``; LIMMITS + IndicTTS-English). Only en:
#: in Indic rows ``&`` sits between native words and may be read in either language (stays blocked).
#: R6b: HTML character references WITH a semicolon (``&amp;`` ``&nbsp;`` ``&#38;``) are decoded first
#: (``html.unescape`` on the reference only; ``&T`` in ``AT&T`` is not one), and the fullwidth / small
#: ampersands U+FF06 U+FE60 count as ``&``. Known limit: ``AT&T`` -> ``AT and T`` (0 corpus rows).
_EN_AMPERSAND_RE = re.compile(r"\s*[&" + chr(0xFF06) + chr(0xFE60) + r"]\s*")
_HTML_REF_RE = re.compile(r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")


def _en_ampersand(text: str) -> str:
    text = _HTML_REF_RE.sub(lambda m: html.unescape(m.group(0)), text)
    return _EN_AMPERSAND_RE.sub(" and ", text)


def _ml_chillu(text: str) -> str:
    text = text.replace(*ML_NTA_LEGACY)
    for legacy, atomic in ML_LEGACY_CHILLU.items():
        text = text.replace(legacy, atomic)
    return text


def _strip_latin_gloss_once(text: str) -> str:
    def repl(m: re.Match) -> str:
        start = m.start()
        if start > 0 and _is_indic_word_char(text[start - 1]) and _HAS_LATIN_RE.search(m.group(1)):
            return ""
        return m.group(0)

    return _GLOSS_RE.sub(repl, text)


def _strip_latin_gloss(text: str) -> str:
    """Remove glosses to a fixpoint (``শব্দ (abc) (def)`` -> ``শব্দ``): one pass only sees
    brackets that follow a native word in the ORIGINAL string."""
    while True:
        new = nfc_whitespace(_strip_latin_gloss_once(text))
        if new == text:
            return text
        text = new


def _is_nonspeech_tag(word: str) -> bool:
    w = word.lower()
    return w in NONSPEECH_TAGS or bool(re.fullmatch(r"[a-z]+(?:_[a-z]+)+", w))


def _strip_nonspeech_tags(text: str) -> str:
    def repl(m: re.Match) -> str:
        return " " if _is_nonspeech_tag(m.group(1) or m.group(2)) else m.group(0)

    return _TAG_RE.sub(repl, text)


def _hi_nukta_matra(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ch != DEV_NUKTA:
            out.append(ch)
            continue
        if out and out[-1] in HI_NUKTA_BASES:
            out.append(ch)
            continue
        j = len(out) - 1
        while j >= 0 and (out[j] in DEV_VOWEL_SIGNS or out[j] in DEV_MODIFIERS):
            j -= 1
        if 0 <= j < len(out) - 1 and out[j] in HI_NUKTA_BASES and out[j + 1] != DEV_NUKTA:
            out.insert(j + 1, DEV_NUKTA)
        # else: doubled / stray nukta -> dropped
    return _deva_vowel_signs("".join(out))


def _deva_vowel_signs(text: str) -> str:
    """Legacy two-sign vowels joined, the two typo pairs, an exactly repeated sign collapsed (the
    vowel-sign part of hi_nukta_matra; v3 step ``deva_vowel_signs`` for mr)."""
    for legacy, sign in HI_TWO_SIGN_VOWELS + HI_TYPO_SIGN_PAIRS:
        text = text.replace(legacy, sign)
    return _REPEATED_SIGN_RE.sub(lambda m: m.group(1), text)


def _replace_pairs(text: str, pairs) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def _as_stray_nukta(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ch == BENG_NUKTA and not (out and out[-1] in AS_NUKTA_BASES):
            continue
        out.append(ch)
    return "".join(out)


def _is_beng_letter_or_digit(ch: str) -> bool:
    return 0x0980 <= ord(ch) <= 0x09FF and unicodedata.category(ch) in ("Lo", "Lm", "Nd")


def _as_latin_bracket(text: str) -> str:
    def repl(m: re.Match) -> str:
        return m.group(0) if any(_is_beng_letter_or_digit(c) for c in m.group(0)) else " "

    return _AS_LATIN_BRACKET_RE.sub(repl, text)


_REPEATED_SIGN_RE = re.compile("([" + "".join(sorted(DEV_VOWEL_SIGNS)) + r"])\1+")


def find_latin_spans(text: str) -> list[str]:
    """Maximal runs of Latin-script words (joined by whitespace) in ``text``."""
    return _LATIN_SPAN_RE.findall(text)


def _check_lang(lang: str) -> None:
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"unsupported language {lang!r}; expected one of {SUPPORTED_LANGS}")


# --------------------------------------------------------------------------- pipelines


def normalize_for_chars(text: str, lang: str) -> NormalizationResult:
    """Character-path normalization (``text_char``). NFC-stable; decomposed nukta."""
    _check_lang(lang)
    applied: list[str] = []
    flags: set[str] = set()

    def step(name: str, new: str) -> str:
        new = _tidy(new)
        if new != current:
            applied.append(name)
        return new

    current = nfc_whitespace(text)
    if current != text:
        applied.append("nfc")
    if lang == "ml":
        current = step("ml_chillu", _ml_chillu(current))
    current = step("zwj_removed", current.replace(ZWJ, ""))
    current = step("zwnj_removed", current.replace(ZWNJ, ""))
    current = step("zwsp_bom_removed", current.translate({ord(c): None for c in INVISIBLE_CHARS}))
    if lang == "as":
        current = step("as_ra", current.replace(*AS_RA))
    if lang == "bn":
        current = step("bn_as_letters", current.translate(str.maketrans(BN_AS_LETTERS)))
    if lang == "hi":
        current = step("hi_nukta_matra", _hi_nukta_matra(current))
    if lang == "mr":
        current = step("deva_vowel_signs", _deva_vowel_signs(current))
    if lang in TYPO_SIGN_PAIRS:
        name, pairs = TYPO_SIGN_PAIRS[lang]
        current = step(name, _replace_pairs(current, pairs))
    if lang == "as":
        current = step("as_stray_nukta_dropped", _as_stray_nukta(current))
    if lang in REPEATED_SIGN_LANGS:
        current = step("repeated_vowel_sign", _REPEATED_VOWEL_SIGN_RE.sub(lambda m: m.group(1), current))
    current = step("nonspeech_tag_removed", _strip_nonspeech_tags(current))
    if "nonspeech_tag_removed" in applied:
        flags.add("nonspeech_tag_removed")
    if lang in GLOSS_KEEP_LANGS:
        if _strip_latin_gloss(current) != current:
            flags.add("latin_gloss_kept")
    elif lang != "en":
        current = step("latin_gloss_removed", _strip_latin_gloss(current))
        if "latin_gloss_removed" in applied:
            flags.add("latin_gloss_removed")
    if lang == "as":
        current = step("as_latin_bracket_removed", _as_latin_bracket(current))
        if "as_latin_bracket_removed" in applied:
            flags.add("latin_gloss_removed")
    if lang == "pa":
        current = step("pa_latin_i_danda", _PA_I_RE.sub(lambda m: m.group(1) + "।", current))
    if lang == "hi":
        current = step("hi_latin_i_danda", _HI_I_RE.sub(lambda m: m.group(1) + "।", current))
    if lang == "or":
        current = step("or_latin_i_danda", _OR_I_RE.sub(lambda m: m.group(1) + "।", current))
    if lang == "en":
        current = step("en_ampersand", _en_ampersand(current))
    verbalized, num_flags = verbalize_digits(current, lang)
    flags |= num_flags
    current = step("digits_verbalized", verbalized)

    assert unicodedata.is_normalized("NFC", current)
    return NormalizationResult(
        text=current,
        lang=lang,
        normalization_applied=applied,
        latin_spans=[] if lang == "en" else find_latin_spans(current),
        flags=[f for f in FLAGS if f in flags],
    )


def espeak_layer(text_char: str, lang: str) -> tuple[str, list[str]]:
    """eSpeak-only rewrites of an already char-normalized string.

    The result is deliberately NOT NFC (recomposed nukta letters are
    composition exclusions); never NFC-normalize it again and never use it as
    character-path input.
    """
    _check_lang(lang)
    applied: list[str] = []
    current = text_char
    for decomposed, precomposed in NUKTA_RECOMPOSE.items():
        current = current.replace(decomposed, precomposed)
    if current != text_char:
        applied.append("nukta_recomposed")
    if lang == "as":
        new = current.translate(str.maketrans(AS_ESPEAK_RRA))
        if new != current:
            applied.append("as_rra_to_ra")
        current = new
    if lang == "or":
        new = current.replace(*OR_ESPEAK_WA)
        if new != current:
            applied.append("or_wa_to_va")
        current = new
    return current, applied


def normalize_for_espeak(text: str, lang: str) -> NormalizationResult:
    """``normalize_for_chars`` followed by :func:`espeak_layer` (``text_espeak``)."""
    chars = normalize_for_chars(text, lang)
    espeak_text, espeak_applied = espeak_layer(chars.text, lang)
    return NormalizationResult(
        text=espeak_text,
        lang=lang,
        normalization_applied=chars.normalization_applied + espeak_applied,
        latin_spans=chars.latin_spans,
        flags=chars.flags,
    )


def text_for_chars(text: str, lang: str) -> str:
    """String-only convenience wrapper: ``normalize_for_chars(text, lang).text``."""
    return normalize_for_chars(text, lang).text


def text_for_espeak(text: str, lang: str) -> str:
    """String-only convenience wrapper: ``normalize_for_espeak(text, lang).text``."""
    return normalize_for_espeak(text, lang).text
