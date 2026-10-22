-- Cloud conversation history. Every row is isolated by Supabase Auth RLS.
create table if not exists public.atlas_conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null check (char_length(title) between 1 and 160),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.atlas_conversation_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.atlas_conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null check (char_length(content) between 1 and 20000),
  created_at timestamptz not null default now()
);

create index if not exists idx_atlas_conversations_user_updated
  on public.atlas_conversations(user_id, updated_at desc);
create index if not exists idx_atlas_messages_conversation_created
  on public.atlas_conversation_messages(conversation_id, created_at);

alter table public.atlas_conversations enable row level security;
alter table public.atlas_conversation_messages enable row level security;

drop policy if exists "Users manage their own Atlas conversations" on public.atlas_conversations;
create policy "Users manage their own Atlas conversations"
  on public.atlas_conversations for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users manage their own Atlas messages" on public.atlas_conversation_messages;
create policy "Users manage their own Atlas messages"
  on public.atlas_conversation_messages for all
  to authenticated
  using (
    auth.uid() = user_id
    and exists (
      select 1 from public.atlas_conversations c
      where c.id = conversation_id and c.user_id = auth.uid()
    )
  )
  with check (
    auth.uid() = user_id
    and exists (
      select 1 from public.atlas_conversations c
      where c.id = conversation_id and c.user_id = auth.uid()
    )
  );

grant select, insert, update, delete on public.atlas_conversations to authenticated;
grant select, insert, update, delete on public.atlas_conversation_messages to authenticated;
