"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { Search, Play, Pause, Mic, Radio, CheckCircle2, Filter, Sparkles, X, LockKeyhole } from "lucide-react";
import { User, UserQuota, Voice } from "@/types";
import AuthModal from "@/components/AuthModal";

interface DynamicFeaturedVoice {
  id: string;
  name: string;
  voice_id: string;
  provider: string;
  label: string;
  sample_text?: string;
  image_url?: string;
  order: number;
  active: boolean;
}

export default function VoiceLibraryPage() {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [featuredVoices, setFeaturedVoices] = useState<DynamicFeaturedVoice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [genderFilter, setGenderFilter] = useState("all");
  const [languageFilter, setLanguageFilter] = useState("all");
  const [toneFilter, setToneFilter] = useState("all");
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const [fishAccessOpen, setFishAccessOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState<"login" | "signup">("signup");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetchFeaturedVoices();
  }, []);

  const fetchFeaturedVoices = async () => {
    try {
      const res = await fetch("/api/featured-voices");
      if (res.ok) {
        const data = await res.json();
        setFeaturedVoices(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchVoices = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (genderFilter !== "all") params.append("gender", genderFilter);
      if (languageFilter !== "all") params.append("language", languageFilter);
      if (toneFilter !== "all") params.append("tone", toneFilter);
      if (search) params.append("search", search);
      const res = await fetch(`/api/voices?${params.toString()}`);
      const data = await res.json();
      setVoices(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, [genderFilter, languageFilter, toneFilter, search]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void fetchVoices(); }, search ? 250 : 0);
    return () => window.clearTimeout(timer);
  }, [fetchVoices, search]);

  const handlePlaySample = (voice: Voice) => {
    if (playingVoiceId === voice.id) {
      audioRef.current?.pause();
      setPlayingVoiceId(null);
      return;
    }
    audioRef.current?.pause();
    const audio = new Audio(voice.sample_url || `/api/voices/${voice.id}/sample`);
    audioRef.current = audio;
    setPlayingVoiceId(voice.id);
    audio.play().catch(() => setPlayingVoiceId(null));
    audio.onended = () => setPlayingVoiceId(null);
  };

  const resetFilters = () => {
    setGenderFilter("all");
    setLanguageFilter("all");
    setToneFilter("all");
    setSearch("");
  };

  const hasActiveFilter = genderFilter !== "all" || languageFilter !== "all" || toneFilter !== "all" || !!search;
  const elevenLabsVoices = voices.filter((voice) => voice.provider === "elevenlabs");
  const catalogVoices = voices.filter((voice) => voice.provider !== "elevenlabs");
  const openAuth = (tab: "login" | "signup") => { setFishAccessOpen(false); setAuthTab(tab); setAuthOpen(true); };
  const handleAuthSuccess = (_user: User, _quota: UserQuota) => setAuthOpen(false);

  return (
    <div className="relative overflow-hidden min-h-screen">
      {/* Gradient mesh — same as home */}
      <div className="gradient-mesh absolute inset-0 -z-10" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[400px] rounded-full bg-gradient-to-br from-indigo-400/20 via-purple-400/15 to-pink-400/10 blur-[120px] -z-10 pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">

        {/* ── Header ── */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/60 backdrop-blur-sm border border-indigo-200/60 text-indigo-600 text-xs font-semibold uppercase tracking-wider mb-3 shadow-sm">
              <Radio className="w-3 h-3" />
              Curated Indian Voice Roster
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 tracking-tight">
              Voice <span className="gradient-text">Library</span>
            </h1>
            <p className="text-gray-500 text-base mt-2">
              Browse our licensed, ethically contracted Hindi and Hinglish generative voices.
            </p>
          </div>
          <Link
            href="/studio"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-gray-900 hover:bg-gray-800 text-white font-semibold text-sm shadow-md transition-all active:scale-95 shrink-0"
          >
            <Mic className="w-4 h-4" />
            Open Studio
          </Link>
        </div>

        {/* ElevenLabs voices lead the library */}
        {elevenLabsVoices.length > 0 && (
          <section className="mb-10 rounded-3xl border border-violet-100 bg-gradient-to-br from-white via-violet-50/60 to-indigo-50/60 p-5 sm:p-7 shadow-sm">
            <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
              <div>
                <div className="mb-1 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-violet-600"><Sparkles className="h-4 w-4" /> Premium voice collection</div>
                <h2 className="text-2xl font-bold tracking-tight text-gray-900">ElevenLabs Voices</h2>
                <p className="mt-1 text-sm text-gray-500">Expressive, studio quality voices for Hindi and Hinglish.</p>
              </div>
              <span className="rounded-full border border-violet-200 bg-white px-3 py-1 text-xs font-semibold text-violet-700">{elevenLabsVoices.length} voices</span>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {elevenLabsVoices.map((voice) => (
                <article key={voice.id} className="rounded-2xl border border-white bg-white/90 p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${voice.avatar_color} text-lg font-bold text-white shadow-sm`}>{voice.display_name.charAt(0)}</div>
                      <div className="min-w-0"><h3 className="truncate font-semibold text-gray-900">{voice.display_name.replace(/ \(ElevenLabs\)$/i, "")}</h3><p className="truncate text-xs text-gray-500">{voice.accent} · {voice.gender}</p></div>
                    </div>
                    <button onClick={() => handlePlaySample(voice)} aria-label={`${playingVoiceId === voice.id ? "Pause" : "Play"} ${voice.display_name} preview`} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-violet-50 text-violet-700 transition hover:bg-violet-100">
                      {playingVoiceId === voice.id ? <Pause className="h-4 w-4 fill-current" /> : <Play className="ml-0.5 h-4 w-4 fill-current" />}
                    </button>
                  </div>
                  <p className="mt-3 line-clamp-2 min-h-10 text-xs leading-relaxed text-gray-600">{voice.description}</p>
                  <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3"><span className="text-[11px] font-medium text-violet-700">ElevenLabs · Premium</span><Link href={`/studio?voice=${voice.id}&provider=elevenlabs`} className="rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-gray-700">Use voice</Link></div>
                </article>
              ))}
            </div>
          </section>
        )}

        {/* ── Featured Voices Showcase (Fish Audio S2.1 Pro) ── */}
        {featuredVoices.length > 0 && (
          <div className="mb-12">
            <div className="flex items-center gap-2 mb-1.5">
              <Sparkles className="w-5 h-5 text-indigo-600" />
              <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Featured Voices</h2>
              <span className="ml-2 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 border border-indigo-200 text-indigo-700">
                Fish Audio S2.1 Pro
              </span>
            </div>
            <p className="text-sm text-gray-500 mb-6">
              Discover expressive AI voices for natural conversations and storytelling.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {featuredVoices.map((fv) => {
                return (
                  <div
                    key={fv.id}
                    className="group relative rounded-2xl bg-white/80 backdrop-blur-xl border border-indigo-100 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/10 p-5 flex flex-col justify-between transition-all"
                  >
                    <div>
                      {/* Banner / Photo if available */}
                      {fv.image_url ? (
                        <div className="w-full h-28 rounded-xl overflow-hidden mb-3 border border-indigo-100 bg-gray-50 relative">
                          <img
                            src={fv.image_url}
                            alt={fv.name}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          />
                        </div>
                      ) : null}

                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div className="flex items-center gap-3">
                          {!fv.image_url && (
                            <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white text-base font-bold shadow-md">
                              {fv.name.charAt(0)}
                            </div>
                          )}
                          <div>
                            <h3 className="font-bold text-gray-900 text-sm leading-tight flex items-center gap-1.5">
                              {fv.name}
                            </h3>
                            <p className="text-[11px] text-indigo-600 font-medium mt-0.5">{fv.label}</p>
                          </div>
                        </div>

                        <button
                          onClick={() => setFishAccessOpen(true)}
                          className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 border border-indigo-200 transition-all"
                          title="Unlock this Fish Audio voice"
                          aria-label={`Unlock ${fv.name}`}
                        >
                          <LockKeyhole className="w-4 h-4" />
                        </button>
                      </div>

                      {fv.sample_text && <p className="text-xs text-gray-600 italic bg-gray-50/80 rounded-lg p-2 mb-2 line-clamp-2 border border-gray-100">&ldquo;{fv.sample_text}&rdquo;</p>}
                    </div>

                    <div className="pt-3 mt-3 border-t border-gray-100 flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-indigo-500">Premium · Fish Audio</span>
                      <button onClick={() => setFishAccessOpen(true)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition-colors shadow-sm">
                        <Mic className="w-3 h-3" />
                        Subscribe to unlock
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Filter bar ── */}
        <div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-white/80 shadow-sm p-4 mb-8 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name or accent..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && fetchVoices()}
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-white border border-gray-200 text-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/40 focus:border-purple-300 transition-all shadow-sm placeholder-gray-400"
              />
            </div>

            {/* Gender */}
            <select
              value={genderFilter}
              onChange={(e) => setGenderFilter(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl bg-white border border-gray-200 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/40 focus:border-purple-300 transition-all shadow-sm cursor-pointer"
            >
              <option value="all">All Genders</option>
              <option value="female">Female Voices</option>
              <option value="male">Male Voices</option>
            </select>

            {/* Language */}
            <select
              value={languageFilter}
              onChange={(e) => setLanguageFilter(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl bg-white border border-gray-200 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/40 focus:border-purple-300 transition-all shadow-sm cursor-pointer"
            >
              <option value="all">All Languages</option>
              <option value="Hindi">Pure Hindi</option>
              <option value="Hinglish">Hinglish</option>
            </select>

            {/* Tone */}
            <select
              value={toneFilter}
              onChange={(e) => setToneFilter(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl bg-white border border-gray-200 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/40 focus:border-purple-300 transition-all shadow-sm cursor-pointer"
            >
              <option value="all">All Tones</option>
              <option value="calm">Calm & Conversational</option>
              <option value="energetic">Energetic & Upbeat</option>
              <option value="news">News & Authoritative</option>
              <option value="storytelling">Storytelling & Narrative</option>
            </select>
          </div>

          {/* Quick filter pills */}
          <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-gray-100 text-xs">
            <span className="text-gray-400 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Quick:
            </span>
            {[
              { label: "Female", action: () => { setGenderFilter("female"); setLanguageFilter("all"); setToneFilter("all"); }, active: genderFilter === "female", activeClass: "bg-rose-50 text-rose-600 border-rose-200" },
              { label: "Male",   action: () => { setGenderFilter("male");   setLanguageFilter("all"); setToneFilter("all"); }, active: genderFilter === "male", activeClass: "bg-blue-50 text-blue-600 border-blue-200" },
              { label: "Hinglish", action: () => { setLanguageFilter("Hinglish"); setGenderFilter("all"); }, active: languageFilter === "Hinglish", activeClass: "bg-amber-50 text-amber-600 border-amber-200" },
              { label: "News Style", action: () => setToneFilter("news"), active: toneFilter === "news", activeClass: "bg-cyan-50 text-cyan-600 border-cyan-200" },
              { label: "Storytelling", action: () => setToneFilter("storytelling"), active: toneFilter === "storytelling", activeClass: "bg-purple-50 text-purple-600 border-purple-200" },
            ].map(({ label, action, active, activeClass }) => (
              <button
                key={label}
                onClick={action}
                className={`px-2.5 py-1 rounded-full border transition-colors ${
                  active
                    ? activeClass
                    : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100 hover:text-gray-700"
                }`}
              >
                {label}
              </button>
            ))}
            {hasActiveFilter && (
              <button onClick={resetFilters} className="ml-auto text-indigo-500 hover:text-indigo-700 font-medium transition-colors">
                Reset filters
              </button>
            )}
          </div>
        </div>

        {/* ── Voice Grid ── */}
        {isLoading ? (
          <div className="py-24 text-center space-y-3">
            <div className="w-10 h-10 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-gray-500 text-sm">Loading Indian voice catalog...</p>
          </div>
        ) : catalogVoices.length === 0 ? (
          <div className="py-20 text-center rounded-2xl bg-white/70 backdrop-blur-xl border border-white/80 p-10 shadow-sm">
            <Radio className="w-10 h-10 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-800">No voices match your filters</h3>
            <p className="text-gray-400 text-sm mt-1">Try resetting the filters or modifying your search.</p>
            <button
              onClick={resetFilters}
              className="mt-5 px-5 py-2.5 rounded-xl bg-gray-900 hover:bg-gray-800 text-white text-xs font-semibold transition-colors"
            >
              Clear All Filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {catalogVoices.map((voice) => {
              const isPlaying = playingVoiceId === voice.id;
              return (
                <div
                  key={voice.id}
                  className="group rounded-2xl bg-white/70 backdrop-blur-xl border border-white/80 hover:border-indigo-200/60 hover:shadow-xl hover:shadow-purple-500/10 p-6 flex flex-col justify-between transition-all"
                >
                  <div>
                    {/* Top row */}
                    <div className="flex items-start justify-between gap-3 mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-tr ${voice.avatar_color} flex items-center justify-center text-white text-lg font-bold shadow-md`}>
                          {voice.display_name.charAt(0)}
                        </div>
                        <div>
                          <h3 className="font-bold text-gray-900 text-base leading-tight">{voice.display_name}</h3>
                          <p className="text-xs text-gray-400 mt-0.5">{voice.accent}</p>
                        </div>
                      </div>

                      {/* Play button */}
                      <button
                        onClick={() => handlePlaySample(voice)}
                        className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
                          isPlaying
                            ? "bg-gradient-to-br from-indigo-500 to-purple-500 text-white scale-105 shadow-md shadow-purple-500/30"
                            : "bg-gray-100 hover:bg-indigo-50 text-gray-500 hover:text-indigo-600 border border-gray-200 hover:border-indigo-200"
                        }`}
                        title={isPlaying ? "Pause sample" : "Play voice sample"}
                      >
                        {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
                      </button>
                    </div>

                    {/* Waveform animation when playing */}
                    {isPlaying && (
                      <div className="mb-4 p-2.5 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-between">
                        <div className="flex items-center gap-1.5 h-5 px-1">
                          {[1,2,3,4,5].map((i) => (
                            <div key={i} className={`w-1 bg-indigo-400 rounded-full animate-wave-${i}`} />
                          ))}
                        </div>
                        <span className="text-[11px] text-indigo-500 font-mono font-medium">Playing Preview...</span>
                      </div>
                    )}

                    {/* Badges */}
                    <div className="flex flex-wrap items-center gap-1.5 mb-3">
                      <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-gray-100 text-gray-600 border border-gray-200 capitalize">{voice.gender}</span>
                      <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-gray-100 text-gray-600 border border-gray-200 capitalize">{voice.age_style}</span>
                      <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-purple-50 text-purple-600 border border-purple-200 capitalize">{voice.tone}</span>
                      <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-50 text-emerald-600 border border-emerald-200">{voice.language}</span>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-gray-500 line-clamp-2 mb-4 leading-relaxed">{voice.description}</p>
                  </div>

                  {/* Footer */}
                  <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-emerald-600 text-[11px]">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{voice.license_type}</span>
                    </div>
                    <Link
                      href={`/studio?voice=${voice.id}`}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-900 hover:bg-gray-800 text-white text-xs font-semibold transition-colors shadow-sm"
                    >
                      <Mic className="w-3.5 h-3.5" />
                      Use in Studio
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      {fishAccessOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) setFishAccessOpen(false); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="fish-access-title" className="relative w-full max-w-md overflow-hidden rounded-3xl border border-white/60 bg-white shadow-2xl">
            <button onClick={() => setFishAccessOpen(false)} aria-label="Close" className="absolute right-4 top-4 rounded-full p-2 text-white/80 transition hover:bg-white/15 hover:text-white"><X className="h-5 w-5" /></button>
            <div className="bg-gradient-to-br from-indigo-700 via-violet-700 to-fuchsia-700 px-7 pb-7 pt-8 text-center text-white">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15"><LockKeyhole className="h-6 w-6" /></div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/75">Fish Audio collection</p>
              <h2 id="fish-access-title" className="mt-2 text-2xl font-bold">Unlock premium voices</h2>
              <p className="mt-2 text-sm leading-relaxed text-white/80">Sign in or start your free trial to access Fish Audio voices and the full studio.</p>
            </div>
            <div className="space-y-3 p-6">
              <button onClick={() => openAuth("signup")} className="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700">Buy subscription / Start free trial</button>
              <button onClick={() => openAuth("login")} className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-semibold text-gray-800 transition hover:bg-gray-50">Sign in</button>
              <p className="text-center text-[11px] text-gray-400">No payment is collected in this demo checkout.</p>
            </div>
          </section>
        </div>
      )}
      <AuthModal isOpen={authOpen} onClose={() => setAuthOpen(false)} onSuccess={handleAuthSuccess} initialTab={authTab} />
    </div>
  );
}
