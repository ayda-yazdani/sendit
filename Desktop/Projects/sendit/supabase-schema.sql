-- Sendit Database Schema
-- Run this in Supabase SQL Editor

-- Enable UUID generation
create extension if not exists "uuid-ossp";

-- Boards
create table boards (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  join_code text unique not null,
  created_at timestamptz default now()
);

-- Members
create table members (
  id uuid primary key default uuid_generate_v4(),
  board_id uuid references boards(id) on delete cascade not null,
  display_name text not null,
  device_id text not null,
  google_id text,
  avatar_url text,
  push_token text,
  unique(board_id, device_id)
);

-- Reels
create table reels (
  id uuid primary key default uuid_generate_v4(),
  board_id uuid references boards(id) on delete cascade not null,
  added_by uuid references members(id) not null,
  url text not null,
  platform text not null,
  extraction_data jsonb,
  classification text,
  created_at timestamptz default now(),
  unique(board_id, url)
);

-- Taste Profiles
create table taste_profiles (
  id uuid primary key default uuid_generate_v4(),
  board_id uuid references boards(id) on delete cascade unique not null,
  profile_data jsonb default '{}'::jsonb,
  identity_label text,
  updated_at timestamptz default now()
);

-- Suggestions
create table suggestions (
  id uuid primary key default uuid_generate_v4(),
  board_id uuid references boards(id) on delete cascade not null,
  suggestion_data jsonb not null,
  status text default 'active' check (status in ('active', 'archived', 'completed')),
  created_at timestamptz default now()
);

-- Commitments
create table commitments (
  id uuid primary key default uuid_generate_v4(),
  suggestion_id uuid references suggestions(id) on delete cascade not null,
  member_id uuid references members(id) not null,
  status text not null check (status in ('in', 'maybe', 'out')),
  receipt_url text,
  updated_at timestamptz default now(),
  unique(suggestion_id, member_id)
);

-- Events (memory pages)
create table events (
  id uuid primary key default uuid_generate_v4(),
  suggestion_id uuid references suggestions(id),
  board_id uuid references boards(id) on delete cascade not null,
  photos jsonb default '[]'::jsonb,
  memories jsonb default '[]'::jsonb,
  narrative text,
  created_at timestamptz default now()
);

-- Calendar Masks
create table calendar_masks (
  id uuid primary key default uuid_generate_v4(),
  member_id uuid references members(id) on delete cascade unique not null,
  busy_slots jsonb default '[]'::jsonb,
  synced_at timestamptz default now()
);

-- Enable Realtime on key tables
alter publication supabase_realtime add table boards;
alter publication supabase_realtime add table reels;
alter publication supabase_realtime add table commitments;
alter publication supabase_realtime add table taste_profiles;
alter publication supabase_realtime add table suggestions;

-- RLS Policies (permissive for hackathon - tighten post-hackathon)
alter table boards enable row level security;
alter table members enable row level security;
alter table reels enable row level security;
alter table taste_profiles enable row level security;
alter table suggestions enable row level security;
alter table commitments enable row level security;
alter table events enable row level security;
alter table calendar_masks enable row level security;

create policy "Allow all on boards" on boards for all using (true) with check (true);
create policy "Allow all on members" on members for all using (true) with check (true);
create policy "Allow all on reels" on reels for all using (true) with check (true);
create policy "Allow all on taste_profiles" on taste_profiles for all using (true) with check (true);
create policy "Allow all on suggestions" on suggestions for all using (true) with check (true);
create policy "Allow all on commitments" on commitments for all using (true) with check (true);
create policy "Allow all on events" on events for all using (true) with check (true);
create policy "Allow all on calendar_masks" on calendar_masks for all using (true) with check (true);
