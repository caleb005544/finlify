-- Stocks Table (Cache)
create table public.stocks (
  ticker text primary key,
  name text,
  sector text,
  last_refreshed_at timestamp with time zone default timezone('utc'::text, now())
);

-- User Watchlist
create table public.user_watchlist (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users not null,
  ticker text references public.stocks(ticker),
  created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Assumption Profiles
create table public.assumption_profiles (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users not null,
  name text default 'Default Profile',
  risk_level text check (risk_level in ('Low', 'Medium', 'High')),
  horizon text check (horizon in ('Short', 'Medium', 'Long')),
  sector_preference text,
  created_at timestamp with time zone default timezone('utc'::text, now()),
  updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- RLS Policies
alter table public.user_watchlist enable row level security;
alter table public.assumption_profiles enable row level security;
alter table public.stocks enable row level security;

-- Watchlist: Users can read/insert/delete their own
create policy "Users can view own watchlist" on public.user_watchlist
  for select using (auth.uid() = user_id);

create policy "Users can insert own watchlist" on public.user_watchlist
  for insert with check (auth.uid() = user_id);

create policy "Users can delete own watchlist" on public.user_watchlist
  for delete using (auth.uid() = user_id);

-- Profiles: Users can read/insert/update their own
create policy "Users can view own profiles" on public.assumption_profiles
  for select using (auth.uid() = user_id);

create policy "Users can insert own profiles" on public.assumption_profiles
  for insert with check (auth.uid() = user_id);

create policy "Users can update own profiles" on public.assumption_profiles
  for update using (auth.uid() = user_id);

-- Stocks: Public read, Server write (service role)
create policy "Public read stocks" on public.stocks
  for select using (true);

-- Insert policy for stocks handled by backend service role usually, 
-- or we allow authenticated users to insert if it doesn't exist (optimistic)
create policy "Auth users can insert stocks" on public.stocks
  for insert with check (auth.role() = 'authenticated');
