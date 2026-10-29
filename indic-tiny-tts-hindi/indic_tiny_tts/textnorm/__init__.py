"""textnorm: shared text normalization for the Indic TTS project (NORMALIZATION_VERSION "4").

Pure Python, standard library only. It never imports eSpeak, ``phonemes`` or
anything GPL (a test enforces this), so it can ship in the on-device runtime.
Users: ``phonemes/`` (eSpeak IPA pipeline) and ``tts/frontend/canon.py``
(character-input model).

Languages: ``SUPPORTED_LANGS`` = as bn en gu hi kn ml mr or pa ta te.

API
---
``normalize_for_chars(text, lang) -> NormalizationResult``
    The character-path canonical form ``text_char`` (stored, and the input of
    the character tokenizer).
``normalize_for_espeak(text, lang) -> NormalizationResult``
    ``normalize_for_chars`` + the eSpeak-only layer -> ``text_espeak``
    (internal: fed to eSpeak, never used as character input, never re-NFC'd).
``espeak_layer(text_char, lang) -> (text_espeak, steps)``
    The eSpeak-only layer alone, for callers that already hold ``text_char``.
``text_for_chars`` / ``text_for_espeak``
    String-only wrappers.
``cardinal(n, lang)``, ``read_digits(digits, lang)``, ``verbalize_digits(text, lang)``
    The digit verbalizer (see ``textnorm.numbers`` for the token rules).

``NormalizationResult`` fields: ``text``, ``lang``, ``normalization_applied``
(ordered list of step names that changed the text), ``latin_spans`` (list of
Latin-script runs left in the text; always ``[]`` for ``en``), ``flags``
(subset of ``FLAGS``); properties ``latin_gloss_removed``,
``numeric_unsupported``, ``latin_gloss_kept``, ``nonspeech_tag_removed``,
``numeric_reading_convention`` (v4). ``str(result)`` is ``result.text``.

Character path (``normalize_for_chars``), steps in order (``CHAR_STEPS``)
-------------------------------------------------------------------------
1. ``nfc``: NFC + whitespace collapse, byte-identical to
   ``data_prep.prepare.normalize_text`` (minus its input validation).
2. ``ml_chillu`` (ml): legacy ``ന്‍റ`` -> ``ന്റ``, then legacy chillu
   (consonant + virama + ZWJ) -> atomic U+0D7A-0D7F (``ML_LEGACY_CHILLU``).
3. ``zwj_removed`` (all languages), then ``zwnj_removed``, then (v2)
   ``zwsp_bom_removed``: U+200B, U+FEFF, U+2060, U+00AD (``INVISIBLE_CHARS``).
4. ``as_ra`` (as): Bengali র U+09B0 -> Assamese ৰ U+09F0.
   (v2) ``bn_as_letters`` (bn): Assamese ৰ/ৱ -> র/ব (``BN_AS_LETTERS``).
   (v2) ``hi_nukta_matra`` (hi): a nukta is kept only right after क ख ग ज ड ढ फ;
   one typed after a vowel sign of such a consonant moves back (``बडे़`` ->
   ``बड़े``), any other (doubled, stray) is dropped; legacy ``ा+ॅ``/``ॅ+ा`` ->
   ``ॉ``, ``े+ा`` -> ``ो``, ``ा+ौ`` -> ``ौ`` (``HI_TWO_SIGN_VOWELS``); a repeated
   sign collapses; ``ीे`` -> ``ी`` and ``ेै`` -> ``े``; other sign pairs stay
   (ambiguous; the row stays blocked downstream).
   (v3) text-typo repairs (moved from the eSpeak-only layer of ``phonemes``):
   ``deva_vowel_signs`` (mr: the vowel-sign part of the hi rule, not its nukta
   part), ``gu_two_sign_vowels`` (``ા+ૅ`` -> ``ૉ``), ``kn_long_o_sign``
   (``ೂ+ೕ`` -> ``ೋ``), ``or_au_sign`` (``ୋ+ୖ`` -> ``ୌ``), ``ta_au_letter``
   (``ஓ+ௗ`` -> ``ஔ``), ``pa_dda_nukta_to_rra`` (``ਡ+਼`` -> ``ੜ``)
   (``TYPO_SIGN_PAIRS``), ``as_stray_nukta_dropped`` (as: a nukta not right after
   ড ঢ য), ``repeated_vowel_sign`` (gu te kn or pa as, ``REPEATED_SIGN_LANGS``:
   an exactly repeated vowel sign collapses). Voice-specific eSpeak workarounds
   (mr/gu/kn nukta drop, te arasunna, mr ॲ) stay in ``phonemes``.
5. (v2) ``nonspeech_tag_removed`` (all languages): bracketed event tags
   (``NONSPEECH_TAGS`` such as ``[noise]``, ``(laugh)``, and any
   ``[word_word]``) are removed wherever they are. Also a flag.
   ``latin_gloss_removed``: a bracketed Latin-only gloss directly after a
   native word is removed, repeated to a fixpoint (``শব্দ (a) (b)`` -> ``শব্দ``):
   ``স্মাৰ্টফোন [smart phone]`` -> ``স্মাৰ্টফোন``. Brackets with other content
   are kept. Also a flag. Per language (D13, ``GLOSS_KEEP_LANGS``): in pa and
   kn glosses are spoken, so they are KEPT (Latin span; flag
   ``latin_gloss_kept``); en never strips; every other language strips.
   (v3) ``as_latin_bracket_removed`` (as): any other bracketed span with a Latin
   letter (after punctuation, row-initial, with ``+`` or digits) is removed if it
   has no Bengali-script letter or digit as written in the source (it runs
   before the digits); flag ``latin_gloss_removed``. ``(৫ km)`` and
   ``(যাক BJP বুলি ...)`` are kept.
6. ``pa_latin_i_danda`` (pa) and (v2) ``hi_latin_i_danda`` (hi): a standalone
   Latin ``I`` after a Gurmukhi letter (hi: attached to a Devanagari letter,
   ``हैI``) and not followed by Latin text, ``.``, ``-``, an apostrophe or a
   digit -> ``।``. (v3) ``or_latin_i_danda`` (or): a text-final Latin ``I``
   after an Odia letter -> ``।``.
6b. (v4) ``en_ampersand`` (en): ``&`` -> ``and`` with single spaces (``J&K`` ->
   ``J and K``). Not in other languages (an ``&`` between native words may be
   read in either language; it stays a blocking symbol on the eSpeak side).
   R6b: HTML character references with a semicolon (``&amp;``, ``&nbsp;``) are
   decoded first, and fullwidth ``＆`` / small ``﹠`` count as ``&``. ``AT&T``
   becomes ``AT and T`` (0 corpus rows).
7. ``digits_verbalized``: ASCII and native digits -> words in ``lang`` (Indian
   lakh/crore system for Indic; years; decimals/percent/rupee for en hi bn ta).
   Forms it cannot read (times, dates, other languages' decimals ...) are left
   unchanged and flagged ``numeric_unsupported``. (v4) For as kn or pa ta, such a
   token is read by a per-language corpus convention where one exists (dates,
   clock times, decimals, percent, ``$`` / ``ଟ.`` amounts; ``textnorm.numbers``)
   and flagged ``numeric_reading_convention`` (INFORMATIONAL: not a blocking
   flag; the reading follows the corpus convention, not a check of the clip).
8. Latin-span detection (no text change) -> ``latin_spans``.

After every step the text is re-NFC'd and whitespace-collapsed. Danda (।) is
kept. Invariant: ``unicodedata.normalize("NFC", text_char) == text_char``, and
``normalize_for_chars`` is idempotent.

Frozen canonical form (Q1, agreed with the mini-TTS session 2026-10-15)
------------------------------------------------------------------------
Nukta letters are stored DECOMPOSED = plain NFC (consonant + U+093C / U+09BC /
U+0A3C / U+0B3C). The precomposed letters in ``COMPOSITION_EXCLUSION_CHARS``
are Unicode composition exclusions, so any NFC/NFKC call (tokenizers,
``datasets``, browsers, IMEs) would decompose them anyway.

eSpeak layer (``espeak_layer``), steps in order (``ESPEAK_STEPS``)
-------------------------------------------------------------------
1. ``nukta_recomposed``: every decomposed composition-exclusion sequence ->
   its precomposed codepoint (``NUKTA_RECOMPOSE``; Devanagari U+0958-095F,
   Bengali 09DC/09DD/09DF, Gurmukhi 0A33/0A36/0A59-0A5B/0A5E, Odia 0B5C/0B5D).
2. ``as_rra_to_ra`` (as): ড় / ঢ় -> ৰ (``AS_ESPEAK_RRA``).
3. ``or_wa_to_va`` (or): ୱ -> ଵ (``OR_ESPEAK_WA``).

Version history
---------------
"1" (2026-10-16, f3a8e915): initial contract.
"2" (2026-10-16, D13/D14): new char steps ``zwsp_bom_removed``,
``bn_as_letters``, ``hi_nukta_matra``, ``nonspeech_tag_removed``,
``hi_latin_i_danda``; gloss removal runs to a fixpoint (idempotent); pa/kn
keep glosses (``latin_gloss_kept``). New flags ``latin_gloss_kept``,
``nonspeech_tag_removed``. API otherwise unchanged; the Q1 canonical form is
unchanged.
"3" (2026-10-16, D16): new char steps ``deva_vowel_signs`` (mr),
``gu_two_sign_vowels``, ``kn_long_o_sign``, ``or_au_sign``, ``ta_au_letter``,
``pa_dda_nukta_to_rra``, ``as_stray_nukta_dropped``, ``repeated_vowel_sign``
(text-typo repairs that ``phonemes`` applied eSpeak-side only up to its
ESPEAK_FIXES_VERSION 3), ``as_latin_bracket_removed``, ``or_latin_i_danda``.
New tables ``TYPO_SIGN_PAIRS``, ``AS_NUKTA_BASES``, ``INDIC_VOWEL_SIGNS``,
``REPEATED_SIGN_LANGS``. No new flag, no signature change. Digits unchanged:
leading zeros and Indic suffixes were already read; dates, times and as/or
decimals/percent stay ``numeric_unsupported`` (their reading is ambiguous).
"4" (2026-10-16, D17): numeric reading conventions (``numbers.CONVENTION_LANGS``
= as kn or pa ta) for tokens that "3" left ``numeric_unsupported``; new
informational flag ``numeric_reading_convention`` (+ result property). Only
tokens that were unsupported change. Also (R6, before the v4 release) the en
char step ``en_ampersand`` (``&`` -> ``and``); no other output changes. R6b
(still "4": no existing row changes): ``en_ampersand`` also decodes HTML
character references and reads fullwidth/small ampersands.

Tests: ``python -m pytest tests/textnorm -q`` from the repo root.
Third-party data: Indic number words derive from AI4Bharat indic_numtowords
(MIT), see ``LICENSE-indic_numtowords``.
"""

from .core import (
    AS_ESPEAK_RRA,
    AS_NUKTA_BASES,
    AS_RA,
    BN_AS_LETTERS,
    GLOSS_KEEP_LANGS,
    HI_NUKTA_BASES,
    INDIC_VOWEL_SIGNS,
    INVISIBLE_CHARS,
    NONSPEECH_TAGS,
    CHAR_STEPS,
    COMPOSITION_EXCLUSION_CHARS,
    ESPEAK_STEPS,
    FLAGS,
    ML_LEGACY_CHILLU,
    ML_NTA_LEGACY,
    NORMALIZATION_VERSION,
    NUKTA_RECOMPOSE,
    OR_ESPEAK_WA,
    REPEATED_SIGN_LANGS,
    SUPPORTED_LANGS,
    TYPO_SIGN_PAIRS,
    NormalizationResult,
    espeak_layer,
    find_latin_spans,
    nfc_whitespace,
    normalize_for_chars,
    normalize_for_espeak,
    text_for_chars,
    text_for_espeak,
)
from .numbers import cardinal, read_digits, verbalize_digits

__all__ = [
    "AS_ESPEAK_RRA",
    "AS_NUKTA_BASES",
    "AS_RA",
    "BN_AS_LETTERS",
    "GLOSS_KEEP_LANGS",
    "HI_NUKTA_BASES",
    "INDIC_VOWEL_SIGNS",
    "INVISIBLE_CHARS",
    "NONSPEECH_TAGS",
    "CHAR_STEPS",
    "COMPOSITION_EXCLUSION_CHARS",
    "ESPEAK_STEPS",
    "FLAGS",
    "ML_LEGACY_CHILLU",
    "ML_NTA_LEGACY",
    "NORMALIZATION_VERSION",
    "NUKTA_RECOMPOSE",
    "OR_ESPEAK_WA",
    "REPEATED_SIGN_LANGS",
    "SUPPORTED_LANGS",
    "TYPO_SIGN_PAIRS",
    "NormalizationResult",
    "cardinal",
    "espeak_layer",
    "find_latin_spans",
    "nfc_whitespace",
    "normalize_for_chars",
    "normalize_for_espeak",
    "read_digits",
    "text_for_chars",
    "text_for_espeak",
    "verbalize_digits",
]
