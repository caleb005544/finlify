# Day 2 Runbook: Supabase + Email Auth

Goal for Day 2:
- Real user auth via email/password
- Real watchlist/profile data in Supabase
- Frontend can read/write `user_watchlist` and `assumption_profiles`

## 1) Create Supabase Project

1. Create a new Supabase project in your target region.
2. Open Project Settings -> API.
3. Copy:
   - `Project URL`
   - `anon public` key

## 2) Configure Auth (Email)

1. Go to Authentication -> Providers -> Email.
2. Enable Email provider.
3. Keep "Confirm email" enabled for production-like flow.
4. Go to Authentication -> URL Configuration and set:
   - Site URL:
     - `https://<your-frontend-domain>.vercel.app`
   - Redirect URLs:
     - `http://localhost:3000/auth/callback`
     - `https://<your-frontend-domain>.vercel.app/auth/callback`

## 3) Apply Database Schema + RLS

1. Open SQL Editor in Supabase.
2. Run the SQL in:
   - `docs/day2_supabase.sql`
3. Confirm tables exist:
   - `public.user_watchlist`
   - `public.assumption_profiles`

## 4) Set Environment Variables

Local `.env` at repo root:

```env
NEXT_PUBLIC_SUPABASE_URL=<your_supabase_project_url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your_supabase_anon_public_key>
NEXT_PUBLIC_API_URL=http://localhost:8000
FINLIFY_POLICY_ID=balanced_v1
BACKEND_CORS_ORIGINS=http://localhost:3000,https://<your-frontend-domain>.vercel.app
```

Vercel `frontend` project env:

```env
NEXT_PUBLIC_SUPABASE_URL=<your_supabase_project_url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your_supabase_anon_public_key>
NEXT_PUBLIC_API_URL=https://<your-backend-domain>.vercel.app
```

Vercel `backend` project env:

```env
BACKEND_CORS_ORIGINS=https://<your-frontend-domain>.vercel.app
FINLIFY_POLICY_ID=balanced_v1
```

## 5) Day 2 Acceptance Checks

1. Signup at `/signup` with a real email.
2. Click verify link in email and land on `/auth/callback`.
3. Login at `/login` succeeds and can reach `/dashboard`.
4. Add ticker to watchlist in dashboard and reload page.
5. Update assumption profile and reload page.
6. Verify data is present in Supabase table rows for that user.

## 6) Known Gaps To Schedule

1. `frontend` currently references `/reset-password`, `/settings`, and `/auth/auth-code-error` routes that are not implemented yet.
2. Add these routes (even as minimal pages) before wider external trial.

