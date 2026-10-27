# AwaazAI — Comprehensive Security Audit Report

**Date:** 2026-10-27  
**Auditor:** Senior Application Security & DevSecOps Engineer  
**Scope:** Full-Stack Codebase Inspection (`backend` & `frontend`)  
**Status:** Audit Completed — Remediation Plan Defined

---

## Executive Summary

A comprehensive architectural, cryptographic, access control, and attack surface analysis was performed on **AwaazAI** (`INConvo`), an ElevenLabs-style generative speech synthesis platform for Indian languages (Hindi & Hinglish).

The current application consists of:
- **Frontend:** Next.js 16 (Turbopack / App Router), React 19, Tailwind CSS v4, Lucide icons.
- **Backend:** FastAPI (Python 3.13), SQLAlchemy ORM with SQLite database (`awaazai.db`).
- **TTS Core:** Modular provider abstraction with an offline/neural hybrid fallback provider (`edge-tts` + procedural acoustic synthesis) and stubs for Azure, Sarvam, Google, and ElevenLabs.
- **Audio Processing:** Mutagen (ID3 tagging), FFmpeg / wave / subprocess manipulation for concatenation and duration probe.

While the core functionality operates locally, the audit identified **7 critical and high vulnerabilities** spanning path traversal, missing authentication/authorization, denial-of-service / resource exhaustion, command injection / subprocess safety, and absent security headers.

---

## Vulnerability Priority Matrix

| ID | Title | Component | Severity | Confidence | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Arbitrary File Read / Path Traversal in `/api/audio/{filename}` | Backend (`tts.py`) | **Critical** | High | Identified |
| **SEC-02** | Unauthenticated & Unthrottled TTS Synthesis / DoS Amplification | Backend (`tts.py`, `config.py`) | **High** | High | Identified |
| **SEC-03** | Subprocess Command Injection Surface & Unsafe Fallback in Audio Pipeline | Backend (`audio_service.py`, `stitcher.py`) | **High** | High | Identified |
| **SEC-04** | Missing Authentication & Access Control on Voice & Audio APIs | Backend (`main.py`, `voices.py`, `tts.py`) | **High** | High | Identified |
| **SEC-05** | Missing Security Headers & Lax CORS Configuration | Backend (`main.py`) | **Medium** | High | Identified |
| **SEC-06** | Insecure Secrets Management & Unrestricted Environment Loading | Backend (`config.py`, `.env`) | **Medium** | High | Identified |
| **SEC-07** | Cache Poisoning & Disk Exhaustion via Unbounded Synthetic Audio Hashes | Backend (`audio_service.py`, `tts.py`) | **Medium** | High | Identified |

---

## Detailed Findings

### SEC-01: Arbitrary File Read / Path Traversal in `/api/audio/{filename}`
- **Severity:** Critical (CVSS 8.6)
- **Affected File & Function:** `backend/app/routers/tts.py` -> `get_audio_file(filename: str, ...)`
- **Evidence:**
  ```python
  @router.get("/audio/{filename}")
  async def get_audio_file(filename: str, download: bool = Query(False)):
      file_path = settings.AUDIO_DIR / filename
      if not file_path.exists():
          raise HTTPException(status_code=404, detail="Audio file not found")
      return FileResponse(path=str(file_path), ...)
  ```
- **Impact:** An attacker can request `../../awaazai.db` or `../../.env` or system files through URL path traversal (`/api/audio/..%2F..%2F.env`), leaking secret API keys and database contents.
- **Reproduction:**
  ```bash
  curl http://127.0.0.1:8000/api/audio/..%2F..%2F.env
  ```
- **Remediation:**
  1. Restrict `filename` using strict alphanumeric regex (`^[a-fA-F0-9_-]+\.(wav|mp3)$`).
  2. Resolve the path canonicalized (`file_path.resolve()`) and ensure `file_path.resolve().is_relative_to(settings.AUDIO_DIR.resolve())`.

---

### SEC-02: Unauthenticated & Unthrottled TTS Synthesis / DoS Amplification
- **Severity:** High (CVSS 7.5)
- **Affected File & Function:** `backend/app/routers/tts.py` -> `generate_tts(req: TTSRequest)`
- **Evidence:**
  `config.py` defined `RATE_LIMIT_PER_MINUTE = 60`, but no rate-limiting middleware or dependency exists in FastAPI. Anyone can hammer `/api/tts` with 2,500 character inputs continuously, causing CPU exhaustion, disk starvation, and third-party API quota exhaustion.
- **Impact:** Financial drain, denial of service for legitimate users, local disk filling up with gigabytes of synthetic `.wav` files.
- **Remediation:**
  Implement in-memory sliding window or token-bucket rate limiter per IP/client, request size limits, and concurrency guards on synthesis workers.

---

### SEC-03: Subprocess Safety & Error Handling in Audio Pipeline
- **Severity:** High (CVSS 7.2)
- **Affected File & Function:** `backend/app/services/stitcher.py` and `audio_service.py`
- **Evidence:**
  - `stitcher.py` uses temporary files with `safe 0` concat in FFmpeg:
    ```python
    p_str = audio_p.resolve().as_posix().replace("'", "'\\''")
    list_file.write(f"file '{p_str}'\n")
    ```
  - `mock_provider.py` creates temp files and calls `os.unlink()` without strict exception containment.
  - Subprocess timeouts and shell execution are vulnerable if untrusted file paths are passed.
- **Impact:** Failed cleanup causing temp file leaks; potential command or filter injection if filename control is subverted.
- **Remediation:** Enforce strict path validation, isolated temp directories, guaranteed context managers for file cleanup, and parameterized list arguments.

---

### SEC-04: Missing Authentication & Access Control on Voice & Audio APIs
- **Severity:** High (CVSS 7.1)
- **Affected File & Function:** `backend/app/routers/tts.py`, `backend/app/routers/voices.py`
- **Evidence:**
  There is zero session validation, API key check, or user identity binding. Generated audio belongs to no user (`AudioGeneration` table has no `user_id` or ownership columns). Anyone can view all voices, execute generation, and access all audio artifacts.
- **Impact:** Cross-user data leakage in multi-user deployment; inability to enforce user quotas or billing.
- **Remediation:**
  Introduce an extensible security dependency layer:
  - API Key / Session authentication middleware or header validation (`X-API-Key` or Bearer token option).
  - User identity context attached to generation requests and storage metadata.

---

### SEC-05: Missing Security Headers & Lax CORS Configuration
- **Severity:** Medium (CVSS 5.3)
- **Affected File & Function:** `backend/app/main.py`
- **Evidence:**
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.CORS_ORIGINS,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  No security headers middleware (`Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`) are configured.
- **Impact:** Clickjacking, MIME-type sniffing, cross-site script inclusion in hostile browser environments.
- **Remediation:** Add strict HTTP security headers middleware to all responses.

---

### SEC-06: Insecure Secrets Management & Missing .gitignore Coverage
- **Severity:** Medium (CVSS 5.0)
- **Affected Files:** Root `.gitignore` (missing initially), `backend/.env`
- **Evidence:**
  The repository was not initialized with Git, lacking a root `.gitignore`. A `.env` file containing provider keys was unprotected against accidental repository commits.
- **Impact:** Accidental credential exposure to version control.
- **Remediation:**
  - Implemented root `.gitignore` excluding all `.env`, `*.db`, `storage/audio/*.wav`.
  - Created sanitized `backend/.env.example`.

---

### SEC-07: Cache Poisoning & Disk Exhaustion via Unbounded Synthetic Audio Hashes
- **Severity:** Medium (CVSS 4.8)
- **Affected File & Function:** `backend/app/services/audio_service.py` -> `compute_cache_key`
- **Evidence:**
  Anyone can send millions of minor text variations to generate unique SHA-256 `.wav` files that never expire, causing unmetered disk bloat.
- **Impact:** Exhaustion of local disk storage.
- **Remediation:**
  Add storage quota checks, maximum file count verification, and sanitize cache key inputs.

---

## Action Plan & Roadmap

1. **Phase 2 & 3:** Implement path traversal prevention on `/api/audio/{filename}` and `/api/voices/{voice_id}/sample`.
2. **Phase 3 & 4:** Implement IP-based sliding-window Rate Limiter Middleware and Request Validator.
3. **Phase 3:** Implement Security Headers Middleware (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`).
4. **Phase 4 & 5:** Sanitize file names, enforce safe tempfile handling in `AudioStitcher` and `MockTTSProvider`, and guarantee safe cleanup.
5. **Phase 6:** Implement caching and audio stream optimizations (ETags, range headers, fast lookup).
6. **Phase 8:** Author automated security regression tests verifying fixes against path traversal, oversized inputs, and rate limiting.
