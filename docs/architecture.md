# Initial architecture

First flow: PySide6 desktop → local FastAPI → Gemini provider. The Supabase adapter is available but memory is not persisted until schema, authentication and RLS are implemented in versioned migrations.

- Desktop never imports Gemini or Supabase SDKs.
- Backend owns provider credentials.
- Windows agent is not active in this phase.
- Memory contracts do not imply automatic persistence.
- Unit tests must not call external services.

Next: structured logs; provider timeouts and mock tests; Supabase Auth, migrations and RLS; curated memory; authenticated local-agent protocol.
