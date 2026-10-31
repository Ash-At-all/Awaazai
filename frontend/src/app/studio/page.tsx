"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Mic, Sparkles, Sliders, RotateCcw, ChevronDown, Play, Pause, Volume2 } from "lucide-react";
import { Voice, TTSResponse } from "@/types";
import AudioPlayer from "@/components/AudioPlayer";

function StudioContent() {
  const searchParams = useSearchParams();
  const initialVoice = searchParams.get("voice") || "neeraj";

  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>(initialVoice);
  const [isPlayingSample, setIsPlayingSample] = useState<boolean>(false);
  const sampleAudioRef = useRef<HTMLAudioElement | null>(null);
  const [text, setText] = useState<string>(
    "नमस्ते! आवाज़ एआई के सिंगल वॉइस स्टूडियो में आपका स्वागत है। यहाँ आप किसी भी हिंदी या हिंग्लिश स्क्रिप्ट को सहजता से हाई क्वालिटी ऑडियो में बदल सकते हैं।"
  );
  const [speed, setSpeed] = useState<number>(1.0);
  const [pitch, setPitch] = useState<number>(1.0);
  const [stability, setStability] = useState<number>(0.5);
  const [format, setFormat] = useState<"wav" | "mp3">("wav");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [result, setResult] = useState<TTSResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/voices")
      .then((res) => res.json())
      .then((data: Voice[]) => {
        setVoices(data);
        if (data.length > 0 && !data.some((v) => v.id === initialVoice)) {
          setSelectedVoiceId(data[0].id);
        }
      })
      .catch((err) => console.error(err));
  }, [initialVoice]);

  const selectedVoice = voices.find((v) => v.id === selectedVoiceId) || voices[0];

  useEffect(() => {
    if (sampleAudioRef.current) {
      sampleAudioRef.current.pause();
      setIsPlayingSample(false);
    }
  }, [selectedVoiceId]);

  const handleToggleSample = () => {
    if (!selectedVoice) return;
    if (isPlayingSample && sampleAudioRef.current) {
      sampleAudioRef.current.pause();
      setIsPlayingSample(false);
    } else {
      const url = selectedVoice.sample_url || `/api/voices/${selectedVoice.id}/sample`;
      if (!sampleAudioRef.current) {
        sampleAudioRef.current = new Audio(url);
        sampleAudioRef.current.onended = () => setIsPlayingSample(false);
      } else {
        sampleAudioRef.current.src = url;
      }
      sampleAudioRef.current.play().then(() => setIsPlayingSample(true)).catch(() => setIsPlayingSample(false));
    }
  };

  const handleGenerate = async () => {
    if (!text.trim()) return;
    setIsGenerating(true);
    setErrorMsg(null);
    try {
      const payload: any = { text, voice_id: selectedVoiceId, speed, pitch, stability, format };
      if (selectedVoice?.provider) {
        payload.provider = selectedVoice.provider;
      }
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to generate audio");
      }
      const data: TTSResponse = await res.json();
      setResult(data);
    } catch (err: any) {
      setErrorMsg(err.message || "An error occurred");
    } finally {
      setIsGenerating(false);
    }
  };

  const samplePrompts = [
    { title: "Pure Hindi", content: "भारत की संस्कृति और धरोहर विश्व भर में अपनी विशिष्ट पहचान रखती है। हमारे विचार ही हमारे भविष्य का निर्माण करते हैं।" },
    { title: "Hinglish Tech", content: "Hey guys! Welcome back to the podcast. Aaj hum breakdown karenge new AI text-to-speech models aur unki Indian voice synthesis capabilities." },
    { title: "Numbers & Currency", content: "Aapka flight ticket confirm ho gaya hai. PNR number 98412 hai aur total amount Rs 4,850 successfully receive ho gaya hai." },
  ];

  return (
    <div className="relative overflow-hidden min-h-screen">
      {/* Same gradient mesh as home page */}
      <div className="gradient-mesh absolute inset-0 -z-10" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[500px] rounded-full bg-gradient-to-br from-indigo-400/20 via-purple-400/15 to-pink-400/15 blur-[120px] -z-10 pointer-events-none" />
      <div className="absolute top-[30%] right-[-5%] w-[500px] h-[400px] rounded-full bg-pink-400/10 blur-[100px] -z-10 pointer-events-none" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">

        {/* Page Header */}
        <div className="mb-10">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/60 backdrop-blur-sm border border-indigo-200/60 text-indigo-600 text-xs font-semibold uppercase tracking-wider mb-3 shadow-sm">
            <Mic className="w-3 h-3" />
            Generative Voice Lab
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 tracking-tight">
            Speech <span className="gradient-text">Studio</span>
          </h1>
          <p className="text-gray-500 text-base mt-2 max-w-xl">
            Synthesize high-fidelity Hindi and Hinglish speech with customizable speed, pitch, and natural inflection.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* ── Left: Script editor (8 cols) ── */}
          <div className="lg:col-span-8 space-y-5">

            {/* Script Card */}
            <div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-white/80 shadow-lg shadow-purple-500/5 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-gray-800">
                  Input Script (Hindi / Hinglish)
                </label>
                <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${text.length > 2000 ? "bg-rose-50 text-rose-500 border border-rose-200" : "bg-gray-100 text-gray-400"}`}>
                  {text.length} / 2500
                </span>
              </div>

              {/* Quick prompts */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-gray-400">Quick test:</span>
                {samplePrompts.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => setText(p.content)}
                    className="px-3 py-1 text-xs rounded-full bg-gray-100 hover:bg-indigo-50 hover:text-indigo-600 text-gray-600 border border-gray-200 hover:border-indigo-200 transition-colors"
                  >
                    {p.title}
                  </button>
                ))}
              </div>

              {/* Textarea */}
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={7}
                maxLength={2500}
                placeholder="Type Hindi (हिंदी) or Hinglish dialogue here..."
                className="w-full p-4 rounded-xl bg-white border border-gray-200 text-gray-800 text-base leading-relaxed focus:outline-none focus:ring-2 focus:ring-purple-400/40 focus:border-purple-300 transition-all resize-y placeholder-gray-300 shadow-inner"
              />

              {/* Format + Generate */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2 border-t border-gray-100">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 font-medium">Format:</span>
                  <div className="inline-flex rounded-xl bg-gray-100 p-0.5 border border-gray-200">
                    {(["wav", "mp3"] as const).map((f) => (
                      <button
                        key={f}
                        onClick={() => setFormat(f)}
                        className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                          format === f
                            ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                            : "text-gray-400 hover:text-gray-700"
                        }`}
                      >
                        {f === "wav" ? "WAV (Lossless)" : "MP3 (Compact)"}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  onClick={handleGenerate}
                  disabled={isGenerating || !text.trim()}
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
                      Generate Audio
                    </>
                  )}
                </button>
              </div>

              {errorMsg && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-xs">
                  {errorMsg}
                </div>
              )}
            </div>

            {/* Audio Result */}
            {result && (
              <div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-indigo-200/60 p-6 space-y-4 shadow-lg shadow-indigo-500/10">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-gray-800 flex items-center gap-2">
                    Generated Audio Output
                    {result.cached && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-500 border border-blue-200">
                        ⚡ Cache Hit
                      </span>
                    )}
                  </h3>
                  <span className="text-xs text-gray-400 font-mono bg-gray-100 px-2 py-0.5 rounded-full">
                    {result.duration_seconds}s · {result.format.toUpperCase()}
                  </span>
                </div>
                <AudioPlayer
                  src={result.audio_url}
                  title="Synthesized Track"
                  voiceName={result.voice.display_name}
                  downloadFilename={`awaazai_${result.voice.id}_${Date.now()}.${result.format}`}
                  autoPlay={true}
                />
                {result.fallback_reason && (
                  <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-800">
                    {result.fallback_reason === "provider_error"
                      ? "The selected voice provider couldn’t generate this clip, so we used a free voice instead. Please check the provider key and voice access, then try again."
                      : "Premium access wasn’t available for this clip, so we used a free voice instead."}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* ── Right: Voice picker + settings (4 cols) ── */}
          <div className="lg:col-span-4 space-y-5">

            {/* Voice Picker */}
            <div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-white/80 shadow-lg shadow-purple-500/5 p-5 space-y-4">
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Speaker Voice
              </label>
              <div className="relative">
                <select
                  value={selectedVoiceId}
                  onChange={(e) => setSelectedVoiceId(e.target.value)}
                  className="w-full pl-3 pr-10 py-3 rounded-xl bg-white border border-gray-200 text-gray-800 font-medium text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-purple-400/40 focus:border-purple-300 cursor-pointer shadow-sm transition-all"
                >
                  {voices.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.display_name} ({v.gender}, {v.tone})
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-gray-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {selectedVoice && (
                <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50/80 to-purple-50/80 border border-indigo-100 space-y-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-tr ${selectedVoice.avatar_color} flex items-center justify-center text-white font-bold text-sm shadow-md`}>
                      {selectedVoice.display_name.charAt(0)}
                    </div>
                    <div>
                      <h4 className="font-bold text-sm text-gray-900">{selectedVoice.display_name}</h4>
                      <p className="text-xs text-gray-500">{selectedVoice.accent}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <LBadge>{selectedVoice.gender}</LBadge>
                    <LBadge color="purple">{selectedVoice.tone}</LBadge>
                    <LBadge color="emerald">{selectedVoice.language}</LBadge>
                  </div>
                  <p className="text-xs text-gray-500 leading-relaxed">{selectedVoice.description}</p>

                  {/* Playable Sample Audition Button & Provider Badge */}
                  <div className="pt-2 border-t border-indigo-100/60 flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={handleToggleSample}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-indigo-50 border border-indigo-200 text-xs font-semibold text-indigo-700 shadow-xs transition"
                    >
                      {isPlayingSample ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                      {isPlayingSample ? "Pause Sample" : "Listen to Sample"}
                    </button>
                    <span className="text-[10px] font-mono text-gray-400">
                      {selectedVoice.tier === "premium" ? "⭐ Studio 24kHz" : "🎙️ Neural Free"}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Voice Settings */}
            <div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-white/80 shadow-lg shadow-purple-500/5 p-5 space-y-5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                  <Sliders className="w-3.5 h-3.5 text-purple-500" />
                  Voice Settings
                </label>
                <button
                  onClick={() => { setSpeed(1.0); setPitch(1.0); setStability(0.5); }}
                  className="text-[11px] text-gray-400 hover:text-purple-500 flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" />
                  Reset
                </button>
              </div>

              <LSliderRow
                label="Speed / Pace"
                value={speed}
                onChange={setSpeed}
                min={0.5} max={2.0} step={0.05}
                display={`${speed.toFixed(2)}x`}
                marks={["0.5x (Slow)", "1.0x (Normal)", "2.0x (Fast)"]}
              />
              <LSliderRow
                label="Pitch / Modulation"
                value={pitch}
                onChange={setPitch}
                min={0.5} max={1.5} step={0.05}
                display={`${pitch.toFixed(2)}x`}
                marks={["0.5x (Deep)", "1.0x (Original)", "1.5x (High)"]}
              />
              <LSliderRow
                label="Stability / Expression"
                value={stability}
                onChange={setStability}
                min={0.0} max={1.0} step={0.05}
                display={stability.toFixed(2)}
                marks={["0.0 (Expressive)", "0.5 (Balanced)", "1.0 (Steady)"]}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Helper sub-components ── */
function LBadge({ children, color = "slate" }: { children: React.ReactNode; color?: "slate" | "purple" | "emerald" }) {
  const styles = {
    slate:   "bg-gray-100 text-gray-600 border-gray-200",
    purple:  "bg-purple-50 text-purple-600 border-purple-200",
    emerald: "bg-emerald-50 text-emerald-600 border-emerald-200",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-[11px] font-medium border capitalize ${styles[color]}`}>
      {children}
    </span>
  );
}

function LSliderRow({
  label, value, onChange, min, max, step, display, marks,
}: {
  label: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number; display: string;
  marks: [string, string, string];
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-gray-700 font-medium">{label}</span>
        <span className="font-mono text-purple-500 font-semibold">{display}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full cursor-pointer accent-purple-500"
      />
      <div className="flex justify-between text-[10px] text-gray-400 font-mono">
        <span>{marks[0]}</span><span>{marks[1]}</span><span>{marks[2]}</span>
      </div>
    </div>
  );
}

export default function StudioPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen gradient-mesh flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-gray-500 text-sm">Loading Studio...</p>
        </div>
      </div>
    }>
      <StudioContent />
    </Suspense>
  );
}
