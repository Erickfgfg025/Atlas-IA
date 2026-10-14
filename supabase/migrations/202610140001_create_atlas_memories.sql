-- ATLAS AI memory foundation.
-- Apply with the Supabase CLI after linking the intended project.
-- Never expose the service_role key to the desktop client.

create table if not exists public.atlas_memories (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    kind text not null check (
        kind in ('session', 'episodic', 'semantic', 'project', 'operational')
    ),
    content text not null check (char_length(content) between 1 and 12000),
    source text not null check (char_length(source) between 1 and 200),
    scope text not null default 'user' check (char_length(scope) between 1 and 200),
    confidence double precision not null default 1.0
        check (confidence >= 0.0 and confidence <= 1.0),
    created_at timestamptz not null default now()
);

create index if not exists atlas_memories_user_created_idx
    on public.atlas_memories (user_id, created_at desc);

create index if not exists atlas_memories_user_kind_created_idx
    on public.atlas_memories (user_id, kind, created_at desc);

alter table public.atlas_memories enable row level security;

revoke all on table public.atlas_memories from anon;
grant select, insert, update, delete on table public.atlas_memories to authenticated;

drop policy if exists "Users can read their own ATLAS memories" on public.atlas_memories;
create policy "Users can read their own ATLAS memories"
    on public.atlas_memories for select
    to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "Users can create their own ATLAS memories" on public.atlas_memories;
create policy "Users can create their own ATLAS memories"
    on public.atlas_memories for insert
    to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their own ATLAS memories" on public.atlas_memories;
create policy "Users can update their own ATLAS memories"
    on public.atlas_memories for update
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete their own ATLAS memories" on public.atlas_memories;
create policy "Users can delete their own ATLAS memories"
    on public.atlas_memories for delete
    to authenticated
    using ((select auth.uid()) = user_id);

comment on table public.atlas_memories is
    'User-scoped persistent memory for ATLAS AI. Access is restricted by RLS.';
