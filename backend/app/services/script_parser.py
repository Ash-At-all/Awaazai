"""
script_parser.py
────────────────
Advanced parser for multi-voice scripts with support for:
- @ArtistName tags (mapped to stable artist_id)
- [pause:<duration>ms] or [pause:<duration>] tokens
- Source character offsets for all segments
- Strict validation for malformed pause tags and unknown artists
- Spoken character counting matching frontend behavior
- Full Unicode and Devanagari support
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# ── Regex Definitions ──────────────────────────────────────────────
# Artist name: letters (ASCII + Devanagari), digits, underscore (1-20 chars)
ARTIST_NAME_RE = re.compile(r"^[\w\u0900-\u097F]{1,20}$", re.UNICODE)

# Speaker tag pattern: @ArtistName
TAG_RE = re.compile(r"@([\w\u0900-\u097F]{1,20})", re.UNICODE)

# Valid pause token pattern: [pause:100ms] or [pause:100]
VALID_PAUSE_RE = re.compile(r"\[pause:\s*(\d{1,5})\s*(?:ms)?\]", re.IGNORECASE)

# Catch-all for any [pause...] construct to detect syntax errors
ANY_PAUSE_RE = re.compile(r"\[pause[^\]]*\]?", re.IGNORECASE)

# Minimum and maximum allowable pause duration in milliseconds
MIN_PAUSE_MS = 50
MAX_PAUSE_MS = 10000


@dataclass
class DialogueSegment:
    """Contiguous spoken text block for an artist with source offsets."""
    type: str = "dialogue"
    artist_id: str = ""
    artist_name: str = ""
    text: str = ""
    source_start: int = 0
    source_end: int = 0


@dataclass
class PauseSegment:
    """Explicit silence pause interval with source offsets."""
    type: str = "pause"
    duration_ms: int = 300
    source_start: int = 0
    source_end: int = 0


Segment = Union[DialogueSegment, PauseSegment]


@dataclass
class ParseResult:
    """Parsed output containing ordered segments or list of errors."""
    segments: List[Segment] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    spoken_char_count: int = 0


def validate_artist_name(name: str) -> Optional[str]:
    """Return an error message if the name is invalid, else None."""
    if not name:
        return "Artist name cannot be empty."
    if len(name) > 20:
        return f"Artist name '{name}' exceeds 20 characters."
    if not ARTIST_NAME_RE.match(name):
        return (
            f"Artist name '{name}' contains invalid characters. "
            "Use letters (including Devanagari), digits, or underscore only — no spaces."
        )
    return None


def count_spoken_characters(script: str) -> int:
    """
    Count spoken characters according to the single unified rule:
    1. Strip valid @tags.
    2. Strip valid [pause:...] markers.
    3. Normalize with Unicode NFC.
    4. Strip leading/trailing whitespace.
    """
    normalized = unicodedata.normalize("NFC", script)
    no_tags = TAG_RE.sub("", normalized)
    no_pauses = VALID_PAUSE_RE.sub("", no_tags)
    return len(no_pauses.strip())


def parse_script(
    script: str,
    artists: List[Dict],
) -> ParseResult:
    """
    Parse a multi-speaker script into ordered DialogueSegment and PauseSegment items.
    
    Parameters
    ----------
    script : str
        The raw script text.
    artists : List[Dict]
        List of artist dicts with at least 'id' and 'name'.

    Returns
    -------
    ParseResult
        Containing segments and validation errors.
    """
    result = ParseResult()
    normalized_script = unicodedata.normalize("NFC", script)
    result.spoken_char_count = count_spoken_characters(normalized_script)

    if not artists:
        result.errors.append("At least one Voice Artist is required in the cast.")
        return result

    # Build name (case-insensitive) -> artist lookup
    name_to_artist: Dict[str, Dict] = {}
    for a in artists:
        lower_name = a["name"].lower()
        if lower_name in name_to_artist:
            result.errors.append(
                f"Duplicate artist name '{a['name']}' detected. Artist names must be unique (case-insensitive)."
            )
            return result
        name_to_artist[lower_name] = a

    default_artist = artists[0]

    # ── Check for Malformed Pause Syntax ──────────────────────────
    # Find all '[pause...' occurrences
    for match in ANY_PAUSE_RE.finditer(normalized_script):
        token = match.group(0)
        valid_match = VALID_PAUSE_RE.fullmatch(token)
        if not valid_match:
            result.errors.append(
                f"Invalid pause syntax '{token}' at position {match.start()}. "
                "Use format '[pause:300ms]' or '[pause:500]' with durations between 50ms and 10000ms."
            )
        else:
            ms_val = int(valid_match.group(1))
            if ms_val < MIN_PAUSE_MS or ms_val > MAX_PAUSE_MS:
                result.errors.append(
                    f"Pause duration {ms_val}ms is out of range ({MIN_PAUSE_MS}ms - {MAX_PAUSE_MS}ms)."
                )

    if result.errors:
        return result

    # ── Unified Tokenizer ──────────────────────────────────────────
    # Matches either a speaker tag or a valid pause token
    TOKEN_PATTERN = re.compile(
        r"(@[\w\u0900-\u097F]{1,20})|(\[pause:\s*\d{1,5}\s*(?:ms)?\])",
        re.IGNORECASE | re.UNICODE,
    )

    current_artist = default_artist
    last_idx = 0
    raw_items: List[Tuple[str, Union[str, int], int, int]] = []  # ('dialogue'|'pause', content, start, end)
    unknown_tags: List[Tuple[str, int]] = []

    for match in TOKEN_PATTERN.finditer(normalized_script):
        token_start, token_end = match.span()

        # Text before this token
        if token_start > last_idx:
            text_chunk = normalized_script[last_idx:token_start]
            if text_chunk.strip():
                raw_items.append(("dialogue", text_chunk, last_idx, token_start, current_artist))

        # Check which token matched
        tag_match = match.group(1)
        pause_match = match.group(2)

        if tag_match:
            tag_name = tag_match[1:]  # strip leading '@'
            tag_lower = tag_name.lower()
            if tag_lower in name_to_artist:
                current_artist = name_to_artist[tag_lower]
            else:
                unknown_tags.append((tag_name, token_start))
        elif pause_match:
            p_val = int(VALID_PAUSE_RE.match(pause_match).group(1))
            raw_items.append(("pause", p_val, token_start, token_end, None))

        last_idx = token_end

    # Trailing text after final token
    if last_idx < len(normalized_script):
        trailing_text = normalized_script[last_idx:]
        if trailing_text.strip():
            raw_items.append(("dialogue", trailing_text, last_idx, len(normalized_script), current_artist))

    # ── Report Unknown Tags ────────────────────────────────────────
    if unknown_tags:
        unique_unknowns = []
        for name, _ in unknown_tags:
            if name not in unique_unknowns:
                unique_unknowns.append(name)
        result.errors.append(
            f"Unknown voice artist(s) in script: {', '.join('@' + u for u in unique_unknowns)}. "
            "Please add them to your cast or fix the tag spelling."
        )
        return result

    if not raw_items:
        result.errors.append("Script contains no dialogue or pause content to synthesize.")
        return result

    # ── Merge Consecutive Dialogue Segments for Same Artist ───────
    merged_segments: List[Segment] = []

    for item in raw_items:
        kind = item[0]
        if kind == "pause":
            merged_segments.append(
                PauseSegment(
                    duration_ms=item[1],
                    source_start=item[2],
                    source_end=item[3],
                )
            )
        elif kind == "dialogue":
            text_content = item[1].strip()
            artist = item[4]
            start_off = item[2]
            end_off = item[3]

            if not text_content:
                continue

            # Merge if the previous segment was dialogue by the same artist
            if merged_segments and isinstance(merged_segments[-1], DialogueSegment) and merged_segments[-1].artist_id == artist["id"]:
                prev = merged_segments[-1]
                prev.text = prev.text + " " + text_content
                prev.source_end = end_off
            else:
                merged_segments.append(
                    DialogueSegment(
                        artist_id=artist["id"],
                        artist_name=artist["name"],
                        text=text_content,
                        source_start=start_off,
                        source_end=end_off,
                    )
                )

    result.segments = merged_segments
    return result
