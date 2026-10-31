"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Users, Plus, X, Pencil, Check, Sparkles, Trash2,
  ChevronDown, AlertTriangle, Download, Play, FileText, Layers,
  Upload, RotateCcw, Clock,
} from "lucide-react";
import { Voice, ScriptArtist, ScriptTTSResponse } from "@/types";
import AudioPlayer from "@/components/AudioPlayer";

// ── Constants ────────────────────────────────────────────────────
const MAX_ARTISTS = 6;
const MAX_CHARS = 2500;
const ARTIST_COLORS = [
  "bg-indigo-500",
  "bg-rose-500",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-purple-500",
  "bg-cyan-500",
];
const HIGHLIGHT_COLORS = [
  "bg-indigo-100 text-indigo-700",
  "bg-rose-100 text-rose-700",
  "bg-emerald-100 text-emerald-700",
  "bg-amber-100 text-amber-700",
  "bg-purple-100 text-purple-700",
  "bg-cyan-100 text-cyan-700",
];
const CHIP_RING_COLORS = [
  "ring-indigo-400",
  "ring-rose-400",
  "ring-emerald-400",
  "ring-amber-400",
  "ring-purple-400",
  "ring-cyan-400",
];
const ARTIST_NAME_RE = /^[\w\u0900-\u097F]{1,20}$/;

const STORAGE_KEY = "awaazai_script_cast";
const SCRIPT_STORAGE_KEY = "awaazai_script_text";

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const DEFAULT_SCRIPT = `@Rohan: अरे प्रिया, सुना तुमने? आवाज़ एआई अब लाइव हो गया है!
[pause:300ms]
@Priya: सच में? मुझे तो यकीन ही नहीं हो रहा। क्या इसमें हिंदी और हिंग्लिश दोनों में नेचुरल आवाज़ें हैं?
[pause:400ms]
@Rohan: बिल्कुल! यह मल्टी-स्पीकर पॉडकास्ट और स्टोरीटेलिंग के लिए एकदम सही है।`;

const DEFAULT_VOICES: Voice[] = [
  {
    id: "neeraj",
    display_name: "Neeraj Sharma",
    gender: "male",
    age_style: "middle aged",
    tone: "news",
    language: "Hindi",
    accent: "Delhi Urban",
    description: "Authoritative, crisp, and deep voice ideal for news, documentaries, and explainers.",
    sample_text: "नमस्कार, आवाज़ एआई में आपका स्वागत है।",
    sample_url: "/api/voices/neeraj/sample",
    license_type: "Exclusive License",
    consent_proof_url: "",
    is_published: true,
    avatar_color: "from-blue-600 to-indigo-800",
    provider: "mock",
    provider_voice_id: "neeraj",
  },
  {
    id: "priya",
    display_name: "Priya Sen",
    gender: "female",
    age_style: "young adult",
    tone: "storytelling",
    language: "Hindi",
    accent: "Varanasi Pure",
    description: "Warm, emotional, and expressive voice designed for audiobooks, narratives, and poetry.",
    sample_text: "एक समय की बात है, जब हिमालय की वादियों में एक शांत नदी बहती थी।",
    sample_url: "/api/voices/priya/sample",
    license_type: "Voice Actor Agreement",
    consent_proof_url: "",
    is_published: true,
    avatar_color: "from-rose-500 to-pink-700",
    provider: "mock",
    provider_voice_id: "priya",
  },
  {
    id: "aarav",
    display_name: "Aarav Mehta",
    gender: "male",
    age_style: "young adult",
    tone: "energetic",
    language: "Hinglish",
    accent: "Mumbai Tech",
    description: "Energetic, modern Hinglish voice perfect for podcasts, tech reviews, and startup videos.",
    sample_text: "Hey everyone! Welcome back to the channel.",
    sample_url: "/api/voices/aarav/sample",
    license_type: "Standard Commercial",
    consent_proof_url: "",
    is_published: true,
    avatar_color: "from-emerald-500 to-teal-700",
    provider: "mock",
    provider_voice_id: "aarav",
  },
  {
    id: "ananya",
    display_name: "Ananya Roy",
    gender: "female",
    age_style: "young adult",
    tone: "calm",
    language: "Hinglish",
    accent: "Bengaluru Conversational",
    description: "Soothing, friendly, and articulate tone suited for customer support, meditation, and chats.",
    sample_text: "Hello! Main aapki help kaise kar sakti hoon?",
    sample_url: "/api/voices/ananya/sample",
    license_type: "Synthetic Royalty-Free",
    consent_proof_url: "",
    is_published: true,
    avatar_color: "from-purple-500 to-violet-700",
    provider: "mock",
    provider_voice_id: "ananya",
  },
  {
    id: "vikram",
    display_name: "Vikram Rathore",
    gender: "male",
    age_style: "senior",
    tone: "storytelling",
    language: "Hindi",
    accent: "Rajasthan Deep",
    description: "Resonant, baritone elder voice for historical tales, mythologies, and cinematic narration.",
    sample_text: "सदियों पहले इस धरती पर वीरों की गाथाएं गूंजती थीं।",
    sample_url: "/api/voices/vikram/sample",
    license_type: "Exclusive License",
    consent_proof_url: "",
    is_published: true,
    avatar_color: "from-amber-600 to-yellow-800",
    provider: "mock",
    provider_voice_id: "vikram",
  },
  {
    id: "kavita",
    display_name: "Kavita Rao",
    gender: "female",
    age_style: "middle aged",
    tone: "news",
    language: "Hindi",
    accent: "Lucknow Refined",
    description: "Refined and clear diction suitable for formal presentations, edtech, and announcements.",
    sample_text: "भारतीय विज्ञान संस्थान द्वारा आयोजित इस विशेष सत्र में आप सभी का स्वागत है।",
    sample_url: "/api/voices/kavita/sample",
    license_type: "Voice Actor Agreement",
    consent_proof_url: "",
    is_published: true,
    avatar_color: "from-cyan-600 to-blue-700",
    provider: "mock",
    provider_voice_id: "kavita",
  },
  {
    id: "ishaan",
    display_name: "Ishaan Verma",
    gender: "male",
    age_style: "young adult",
    tone: "conversational",
    language: "Hinglish",
    accent: "Delhi Youth",
    description: "Casual, buddy-like Hinglish tone great for casual dialogue, gaming, and lifestyle content.",
    sample_text: "Arre yaar, weekend pe chalte hain movie dekhne.",
    sample_url: "/api/voices/ishaan/sample",
    license_type: "Standard Commercial",
    consent_proof_url: "",
    is_published: true,
    avatar_color: "from-orange-500 to-red-600",
    provider: "mock",
    provider_voice_id: "ishaan",
  },
  {
    id: "meera",
    display_name: "Meera Joshi",
    gender: "female",
    age_style: "young adult",
    tone: "energetic",
    language: "Hinglish",
    accent: "Pune Urban",
    description: "Upbeat, lively and engaging voice for social media reels, ads, and entertainment.",
    sample_text: "Check out this super cool new feature!",
    sample_url: "/api/voices/meera/sample",
    license_type: "Synthetic Royalty-Free",
    consent_proof_url: "",
    is_published: true,
    avatar_color: "from-fuchsia-500 to-pink-600",
    provider: "mock",
    provider_voice_id: "meera",
  },
];

// ── Helpers ──────────────────────────────────────────────────────
function loadCast(): ScriptArtist[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return [];
}
function saveCast(artists: ScriptArtist[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(artists));
  } catch {}
}

function makeId() {
  return "a" + Math.random().toString(36).slice(2, 8);
}

function spokenCharCount(script: string) {
  // Strip valid @tags and [pause:...] markers to match backend count_spoken_characters
  return script
    .replace(/@[\w\u0900-\u097F]{1,20}/g, "")
    .replace(/\[pause:\s*\d{1,5}\s*(?:ms)?\]/gi, "")
    .trim().length;
}

// Find @tags and [pause:...] tokens in script text and return tagged spans for preview
function tagify(
  script: string,
  artists: ScriptArtist[]
): { text: string; className: string; isTag: boolean }[] {
  const result: { text: string; className: string; isTag: boolean }[] = [];
  const nameMap = new Map<string, number>();
  artists.forEach((a, i) => nameMap.set(a.name.toLowerCase(), i));

  // Matches either @ArtistName or [pause:...]
  const regex = /(@[\w\u0900-\u097F]{1,20})|(\[pause:\s*\d{1,5}\s*(?:ms)?\])|(\[pause[^\]]*\]?)/gi;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(script)) !== null) {
    if (match.index > last) {
      result.push({ text: script.slice(last, match.index), className: "", isTag: false });
    }

    const tagMatch = match[1];
    const validPause = match[2];
    const invalidPause = match[3];

    if (tagMatch) {
      const name = tagMatch.slice(1);
      const idx = nameMap.get(name.toLowerCase());
      if (idx !== undefined) {
        result.push({
          text: tagMatch,
          className: HIGHLIGHT_COLORS[idx % HIGHLIGHT_COLORS.length] + " px-1 rounded font-semibold",
          isTag: true,
        });
      } else {
        result.push({
          text: tagMatch,
          className: "bg-red-100 text-red-600 px-1 rounded font-semibold line-through",
          isTag: true,
        });
      }
    } else if (validPause) {
      result.push({
        text: validPause,
        className: "bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-mono text-xs font-semibold border border-purple-200",
        isTag: true,
      });
    } else if (invalidPause) {
      result.push({
        text: invalidPause,
        className: "bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-mono text-xs font-semibold border border-red-300",
        isTag: true,
      });
    }

    last = match.index + match[0].length;
  }
  if (last < script.length) {
    result.push({ text: script.slice(last), className: "", isTag: false });
  }
  return result;
}

function unknownTags(script: string, artists: ScriptArtist[]): string[] {
  const names = new Set(artists.map((a) => a.name.toLowerCase()));
  const regex = /@([\w\u0900-\u097F]{1,20})/g;
  const unknown: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = regex.exec(script)) !== null) {
    if (!names.has(m[1].toLowerCase()) && !unknown.includes(m[1])) {
      unknown.push(m[1]);
    }
  }
  return unknown;
}

// ── Main Component ───────────────────────────────────────────────
export default function ConversationPage() {
  const [voices, setVoices] = useState<Voice[]>(DEFAULT_VOICES);
  const [artists, setArtists] = useState<ScriptArtist[]>([]);
  const [script, setScript] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [panelArtistId, setPanelArtistId] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<ScriptTTSResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [autocomplete, setAutocomplete] = useState<{ visible: boolean; x: number; y: number; filter: string }>({
    visible: false, x: 0, y: 0, filter: "",
  });
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Load voices ──────────────────────────────────────────────
  useEffect(() => {
    fetch("/api/voices")
      .then((r) => r.json())
      .then((data: Voice[]) => {
        if (Array.isArray(data) && data.length > 0) {
          setVoices(data);
        }
      })
      .catch((err) => console.log("Using default voice roster:", err));
  }, []);

  // ── Load persisted cast & script ─────────────────────────────
  useEffect(() => {
    const saved = loadCast();
    if (saved.length > 0) {
      setArtists(saved);
    } else {
      setArtists([
        { id: "a1", name: "Rohan", voice_id: "aarav", speed: 0, stability: 0.5, color: ARTIST_COLORS[0] },
        { id: "a2", name: "Priya", voice_id: "priya", speed: 0, stability: 0.5, color: ARTIST_COLORS[1] },
      ]);
    }

    try {
      const savedScript = localStorage.getItem(SCRIPT_STORAGE_KEY);
      if (savedScript && savedScript.trim()) {
        setScript(savedScript);
      } else {
        setScript(DEFAULT_SCRIPT);
      }
    } catch {}
  }, []);

  // ── Persist cast on change ───────────────────────────────────
  useEffect(() => {
    if (artists.length > 0) saveCast(artists);
  }, [artists]);

  // ── Persist script draft on change ───────────────────────────
  useEffect(() => {
    if (script) {
      try {
        localStorage.setItem(SCRIPT_STORAGE_KEY, script);
      } catch {}
    }
  }, [script]);

  // ── Autocomplete filtered list ───────────────────────────────
  const filteredArtists = useMemo(() => {
    if (!autocomplete.filter) return artists;
    return artists.filter((a) =>
      a.name.toLowerCase().startsWith(autocomplete.filter.toLowerCase())
    );
  }, [artists, autocomplete.filter]);

  // ── Spoken char count ────────────────────────────────────────
  const charCount = useMemo(() => spokenCharCount(script), [script]);
  const unknowns = useMemo(() => unknownTags(script, artists), [script, artists]);

  // ── Add artist ───────────────────────────────────────────────
  const addArtist = () => {
    if (artists.length >= MAX_ARTISTS) return;
    const idx = artists.length;
    const defaultVoice = voices.length > 0 ? voices[idx % voices.length].id : "neeraj";
    const newArtist: ScriptArtist = {
      id: makeId(),
      name: `Artist${idx + 1}`,
      voice_id: defaultVoice,
      speed: 0,
      stability: 0.5,
      color: ARTIST_COLORS[idx % ARTIST_COLORS.length],
    };
    setArtists([...artists, newArtist]);
    setPanelArtistId(newArtist.id);
  };

  // ── Delete artist ────────────────────────────────────────────
  const deleteArtist = (id: string) => {
    setArtists(artists.filter((a) => a.id !== id));
    if (panelArtistId === id) setPanelArtistId(null);
  };

  // ── Rename artist ────────────────────────────────────────────
  const startRename = (a: ScriptArtist) => {
    setEditingId(a.id);
    setEditName(a.name);
    setNameError(null);
  };

  const commitRename = () => {
    if (!editingId) return;
    const trimmed = editName.trim();
    if (!ARTIST_NAME_RE.test(trimmed)) {
      setNameError("1-20 chars: letters, digits, underscore, Devanagari. No spaces.");
      return;
    }
    const dup = artists.find(
      (a) => a.id !== editingId && a.name.toLowerCase() === trimmed.toLowerCase()
    );
    if (dup) {
      setNameError(`Name "${trimmed}" is already used by another artist.`);
      return;
    }
    const oldName = artists.find((a) => a.id === editingId)?.name;
    setArtists(
      artists.map((a) => (a.id === editingId ? { ...a, name: trimmed } : a))
    );
    // Update @tags in script (Unicode-safe word boundary)
    if (oldName && oldName !== trimmed) {
      setScript((prev) =>
        prev.replace(new RegExp(`@${escapeRegex(oldName)}(?=[\\s:,\\[\\].!?-]|$)`, "gu"), `@${trimmed}`)
      );
    }
    setEditingId(null);
    setNameError(null);
  };

  // ── Project JSON Export / Import / Pause Helpers ─────────────
  const handleExportProject = () => {
    const projectData = {
      app: "AwaazAI",
      version: "1.0",
      exported_at: new Date().toISOString(),
      cast: artists,
      script: script,
    };
    const blob = new Blob([JSON.stringify(projectData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `awaazai_project_${Date.now()}.awaaz.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleImportProject = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const data = JSON.parse(text);
        if (!data || typeof data !== "object") throw new Error("Invalid project JSON");
        if (!Array.isArray(data.cast) || typeof data.script !== "string") {
          throw new Error("Project JSON must contain 'cast' array and 'script' text.");
        }
        const validCast: ScriptArtist[] = data.cast.slice(0, MAX_ARTISTS).map((c: any, i: number) => ({
          id: String(c.id || makeId()),
          name: String(c.name || `Artist${i + 1}`).trim().slice(0, 20),
          voice_id: String(c.voice_id || "neeraj"),
          speed: typeof c.speed === "number" ? Math.max(-2, Math.min(3, c.speed)) : 0,
          stability: typeof c.stability === "number" ? Math.max(0, Math.min(1, c.stability)) : 0.5,
          color: ARTIST_COLORS[i % ARTIST_COLORS.length],
        }));
        setArtists(validCast);
        setScript(data.script);
        setErrorMsg(null);
      } catch (err: any) {
        setErrorMsg(`Failed to import project: ${err.message}`);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleResetToSample = () => {
    if (confirm("Reset current cast and script back to default sample dialogue?")) {
      setArtists([
        { id: "a1", name: "Rohan", voice_id: "aarav", speed: 0, stability: 0.5, color: ARTIST_COLORS[0] },
        { id: "a2", name: "Priya", voice_id: "priya", speed: 0, stability: 0.5, color: ARTIST_COLORS[1] },
      ]);
      setScript(DEFAULT_SCRIPT);
    }
  };

  const insertPause = (ms: number) => {
    const ta = textareaRef.current;
    const token = ` [pause:${ms}ms] `;
    if (!ta) {
      setScript((prev) => prev + token);
      return;
    }
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const before = script.substring(0, start);
    const after = script.substring(end);
    setScript(before + token + after);
    setTimeout(() => {
      ta.focus();
      const nextPos = start + token.length;
      ta.setSelectionRange(nextPos, nextPos);
    }, 0);
  };

  // ── Update artist config ─────────────────────────────────────
  const updateArtist = (id: string, patch: Partial<ScriptArtist>) => {
    setArtists(artists.map((a) => (a.id === id ? { ...a, ...patch } : a)));
  };

  // ── Insert @tag from autocomplete ────────────────────────────
  const insertTag = (name: string) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const pos = ta.selectionStart;
    // Find the @ that triggered autocomplete
    const before = script.slice(0, pos);
    const atIdx = before.lastIndexOf("@");
    if (atIdx === -1) return;
    const after = script.slice(pos);
    const newScript = before.slice(0, atIdx) + `@${name} ` + after;
    setScript(newScript);
    setAutocomplete({ visible: false, x: 0, y: 0, filter: "" });
    // Restore focus
    setTimeout(() => {
      ta.focus();
      const newPos = atIdx + name.length + 2;
      ta.setSelectionRange(newPos, newPos);
    }, 0);
  };

  // ── Handle textarea input ────────────────────────────────────
  const handleScriptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setScript(val);

    // Autocomplete trigger: detect @ at cursor
    const pos = e.target.selectionStart;
    const textBefore = val.slice(0, pos);
    const atMatch = textBefore.match(/@([\w\u0900-\u097F]*)$/);
    if (atMatch) {
      const rect = e.target.getBoundingClientRect();
      setAutocomplete({
        visible: true,
        x: rect.left + 16,
        y: rect.bottom + 4,
        filter: atMatch[1],
      });
    } else {
      setAutocomplete({ visible: false, x: 0, y: 0, filter: "" });
    }
  };

  // ── Handle textarea key down (for autocomplete navigation) ──
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (autocomplete.visible && e.key === "Escape") {
      setAutocomplete({ visible: false, x: 0, y: 0, filter: "" });
    }
    if (autocomplete.visible && e.key === "Tab" && filteredArtists.length > 0) {
      e.preventDefault();
      insertTag(filteredArtists[0].name);
    }
  };

  // ── Close autocomplete on blur ───────────────────────────────
  const handleBlur = () => {
    // Delay so click on autocomplete item registers first
    setTimeout(() => setAutocomplete({ visible: false, x: 0, y: 0, filter: "" }), 200);
  };

  // ── Generate ─────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (artists.length === 0) {
      setErrorMsg("Add at least one Voice Artist before generating.");
      return;
    }
    if (unknowns.length > 0) {
      setErrorMsg(
        `Unknown artist(s) in script: ${unknowns.map((u) => "@" + u).join(", ")}. Add them to your cast or fix the spelling.`
      );
      return;
    }
    if (charCount === 0) {
      setErrorMsg("Script has no spoken text.");
      return;
    }
    if (charCount > MAX_CHARS) {
      setErrorMsg(`Spoken text exceeds ${MAX_CHARS} characters (currently ${charCount}).`);
      return;
    }

    setIsGenerating(true);
    setErrorMsg(null);
    setResult(null);

    try {
      const res = await fetch("/api/tts/script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          artists: artists.map((a) => ({
            id: a.id,
            name: a.name,
            voice_id: a.voice_id,
            speed: a.speed,
            stability: a.stability,
          })),
          script,
          audio_format: "wav",
        }),
      });
      if (!res.ok) {
        let msg = "Generation failed";
        try {
          const err = await res.json();
          msg = err.detail || msg;
        } catch {
          if (res.status === 500 || res.status === 502 || res.status === 503 || res.status === 504) {
            msg = "Backend server is offline or unreachable. Please start the FastAPI backend server on port 8000 (uvicorn app.main:app --port 8000).";
          } else {
            msg = `Request failed with status ${res.status}`;
          }
        }
        throw new Error(msg);
      }
      const data: ScriptTTSResponse = await res.json();
      setResult(data);
    } catch (err: any) {
      setErrorMsg(err.message || "An error occurred");
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Currently-editing panel artist ───────────────────────────
  const panelArtist = artists.find((a) => a.id === panelArtistId);

  // ── Tagged preview spans ─────────────────────────────────────
  const taggedSpans = useMemo(() => tagify(script, artists), [script, artists]);

  return (
    <div className="relative overflow-hidden min-h-screen">
      {/* Background */}
      <div className="gradient-mesh absolute inset-0 -z-10" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[500px] rounded-full bg-gradient-to-br from-indigo-400/20 via-purple-400/15 to-pink-400/15 blur-[120px] -z-10 pointer-events-none" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/60 backdrop-blur-sm border border-indigo-200/60 text-indigo-600 text-xs font-semibold uppercase tracking-wider mb-3 shadow-sm">
            <Users className="w-3 h-3" />
            Multi-Voice Script Studio
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 tracking-tight">
            Conversation <span className="gradient-text">Studio</span>
          </h1>
          <p className="text-gray-500 text-base mt-2 max-w-2xl">
            Build a cast of Voice Artists, write your script with @tags, and generate a single combined audio file.
          </p>
        </div>

        {/* ── Cast bar ──────────────────────────────────────────── */}
        <div className="mb-6 rounded-2xl bg-white/70 backdrop-blur-xl border border-white/80 shadow-lg shadow-purple-500/5 p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Voice Artists
            </span>
            <span className="text-[10px] text-gray-400 font-mono">
              {artists.length}/{MAX_ARTISTS}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {artists.map((a, idx) => (
              <div key={a.id} className="relative">
                {editingId === a.id ? (
                  /* Inline rename */
                  <div className="flex items-center gap-1">
                    <input
                      autoFocus
                      value={editName}
                      onChange={(e) => { setEditName(e.target.value); setNameError(null); }}
                      onKeyDown={(e) => { if (e.key === "Enter") commitRename(); if (e.key === "Escape") { setEditingId(null); setNameError(null); } }}
                      className={`w-28 px-2 py-1.5 text-sm rounded-lg border ${nameError ? "border-red-400 bg-red-50" : "border-indigo-300 bg-white"} focus:outline-none focus:ring-2 focus:ring-indigo-400/50`}
                    />
                    <button onClick={commitRename} className="p-1 rounded hover:bg-green-100 text-green-600"><Check className="w-4 h-4" /></button>
                    <button onClick={() => { setEditingId(null); setNameError(null); }} className="p-1 rounded hover:bg-gray-100 text-gray-400"><X className="w-4 h-4" /></button>
                  </div>
                ) : (
                  /* Artist chip */
                  <button
                    onClick={() => setPanelArtistId(panelArtistId === a.id ? null : a.id)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold transition-all border ${
                      panelArtistId === a.id
                        ? `bg-white shadow-md ring-2 ${CHIP_RING_COLORS[idx % CHIP_RING_COLORS.length]} border-transparent text-gray-900`
                        : "bg-white/60 border-gray-200 text-gray-700 hover:bg-white hover:shadow-sm"
                    }`}
                  >
                    <span className={`w-3 h-3 rounded-full ${ARTIST_COLORS[idx % ARTIST_COLORS.length]}`} />
                    {a.name}
                    <Pencil
                      className="w-3 h-3 text-gray-400 hover:text-indigo-500"
                      onClick={(e) => { e.stopPropagation(); startRename(a); }}
                    />
                  </button>
                )}
              </div>
            ))}

            {artists.length < MAX_ARTISTS && (
              <button
                onClick={addArtist}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium text-gray-500 border border-dashed border-gray-300 hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50/50 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Add artist
              </button>
            )}
          </div>

          {/* Name validation error */}
          {nameError && (
            <p className="mt-2 text-xs text-red-500 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" /> {nameError}
            </p>
          )}
        </div>

        {/* ── Artist settings panel ─────────────────────────────── */}
        {panelArtist && (
          <div className="mb-6 rounded-2xl bg-white border border-indigo-200/90 shadow-xl shadow-purple-500/10 p-6 space-y-5 transition-all">
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-xl ${panelArtist.color} flex items-center justify-center text-white font-bold text-sm shadow-md`}>
                  {panelArtist.name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                    {panelArtist.name}
                    <span className="text-xs font-normal text-purple-600 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-full font-mono">
                      Settings
                    </span>
                  </h3>
                  <p className="text-xs text-gray-500">Configure underlying voice, pace, and stability</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => deleteArtist(panelArtist.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg text-rose-600 hover:bg-rose-50 border border-rose-200 hover:border-rose-300 transition-colors shadow-xs"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Remove Artist
                </button>
                <button
                  onClick={() => setPanelArtistId(null)}
                  className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                  title="Close settings"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Voice selector */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Assigned Indian Voice
                </label>
                <span className="text-xs text-purple-600 font-medium">
                  {voices.length} voices available
                </span>
              </div>
              <div className="relative">
                <select
                  value={panelArtist.voice_id}
                  onChange={(e) => updateArtist(panelArtist.id, { voice_id: e.target.value })}
                  className="w-full pl-3.5 pr-10 py-3 rounded-xl bg-gray-50 hover:bg-white border border-gray-300 focus:bg-white text-gray-900 font-semibold text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-purple-400/40 focus:border-purple-300 cursor-pointer shadow-xs transition-all"
                >
                  <optgroup label="⭐ Curated Premium Voices (10 Sarvam Bulbul Studio)">
                    {voices
                      .filter((v) => v.tier === "premium" || v.id.startsWith("sarvam_"))
                      .map((v) => (
                        <option key={v.id} value={v.id} className="text-gray-900 font-medium py-1">
                          ⭐ {v.display_name} • {v.gender} • {v.tone} ({v.language})
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="🎙️ Free Voices (Microsoft Edge TTS)">
                    {voices
                      .filter((v) => v.tier !== "premium" && !v.id.startsWith("sarvam_"))
                      .map((v) => (
                        <option key={v.id} value={v.id} className="text-gray-900 font-medium py-1">
                          🎙️ {v.display_name} • {v.gender} • {v.tone} ({v.language})
                        </option>
                      ))}
                  </optgroup>
                </select>
                <ChevronDown className="w-4 h-4 text-gray-500 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Selected Voice Info Card */}
              {(() => {
                const currentVoice = voices.find((v) => v.id === panelArtist.voice_id) || voices[0];
                if (!currentVoice) return null;
                return (
                  <div className="p-3.5 rounded-xl bg-gradient-to-br from-indigo-50/70 to-purple-50/70 border border-indigo-100 flex items-center justify-between gap-3 shadow-xs">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-9 h-9 rounded-lg bg-gradient-to-tr ${currentVoice.avatar_color || "from-indigo-500 to-purple-600"} flex items-center justify-center text-white font-bold text-sm shadow-xs shrink-0`}>
                        {currentVoice.display_name.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-gray-900 truncate">{currentVoice.display_name}</div>
                        <div className="text-[11px] text-gray-500 truncate">{currentVoice.accent} • {currentVoice.description}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-white text-gray-700 border border-gray-200 capitalize shadow-xs">
                        {currentVoice.gender}
                      </span>
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200 capitalize shadow-xs">
                        {currentVoice.tone}
                      </span>
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-xs">
                        {currentVoice.language}
                      </span>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Sliders Grid: Speed & Stability */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              {/* Speed slider card */}
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-200 space-y-3 shadow-xs">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-gray-800 block">Pace / Speed</span>
                    <span className="text-[11px] text-gray-500">Integer step multiplier (-2 to +3)</span>
                  </div>
                  <span className="px-2.5 py-1 text-xs font-mono font-bold rounded-lg bg-purple-100 text-purple-700 border border-purple-200 shadow-xs">
                    {panelArtist.speed > 0 ? `+${panelArtist.speed}` : panelArtist.speed}
                    {" "}
                    ({(1.0 + panelArtist.speed * 0.25).toFixed(2)}x)
                  </span>
                </div>
                <div className="space-y-1.5">
                  <input
                    type="range"
                    min={-2} max={3} step={1}
                    value={panelArtist.speed}
                    onChange={(e) => updateArtist(panelArtist.id, { speed: parseInt(e.target.value) })}
                    className="w-full cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-gray-500 font-mono font-medium pt-1">
                    <span className={panelArtist.speed === -2 ? "text-purple-700 font-bold" : ""}>-2 (0.5x Slow)</span>
                    <span className={panelArtist.speed === 0 ? "text-purple-700 font-bold" : ""}>0 (1.0x Normal)</span>
                    <span className={panelArtist.speed === 3 ? "text-purple-700 font-bold" : ""}>+3 (2.0x Fast)</span>
                  </div>
                </div>
              </div>

              {/* Stability slider card */}
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-200 space-y-3 shadow-xs">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-gray-800 block">Clarity / Stability</span>
                    <span className="text-[11px] text-gray-500">Expression & consistency (0 to 1)</span>
                  </div>
                  <span className="px-2.5 py-1 text-xs font-mono font-bold rounded-lg bg-indigo-100 text-indigo-700 border border-indigo-200 shadow-xs">
                    {panelArtist.stability.toFixed(2)}
                  </span>
                </div>
                <div className="space-y-1.5">
                  <input
                    type="range"
                    min={0} max={1} step={0.05}
                    value={panelArtist.stability}
                    onChange={(e) => updateArtist(panelArtist.id, { stability: parseFloat(e.target.value) })}
                    className="w-full cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-gray-500 font-mono font-medium pt-1">
                    <span className={panelArtist.stability < 0.3 ? "text-indigo-700 font-bold" : ""}>0.0 (Expressive)</span>
                    <span className={panelArtist.stability >= 0.3 && panelArtist.stability <= 0.7 ? "text-indigo-700 font-bold" : ""}>0.5 (Balanced)</span>
                    <span className={panelArtist.stability > 0.7 ? "text-indigo-700 font-bold" : ""}>1.0 (Steady)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Script editor ─────────────────────────────────────── */}
        <div className="mb-6 rounded-2xl bg-white/70 backdrop-blur-xl border border-white/80 shadow-lg shadow-purple-500/5 p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <label className="text-sm font-semibold text-gray-800">Script Editor</label>
              <span className="text-[10px] text-emerald-600 font-medium bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                Draft Autosaved
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,.awaaz.json"
                className="hidden"
                onChange={handleImportProject}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-lg bg-gray-50 hover:bg-gray-100 text-gray-700 border border-gray-200 transition shadow-xs"
                title="Import .awaaz.json project"
              >
                <Upload className="w-3.5 h-3.5 text-gray-500" /> Import Project
              </button>
              <button
                type="button"
                onClick={handleExportProject}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-lg bg-gray-50 hover:bg-gray-100 text-gray-700 border border-gray-200 transition shadow-xs"
                title="Export .awaaz.json project"
              >
                <Download className="w-3.5 h-3.5 text-gray-500" /> Export Project
              </button>
              <button
                type="button"
                onClick={handleResetToSample}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-lg bg-gray-50 hover:bg-gray-100 text-gray-600 border border-gray-200 transition shadow-xs"
                title="Reset to default sample"
              >
                <RotateCcw className="w-3.5 h-3.5 text-gray-400" /> Reset
              </button>
              <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${
                charCount > MAX_CHARS ? "bg-rose-50 text-rose-500 border border-rose-200" : "bg-gray-100 text-gray-500"
              }`}>
                {charCount} / {MAX_CHARS} chars
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
            <p className="text-gray-400">
              Type <code className="px-1 py-0.5 bg-gray-100 rounded text-indigo-600">@ArtistName</code> to switch speakers.
            </p>
            {/* Quick Pause Insertion Buttons */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-gray-400 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Quick Pause:
              </span>
              <button
                type="button"
                onClick={() => insertPause(200)}
                className="px-2 py-0.5 rounded-md bg-purple-50 hover:bg-purple-100 text-purple-700 font-mono text-[11px] border border-purple-200 transition"
              >
                +200ms
              </button>
              <button
                type="button"
                onClick={() => insertPause(500)}
                className="px-2 py-0.5 rounded-md bg-purple-50 hover:bg-purple-100 text-purple-700 font-mono text-[11px] border border-purple-200 transition"
              >
                +500ms
              </button>
              <button
                type="button"
                onClick={() => insertPause(1000)}
                className="px-2 py-0.5 rounded-md bg-purple-50 hover:bg-purple-100 text-purple-700 font-mono text-[11px] border border-purple-200 transition"
              >
                +1.0s
              </button>
            </div>
          </div>

          {/* Textarea with relative container for autocomplete */}
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={script}
              onChange={handleScriptChange}
              onKeyDown={handleKeyDown}
              onBlur={handleBlur}
              rows={8}
              placeholder={artists.length > 0
                ? `@${artists[0].name} नमस्ते! आज का विषय बहुत दिलचस्प है...`
                : "Add an artist first, then start writing your script..."
              }
              className="w-full p-4 rounded-xl bg-white border border-gray-200 text-gray-800 text-base leading-relaxed focus:outline-none focus:ring-2 focus:ring-purple-400/40 focus:border-purple-300 transition-all resize-y placeholder-gray-300 shadow-inner font-mono"
            />

            {/* Autocomplete dropdown */}
            {autocomplete.visible && filteredArtists.length > 0 && (
              <div className="absolute z-50 left-4 mt-1 w-56 bg-white rounded-xl border border-gray-200 shadow-xl py-1 max-h-48 overflow-y-auto">
                {filteredArtists.map((a, idx) => (
                  <button
                    key={a.id}
                    onMouseDown={(e) => { e.preventDefault(); insertTag(a.name); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
                  >
                    <span className={`w-2.5 h-2.5 rounded-full ${a.color}`} />
                    <span className="font-medium">{a.name}</span>
                    <span className="ml-auto text-[10px] text-gray-400">
                      {voices.find((v) => v.id === a.voice_id)?.display_name || a.voice_id}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Tagged preview */}
          {script.trim() && (
            <div className="p-4 rounded-xl bg-gray-50 border border-gray-200 text-sm leading-relaxed min-h-[3rem] whitespace-pre-wrap">
              <span className="text-[10px] text-gray-400 uppercase tracking-wider block mb-2">Preview</span>
              {taggedSpans.map((span, i) => (
                <span key={i} className={span.className}>{span.text}</span>
              ))}
            </div>
          )}

          {/* Unknown tag warnings */}
          {unknowns.length > 0 && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-xs flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>
                Unknown artist(s): <strong>{unknowns.map((u) => "@" + u).join(", ")}</strong>.
                Add them to your cast or fix the spelling. Generation is blocked until resolved.
              </span>
            </div>
          )}

          {/* Error message */}
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-xs">
              {errorMsg}
            </div>
          )}
        </div>

        {/* ── Bottom bar ────────────────────────────────────────── */}
        <div className="mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-gray-400">
            {artists.length} artist{artists.length !== 1 ? "s" : ""} · {charCount} spoken characters
          </div>
          <button
            onClick={handleGenerate}
            disabled={isGenerating || artists.length === 0 || charCount === 0 || unknowns.length > 0}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:from-indigo-600 hover:via-purple-600 hover:to-pink-600 disabled:opacity-50 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-purple-500/25 active:scale-95 transition-all"
          >
            {isGenerating ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Generate Script Audio
              </>
            )}
          </button>
        </div>

        {/* ── Audio result ──────────────────────────────────────── */}
        {result && (
          <div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-indigo-200/60 p-6 space-y-4 shadow-lg shadow-indigo-500/10">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-gray-800 flex items-center gap-2">
                Generated Multi-Voice Audio
                {result.cached && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-500 border border-blue-200">
                    ⚡ Cache Hit
                  </span>
                )}
                {result.engine_used === "premium" && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200 font-semibold">
                    ⭐ Studio Premium
                  </span>
                )}
                {result.engine_used === "free" && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                    🎙️ Free Tier
                  </span>
                )}
              </h3>
              <span className="text-xs text-gray-400 font-mono bg-gray-100 px-2 py-0.5 rounded-full">
                {result.duration_seconds}s · {result.format.toUpperCase()}
              </span>
            </div>

            {/* Fallback Notice Banner */}
            {result.fallback_reason && (
              <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-3 shadow-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                  <span>
                    {result.fallback_reason === "daily_limit"
                      ? "Daily trial quota reached. Synthesized automatically with free natural voices without stopping!"
                      : result.fallback_reason === "trial_expired"
                      ? "30-day trial period completed. Continuing seamlessly with free natural voices."
                      : result.fallback_reason === "total_limit"
                      ? "Total trial quota reached. Continuing seamlessly with free natural voices."
                      : result.fallback_reason === "unauthenticated"
                      ? "Sign up for a 30-day free trial to enable Studio Neural Voices. Synthesized with free voices."
                      : "Automatic failover active: generated with free natural voices."}
                  </span>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700 bg-amber-100 px-2 py-0.5 rounded">
                  Auto Fallback
                </span>
              </div>
            )}

            <AudioPlayer
              src={result.audio_url}
              title="Multi-Voice Script"
              downloadFilename={`awaazai_script_${Date.now()}.${result.format}`}
              autoPlay={true}
            />

            {/* Segment timeline */}
            {result.segments.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] text-gray-400 uppercase tracking-wider">Segments Timeline</span>
                <div className="space-y-1.5">
                  {result.segments.map((seg, i) => {
                    if (seg.type === "pause") {
                      return (
                        <div key={i} className="flex items-center gap-2 text-xs py-1 px-2 rounded-lg bg-gray-50 border border-dashed border-gray-200">
                          <span className="w-2 h-2 rounded-full bg-gray-400" />
                          <span className="font-semibold text-gray-500 w-20">Pause</span>
                          <span className="text-gray-400 font-mono w-24 shrink-0">
                            {(seg.start_ms / 1000).toFixed(1)}s – {(seg.end_ms / 1000).toFixed(1)}s
                          </span>
                          <span className="text-purple-600 font-mono text-[11px]">{seg.duration_ms}ms silence</span>
                        </div>
                      );
                    }
                    const artistObj = artists.find((a) => a.id === seg.artist_id || a.name.toLowerCase() === (seg.artist || "").toLowerCase());
                    const colorIdx = artistObj ? artists.indexOf(artistObj) : 0;
                    return (
                      <div key={i} className="flex items-center gap-2 text-xs py-1 px-2 rounded-lg bg-white border border-gray-100">
                        <span className={`w-2 h-2 rounded-full ${ARTIST_COLORS[colorIdx % ARTIST_COLORS.length]}`} />
                        <span className="font-semibold text-gray-800 w-20 truncate">{seg.artist}</span>
                        <span className="text-gray-400 font-mono w-24 shrink-0">
                          {(seg.start_ms / 1000).toFixed(1)}s – {(seg.end_ms / 1000).toFixed(1)}s
                        </span>
                        <span className="text-gray-600 truncate">{seg.text}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Character & Cost Accounting Ledger */}
            <div className="p-3.5 rounded-xl bg-gray-50/80 border border-gray-200/80 space-y-2 text-xs">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold block">
                Billing & Cache Efficiency
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                <div className="p-2 rounded-lg bg-white border border-gray-100 shadow-xs">
                  <div className="text-gray-400 text-[10px]">Submitted</div>
                  <div className="font-bold text-gray-800 font-mono">{result.characters_submitted} chars</div>
                </div>
                <div className="p-2 rounded-lg bg-emerald-50 border border-emerald-200 shadow-xs">
                  <div className="text-emerald-600 text-[10px]">Cached (Saved)</div>
                  <div className="font-bold text-emerald-700 font-mono">{result.characters_cached} chars</div>
                </div>
                <div className="p-2 rounded-lg bg-purple-50 border border-purple-200 shadow-xs">
                  <div className="text-purple-600 text-[10px]">Synthesized</div>
                  <div className="font-bold text-purple-700 font-mono">{result.characters_synthesized} chars</div>
                </div>
                <div className="p-2 rounded-lg bg-white border border-gray-100 shadow-xs">
                  <div className="text-gray-400 text-[10px]">Estimated Cost</div>
                  <div className="font-bold text-gray-900 font-mono">₹{result.estimated_cost_inr.toFixed(4)}</div>
                </div>
              </div>
            </div>

            {/* Export Actions (WAV, SRT, JSON, Stems) */}
            <div className="space-y-2 pt-2 border-t border-gray-100">
              <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Timeline & Stem Exports</span>
              <div className="flex flex-wrap items-center gap-2">
                <a
                  href={result.download_url}
                  download={`awaazai_script_${Date.now()}.${result.format}`}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-gray-900 hover:bg-gray-800 text-white transition-colors shadow-xs"
                >
                  <Download className="w-3.5 h-3.5" /> Download Master ({result.format.toUpperCase()})
                </a>
                <a
                  href={result.srt_url}
                  download={`awaazai_script_${result.id}.srt`}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white hover:bg-purple-50 text-purple-700 border border-purple-200 transition-colors shadow-xs"
                >
                  <FileText className="w-3.5 h-3.5 text-purple-500" /> Export Subtitles (.SRT)
                </a>
                <a
                  href={result.transcript_url}
                  download={`awaazai_script_${result.id}_transcript.json`}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-200 transition-colors shadow-xs"
                >
                  <FileText className="w-3.5 h-3.5 text-indigo-500" /> Export Transcript (.JSON)
                </a>
              </div>

              {/* Speaker Stems download pills */}
              {result.stems && result.stems.length > 0 && (
                <div className="pt-2">
                  <span className="text-[11px] font-semibold text-gray-600 block mb-1.5 flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-indigo-500" /> Isolated Speaker Stems:
                  </span>
                  <div className="flex flex-wrap items-center gap-2">
                    {result.stems.map((stem) => (
                      <a
                        key={stem.artist_id}
                        href={stem.stem_url}
                        download={`awaazai_${stem.artist_name}_stem.${result.format}`}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200 transition-colors"
                      >
                        <Download className="w-3 h-3 text-gray-400" /> {stem.artist_name} Stem
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between text-[11px] text-gray-400 pt-2 border-t border-gray-100">
              <span className="text-emerald-600 font-medium">✓ {result.ai_label}</span>
              <span className="font-mono text-gray-400">ID: {result.id}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
