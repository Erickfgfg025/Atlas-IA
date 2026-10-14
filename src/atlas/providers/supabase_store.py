class MissingSupabaseConfiguration(RuntimeError):
    pass


def create_supabase_client(url: str, key: str):
    """Create a server-side client on demand, never from the desktop app."""
    if not url.strip() or not key.strip():
        raise MissingSupabaseConfiguration(
            "Supabase não configurado. Defina SUPABASE_URL e SUPABASE_KEY no backend."
        )
    from supabase import create_client
    return create_client(url.strip(), key.strip())
