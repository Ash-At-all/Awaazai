"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Mic, Radio, Users, Sparkles, Play, ArrowRight, Zap, Globe, Shield } from "lucide-react";
import { Voice } from "@/types";

export default function LandingPage() {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("neeraj");
  const [demoText, setDemoText] = useState<string>(
    "AwaazAI ke saath, Hindi aur Hinglish mein apne ideas ko awaaz dein. Natural AI voices, kahaniyon se lekar videos tak — create karein, sunein, aur share karein. AwaazAI: aapki baat, aapki awaaz."
  );
  const [isGenerating, setIsGenerating] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/voices")
      .then((res) => res.json())
      .then((data: Voice[]) => {
        setVoices(data);
        if (data.length > 0) setSelectedVoice(data[0].id);
      })
      .catch((err) => console.log(err));
  }, []);

  const handleGenerateDemo = async () => {
    setIsGenerating(true);
    setAudioUrl(null);
    setDemoError(null);
    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: demoText,
          voice_id: selectedVoice,
          speed: 1.0,
          pitch: 1.0,
          stability: 0.5,
          format: "wav",
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "We couldn’t create the audio sample. Please try again.");
      if (data.audio_url) setAudioUrl(data.audio_url);
      else throw new Error("The audio sample wasn’t returned. Please try again.");
    } catch (e) {
      setDemoError(e instanceof Error ? e.message : "We couldn’t create the audio sample. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="relative overflow-hidden">
      {/* ── Gradient mesh background (Lovable style) ── */}
      <div className="gradient-mesh absolute inset-0 -z-10" />

      {/* Extra soft blobs */}
      <div className="absolute top-[-5%] left-1/2 -translate-x-1/2 w-[1100px] h-[700px] rounded-full bg-gradient-to-br from-indigo-400/20 via-purple-400/15 to-pink-400/20 blur-[120px] -z-10 pointer-events-none" />
      <div className="absolute top-[20%] right-[-10%] w-[600px] h-[400px] rounded-full bg-pink-400/10 blur-[100px] -z-10 pointer-events-none" />
      <div className="absolute top-[30%] left-[-5%] w-[500px] h-[350px] rounded-full bg-indigo-400/10 blur-[80px] -z-10 pointer-events-none" />

      {/* ── Hero section ── */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 md:pt-40 pb-20">
        <div className="text-center max-w-4xl mx-auto space-y-8">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/60 backdrop-blur-sm border border-indigo-200/60 text-sm font-medium text-indigo-700 shadow-sm shadow-indigo-200/40">
            <Sparkles className="w-3.5 h-3.5 text-purple-500" />
            <span>Dedicated Generative Speech for Bharat</span>
          </div>

          {/* Headline */}
          <h1 className="text-5xl md:text-7xl font-bold leading-[1.08] tracking-[-2px] text-gray-900">
            Build something{" "}
            <span className="gradient-text">
              incredible
            </span>{" "}
            with Indian voices
          </h1>

          <p className="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed font-normal">
            Expressive Hindi & Hinglish speech AI. Natural inflection, seamless Roman Hinglish,
            and a full multi-speaker script studio — built for Bharat.
          </p>

          {/* CTA row */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <Link
              href="/studio"
              className="px-6 py-3 rounded-xl bg-gray-900 hover:bg-gray-800 text-white text-sm font-semibold transition-all shadow-lg shadow-gray-900/20 flex items-center gap-2 active:scale-95"
            >
              <Mic className="w-4 h-4" />
              Open Voice Studio
            </Link>
            <Link
              href="/voices"
              className="px-6 py-3 rounded-xl bg-white/70 hover:bg-white text-gray-700 text-sm font-semibold border border-gray-200 transition-all shadow-sm flex items-center gap-2 backdrop-blur-sm active:scale-95"
            >
              <Radio className="w-4 h-4" />
              Browse Voice Library
            </Link>
          </div>
        </div>

        {/* ── Central TTS Panel (Lovable-style search box) ── */}
        <div className="mt-20 max-w-2xl mx-auto">
          <div className="relative rounded-2xl bg-white/70 backdrop-blur-xl border border-white/80 shadow-2xl shadow-purple-500/10 p-6 md:p-8 space-y-5">
            {/* Glow ring */}
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-indigo-500/10 via-purple-500/5 to-pink-500/10 pointer-events-none" />

            <div className="relative space-y-5">
              <div className="flex items-center gap-2 text-xs font-semibold text-purple-600 uppercase tracking-wider">
                <Zap className="w-3.5 h-3.5" />
                <span>Hear the AwaazAI voice sample · Edit it or play it instantly</span>
              </div>

              {/* Voice selector */}
              {voices.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {voices.slice(0, 5).map((v) => (
                    <button
                      key={v.id}
                      onClick={() => { setSelectedVoice(v.id); setAudioUrl(null); }}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                        selectedVoice === v.id
                          ? "bg-gray-900 text-white shadow-md"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {v.display_name.split(" ")[0]}
                    </button>
                  ))}
                </div>
              )}

              {/* Textarea */}
              <textarea
                value={demoText}
                onChange={(e) => setDemoText(e.target.value)}
                rows={3}
                className="w-full px-4 py-3 rounded-xl bg-white border border-gray-200 text-gray-800 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-purple-400/50 focus:border-purple-300 transition-all resize-none placeholder-gray-400 shadow-inner"
                placeholder="Type in Hindi or Hinglish..."
              />

              {/* Action row */}
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs text-gray-400 font-mono">{demoText.length} / 2500</span>
                <button
                  onClick={handleGenerateDemo}
                  disabled={isGenerating || !demoText.trim()}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:from-indigo-600 hover:via-purple-600 hover:to-pink-600 disabled:opacity-50 text-white font-semibold text-sm flex items-center gap-2 shadow-lg shadow-purple-500/30 active:scale-95 transition-all"
                >
                  {isGenerating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Synthesizing...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-current" />
                      Generate & Play
                    </>
                  )}
                </button>
              </div>

              {/* Audio output */}
              {audioUrl && (
                <div className="pt-2 border-t border-gray-100 space-y-2">
                  <audio src={audioUrl} controls autoPlay className="w-full rounded-lg" />
                  <div className="flex items-center justify-between text-[11px] text-gray-400">
                    <span className="text-green-600 font-medium">✓ AI-Generated Voice (AwaazAI)</span>
                    <a
                      href={`${audioUrl}?download=true`}
                      download="awaazai_demo.wav"
                      className="text-indigo-500 hover:text-indigo-700 underline underline-offset-2 transition-colors"
                    >
                      Download WAV
                    </a>
                  </div>
                </div>
              )}
              {demoError && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{demoError}</p>}
            </div>
          </div>
        </div>

        {/* ── Feature cards ── */}
        <div className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard
            icon={<Users className="w-5 h-5" />}
            color="from-indigo-500 to-blue-500"
            title="Conversation Studio"
            body="Script dialogues with @speaker tags. Generates per-line audio and stitches into seamless podcasts, interviews, and dramas."
          />
          <FeatureCard
            icon={<Globe className="w-5 h-5" />}
            color="from-purple-500 to-pink-500"
            title="Hindi & Hinglish Precision"
            body="Roman Hinglish → phonetic Devanagari, Indian currency, numbers, and dates spoken naturally."
          />
          <FeatureCard
            icon={<Shield className="w-5 h-5" />}
            color="from-emerald-500 to-teal-500"
            title="Ethical Voice Roster"
            body="All voices are licensed. Consented voice actors only. No unauthorized clones or deepfakes — ever."
          />
        </div>
      </div>
    </div>
  );
}

function FeatureCard({
  icon,
  color,
  title,
  body,
}: {
  icon: React.ReactNode;
  color: string;
  title: string;
  body: string;
}) {
  return (
    <div className="group p-6 rounded-2xl bg-white/60 backdrop-blur-sm border border-white/80 hover:border-indigo-200/60 hover:shadow-xl hover:shadow-purple-500/10 transition-all space-y-4">
      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center text-white shadow-md`}>
        {icon}
      </div>
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      <p className="text-sm text-gray-500 leading-relaxed">{body}</p>
    </div>
  );
}
