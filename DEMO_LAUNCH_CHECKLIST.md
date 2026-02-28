# Finlify Demo Launch Checklist

## Phase A: Auth & Database (1-2 days)

### Supabase Setup
- [x] Confirm Supabase project is created (URL + Anon Key in .env)
- [ ] Execute `docs/day2_supabase.sql` to create table schema
- [ ] Verify tables exist: `user_watchlist` and `assumption_profiles`
- [ ] Enable Row Level Security (RLS) on both tables

### Auth Flow Testing
- [ ] Test complete signup flow (Sign Up → Email verification → Log In)
- [ ] Test email verification link redirects correctly
- [ ] Test login with valid credentials
- [ ] Test login fails with invalid credentials
- [ ] Verify redirect to original page after login (auth redirect)
- [ ] Test logout functionality

### Watchlist & Profile Testing
- [ ] Test adding ticker to watchlist
- [ ] Test removing ticker from watchlist
- [ ] Verify watchlist persists after page reload
- [ ] Test updating assumption profile (risk_level, horizon, sector_preference)
- [ ] Verify profile updates persist after page reload
- [ ] Test user can only see their own watchlist/profile (RLS)

### Missing Routes Implementation
- [x] Implement `/reset-password` page
- [x] Implement `/settings` page
- [x] Implement `/auth/auth-code-error` page

---

## Phase B: Frontend & UX Validation (0.5-1 day)

### Public Pages
- [x] Test `/` (homepage) - search box works and navigates to ticker
- [x] Test `/ticker/[ticker]` - accessible without login
- [x] Test `/demo` - has clear introduction and CTA
- [x] Test `/about` - content is complete

### Loading & Error States
- [x] All pages have skeleton loaders or spinners while loading
- [ ] All pages display clear error messages (no blank/broken screens)
- [ ] Test network error handling on market data endpoints
- [ ] Test timeout handling for slow API responses

### Responsive Design
- [ ] Test all pages on mobile device (iPhone size)
- [ ] Test all pages on tablet size
- [ ] Test all pages on desktop
- [ ] Verify navigation works on all screen sizes

### Code Quality
- [ ] Clear all `console.error` warnings from browser console
- [ ] Clear all `console.warn` warnings from browser console
- [ ] No TypeScript type errors in console
- [ ] No React warnings about missing dependencies or keys

---

## Phase C: Cloud Deployment (2-3 days)

### Backend Setup (Finnhub API)
- [ ] Acquire Finnhub API Key from https://finnhub.io (free tier)
- [ ] Add `FINNHUB_API_KEY` to `.env`
- [ ] Test `/api/quotes` endpoint returns real data
- [ ] Test `/api/history` endpoint returns real data
- [ ] Test `/api/search` endpoint returns real results

### Frontend → Vercel Deployment
- [ ] Create Vercel project and connect GitHub repo
- [ ] Set all environment variables in Vercel Dashboard:
  - [ ] `NEXT_PUBLIC_SUPABASE_URL`
  - [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - [ ] `NEXT_PUBLIC_API_URL` (pointing to backend domain)
- [ ] Verify `next.config.ts` has no blocking settings
- [ ] Test Vercel Preview Deployment builds successfully
- [ ] Deploy to production

### Backend → Vercel or Fly.io
- [ ] Decide deployment platform (Vercel or Fly.io)
- [ ] **If Vercel:**
  - [ ] Verify `backend/vercel.json` config is correct
  - [ ] Set environment variables in Vercel Dashboard
  - [ ] Test `POST /score` endpoint works online
  - [ ] Test `POST /forecast` endpoint works online
- [ ] **If Fly.io:**
  - [ ] Run `fly launch` to initialize
  - [ ] Configure `fly.toml` settings
  - [ ] Set environment variables
  - [ ] Deploy and test endpoints

### Forecast Service → Fly.io
- [ ] Run `fly launch` to initialize forecast service
- [ ] Set `FORECAST_CORS_ORIGINS` to online frontend domain
- [ ] Configure persistent volume for `FORECAST_USAGE_LOG_DB_PATH`
- [ ] Test `POST /forecast` works online
- [ ] Test `GET /runtime/status` responds correctly

### CORS Configuration
- [ ] Set `BACKEND_CORS_ORIGINS` to Vercel frontend URL
- [ ] Set `FORECAST_CORS_ORIGINS` to Vercel frontend URL
- [ ] Verify frontend `NEXT_PUBLIC_API_URL` points to online backend
- [ ] Verify forecast requests use online Forecast Service URL
- [ ] Test cross-origin requests work without CORS errors

---

## Phase D: Final QA & Launch (1 day)

### End-to-End Testing
- [ ] Complete flow: Search stock → Enter Ticker page → View history chart → View forecast
- [ ] Complete auth flow: Sign Up → Verify email → Log In → Add Watchlist → Log Out
- [ ] Test on mobile browser (RWD)
- [ ] Test all internal links navigate correctly

### Demo Protection (Optional - for closed beta)
- [ ] Set `DEMO_BASIC_AUTH_ENABLED=true` in online environment
- [ ] Configure `DEMO_BASIC_AUTH_USERNAME` and `DEMO_BASIC_AUTH_PASSWORD`
- [ ] Test unauthorized access prompts Basic Auth dialog
- [ ] Test authorized access grants full access

### Security Verification
- [ ] Confirm all services use HTTPS (Vercel/Fly.io provide by default)
- [ ] Verify Supabase RLS is enabled on all tables
- [ ] Confirm API keys are NOT exposed in frontend code
- [ ] Verify `.gitignore` prevents `.env` from being committed
- [ ] Check no secrets in git history

### Final Test Suite
- [ ] Run complete backend test suite: `pytest tests/ -v` (112 tests)
- [ ] Run forecast service tests (8 tests)
- [ ] Verify all tests pass
- [ ] No console errors or warnings in any browser tab

### CI/CD Setup (Optional but Recommended)
- [ ] Configure GitHub Actions to run backend tests on PR
- [ ] Configure GitHub Actions to run forecast tests on PR
- [ ] Enable Vercel Preview Deployment for PRs
- [ ] Test that PR previews deploy successfully

---

## Summary

**Total Estimated Time:** 6-9 days

**Parallel Execution Opportunity:** Phase B & C can run in parallel to save time.

**Critical Path:**
1. Phase A (Auth & Database) - Highest priority, blocks Phase D testing
2. Phase B (Frontend UX) - Can start immediately in parallel
3. Phase C (Cloud Deployment) - Can start after Phase A basics
4. Phase D (QA & Launch) - Final validation before public release

---

## Progress Tracking

- **✅ Completed:**
  - Backend tests (112/112 passing)
  - Market API integration (Finnhub endpoints working)
  - Supabase setup (SQL schema executed, RLS enabled)
  - All auth routes implemented (/signup, /login, /reset-password, /settings)
  - Frontend components (Watchlist, Profile, Dashboard)
  - Email verification flow fixed

- **⏳ In Progress:**
  - Phase A testing (auth flow, watchlist, profile)
  - Phase B frontend UX validation

- **⏱️ Pending:**
  - Phase C: Vercel/Fly.io deployment
  - Phase D: Final QA and launch

---

## Immediate Next Steps (Within 24 hours)

### 1. Complete Phase A Testing (2-3 hours)
- [ ] Test signup → email verification → login flow
- [ ] Test watchlist add/remove
- [ ] Test profile save/update
- [ ] Verify Supabase data persistence

### 2. Phase B: Frontend Validation (1 hour)
- [ ] Test RWD on mobile/tablet
- [ ] Clear console errors/warnings
- [ ] Verify error handling

### 3. Phase C: Deployment Planning (2-4 hours)
- [ ] Create Vercel projects for frontend
- [ ] Deploy backend to Vercel or Fly.io
- [ ] Configure environment variables
- [ ] Test online endpoints

### 4. Phase D: Final QA (1 hour)
- [ ] End-to-end testing
- [ ] Security verification
- [ ] Performance check
