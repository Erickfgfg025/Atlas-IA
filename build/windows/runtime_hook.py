"""PyInstaller runtime configuration for the cloud-first Windows release."""

import os
import sys

# Keep local development pointed at localhost. Only packaged builds use Render.
if getattr(sys, "frozen", False):
    cloud_api_url = "https://atlas-ai-api-a58n.onrender.com"
    os.environ.setdefault("ATLAS_API_URL", cloud_api_url)

    # The memory dialog currently has its own API_BASE constant. Set it before
    # the entry point imports MemoryDialog so every desktop view uses the same API.
    try:
        from atlas.desktop import memories_dialog

        memories_dialog.API_BASE = os.environ["ATLAS_API_URL"].rstrip("/")
    except ImportError:
        # The normal app import will surface a missing dependency more clearly.
        pass
