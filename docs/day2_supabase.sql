-- Finlify Day 2: Supabase schema + RLS bootstrap
-- Execute in Supabase SQL Editor

create extension if not exists pgcrypto;

create table if not exists public.user_watchlist (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  ticker text not null,
  created_at timestamptz not null default timezone('utc', now()),
  constraint user_watchlist_ticker_format_chk
    check (
      char_length(trim(ticker)) > 0
      and ticker = upper(ticker)
      and ticker ~ '^[A-Z.-]+$'
    )
);

create unique index if not exists user_watchlist_user_ticker_uniq
  on public.user_watchlist (user_id, ticker);

create index if not exists user_watchlist_user_created_at_idx
  on public.user_watchlist (user_id, created_at desc);

create table if not exists public.assumption_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  risk_level text not null check (risk_level in ('Low', 'Medium', 'High')),
  horizon text not null check (horizon in ('Short', 'Medium', 'Long')),
  sector_preference text not null check (char_length(trim(sector_preference)) > 0),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists set_assumption_profiles_updated_at on public.assumption_profiles;
create trigger set_assumption_profiles_updated_at
before update on public.assumption_profiles
for each row
execute function public.set_updated_at();

alter table public.user_watchlist enable row level security;
alter table public.assumption_profiles enable row level security;

drop policy if exists watchlist_select_own on public.user_watchlist;
create policy watchlist_select_own
on public.user_watchlist
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists watchlist_insert_own on public.user_watchlist;
create policy watchlist_insert_own
on public.user_watchlist
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists watchlist_delete_own on public.user_watchlist;
create policy watchlist_delete_own
on public.user_watchlist
for delete
to authenticated
using (auth.uid() = user_id);

drop policy if exists profile_select_own on public.assumption_profiles;
create policy profile_select_own
on public.assumption_profiles
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists profile_insert_own on public.assumption_profiles;
create policy profile_insert_own
on public.assumption_profiles
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists profile_update_own on public.assumption_profiles;
create policy profile_update_own
on public.assumption_profiles
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

grant usage on schema public to anon, authenticated;
grant select, insert, delete on public.user_watchlist to authenticated;
grant select, insert, update on public.assumption_profiles to authenticated;

