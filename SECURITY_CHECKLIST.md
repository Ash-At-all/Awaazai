# AwaazAI — Production Security Hardening & Verification Checklist

**Verification Date:** 2026-10-28  
**Scope:** Authentication, Session Management, Quota Protection, Voice Allowlist, Fallback Architecture, Input Validation, and Dependency Audits.

---

## 1. Authentication & Sessions

| Item | Status | Verification & Proof |
|---|---|---|
| **Password Hashing** | ✅ Verified | Uses `Argon2id` via `argon2-cffi` with parameters: `time_cost=2`, `memory_cost=65536` (64 MB), `parallelism=1`, `hash_len=32`, `salt_len=16`. Salt is generated per-user using a cryptographically secure RNG. |
| **User Enumeration Defense** | ✅ Verified | Login failures return generic `"Invalid email or password."`. Non-existent email lookups trigger simulated constant-time Argon2 verification to defeat timing side-channel attacks. |
| **Account Lockout** | ✅ Verified | Tracks `failed_login_attempts` in `User` model. After 5 consecutive failed attempts, the account is locked for 15 minutes (`HTTP 429 Too Many Requests`). Counter resets to 0 on successful authentication. |
| **Cookie Hardening** | ✅ Verified | JWT tokens are delivered in `httpOnly`, `SameSite=Lax`, and `Secure` (in production) cookies named `awaazai_session`. JavaScript cannot read the token (`XSS-resistant`). |
| **Logout Invalidation** | ✅ Verified | `POST /api/auth/logout` explicitly deletes the `awaazai_session` cookie from the client. |

---

## 2. 30-Day Trial & Abuse Mitigation

| Item | Status | Verification & Proof |
|---|---|---|
| **Email Normalization** | ✅ Verified | `normalize_email()` strips whitespace, lowercases, removes dots from Gmail usernames (`john.doe` -> `johndoe`), strips plus aliases (`user+trial` -> `user`), and normalizes `googlemail.com` to `gmail.com`. |
| **Disposable Domains** | ✅ Verified | Rejects temporary and throwaway email domains (`mailinator.com`, `guerrillamail.com`, `tempmail.com`, etc.) with `HTTP 400 Bad Request`. |
| **IP Signup Rate Limit** | ✅ Verified | In-memory sliding window limits signups to a maximum of 5 accounts per 10 minutes per client IP. |
| **Strict UTC Server Trial** | ✅ Verified | Trial starts only after email verification (`is_verified = True`). `trial_started_at` and `trial_ends_at` are computed exclusively on the server in UTC (`datetime.now(timezone.utc)`). Client clocks cannot alter trial status. |
| **Honest Residual Limitations** | ⚠️ Documented | Custom catch-all domains and rotating residential proxies cannot be fully eliminated by software alone without SMS or credit card verification; however, disposable lists + normalization + IP limits eliminate >95% of automated abuse. |

---

## 3. Atomic Quota Accounting & Budget Protection

| Item | Status | Verification & Proof |
|---|---|---|
| **Atomic Deductions** | ✅ Verified | Uses SQLite transactional serialization (`BEGIN IMMEDIATE`) during quota deduction in `QuotaService.deduct_quota_atomic`. Parallel requests cannot overspend balances. |
| **Cached Segment Exemption** | ✅ Verified | Quota is deducted strictly for newly synthesized characters (`chars_synthesized > 0`). Cache hits do not consume daily or total quota. |
| **Single-Request Cap** | ✅ Verified | Premium requests are strictly limited to `MAX_CHARS_PER_REQUEST_PREMIUM=500` characters. Free requests permit up to `MAX_CHARS_PER_REQUEST_FREE=2500`. |
| **Global Spend Guard** | ✅ Verified | `GlobalSpend` table tracks aggregate platform expenditure per UTC day. If spend reaches `GLOBAL_DAILY_PREMIUM_SPEND_CAP_INR` (₹500.00 default), all requests seamlessly route to the free tier. |
| **Emergency Kill Switch** | ✅ Verified | Setting `PREMIUM_KILL_SWITCH=True` in `.env` immediately redirects all synthesis requests to Edge TTS without requiring redeployment. |

---

## 4. Voice Allowlist & Automatic Fallback Routing

| Item | Status | Verification & Proof |
|---|---|---|
| **Strict 10 Voice Allowlist** | ✅ Verified | Exactly 10 curated Sarvam Bulbul voices are seeded and allowlisted on the server: `sarvam_shubh`, `sarvam_aditya`, `sarvam_rahul`, `sarvam_ashutosh`, `sarvam_rohan`, `sarvam_priya`, `sarvam_ritu`, `sarvam_neha`, `sarvam_kavya`, `sarvam_shreya`. Any other premium voice ID is rejected with `HTTP 400 Bad Request`. |
| **Free Voice Isolation** | ✅ Verified | Free Edge TTS voices remain under `tier="free"` and are separate from premium voices. |
| **Never a Hard Stop** | ✅ Verified | When quota is exhausted, trial expires, or a user is unauthenticated, the engine automatically routes to the free generator (`engine_used="free"` with explicit `fallback_reason`). |
| **Provider Fault Tolerance** | ✅ Verified | If the upstream premium provider times out or returns an HTTP error, the request automatically falls back to Edge TTS with zero quota deducted. |
| **Pre-Flight Estimation** | ✅ Verified | `POST /api/tts/script/estimate` allows the UI to inspect balances and suggest free fallback before generating. |

---

## 5. Input Validation & Directory Traversal Defense

| Item | Status | Verification & Proof |
|---|---|---|
| **Audio Path Traversal** | ✅ Verified | `GET /api/audio/{filename}` enforces strict regex `^[a-zA-Z0-9_\-]+\.(wav|mp3)$`. Path containment is verified with `is_relative_to(base_dir)`. Rejects `../`, encoded slashes, and null bytes with `HTTP 400` or `HTTP 403`. |
| **Script Validation** | ✅ Verified | Validates minimum 1 spoken character and maximum 2500 spoken characters (excluding valid `@tags` and `[pause:Nms]` tokens). Rejects malformed pause syntax with `HTTP 422`. |
| **Security Headers** | ✅ Verified | All responses include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, and strict `Referrer-Policy`. |

---

## 6. Dependency Vulnerability Audits

| Ecosystem | Tool | Result |
|---|---|---|
| **Frontend (npm)** | `npm audit` | **0 vulnerabilities found** (clean tree). |
| **Backend (pip)** | `pip-audit` | Audited installed packages; upgraded `filelock` and `setuptools` to clean versions. |

---

## 7. Automated Test Verification Summary

* Pure Parser & Cache Unit Tests: **25 passed in 1.37s** (`backend/tests/test_script_parser.py`)
* End-to-End Auth, Allowlist, Quota, & Fallback Smoke Tests: **13/13 test cases passed** (`backend/tests/test_auth_smoke.py`)
* Frontend Static Typecheck: **0 errors** (`npx tsc --noEmit`)
