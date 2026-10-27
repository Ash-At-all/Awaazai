# AwaazAI Pre-Deployment Security Checklist

Use this checklist before releasing or deploying AwaazAI to staging or production environments.

- [ ] **1. Secrets Management**
  - [ ] No real API keys, tokens, or credentials committed to version control.
  - [ ] Production `.env` configured securely via secrets manager (AWS Secrets Manager, Doppler, Vault).
  - [ ] API keys rotated if exposed in local development or logs.

- [ ] **2. Authentication & Authorization**
  - [ ] API keys or OAuth authentication enabled for administrative and generation endpoints.
  - [ ] Per-user authorization enforced on private audio generations and custom voices.
  - [ ] Rate limits configured per IP and per authenticated user.

- [ ] **3. Input Validation & File Security**
  - [ ] Filenames sanitized with strict regex (`^[a-zA-Z0-9_-]+\.(wav|mp3)$`).
  - [ ] Canonical path traversal protection verified (`is_relative_to` / `commonpath`).
  - [ ] Text inputs capped at maximum character limits (`MAX_CHAR_LIMIT <= 2500`).
  - [ ] Subprocess arguments parameterized with absolute paths and strict timeouts.

- [ ] **4. Network & Transport Security**
  - [ ] HTTPS enforced (TLS 1.3 / 1.2).
  - [ ] Strict CORS origins configured (no wildcard `*` with credentials in production).
  - [ ] HTTP Security Headers enabled (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `HSTS`).

- [ ] **5. AI & Voice Protection**
  - [ ] AI-Generated Voice disclosure embedded in metadata (ID3 / WAV RIFF headers).
  - [ ] Consent agreements and licensing proofs verified for all production voice models.
  - [ ] Voice cloning restricted to authenticated users with validated consent.

- [ ] **6. Reliability & DoS Prevention**
  - [ ] Global and per-endpoint sliding-window rate limiters active.
  - [ ] Maximum concurrency limits on audio synthesis workers.
  - [ ] Automatic disk cleanup policy for cached audio files.
