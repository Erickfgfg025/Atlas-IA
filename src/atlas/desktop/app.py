import html
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx
from PySide6.QtCore import QThread, Signal, QSettings, QBuffer, QByteArray, QIODevice, QUrl, QTimer, Qt
from PySide6.QtMultimedia import (
    QAudioInput,
    QAudioOutput,
    QMediaCaptureSession,
    QMediaFormat,
    QMediaPlayer,
    QMediaRecorder,
)
from PySide6.QtWidgets import QFileDialog
from atlas.desktop.memories_dialog import MemoryDialog
from atlas.desktop.voice_orb import VoiceOrb
from atlas.desktop.visual_canvas import VisualCanvas
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QSizePolicy,
    QWidget,
)

API_BASE = os.environ.get("ATLAS_API_URL", "http://127.0.0.1:8000").rstrip("/")


def _safe_html(text: str) -> str:
    """Escape untrusted chat content before displaying it in QTextEdit."""
    return html.escape(text).replace("\n", "<br>")


def _load_session_token() -> str:
    """Load the access token from the Windows credential vault via keyring."""
    try:
        import keyring
        return keyring.get_password("AtlasAI", "desktop-session") or ""
    except Exception:
        return ""


def _store_session_token(token: str) -> bool:
    """Persist a session token in the OS credential store, never in plain settings."""
    try:
        import keyring
        keyring.set_password("AtlasAI", "desktop-session", token)
        return True
    except Exception:
        return False


def _clear_session_token() -> None:
    try:
        import keyring
        keyring.delete_password("AtlasAI", "desktop-session")
    except Exception:
        pass


class ApiWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        operation: str,
        *,
        email: str = "",
        password: str = "",
        message: str = "",
        access_token: str = "",
        conversation_id: str = "",
        audio_path: str = "",
        public_cloud: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.operation = operation
        self.email = email
        self.password = password
        self.message = message
        self.access_token = access_token
        self.conversation_id = conversation_id
        self.audio_path = audio_path
        self.public_cloud = public_cloud

    @staticmethod
    def _mime_type(path: str) -> str:
        suffix = path.lower().rsplit(".", 1)[-1] if "." in path else ""
        return {"mp3": "audio/mpeg", "wav": "audio/wav", "webm": "audio/webm", "ogg": "audio/ogg", "m4a": "audio/mp4", "mp4": "audio/mp4", "aac": "audio/aac", "flac": "audio/flac", "3gp": "audio/3gpp"}.get(suffix, "application/octet-stream")

    def run(self) -> None:
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}
            if self.operation == "activate":
                response = httpx.post(
                    f"{API_BASE}/auth/activate",
                    json={"code": self.email},
                    timeout=15.0,
                )
            elif self.operation in ("login", "signup", "activate"):
                response = httpx.post(
                    f"{API_BASE}/auth/{self.operation}",
                    json={"email": self.email, "password": self.password},
                    timeout=15.0,
                )
            elif self.operation == "new_conversation":
                response = httpx.post(f"{API_BASE}/conversations", json={"title": "Nova conversa"}, headers=headers, timeout=10.0)
            elif self.operation == "history":
                response = httpx.get(
                    f"{API_BASE}/conversations/{self.conversation_id}/messages",
                    headers=headers,
                    timeout=10.0,
                )
            elif self.operation == "visual_scene":
                response = httpx.post(
                    f"{API_BASE}/visual/scene",
                    json={"prompt": self.message},
                    headers=headers,
                    timeout=90.0,
                )
            elif self.operation == "chat" and not self.access_token and self.public_cloud:
                response = httpx.post(
                    f"{API_BASE}/public/chat",
                    json={"message": self.message},
                    timeout=60.0,
                )
            elif self.operation == "chat":
                response = httpx.post(
                    f"{API_BASE}/chat",
                    json={"message": self.message, "conversation_id": self.conversation_id or None},
                    headers=headers,
                    timeout=60.0,
                )
            elif self.operation == "voice_synthesize":
                response = httpx.post(f"{API_BASE}/voice/synthesize", json={"text": self.message}, headers=headers, timeout=60.0)
                if not response.is_success:
                    try:
                        payload = response.json()
                    except ValueError:
                        payload = {}
                    detail = payload.get("detail", "Não foi possível gerar o áudio.") if isinstance(payload, dict) else "Não foi possível gerar o áudio."
                    self.failed.emit(str(detail))
                    return
                if not response.content:
                    self.failed.emit("O serviço de voz retornou um áudio vazio.")
                    return
                self.succeeded.emit({"operation": "voice_synthesize", "audio": response.content})
                return
            elif self.operation == "voice_transcribe":
                try:
                    with open(self.audio_path, "rb") as audio_file:
                        response = httpx.post(
                            f"{API_BASE}/voice/transcribe",
                            files={"audio": (Path(self.audio_path).name, audio_file, self._mime_type(self.audio_path))},
                            headers=headers,
                            timeout=90.0,
                        )
                except OSError:
                    self.failed.emit("Não foi possível abrir o arquivo de áudio selecionado.")
                    return
            elif self.operation == "logout":
                response = httpx.post(f"{API_BASE}/auth/logout", headers=headers, timeout=8.0)
                if response.status_code == 204:
                    self.succeeded.emit({"operation": "logout"})
                    return
            else:
                self.failed.emit("Operação desconhecida.")
                return

            try:
                payload = response.json()
            except ValueError:
                payload = {}

            if not response.is_success:
                detail = payload.get("detail", "A solicitação falhou.") if isinstance(payload, dict) else "A solicitação falhou."
                self.failed.emit(str(detail))
                return
            if self.operation in ("login", "signup", "activate"):
                if not isinstance(payload, dict):
                    self.failed.emit("Resposta de autenticação inválida.")
                    return
                self.succeeded.emit({"operation": self.operation, **payload})
            elif self.operation == "new_conversation":
                if isinstance(payload, dict) and isinstance(payload.get("id"), str):
                    self.succeeded.emit({"operation": "new_conversation", "conversation_id": payload["id"]})
                else:
                    self.failed.emit("Não foi possível criar uma conversa.")
            elif self.operation == "history":
                if isinstance(payload, list):
                    self.succeeded.emit({"operation": "history", "messages": payload})
                else:
                    self.failed.emit("O histórico retornou uma resposta inválida.")
            elif self.operation == "voice_transcribe":
                transcript = payload.get("text") if isinstance(payload, dict) else None
                if not isinstance(transcript, str) or not transcript.strip():
                    self.failed.emit("A API não retornou uma transcrição válida.")
                    return
                self.succeeded.emit({"operation": "voice_transcribe", "text": transcript})
            elif self.operation == "visual_scene":
                if isinstance(payload, dict) and isinstance(payload.get("elements"), list):
                    self.succeeded.emit({"operation": "visual_scene", "scene": payload})
                else:
                    self.failed.emit("A API retornou uma cena visual inválida.")
            elif self.operation == "chat":
                answer = payload.get("response") if isinstance(payload, dict) else None
                if not isinstance(answer, str) or not answer.strip():
                    self.failed.emit("A API retornou uma resposta inválida.")
                    return
                self.succeeded.emit({"operation": "chat", "response": answer, "conversation_id": payload.get("conversation_id")})
        except httpx.HTTPError:
            self.failed.emit("Não foi possível conectar ao Atlas. Verifique sua internet.")
        except (TypeError, ValueError):
            self.failed.emit("A API retornou uma resposta inválida.")


class AtlasWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._access_token = ""
        self._auth_mode = "supabase"
        self._worker: ApiWorker | None = None
        self._pending_operation = ""
        self._settings = QSettings("AtlasAI", "ATLAS")
        self._audio_output = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.playbackStateChanged.connect(self._sync_orb_to_playback)
        self._audio_buffer: QBuffer | None = None
        self._last_answer = ""
        self._capture_session = QMediaCaptureSession(self)
        self._audio_input = QAudioInput(self)
        self._recorder = QMediaRecorder(self)
        self._capture_session.setAudioInput(self._audio_input)
        self._capture_session.setRecorder(self._recorder)
        self._recording_path = ""
        self._temporary_recording_path = ""
        self._is_recording = False
        self._recording_timeout = QTimer(self)
        self._recording_timeout.setSingleShot(True)
        self._recording_timeout.timeout.connect(self._stop_microphone_recording)
        self._recorder.errorOccurred.connect(self._on_recording_error)
        self._conversation_id = self._settings.value("active_conversation_id", "", type=str)
        self._access_token = _load_session_token()
        self._settings.remove("access_token")
        self.setWindowTitle("ATLAS AI")
        self.resize(760, 560)
        self.setMinimumSize(600, 420)

        self.status = QLabel("ATLAS API: verificando...")
        self.voice_orb = VoiceOrb(self)
        self.visual_canvas = VisualCanvas(self)
        self.voice_state = QLabel("PRONTO PARA CONVERSAR")
        self.voice_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.voice_state.setStyleSheet("color: #8FA7C7; letter-spacing: 2px; font-size: 9px; font-weight: 600;")
        self.auth_title = QLabel("Ative seu acesso ao ATLAS")
        self.email = QLineEdit()
        self.email.setPlaceholderText("Código de ativação")
        self.password = QLineEdit()
        self.password.setVisible(False)
        self.login_button = QPushButton("ATIVAR ACESSO")
        self.signup_button = QPushButton(" ")
        self.signup_button.setVisible(False)
        self.login_button.clicked.connect(lambda: self.start_auth("activate"))

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Escreva uma mensagem para o ATLAS...")
        self.send_button = QPushButton("Enviar")
        self.transcribe_button = QPushButton("Transcrever arquivo de áudio")
        self.record_button = QPushButton("🎙 Gravar pelo microfone")
        self.speak_button = QPushButton("Ouvir última resposta")
        self.transcribe_button.clicked.connect(self.transcribe_audio_file)
        self.record_button.clicked.connect(self._toggle_microphone_recording)
        self.speak_button.clicked.connect(self.speak_last_answer)
        self.logout_button = QPushButton("Sair da conta")
        self.memories_button = QPushButton("Memórias")
        self.new_conversation_button = QPushButton("Nova conversa")
        self.new_conversation_button.clicked.connect(self.new_conversation)
        self.memories_button.clicked.connect(self.open_memories)
        self.send_button.clicked.connect(self.send_message)
        self.input.returnPressed.connect(self.send_message)
        self.logout_button.clicked.connect(self.logout)

        self.setMinimumSize(900, 620)
        self.resize(1180, 760)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #08090B; color: #F3F4F6;
                font-family: 'Inter', 'Segoe UI', sans-serif; font-size: 13px;
            }
            QFrame#Topbar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #101114, stop:1 #0B0C0E);
                border-bottom: 1px solid #25262B;
            }
            QLabel#Brand {
                color: #F5F5F6; font-family: 'Space Grotesk', 'Segoe UI', sans-serif;
                font-size: 17px; font-weight: 700; letter-spacing: 2px;
            }
            QLabel#Eyebrow { color: #777D87; font-size: 9px; font-weight: 600; letter-spacing: 2px; }
            QLabel#Status {
                color: #A8ADB5; background: #111216; border: 1px solid #292A30;
                border-radius: 10px; padding: 7px 10px; font-size: 10px;
            }
            QLabel#VoiceState { color: #FF7830; font-size: 9px; font-weight: 700; letter-spacing: 2px; padding: 3px; }
            QLabel#Headline { color: #F5F5F6; font-family: 'Sora', 'Inter', sans-serif; font-size: 28px; font-weight: 700; }
            QLabel#Subheadline { color: #8F949D; font-size: 10px; letter-spacing: 2px; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #191A1F, stop:1 #121317);
                color: #E7E8EB; border: 1px solid #303138; border-radius: 12px;
                padding: 10px 14px; font-size: 10px; font-weight: 650;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #24252B, stop:1 #191A1F);
                border-color: #50515A; color: #FFFFFF;
            }
            QPushButton:pressed { background: #101114; border-color: #FF7830; }
            QPushButton:disabled { color: #555962; background: #101114; border-color: #222329; }
            QPushButton#Primary {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF8540, stop:0.48 #FF7025, stop:1 #F45C12);
                color: #1B1009; border: 1px solid #FF9A5C; border-radius: 12px;
                font-size: 11px; font-weight: 750; padding: 10px 18px;
            }
            QPushButton#Primary:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFA064, stop:1 #FF7830);
                border-color: #FFB07D;
            }
            QPushButton#Primary:pressed { background: #E9570D; }
            QPushButton#Quiet { background: transparent; color: #9297A1; border: 1px solid transparent; }
            QPushButton#Quiet:hover { background: #15161A; color: #F0F1F3; border-color: #292A30; }
            QLineEdit, QTextEdit {
                background: #0E0F12; color: #F4F5F7; border: 1px solid #2B2D33;
                border-radius: 13px; padding: 12px; selection-background-color: #A94D17;
            }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #FF7830; background: #101114; }
            QLineEdit { min-height: 26px; font-size: 14px; }
            QTextEdit { font-size: 13px; }
            QFrame#Composer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #131418, stop:1 #0D0E11);
                border: 1px solid #303137; border-radius: 18px;
            }
            QFrame#LoginPanel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #15161A, stop:1 #0E0F12);
                border: 1px solid #303137; border-radius: 18px;
            }
        """)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("Topbar")
        top = QHBoxLayout(topbar)
        top.setContentsMargins(28, 15, 28, 15)
        top.setSpacing(12)
        mark = QLabel("A")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(28, 28)
        mark.setStyleSheet("background:#FF6B18;color:#17100B;border-radius:8px;font-size:17px;font-weight:800;")
        top.addWidget(mark)
        brand_stack = QVBoxLayout()
        brand_stack.setSpacing(0)
        brand = QLabel("ATLAS AI")
        brand.setObjectName("Brand")
        tagline = QLabel("ASSISTENTE PESSOAL")
        tagline.setObjectName("Eyebrow")
        brand_stack.addWidget(brand)
        brand_stack.addWidget(tagline)
        top.addLayout(brand_stack)
        top.addStretch(1)
        self.status.setObjectName("Status")
        top.addWidget(self.status)
        self.new_conversation_button.setText("NOVA CONVERSA")
        self.new_conversation_button.setObjectName("Quiet")
        top.addWidget(self.new_conversation_button)
        self.logout_button.setText("SAIR")
        self.logout_button.setObjectName("Quiet")
        top.addWidget(self.logout_button)
        root_layout.addWidget(topbar)

        workspace = QWidget()
        work = QVBoxLayout(workspace)
        work.setContentsMargins(32, 12, 32, 18)
        work.setSpacing(8)

        eyebrow = QLabel("SUA IA PESSOAL")
        eyebrow.setObjectName("VoiceState")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        work.addWidget(eyebrow)

        work.addStretch(1)
        self.voice_orb.setMinimumHeight(250)
        self.voice_orb.setMaximumHeight(340)
        self.voice_orb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        work.addWidget(self.voice_orb, 5)

        self.auth_title.setText("ENTRE NA SUA CONTA ATLAS")
        self.auth_title.setStyleSheet("font-size:20px;font-weight:700;color:#F4F6FA;padding:6px;")
        self.email.setPlaceholderText("E-MAIL")
        self.password.setPlaceholderText("SENHA")
        # A interface desktop pessoal não exige cadastro.

        headline = QLabel("COMO POSSO AJUDAR?")
        headline.setObjectName("Headline")
        headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        work.addWidget(headline)
        subheadline = QLabel("PENSE. CRIE. PLANEJE. RESOLVA.")
        subheadline.setObjectName("Subheadline")
        subheadline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        work.addWidget(subheadline)

        self.visual_canvas.setMaximumHeight(380)
        work.addWidget(self.visual_canvas, 2)

        self.transcript.setMinimumHeight(100)
        self.transcript.setMaximumHeight(230)
        self.transcript.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.transcript.hide()
        work.addWidget(self.transcript, 2)
        self.visual_canvas.hide()

        composer = QFrame()
        composer.setObjectName("Composer")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(16, 10, 10, 10)
        composer_layout.setSpacing(7)
        self.input.setPlaceholderText("DIGITE SEU PEDIDO...")
        self.input.setStyleSheet("QLineEdit { background:transparent;border:0;padding:3px;color:#F4F6FA;font-size:14px; }")
        composer_layout.addWidget(self.input)
        composer_divider = QFrame()
        composer_divider.setFixedHeight(1)
        composer_divider.setStyleSheet("background:#29313D;border:0;")
        composer_layout.addWidget(composer_divider)
        composer_bottom = QHBoxLayout()
        hint = QLabel("PRESSIONE ENTER PARA ENVIAR")
        hint.setObjectName("Eyebrow")
        composer_bottom.addWidget(hint)
        composer_bottom.addStretch(1)
        self.record_button.setText("MICROFONE")
        self.record_button.setObjectName("Quiet")
        self.transcribe_button.setText("ÁUDIO PARA TEXTO")
        self.transcribe_button.setToolTip("Converter um arquivo de áudio em texto")
        self.record_button.setToolTip("Gravar áudio pelo microfone")
        self.speak_button.setToolTip("Reproduzir a resposta em voz alta")
        self.send_button.setToolTip("Enviar mensagem (Enter)")
        self.transcribe_button.setObjectName("Quiet")
        self.speak_button.setText("OUVIR RESPOSTA")
        self.speak_button.setObjectName("Quiet")
        composer_bottom.addWidget(self.record_button)
        composer_bottom.addWidget(self.transcribe_button)
        composer_bottom.addWidget(self.speak_button)
        self.send_button.setText("ENVIAR  ↗")
        self.send_button.setObjectName("Primary")
        composer_bottom.addWidget(self.send_button)
        composer_layout.addLayout(composer_bottom)
        work.addWidget(composer)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        actions.addStretch(1)
        self.quick_write = QPushButton("ESCREVER TEXTO")
        self.quick_code = QPushButton("AJUDA COM CÓDIGO")
        self.quick_plan = QPushButton("CRIAR PLANO")
        self.quick_visual = QPushButton("CRIAR ANIMAÇÃO")
        self.quick_visual.clicked.connect(self.create_visual_scene)
        self.quick_write.clicked.connect(lambda: self._use_quick_prompt("Ajude-me a escrever um texto."))
        self.quick_code.clicked.connect(lambda: self._use_quick_prompt("Ajude-me com código."))
        self.quick_plan.clicked.connect(lambda: self._use_quick_prompt("Ajude-me a criar um plano."))
        # A tela inicial segue o layout minimalista do Figma. Atalhos ficam
        # disponíveis no código para uma futura paleta de comandos, sem poluir a home.
        for quick_action in (self.quick_write, self.quick_code, self.quick_plan, self.quick_visual):
            quick_action.hide()
        work.addLayout(actions)

        footer = QLabel("ATLAS AI  ·  FEITO PARA VOCÊ")
        footer.setObjectName("Eyebrow")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        work.addSpacing(4)
        work.addWidget(footer)
        work.addStretch(1)
        root_layout.addWidget(workspace, 1)
        self.setCentralWidget(root)
        self._login_panel = QFrame()
        self._login_panel.setObjectName("LoginPanel")
        self._login_panel.setStyleSheet("")
        login_layout = QVBoxLayout(self._login_panel)
        login_layout.setContentsMargins(22, 18, 22, 18)
        login_layout.setSpacing(10)
        login_layout.addWidget(self.auth_title)
        login_layout.addWidget(self.email)
        login_layout.addWidget(self.password)
        auth_actions = QHBoxLayout()
        self.login_button.setObjectName("Primary")
        auth_actions.addWidget(self.login_button)
        auth_actions.addWidget(self.signup_button)
        login_layout.addLayout(auth_actions)
        work.insertWidget(2, self._login_panel, 0, Qt.AlignmentFlag.AlignHCenter)
        self.speak_button.setEnabled(False)
        self._set_chat_visible(False)
        self.check_api()

    def _use_quick_prompt(self, prompt: str) -> None:
        self.input.setText(prompt)
        self.input.setFocus()

    def _set_chat_visible(self, visible: bool = True) -> None:
        chat_widgets = (self.transcript, self.input, self.send_button, self.transcribe_button, self.record_button, self.speak_button, self.quick_write, self.quick_code, self.quick_plan, self.quick_visual)
        for widget in chat_widgets:
            widget.setVisible(visible)
        if self._login_panel is not None:
            self._login_panel.setVisible(not visible and self._auth_mode in {"supabase", "activation_code"})
        self.new_conversation_button.setVisible(visible and self._auth_mode in {"supabase", "activation_code"})
        self.logout_button.setVisible(visible and self._auth_mode in {"supabase", "activation_code"})
        for widget in (self.auth_title, self.email, self.login_button):
            widget.setVisible(not visible and self._auth_mode in {"supabase", "activation_code"})
        self.password.setVisible(False)
        self.signup_button.setVisible(False)

    def check_api(self) -> None:
        try:
            response = httpx.get(f"{API_BASE}/health", timeout=2.0)
            response.raise_for_status()
            payload = response.json()
            reported_auth_mode = payload.get("auth_mode")
            self._auth_mode = (
                reported_auth_mode
                if reported_auth_mode in {"local", "supabase", "supabase_single_user", "activation_code", "public_cloud"}
                else "supabase"
            )
            if self._auth_mode == "public_cloud":
                self._access_token = ""
                self._set_chat_visible(True)
                self.status.setText("ATLAS conectado · nuvem pública · sem histórico privado")
            elif self._auth_mode == "activation_code":
                if self._access_token:
                    try:
                        auth_response = httpx.get(f"{API_BASE}/auth/me", headers={"Authorization": f"Bearer {self._access_token}"}, timeout=8.0)
                        if auth_response.is_success:
                            self._set_chat_visible(True)
                            self.status.setText("Acesso ATLAS restaurado neste computador.")
                            if self._conversation_id:
                                self._load_history()
                        else:
                            self._access_token = ""
                            _clear_session_token()
                            self._set_chat_visible(False)
                            self.status.setText("Sessão expirada. Informe seu código de ativação.")
                    except httpx.HTTPError:
                        self.status.setText("Sem conexão. A sessão será verificada quando voltar.")
                else:
                    self._set_chat_visible(False)
                    self.status.setText("Informe seu código pessoal para ativar o ATLAS.")
            elif self._auth_mode == "local":
                self._set_chat_visible(True)
                self.status.setText("ATLAS conectado · memória e histórico locais")
                if self._conversation_id:
                    self._load_history()
            elif self._auth_mode == "supabase_single_user":
                self._set_chat_visible(True)
                self.status.setText("ATLAS conectado · Supabase · modo pessoal sem login")
                if self._conversation_id:
                    self._load_history()
            else:
                if self._access_token:
                    try:
                        auth_response = httpx.get(f"{API_BASE}/auth/me", headers={"Authorization": f"Bearer {self._access_token}"}, timeout=8.0)
                        if auth_response.is_success:
                            self._set_chat_visible(True)
                            self.status.setText("Sessão ATLAS restaurada · dados sincronizados")
                            if self._conversation_id:
                                self._load_history()
                        else:
                            self._access_token = ""
                            _clear_session_token()
                            self._set_chat_visible(False)
                            self.status.setText("Sua sessão expirou. Entre novamente.")
                    except httpx.HTTPError:
                        self.status.setText("Sem conexão. A sessão será verificada quando voltar.")
                else:
                    self._set_chat_visible(False)
                    self.status.setText("Entre ou crie sua conta ATLAS para sincronizar seus dados.")
        except (httpx.HTTPError, ValueError):
            self.status.setText("Sem conexão com o Atlas. Verifique sua internet e tente novamente.")

    def _start_worker(self, worker: ApiWorker, operation: str) -> None:
        if self._worker is not None:
            return
        self._worker = worker
        self._pending_operation = operation
        worker.succeeded.connect(self._on_success)
        worker.failed.connect(self._on_failure)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def start_auth(self, operation: str) -> None:
        if self._auth_mode == "local":
            return
        code = self.email.text().strip()
        if not code:
            self.status.setText("Informe seu código de ativação.")
            return
        self.login_button.setEnabled(False)
        self.status.setText("Validando código de ativação...")
        self._start_worker(
            ApiWorker("activate", email=code, parent=self),
            "activate",
        )

    def send_message(self) -> None:
        message = self.input.text().strip()
        if not message or self._worker is not None:
            return
        if self._auth_mode in {"supabase", "activation_code"} and not self._access_token:
            self.status.setText(
                "O backend está em modo Supabase. Configure ATLAS_MEMORY_BACKEND=local "
                "para usar sem conta."
            )
            return
        self.transcript.show()
        self.transcript.append(f"<b>Você:</b> {_safe_html(message)}")
        if self._auth_mode != "public_cloud" and any(term in message.casefold() for term in ("crie uma anima", "cria uma anima", "motion design", "gere uma cena", "crie uma cena", "visualize", "animação de", "animacao de", "desenhe", "gere um diagrama")):
            self._start_visual_scene(message)
            self.input.clear()
            return
        self._set_voice_state("thinking", "PENSANDO")
        self.input.clear()
        self.send_button.setEnabled(False)
        self.input.setEnabled(False)
        self._start_worker(
            ApiWorker(
                "chat",
                message=message,
                access_token=self._access_token,
                conversation_id="" if self._auth_mode == "public_cloud" else self._conversation_id,
                public_cloud=self._auth_mode == "public_cloud",
                parent=self,
            ),
            "chat",
        )

    def create_visual_scene(self) -> None:
        prompt = self.input.text().strip()
        if not prompt:
            self.status.setText("Descreva a animação que deseja criar.")
            self.input.setFocus()
            return
        if self._worker is not None:
            self.status.setText("Aguarde a operação atual terminar.")
            return
        self.transcript.append(f"<b>Você · CANVAS:</b> {_safe_html(prompt)}")
        self.input.clear()
        self._start_visual_scene(prompt)

    def _start_visual_scene(self, prompt: str) -> None:
        if self._auth_mode == "supabase" and not self._access_token:
            self.status.setText("Entre na sua conta para gerar cenas com IA.")
            return
        self.visual_canvas.show()
        self.visual_canvas.hint.setText("A IA está planejando a composição...")
        self.status.setText("Gerando elementos e movimentos com a IA...")
        self._set_voice_state("thinking", "CRIANDO CENA")
        self._start_worker(
            ApiWorker("visual_scene", message=prompt, access_token=self._access_token, parent=self),
            "visual_scene",
        )

    def transcribe_audio_file(self) -> None:
        if self._worker is not None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar áudio para transcrição", "",
            "Arquivos de áudio (*.mp3 *.wav *.webm *.ogg *.m4a *.mp4 *.aac *.flac *.3gp)",
        )
        if not path:
            return
        if self._auth_mode == "supabase" and not self._access_token:
            self.status.setText("Entre na sua conta antes de enviar áudio.")
            return
        self.status.setText("Transcrevendo áudio na nuvem...")
        self._start_worker(ApiWorker("voice_transcribe", audio_path=path, access_token=self._access_token, parent=self), "voice_transcribe")

    def _toggle_microphone_recording(self) -> None:
        if self._is_recording:
            self._stop_microphone_recording()
            return
        if self._worker is not None:
            self.status.setText("Aguarde a operação atual terminar antes de gravar.")
            return
        if self._auth_mode == "supabase" and not self._access_token:
            self.status.setText("Entre na sua conta antes de gravar áudio.")
            return
        try:
            handle = tempfile.NamedTemporaryFile(prefix="atlas-mic-", suffix=".wav", delete=False)
            self._recording_path = handle.name
            handle.close()
            media_format = QMediaFormat()
            media_format.setFileFormat(QMediaFormat.FileFormat.Wave)
            self._recorder.setMediaFormat(media_format)
            self._recorder.setOutputLocation(QUrl.fromLocalFile(self._recording_path))
            self._recorder.record()
            self._is_recording = True
            self._temporary_recording_path = self._recording_path
            self.record_button.setText("■ Parar gravação")
            self.status.setText("Gravando pelo microfone. Máximo de 60 segundos.")
            self._recording_timeout.start(60_000)
        except (OSError, RuntimeError, AttributeError) as exc:
            self._cleanup_temporary_recording()
            self.status.setText(f"Não foi possível iniciar o microfone: {exc}")

    def _stop_microphone_recording(self) -> None:
        if not self._is_recording:
            return
        self._recording_timeout.stop()
        self._is_recording = False
        self.record_button.setText("🎙 Gravar pelo microfone")
        self._recorder.stop()
        self.status.setText("Finalizando gravação...")
        QTimer.singleShot(700, self._submit_microphone_recording)

    def _submit_microphone_recording(self) -> None:
        path = self._temporary_recording_path
        if not path or not os.path.isfile(path) or os.path.getsize(path) < 44:
            self._cleanup_temporary_recording()
            self.status.setText("A gravação ficou vazia. Verifique a permissão do microfone e tente novamente.")
            return
        self._start_worker(
            ApiWorker("voice_transcribe", audio_path=path, access_token=self._access_token, parent=self),
            "voice_transcribe",
        )
        self.status.setText("Enviando gravação para transcrição na nuvem...")

    def _on_recording_error(self, error: QMediaRecorder.Error, message: str) -> None:
        if error == QMediaRecorder.Error.NoError:
            return
        self._recording_timeout.stop()
        self._is_recording = False
        self.record_button.setText("🎙 Gravar pelo microfone")
        self._cleanup_temporary_recording()
        self.status.setText(f"Erro de gravação: {message or 'verifique o microfone e as permissões do Windows.'}")

    def _cleanup_temporary_recording(self) -> None:
        path = self._temporary_recording_path
        self._temporary_recording_path = ""
        self._recording_path = ""
        if path:
            try:
                os.remove(path)
            except OSError:
                pass

    def speak_last_answer(self) -> None:
        if self._worker is not None or not self._last_answer:
            return
        if self._auth_mode == "supabase" and not self._access_token:
            self.status.setText("Entre na sua conta antes de usar a voz.")
            return
        self.status.setText("Gerando resposta em áudio...")
        self._set_voice_state("thinking", "PREPARANDO A VOZ")
        self._start_worker(ApiWorker("voice_synthesize", message=self._last_answer, access_token=self._access_token, parent=self), "voice_synthesize")

    def _play_audio(self, audio_bytes: bytes) -> None:
        if self._audio_buffer is not None:
            self._audio_buffer.close()
            self._audio_buffer.deleteLater()
        buffer = QBuffer(self)
        buffer.setData(QByteArray(audio_bytes))
        if not buffer.open(QIODevice.ReadOnly):
            self.status.setText("Não foi possível preparar o áudio para reprodução.")
            return
        self._audio_buffer = buffer
        self._player.setSourceDevice(buffer, QUrl("atlas-response.mp3"))
        self._player.play()
        self._set_voice_state("speaking", "ATLAS ESTÁ FALANDO")
        self.status.setText("Reproduzindo resposta do ATLAS.")

    def _set_voice_state(self, state: str, label: str) -> None:
        self.voice_orb.set_state(state)
        self.voice_state.setText(label)

    def _sync_orb_to_playback(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._set_voice_state("speaking", "ATLAS ESTÁ FALANDO")
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self._set_voice_state("idle", "PRONTO PARA CONVERSAR")

    def new_conversation(self) -> None:
        if self._worker is not None or self._auth_mode not in {"local", "supabase_single_user", "supabase"}:
            return
        self._start_worker(ApiWorker("new_conversation", access_token=self._access_token, parent=self), "new_conversation")

    def _load_history(self) -> None:
        if self._worker is not None or not self._conversation_id or self._auth_mode not in {"local", "supabase_single_user", "supabase"}:
            return
        self._start_worker(ApiWorker("history", conversation_id=self._conversation_id, access_token=self._access_token, parent=self), "history")

    def open_memories(self) -> None:
        if self._worker is not None:
            return
        dialog = MemoryDialog(self._access_token, self)
        dialog.exec()

    def logout(self) -> None:
        if self._worker is not None or not self._access_token:
            return
        token = self._access_token
        self._access_token = ""
        _clear_session_token()
        self._settings.remove("access_token")
        self._settings.remove("active_conversation_id")
        self._conversation_id = ""
        self.status.setText("Encerrando sessão...")
        self._start_worker(ApiWorker("logout", access_token=token, parent=self), "logout")

    def _on_success(self, result: Any) -> None:
        if not isinstance(result, dict):
            self.status.setText("A API retornou uma resposta inválida.")
            return
        operation = result.get("operation")
        if operation in ("login", "signup", "activate"):
            token = result.get("access_token")
            if isinstance(token, str) and token:
                self._access_token = token
                _store_session_token(token)
                user_id = result.get("user_id")
                suffix = f" · usuário {user_id}" if isinstance(user_id, str) else ""
                self.status.setText(f"ATLAS conectado{suffix}")
                self.transcript.clear()
                self._set_chat_visible(True)
                self.input.setFocus()
                if self._conversation_id:
                    self._load_history()
            elif operation == "signup" and result.get("confirmation_required"):
                self.status.setText(
                    "Conta criada. Confirme o e-mail e depois entre com sua senha."
                )
            else:
                self.status.setText("A autenticação não retornou uma sessão válida.")
        elif operation == "new_conversation":
            conversation_id = result.get("conversation_id")
            if isinstance(conversation_id, str):
                self._conversation_id = conversation_id
                self._settings.setValue("active_conversation_id", conversation_id)
                self.transcript.clear()
                self.transcript.hide()
                self.status.setText("Nova conversa iniciada.")
        elif operation == "history":
            self.transcript.clear()
            history_messages = result.get("messages", [])
            self.transcript.setVisible(bool(history_messages))
            for message in history_messages:
                if not isinstance(message, dict):
                    continue
                role = message.get("role")
                content = message.get("content")
                if role in ("user", "assistant") and isinstance(content, str):
                    label = "Você" if role == "user" else "ATLAS"
                    self.transcript.append(f"<b>{label}:</b> {_safe_html(content)}")
            self.status.setText("Histórico da conversa restaurado.")
        elif operation == "voice_transcribe":
            transcript = result.get("text")
            if isinstance(transcript, str):
                self.input.setText(transcript)
                self.input.setFocus()
                self.status.setText("Transcrição pronta. Revise o texto antes de enviar.")
        elif operation == "voice_synthesize":
            audio = result.get("audio")
            if isinstance(audio, bytes):
                self._play_audio(audio)
        elif operation == "visual_scene":
            scene = result.get("scene")
            if isinstance(scene, dict):
                try:
                    self.visual_canvas.set_scene(scene)
                    self.status.setText("Cena criada. A animação está rodando no canvas.")
                    self._set_voice_state("idle", "CENA EM MOVIMENTO")
                except (TypeError, ValueError) as exc:
                    self.status.setText(f"Não foi possível exibir a cena: {exc}")
        elif operation == "chat":
            answer = result.get("response")
            conversation_id = result.get("conversation_id")
            if isinstance(conversation_id, str) and conversation_id:
                self._conversation_id = conversation_id
                self._settings.setValue("active_conversation_id", conversation_id)
            if isinstance(answer, str):
                self._last_answer = answer
                self.speak_button.setEnabled(bool(answer.strip()))
                self.transcript.show()
                self.transcript.append(f"<b>ATLAS:</b> {_safe_html(answer)}")
        elif operation == "logout":
            self._set_chat_visible(False)
            self.transcript.clear()
            self.email.clear()
            self.password.clear()
            self.status.setText("Sessão encerrada.")
        self._update_controls()

    def _on_failure(self, message: str) -> None:
        if self._pending_operation == "logout":
            self._set_chat_visible(False)
            self.transcript.clear()
            self.email.clear()
            self.password.clear()
            self.status.setText(
                "Sessão local encerrada; o serviço não confirmou o encerramento remoto."
            )
        else:
            self.status.setText(message)
        self._set_voice_state("idle", "PRONTO PARA CONVERSAR")
        self._update_controls()

    def _on_finished(self) -> None:
        if self._pending_operation == "voice_transcribe" and self._temporary_recording_path:
            self._cleanup_temporary_recording()
        finished_operation = self._pending_operation
        self._worker = None
        if finished_operation in ("login", "signup", "activate") and self._access_token and self._conversation_id:
            self._load_history()
        if self._pending_operation in ("chat", "voice_transcribe") and self._player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self._set_voice_state("idle", "PRONTO PARA CONVERSAR")
        self._update_controls()

    def _update_controls(self) -> None:
        busy = self._worker is not None
        authenticated = self._auth_mode in {"local", "supabase_single_user"} or bool(self._access_token)
        self.login_button.setEnabled(not busy)
        self.signup_button.setEnabled(not busy)
        self.send_button.setEnabled(not busy and authenticated)
        self.input.setEnabled(not busy and authenticated)
        self.transcribe_button.setEnabled(not busy and authenticated)
        self.record_button.setEnabled((not busy and authenticated) or self._is_recording)
        self.speak_button.setEnabled(not busy and authenticated and bool(self._last_answer))


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AtlasWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
