"""One-click Windows launcher for the packaged ATLAS AI application."""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog

APP_NAME = "ATLAS AI"
API_URL = "http://127.0.0.1:8000/health"
MODEL = "gemini-3.8-flash"


def app_directory() -> Path:
    return Path(sys.executable).resolve().parent


def show_root() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    try:
        root.wm_attributes("-topmost", True)
    except tk.TclError:
        pass
    return root


def configure_first_run(root: tk.Tk, env_path: Path) -> bool:
    if env_path.exists():
        return True

    key = simpledialog.askstring(
        APP_NAME,
        "Cole sua chave da API Gemini para ativar o chat.\n"
        "A chave será salva somente neste computador, no arquivo .env.",
        parent=root,
        show="*",
    )
    if not key or not key.strip():
        messagebox.showinfo(
            APP_NAME,
            "Configuração cancelada. Abra o ATLAS AI novamente e informe sua chave Gemini.",
            parent=root,
        )
        return False

    key = key.strip().replace("\r", "").replace("\n", "")
    env_path.write_text(
        "ATLAS_MEMORY_BACKEND=local\n"
        f"GEMINI_API_KEY={key}\n"
        f"GEMINI_MODEL={MODEL}\n",
        encoding="utf-8",
    )
    return True


def api_is_ready() -> bool:
    try:
        with urllib.request.urlopen(API_URL, timeout=1.5) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def main() -> int:
    base = app_directory()
    root = show_root()
    try:
        env_path = base / ".env"
        if not configure_first_run(root, env_path):
            return 1

        api_exe = base / "ATLAS API.exe"
        desktop_exe = base / "ATLAS Desktop.exe"
        if not api_exe.is_file() or not desktop_exe.is_file():
            messagebox.showerror(
                APP_NAME,
                "Os arquivos do aplicativo estão incompletos. Reinstale o ATLAS AI.",
                parent=root,
            )
            return 1

        if not api_is_ready():
            log_dir = base / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = (log_dir / "api.log").open("a", encoding="utf-8")
            try:
                subprocess.Popen(
                    [str(api_exe)],
                    cwd=str(base),
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    close_fds=True,
                )
            finally:
                log_file.close()

        for _ in range(40):
            if api_is_ready():
                break
            time.sleep(0.5)
        else:
            log_path = base / "logs" / "api.log"
            messagebox.showerror(
                APP_NAME,
                "O serviço local não iniciou. Consulte o registro em:\n"
                f"{log_path}\n\n"
                "Confirme se a porta 8000 está livre e tente novamente.",
                parent=root,
            )
            return 1

        subprocess.Popen(
            [str(desktop_exe)],
            cwd=str(base),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            close_fds=True,
        )
        return 0
    except (OSError, tk.TclError) as exc:
        messagebox.showerror(APP_NAME, f"Não foi possível iniciar o aplicativo:\n{exc}", parent=root)
        return 1
    finally:
        root.destroy()


if __name__ == "__main__":
    raise SystemExit(main())
