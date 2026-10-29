"""Hybrid tokenizer: native-script characters (Indic) and/or eSpeak IPA tokens, one vocabulary.

Modes (U9 / plan §3.3):
  chr: Indic rows -> characters of textnorm.text_for_chars(text, lang); English rows -> IPA phone_tokens.
  ipa: every row -> IPA phone_tokens (from ipa/pilot_ipa.parquet).
Token strings are namespaced ("c:" chars, "p:" IPA) so a Latin char never collides with an IPA symbol.
Id 0 = pad AND the interspersed blank (Matcha convention); id 1 = <unk>.
The vocabulary is built deterministically from the training rows and saved in every checkpoint, together with the
normaliser name + NORMALIZATION_VERSION; loading refuses a different running normaliser (strict).
There is exactly ONE normaliser: the repo-root `textnorm` package (no fallback; a missing package is an ImportError).
"""
import hashlib
import json

from indic_tiny_tts import textnorm
NORMALIZER = "textnorm"
NORMALIZATION_VERSION = textnorm.NORMALIZATION_VERSION

PAD, UNK = "<blank>", "<unk>"
MODES = ("chr", "ipa")


def row_symbols(mode, lang, text, phone_tokens):
    """Namespaced symbol list for one utterance, or None if the row cannot be tokenised in this mode."""
    if mode not in MODES:
        raise ValueError(mode)
    if lang == "en" or mode == "ipa":
        if phone_tokens is None or len(phone_tokens) == 0:
            return None
        return ["p:" + t for t in phone_tokens]
    norm = textnorm.text_for_chars(text, lang)  # str (normalize_for_chars returns a NormalizationResult)
    if not norm:
        return None
    return ["c:" + ch for ch in norm]


class Tokenizer:
    def __init__(self, mode, symbols, add_blank=True):
        self.mode = mode
        self.add_blank = add_blank
        self.symbols = list(symbols)
        assert self.symbols[:2] == [PAD, UNK]
        self.id = {s: i for i, s in enumerate(self.symbols)}

    @classmethod
    def build(cls, mode, rows, add_blank=True):
        """rows: iterable of (lang, text, phone_tokens). Sorted symbol order -> deterministic ids."""
        seen = set()
        for lang, text, phones in rows:
            syms = row_symbols(mode, lang, text, phones)
            if syms:
                seen.update(syms)
        return cls(mode, [PAD, UNK] + sorted(seen), add_blank)

    def __len__(self):
        return len(self.symbols)

    def encode(self, lang, text, phone_tokens=None):
        """-> (ids list (blank-interspersed if add_blank), n_unk) or (None, 0) if untokenisable."""
        syms = row_symbols(self.mode, lang, text, phone_tokens)
        if syms is None:
            return None, 0
        ids = [self.id.get(s, 1) for s in syms]
        n_unk = sum(1 for i in ids if i == 1)
        if self.add_blank:
            out = [0] * (2 * len(ids) + 1)
            out[1::2] = ids
            ids = out
        return ids, n_unk

    def to_dict(self):
        return {"mode": self.mode, "add_blank": self.add_blank, "symbols": self.symbols,
                "normalizer": NORMALIZER, "normalization_version": NORMALIZATION_VERSION, "hash": self.hash()}

    @classmethod
    def from_dict(cls, d, strict=True):
        """strict: the running normaliser must be the one the vocabulary was built with (review B12) —
        otherwise text maps to different symbols / <unk> silently. Use strict=False only for analysis."""
        if (d.get("normalization_version"), d.get("normalizer")) != (NORMALIZATION_VERSION, NORMALIZER):
            msg = (f"vocab built with normaliser {d.get('normalizer')}@{d.get('normalization_version')}, "
                   f"running {NORMALIZER}@{NORMALIZATION_VERSION}")
            if strict:
                raise RuntimeError("tokenizer: " + msg)
            print("WARNING: " + msg, flush=True)
        tok = cls(d["mode"], d["symbols"], d.get("add_blank", True))
        if d.get("hash") not in (None, tok.hash()):
            raise RuntimeError("tokenizer: vocabulary hash mismatch")
        return tok

    def hash(self):
        blob = json.dumps([self.mode, self.add_blank, self.symbols], ensure_ascii=False).encode()
        return hashlib.sha256(blob).hexdigest()[:16]
