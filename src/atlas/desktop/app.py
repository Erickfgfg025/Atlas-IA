import html
import sys
from typing import Any

import httpx
from PySide6.QtCore import QThread, Signal, QSettings, QBuffer, QByteArray, QIODevice, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QFileDialog
from atlas.desktop.memories_dialog import MemoryDialog
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

API_BASE = "http://127.0.0.1:8000"


def _safe_html(text: str) -> str:
    """Escape untrusted chat content before displaying it in QTextEdit."""
    return html.escape(text).replace("\n", "<br>")


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

    @staticmethod
    def _mime_type(path: str) -> str:
        suffix = path.lower().rsplit(".", 1)[-1] if "." in path else ""
        return {"mp3": "audio/mpeg", "wav": "audio/wav", "webm": "audio/webm", "ogg": "audio/ogg", "m4a": "audio/mp4", "mp4": "audio/mp4", "aac": "audio/aac", "flac": "audio/flac", "3gp": "audio/3gpp"}.get(suffix, "application/octet-stream")

    def run(self) -> None:
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}
            if self.operation in ("login", "signup"):
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
                            files={"audio": (self.audio_path.rsplit("/", 1)[-1].rsplit("\\\\", 1)[-1], audio_file, self._mime_type(self.audio_path))},
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
            if self.operation in ("login", "signup"):
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
            elif self.operation == "chat":
                answer = payload.get("response") if isinstance(payload, dict) else None
                if not isinstance(answer, str) or not answer.strip():
                    self.failed.emit("A API retornou uma resposta inválida.")
                    return
                self.succeeded.emit({"operation": "chat", "response": answer, "conversation_id": payload.get("conversation_id")})
        except httpx.HTTPError:
            self.failed.emit("Não foi possível conectar à API local.")
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
        self._audio_buffer: QBuffer | None = None
        self._last_answer = ""
        self._conversation_id = self._settings.value("active_conversation_id", "", type=str)
        self.setWindowTitle("ATLAS AI")
        self.resize(760, 560)
        self.setMinimumSize(600, 420)

        self.status = QLabel("ATLAS API: verificando...")
        self.auth_title = QLabel("Entre na sua conta ATLAS")
        self.email = QLineEdit()
        self.email.setPlaceholderText("E-mail")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Senha (mínimo 8 caracteres)")
        self.password.setEchoMode(QLineEdit.Password)
        self.login_button = QPushButton("Entrar")
        self.signup_button = QPushButton("Criar conta")
        self.login_button.clicked.connect(lambda: self.start_auth("login"))
        self.signup_button.clicked.connect(lambda: self.start_auth("signup"))

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Escreva uma mensagem para o ATLAS...")
        self.send_button = QPushButton("Enviar")
        self.transcribe_button = QPushButton("Transcrever arquivo de áudio")
        self.speak_button = QPushButton("Ouvir última resposta")
        self.transcribe_button.clicked.connect(self.transcribe_audio_file)
        self.speak_button.clicked.connect(self.speak_last_answer)
        self.logout_button = QPushButton("Sair da conta")
        self.memories_button = QPushButton("Memórias")
        self.new_conversation_button = QPushButton("Nova conversa")
        self.new_conversation_button.clicked.connect(self.new_conversation)
        self.memories_button.clicked.connect(self.open_memories)
        self.send_button.clicked.connect(self.send_message)
        self.input.returnPressed.connect(self.send_message)
        self.logout_button.clicked.connect(self.logout)

        layout = QVBoxLayout()
        for widget in (
            self.status,
            self.auth_title,
            self.email,
            self.password,
            self.login_button,
            self.signup_button,
            self.transcript,
            self.input,
            self.send_button,
            self.transcribe_button,
            self.speak_button,
            self.memories_button,
            self.new_conversation_button,
            self.logout_button,
        ):
            layout.addWidget(widget)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self._set_chat_visible(False)
        self.speak_button.setEnabled(False)
        self.check_api()

    def _set_chat_visible(self, visible: bool) -> None:
        for widget in (self.transcript, self.input, self.send_button, self.transcribe_button, self.speak_button):
            widget.setVisible(visible)
        self.memories_button.setVisible(visible)
        self.new_conversation_button.setVisible(visible and self._auth_mode == "local")
        self.logout_button.setVisible(visible and self._auth_mode == "supabase")
        for widget in (
            self.auth_title,
            self.email,
            self.password,
            self.login_button,
            self.signup_button,
        ):
            widget.setVisible(not visible)

    def check_api(self) -> None:
        try:
            response = httpx.get(f"{API_BASE}/health", timeout=2.0)
            response.raise_for_status()
            payload = response.json()
            self._auth_mode = (
                "local" if payload.get("auth_mode") == "local" else "supabase"
            )
            if self._auth_mode == "local":
                self._set_chat_visible(True)
                self.status.setText("ATLAS conectado · memória e histórico locais")
                if self._conversation_id:
                    self._load_history()
            else:
                self.status.setText("ATLAS API conectada · autenticação Supabase")
        except (httpx.HTTPError, ValueError):
            self.status.setText("ATLAS API: offline. Inicie o backend local.")

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
        email = self.email.text().strip()
        password = self.password.text()
        if not email or not password:
            self.status.setText("Informe e-mail e senha.")
            return
        if len(password) < 8:
            self.status.setText("A senha deve ter pelo menos 8 caracteres.")
            return
        self.login_button.setEnabled(False)
        self.signup_button.setEnabled(False)
        self.status.setText("Conectando ao Supabase Auth...")
        self._start_worker(
            ApiWorker(operation, email=email, password=password, parent=self),
            operation,
        )

    def send_message(self) -> None:
        message = self.input.text().strip()
        if not message or self._worker is not None:
            return
        if self._auth_mode == "supabase" and not self._access_token:
            return
        self.transcript.append(f"<b>Você:</b> {_safe_html(message)}")
        self.input.clear()
        self.send_button.setEnabled(False)
        self.input.setEnabled(False)
        self._start_worker(
            ApiWorker(
                "chat",
                message=message,
                access_token=self._access_token,
                conversation_id=self._conversation_id,
                parent=self,
            ),
            "chat",
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

    def speak_last_answer(self) -> None:
        if self._worker is not None or not self._last_answer:
            return
        if self._auth_mode == "supabase" and not self._access_token:
            self.status.setText("Entre na sua conta antes de usar a voz.")
            return
        self.status.setText("Gerando resposta em áudio...")
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
        self._player.setSourceDevice(buffer, QUrl("audio/mpeg"))
        self._player.play()
        self.status.setText("Reproduzindo resposta do ATLAS.")

    def new_conversation(self) -> None:
        if self._worker is not None or self._auth_mode != "local":
            return
        self._start_worker(ApiWorker("new_conversation", parent=self), "new_conversation")

    def _load_history(self) -> None:
        if self._worker is not None or not self._conversation_id or self._auth_mode != "local":
            return
        self._start_worker(
            ApiWorker("history", conversation_id=self._conversation_id, parent=self),
            "history",
        )

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
        self.status.setText("Encerrando sessão...")
        self._start_worker(ApiWorker("logout", access_token=token, parent=self), "logout")

    def _on_success(self, result: Any) -> None:
        if not isinstance(result, dict):
            self.status.setText("A API retornou uma resposta inválida.")
            return
        operation = result.get("operation")
        if operation in ("login", "signup"):
            token = result.get("access_token")
            if isinstance(token, str) and token:
                self._access_token = token
                user_id = result.get("user_id")
                suffix = f" · usuário {user_id}" if isinstance(user_id, str) else ""
                self.status.setText(f"ATLAS conectado{suffix}")
                self.transcript.clear()
                self._set_chat_visible(True)
                self.input.setFocus()
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
                self.status.setText("Nova conversa iniciada.")
        elif operation == "history":
            self.transcript.clear()
            for message in result.get("messages", []):
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
        elif operation == "chat":
            answer = result.get("response")
            conversation_id = result.get("conversation_id")
            if isinstance(conversation_id, str) and conversation_id:
                self._conversation_id = conversation_id
                self._settings.setValue("active_conversation_id", conversation_id)
            if isinstance(answer, str):
                self._last_answer = answer
                self.speak_button.setEnabled(bool(answer.strip()))
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
        self._update_controls()

    def _on_finished(self) -> None:
        self._worker = None
        self._update_controls()

    def _update_controls(self) -> None:
        busy = self._worker is not None
        authenticated = self._auth_mode == "local" or bool(self._access_token)
        self.login_button.setEnabled(not busy)
        self.signup_button.setEnabled(not busy)
        self.send_button.setEnabled(not busy and authenticated)
        self.input.setEnabled(not busy and authenticated)
        self.transcribe_button.setEnabled(not busy and authenticated)
        self.speak_button.setEnabled(not busy and authenticated and bool(self._last_answer))


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AtlasWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
