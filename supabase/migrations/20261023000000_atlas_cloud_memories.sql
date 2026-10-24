create table if not exists public.atlas_memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  kind text not null check (kind in ('session', 'episodic', 'semantic', 'project', 'operational')),
  content text not null check (char_length(content) between 1 and 12000),
  source text not null check (char_length(source) between 1 and 200),
  scope text not null default 'user' check (char_length(scope) between 1 and 200),
  confidence double precision not null default 1.0 check (confidence >= 0 and confidence <= 1),
  created_at timestamptz not null default now()
);

create index if not exists idx_atlas_memories_user_created
  on public.atlas_memories(user_id, created_at desc);

alter table public.atlas_memories enable row level security;

drop policy if exists "Users manage their own Atlas memories" on public.atlas_memories;
create policy "Users manage their own Atlas memories"
  on public.atlas_memories for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

grant select, insert, update, delete on public.atlas_memories to authenticated;