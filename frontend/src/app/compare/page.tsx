"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Sliders,
  Play,
  Pause,
  Sparkles,
  RotateCcw,
  Volume2,
  Download,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Layers,
  ArrowRightLeft,
} from "lucide-react";
import { Voice, TTSResponse } from "@/types";

const PRESET_SCRIPTS = [
  {
    label: "News & Formal (Hindi)",
    text: "नमस्कार, आज के मुख्य समाचारों के साथ मैं हाज़िर हूँ। भारतीय अर्थव्यवस्था में इस तिमाही रिकॉर्ड वृद्धि दर्ज की गई है।",
  },
  {
    label: "Storytelling & Emotion (Hindi)",
    text: "एक समय की बात है, जब हिमालय की शांत वादियों में बहती नदी अपने साथ पुरानी कहानियों के अनकहे रहस्य ले जाती थी।",
  },
  {
    label: "Tech & Casual (Hinglish)",
    text: "Hey everyone! Welcome back to the review. Aaj hum test karenge best Indian AI voice models aur check karenge naturalness.",
  },
  {
    label: "Customer Support (Hinglish)",
    text: "नमस्ते! आवाज़ एआई सपोर्ट में आपका स्वागत है। बताइए, आज मैं आपकी क्या मदद कर सकती हूँ?",
  },
];

export default function ComparePage() {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loadingVoices, setLoadingVoices] = useState(true);

  const [text, setText] = useState(PRESET_SCRIPTS[0].text);
  const [voiceAId, setVoiceAId] = useState("neeraj");
  const [voiceBId, setVoiceBId] = useState("priya");

  const [speedA, setSpeedA] = useState(1.0);
  const [speedB, setSpeedB] = useState(1.0);

  const [isGenerating, setIsGenerating] = useState(false);
  const [resultA, setResultA] = useState<TTSResponse | null>(null);
  const [resultB, setResultB] = useState<TTSResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Audio Playback states
  const [isPlayingA, setIsPlayingA] = useState(false);
  const [isPlayingB, setIsPlayingB] = useState(false);

  const audioRefA = useRef<HTMLAudioElement | null>(null);
  const audioRefB = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetch("/api/voices")
      .then((res) => res.json())
      .then((data: Voice[]) => {
        if (Array.isArray(data) && data.length > 0) {
          setVoices(data);
          const premium = data.find((v) => v.tier === "premium") || data[0];
          const free = data.find((v) => v.tier !== "premium" && v.id !== premium.id) || data[1] || data[0];
          setVoiceAId(premium.id);
          setVoiceBId(free.id);
        }
      })
      .catch((err) => console.error("Error fetching voices:", err))
      .finally(() => setLoadingVoices(false));
  }, []);

  const voiceA = voices.find((v) => v.id === voiceAId) || voices[0];
  const voiceB = voices.find((v) => v.id === voiceBId) || voices[1] || voices[0];

  const handleCompare = async () => {
    if (!text.trim()) return;
    setIsGenerating(true);
    setErrorMsg(null);
    setResultA(null);
    setResultB(null);

    try {
      const [resA, resB] = await Promise.all([
        fetch("/api/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: text.trim(),
            voice_id: voiceAId,
            speed: speedA,
            pitch: 1.0,
            stability: 0.5,
            format: "wav",
          }),
        }),
        fetch("/api/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: text.trim(),
            voice_id: voiceBId,
            speed: speedB,
            pitch: 1.0,
            stability: 0.5,
            format: "wav",
          }),
        }),
      ]);

      if (!resA.ok || !resB.ok) {
        const errA = !resA.ok ? await resA.json().catch(() => ({})) : null;
        const errB = !resB.ok ? await resB.json().catch(() => ({})) : null;
        throw new Error(errA?.detail || errB?.detail || "Voice generation failed for one or both voices.");
      }

      const dataA: TTSResponse = await resA.json();
      const dataB: TTSResponse = await resB.json();

      setResultA(dataA);
      setResultB(dataB);
    } catch (err: any) {
      setErrorMsg(err.message || "An unexpected error occurred during comparison synthesis.");
    } finally {
      setIsGenerating(false);
    }
  };

  const togglePlayA = () => {
    if (!audioRefA.current && resultA) {
      audioRefA.current = new Audio(resultA.audio_url);
      audioRefA.current.onended = () => setIsPlayingA(false);
    }
    if (audioRefA.current) {
      if (isPlayingA) {
        audioRefA.current.pause();
        setIsPlayingA(false);
      } else {
        audioRefB.current?.pause();
        setIsPlayingB(false);
        audioRefA.current.play();
        setIsPlayingA(true);
      }
    }
  };

  const togglePlayB = () => {
    if (!audioRefB.current && resultB) {
      audioRefB.current = new Audio(resultB.audio_url);
      audioRefB.current.onended = () => setIsPlayingB(false);
    }
    if (audioRefB.current) {
      if (isPlayingB) {
        audioRefB.current.pause();
        setIsPlayingB(false);
      } else {
        audioRefA.current?.pause();
        setIsPlayingA(false);
        audioRefB.current.play();
        setIsPlayingB(true);
      }
    }
  };

  const handleSwapVoices = () => {
    const tempId = voiceAId;
    setVoiceAId(voiceBId);
    setVoiceBId(tempId);
    const tempResult = resultA;
    setResultA(resultB);
    setResultB(tempResult);
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] p-4 md:p-8 max-w-6xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="text-center max-w-2xl mx-auto space-y-2">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-50 border border-purple-200/60 text-purple-700 text-xs font-semibold">
          <Sliders className="w-3.5 h-3.5" /> A/B Voice Audition
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold text-gray-900 tracking-tight">
          Compare <span className="gradient-text">Indian Voices</span>
        </h1>
        <p className="text-sm text-gray-500 leading-relaxed">
          Evaluate speech prosody, naturalness, cadence, and Hinglish fluency between any two voices side-by-side.
        </p>
      </div>

      {/* Script Input Card with Presets */}
      <div className="p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-gray-200 shadow-xl shadow-purple-500/5 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">
            Test Utterance / Comparison Script
          </label>
          <span className="text-xs text-gray-400 font-mono">
            {text.length} / 500 characters
          </span>
        </div>

        {/* Quick Presets Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-gray-500">Presets:</span>
          {PRESET_SCRIPTS.map((preset, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setText(preset.text)}
              className={`text-xs px-2.5 py-1 rounded-lg border transition ${
                text === preset.text
                  ? "bg-purple-100 text-purple-800 border-purple-300 font-semibold"
                  : "bg-gray-50 hover:bg-gray-100 text-gray-600 border-gray-200"
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <textarea
          rows={3}
          maxLength={500}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter text to synthesize across both voices simultaneously..."
          className="w-full p-4 rounded-2xl bg-gray-50/50 hover:bg-white focus:bg-white border border-gray-200 focus:border-purple-300 focus:ring-2 focus:ring-purple-400/20 text-sm text-gray-900 leading-relaxed transition outline-none resize-none font-medium"
        />

        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* Dual Voice Selection Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative">
        {/* Swap Button In Center */}
        <button
          type="button"
          onClick={handleSwapVoices}
          title="Swap Voice A and Voice B"
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 hidden md:flex items-center justify-center w-10 h-10 rounded-full bg-white border border-gray-300 shadow-md text-gray-600 hover:text-purple-600 hover:border-purple-300 hover:scale-110 active:scale-95 transition"
        >
          <ArrowRightLeft className="w-4 h-4" />
        </button>

        {/* Card A */}
        <div className="p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-indigo-200/80 shadow-lg shadow-indigo-500/5 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-indigo-600 text-white font-bold text-xs flex items-center justify-center">
                A
              </span>
              <h3 className="font-bold text-gray-900 text-sm">Primary Voice (Left)</h3>
            </div>
            {voiceA && (
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                voiceA.tier === "premium"
                  ? "bg-purple-100 text-purple-700 border border-purple-200"
                  : "bg-emerald-100 text-emerald-700 border border-emerald-200"
              }`}>
                {voiceA.tier === "premium" ? "⭐ Studio Premium" : "🎙️ Free Neural"}
              </span>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-gray-600">Select Voice Model</label>
            <div className="relative">
              <select
                value={voiceAId}
                onChange={(e) => setVoiceAId(e.target.value)}
                className="w-full pl-3.5 pr-10 py-2.5 rounded-xl bg-gray-50 hover:bg-white focus:bg-white border border-gray-300 text-sm font-semibold text-gray-800 appearance-none focus:outline-none focus:ring-2 focus:ring-indigo-400/40 cursor-pointer shadow-xs"
              >
                {voices.map((v) => (
                  <option key={`a-${v.id}`} value={v.id}>
                    {v.display_name} • {v.gender} ({v.tone})
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-gray-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          {voiceA && (
            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200 text-xs text-gray-600 space-y-1">
              <p className="font-semibold text-gray-800">{voiceA.display_name} — {voiceA.accent}</p>
              <p className="text-[11px] text-gray-500 leading-relaxed">{voiceA.description}</p>
            </div>
          )}

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-gray-600 font-medium">
              <span>Pace / Speed</span>
              <span className="font-mono font-bold text-indigo-600">{speedA.toFixed(2)}x</span>
            </div>
            <input
              type="range"
              min={0.5} max={2.0} step={0.05}
              value={speedA}
              onChange={(e) => setSpeedA(parseFloat(e.target.value))}
              className="w-full cursor-pointer"
            />
          </div>

          {resultA && (
            <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-200/80 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-indigo-900">Voice A Synthesized</span>
                <span className="font-mono text-indigo-600">{resultA.duration_seconds.toFixed(2)}s</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={togglePlayA}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-md transition"
                >
                  {isPlayingA ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  {isPlayingA ? "Pause" : "Play Voice A"}
                </button>
                <a
                  href={resultA.download_url}
                  download={`compare_A_${resultA.filename}`}
                  className="p-2 rounded-xl bg-white border border-gray-200 text-gray-600 hover:text-gray-900 shadow-xs"
                >
                  <Download className="w-4 h-4" />
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Card B */}
        <div className="p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-purple-200/80 shadow-lg shadow-purple-500/5 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-purple-600 text-white font-bold text-xs flex items-center justify-center">
                B
              </span>
              <h3 className="font-bold text-gray-900 text-sm">Secondary Voice (Right)</h3>
            </div>
            {voiceB && (
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                voiceB.tier === "premium"
                  ? "bg-purple-100 text-purple-700 border border-purple-200"
                  : "bg-emerald-100 text-emerald-700 border border-emerald-200"
              }`}>
                {voiceB.tier === "premium" ? "⭐ Studio Premium" : "🎙️ Free Neural"}
              </span>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-gray-600">Select Voice Model</label>
            <div className="relative">
              <select
                value={voiceBId}
                onChange={(e) => setVoiceBId(e.target.value)}
                className="w-full pl-3.5 pr-10 py-2.5 rounded-xl bg-gray-50 hover:bg-white focus:bg-white border border-gray-300 text-sm font-semibold text-gray-800 appearance-none focus:outline-none focus:ring-2 focus:ring-purple-400/40 cursor-pointer shadow-xs"
              >
                {voices.map((v) => (
                  <option key={`b-${v.id}`} value={v.id}>
                    {v.display_name} • {v.gender} ({v.tone})
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-gray-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          {voiceB && (
            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200 text-xs text-gray-600 space-y-1">
              <p className="font-semibold text-gray-800">{voiceB.display_name} — {voiceB.accent}</p>
              <p className="text-[11px] text-gray-500 leading-relaxed">{voiceB.description}</p>
            </div>
          )}

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-gray-600 font-medium">
              <span>Pace / Speed</span>
              <span className="font-mono font-bold text-purple-600">{speedB.toFixed(2)}x</span>
            </div>
            <input
              type="range"
              min={0.5} max={2.0} step={0.05}
              value={speedB}
              onChange={(e) => setSpeedB(parseFloat(e.target.value))}
              className="w-full cursor-pointer"
            />
          </div>

          {resultB && (
            <div className="p-4 rounded-2xl bg-purple-50/60 border border-purple-200/80 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-purple-900">Voice B Synthesized</span>
                <span className="font-mono text-purple-600">{resultB.duration_seconds.toFixed(2)}s</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={togglePlayB}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold shadow-md transition"
                >
                  {isPlayingB ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  {isPlayingB ? "Pause" : "Play Voice B"}
                </button>
                <a
                  href={resultB.download_url}
                  download={`compare_B_${resultB.filename}`}
                  className="p-2 rounded-xl bg-white border border-gray-200 text-gray-600 hover:text-gray-900 shadow-xs"
                >
                  <Download className="w-4 h-4" />
                </a>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Action Button */}
      <div className="flex justify-center pt-2">
        <button
          type="button"
          onClick={handleCompare}
          disabled={isGenerating || !text.trim() || loadingVoices}
          className="flex items-center gap-2.5 px-8 py-3.5 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-500 hover:via-purple-500 hover:to-pink-500 text-white font-bold text-sm shadow-xl shadow-purple-500/20 disabled:opacity-50 active:scale-95 transition"
        >
          {isGenerating ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Synthesizing Both Voices...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Synthesize & Compare (A vs B)
            </>
          )}
        </button>
      </div>
    </div>
  );
}
