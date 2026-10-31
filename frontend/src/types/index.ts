export interface Voice {
  id: string;
  display_name: string;
  provider: string;
  provider_voice_id: string;
  gender: "male" | "female";
  age_style: string;
  tone: string;
  language: string;
  accent: string;
  description: string;
  sample_text: string;
  sample_url: string;
  license_type: string;
  consent_proof_url: string;
  is_published: boolean;
  avatar_color: string;
  tier?: "free" | "premium" | "featured";
  is_active?: boolean;
  created_at?: string;
}

export interface UserQuota {
  is_trial_active: boolean;
  days_left: number;
  trial_ends_at?: string | null;
  premium_daily_chars_left: number;
  premium_total_chars_left: number;
  free_daily_chars_left: number;
  current_engine: "premium" | "free";
  ineligibility_reason?: string | null;
}

export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
  is_verified: boolean;
  trial_started_at?: string | null;
  trial_ends_at?: string | null;
}

export interface TTSRequest {
  text: string;
  voice_id: string;
  speed: number;
  pitch: number;
  stability: number;
  format: "wav" | "mp3";
  provider?: string;
}

export interface TTSResponse {
  id: string;
  filename: string;
  audio_url: string;
  download_url: string;
  duration_seconds: float;
  cached: boolean;
  ai_label: string;
  voice: Voice;
  speed: number;
  pitch: number;
  stability: number;
  format: string;
  engine_used?: "premium" | "free";
  fallback_reason?: string | null;
}

type float = number;

// ── Multi-voice Script Editor types ────────────────────────────
export interface ScriptArtist {
  id: string;
  name: string;
  voice_id: string;
  speed: number;       // integer slider: -2 to +3
  stability: number;   // 0.0 to 1.0
  color: string;       // tailwind color class for chip/tag highlight
}

export interface ScriptTTSRequest {
  artists: {
    id: string;
    name: string;
    voice_id: string;
    speed: number;
    stability: number;
  }[];
  script: string;
  audio_format: "wav" | "mp3";
}

export interface ScriptSegment {
  type: "dialogue" | "pause";
  artist?: string;
  artist_id?: string;
  text?: string;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  source_start?: number;
  source_end?: number;
}

export interface StemOut {
  artist_id: string;
  artist_name: string;
  stem_url: string;
}

export interface ScriptTTSResponse {
  id: string;
  audio_url: string;
  download_url: string;
  srt_url: string;
  transcript_url: string;
  duration_seconds: number;
  segments: ScriptSegment[];
  cached: boolean;
  ai_label: string;
  format: string;
  spoken_char_count: number;
  characters_submitted: number;
  characters_cached: number;
  characters_synthesized: number;
  estimated_cost_inr: number;
  stems: StemOut[];
  engine_used?: "premium" | "free";
  fallback_reason?: string | null;
}
