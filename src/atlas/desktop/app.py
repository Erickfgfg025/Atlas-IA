import html
import sys
from typing import Any

import httpx
from PySide6.QtCore import QThread, Signal, QSettings
from atlas.desktop.memories_dialog import MemoryDialog
from PySide6.QtCore import QThread, Signal, QSettings, Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
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
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.operation = operation
        self.email = email
        self.password = password
        self.message = message
        self.access_token = access_token
        self.conversation_id = conversation_id

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


class FloatingAssistant(QDialog):
    """Compact companion window; uses the same conversation and API state."""

    send_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("ATLAS · Quick")
        self.setFixedSize(370, 440)
        self.setStyleSheet("""
            QDialog { background: #111113; color: #F4F4F5; border: 1px solid #343438; }
            QLabel { color: #F4F4F5; }
            QTextEdit { background: #19191C; color: #F4F4F5; border: 1px solid #303035; border-radius: 12px; padding: 10px; }
            QLineEdit { background: #1B1B1F; color: #F4F4F5; border: 1px solid #37373D; border-radius: 10px; padding: 11px; }
            QPushButton { background: #FF7900; color: #111113; border: 0; border-radius: 10px; padding: 10px 14px; font-weight: 700; }
            QPushButton:hover { background: #FF9A3D; }
        """)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        mark = QLabel("◈")
        mark.setStyleSheet("color:#FF7900;font-size:22px;font-weight:800;")
        title = QLabel("ATLAS <span style='color:#FF7900'>QUICK</span>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setStyleSheet("font-size:14px;font-weight:800;letter-spacing:1px;")
        top.addWidget(mark)
        top.addWidget(title)
        top.addStretch()
        layout.addLayout(top)
        self.reply = QTextEdit()
        self.reply.setReadOnly(True)
        self.reply.setPlaceholderText("Seu assistente, a um atalho de distância.")
        layout.addWidget(self.reply, 1)
        row = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Pergunte ao ATLAS...")
        self.send = QPushButton("Enviar")
        self.send.clicked.connect(self._send)
        self.entry.returnPressed.connect(self._send)
        row.addWidget(self.entry, 1)
        row.addWidget(self.send)
        layout.addLayout(row)

    def _send(self):
        value = self.entry.text().strip()
        if value:
            self.entry.clear()
            self.send_requested.emit(value)

    def show_answer(self, question: str, answer: str):
        self.reply.append(f"<b style='color:#FF9A3D'>Você</b><br>{_safe_html(question)}")
        self.reply.append(f"<b style='color:#FF9A3D'>ATLAS</b><br>{_safe_html(answer)}")


class AtlasWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._access_token = ""
        self._auth_mode = "supabase"
        self._worker: ApiWorker | None = None
        self._pending_operation = ""
        self._settings = QSettings("AtlasAI", "ATLAS")
        self._conversation_id = self._settings.value("active_conversation_id", "", type=str)
        self._last_question = ""
        self._floating = None
        self.setWindowTitle("ATLAS AI")
        self.resize(1420, 900)
        self.setMinimumSize(1040, 680)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()
        self._set_chat_visible(False)
        self.check_api()

    def _stylesheet(self) -> str:
        return """
        * { font-family: 'Inter', 'Segoe UI', sans-serif; }
        QMainWindow, QWidget#root { background:#0B0B0D; color:#F2F2F4; }
        QFrame#sidebar { background:#101012; border-right:1px solid #242428; }
        QFrame#topbar { background:#0B0B0D; border-bottom:1px solid #242428; }
        QLabel { color:#F2F2F4; }
        QLabel#brand { font-family:'Manrope','Segoe UI'; font-size:22px; font-weight:800; letter-spacing:2px; }
        QLabel#eyebrow { color:#85858E; font-size:10px; font-weight:800; letter-spacing:2px; }
        QLabel#pageTitle { font-family:'Manrope','Segoe UI'; font-size:22px; font-weight:800; }
        QLabel#muted { color:#92929B; font-size:12px; }
        QLabel#orange { color:#FF7900; font-weight:800; }
        QLabel#statusDot { color:#FF7900; font-size:13px; }
        QPushButton { background:#202024; color:#D9D9DE; border:1px solid #303035; border-radius:10px; padding:10px 13px; font-weight:600; }
        QPushButton:hover { background:#2A2A2F; border-color:#4A4A52; }
        QPushButton:disabled { color:#66666E; background:#171719; }
        QPushButton#primary { background:#FF7900; color:#111113; border:0; font-weight:800; }
        QPushButton#primary:hover { background:#FF9A3D; }
        QPushButton#nav { background:transparent; border:0; text-align:left; padding:12px 14px; color:#A8A8B0; }
        QPushButton#nav:hover { background:#1C1C20; color:#F2F2F4; }
        QPushButton#navActive { background:#2A1A10; border:1px solid #593016; color:#FF9A3D; text-align:left; padding:12px 14px; }
        QFrame#panel { background:#121214; border:1px solid #28282D; border-radius:16px; }
        QFrame#activityCard { background:#18181B; border:1px solid #29292F; border-radius:12px; }
        QTextEdit { background:#101012; color:#EDEDF0; border:0; padding:12px; selection-background-color:#6B350F; font-size:14px; }
        QLineEdit { background:#18181B; color:#F2F2F4; border:1px solid #34343A; border-radius:12px; padding:13px 14px; selection-background-color:#6B350F; }
        QLineEdit:focus { border:1px solid #FF7900; }
        QScrollBar:vertical { background:#101012; width:8px; margin:0; }
        QScrollBar::handle:vertical { background:#38383F; min-height:24px; border-radius:4px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(224)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(18, 24, 18, 18)
        side.setSpacing(10)
        brand_row = QHBoxLayout()
        logo = QLabel("◈")
        logo.setStyleSheet("color:#FF7900;font-size:28px;font-weight:900;")
        brand = QLabel("ATLAS")
        brand.setObjectName("brand")
        brand_row.addWidget(logo)
        brand_row.addWidget(brand)
        brand_row.addStretch()
        side.addLayout(brand_row)
        sub = QLabel("INTELLIGENCE SYSTEM")
        sub.setObjectName("eyebrow")
        side.addWidget(sub)
        side.addSpacing(28)
        nav_label = QLabel("ESPAÇO DE TRABALHO")
        nav_label.setObjectName("eyebrow")
        side.addWidget(nav_label)
        self.chat_nav = QPushButton("◉   Conversa")
        self.chat_nav.setObjectName("navActive")
        self.activity_nav = QPushButton("⌁   Atividades")
        self.activity_nav.setObjectName("nav")
        self.memory_nav = QPushButton("▤   Memórias")
        self.memory_nav.setObjectName("nav")
        self.settings_nav = QPushButton("⚙   Configurações")
        self.settings_nav.setObjectName("nav")
        for button in (self.chat_nav, self.activity_nav, self.memory_nav, self.settings_nav):
            side.addWidget(button)
        self.chat_nav.clicked.connect(lambda: self.transcript.setFocus())
        self.activity_nav.clicked.connect(lambda: self.activity_panel.setVisible(not self.activity_panel.isVisible()))
        self.memory_nav.clicked.connect(self.open_memories)
        self.settings_nav.clicked.connect(self.open_settings)
        side.addStretch()
        self.side_state = QLabel("●  SISTEMA PRONTO")
        self.side_state.setStyleSheet("color:#FF9A3D;font-size:10px;font-weight:800;letter-spacing:1px;")
        side.addWidget(self.side_state)
        side.addWidget(QLabel("Desktop • Windows 10/11"))
        side.addWidget(QLabel("ATLAS AI  /  0.1.0"))
        outer.addWidget(self.sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 0, 28, 22)
        content_layout.setSpacing(18)
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(84)
        top = QHBoxLayout(topbar)
        top.setContentsMargins(0, 14, 0, 14)
        titles = QVBoxLayout()
        title = QLabel("Seu espaço de inteligência")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Converse, organize ideias e acompanhe o que o ATLAS está fazendo.")
        subtitle.setObjectName("muted")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        top.addLayout(titles)
        top.addStretch()
        self.status = QLabel("●  Verificando conexão")
        self.status.setObjectName("orange")
        top.addWidget(self.status)
        self.quick_button = QPushButton("↗  Painel flutuante")
        self.quick_button.clicked.connect(self.open_floating)
        top.addWidget(self.quick_button)
        content_layout.addWidget(topbar)

        workspace = QHBoxLayout()
        workspace.setSpacing(18)
        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("panel")
        chat_layout = QVBoxLayout(self.chat_panel)
        chat_layout.setContentsMargins(20, 18, 20, 18)
        chat_layout.setSpacing(12)
        chat_head = QHBoxLayout()
        chat_heading = QVBoxLayout()
        chat_heading.addWidget(QLabel("CONVERSA"))
        self.conversation_caption = QLabel("Uma conversa com contexto e memória")
        self.conversation_caption.setObjectName("muted")
        chat_heading.addWidget(self.conversation_caption)
        chat_head.addLayout(chat_heading)
        chat_head.addStretch()
        self.new_conversation_button = QPushButton("+  Nova conversa")
        self.new_conversation_button.clicked.connect(self.new_conversation)
        chat_head.addWidget(self.new_conversation_button)
        chat_layout.addLayout(chat_head)
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("O ATLAS está pronto. Comece uma conversa para explorar ideias, planejar tarefas ou pedir ajuda.")
        chat_layout.addWidget(self.transcript, 1)
        composer = QFrame()
        composer.setObjectName("activityCard")
        composer_layout = QHBoxLayout(composer)
        composer_layout.setContentsMargins(10, 8, 8, 8)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Escreva uma mensagem para o ATLAS...")
        self.input.returnPressed.connect(self.send_message)
        self.send_button = QPushButton("Enviar  ↑")
        self.send_button.setObjectName("primary")
        self.send_button.clicked.connect(self.send_message)
        composer_layout.addWidget(self.input, 1)
        composer_layout.addWidget(self.send_button)
        chat_layout.addWidget(composer)
        hint = QLabel("ENTER para enviar  ·  Ações no computador exigirão permissões explícitas")
        hint.setObjectName("muted")
        chat_layout.addWidget(hint)
        workspace.addWidget(self.chat_panel, 1)

        self.activity_panel = QFrame()
        self.activity_panel.setObjectName("panel")
        self.activity_panel.setFixedWidth(258)
        activity = QVBoxLayout(self.activity_panel)
        activity.setContentsMargins(16, 18, 16, 16)
        activity.setSpacing(12)
        activity_title = QLabel("CENTRAL DE ATIVIDADES")
        activity_title.setObjectName("eyebrow")
        activity.addWidget(activity_title)
        activity.addWidget(QLabel("Visão geral"))
        self.api_activity = self._activity_card("●", "Backend local", "Aguardando verificação")
        self.memory_activity = self._activity_card("▤", "Memória", "Armazenamento local")
        self.model_activity = self._activity_card("✳", "Modelo de IA", "Gemini configurável")
        activity.addWidget(self.api_activity)
        activity.addWidget(self.memory_activity)
        activity.addWidget(self.model_activity)
        activity.addSpacing(10)
        activity.addWidget(QLabel("EXECUÇÃO SEGURA"))
        safety = QLabel("O ATLAS deve pedir confirmação antes de ações sensíveis. Nenhuma ação no computador é executada apenas por aparecer no chat.")
        safety.setWordWrap(True)
        safety.setObjectName("muted")
        activity.addWidget(safety)
        activity.addStretch()
        self.activity_status = QLabel("Nenhuma tarefa em execução.")
        self.activity_status.setWordWrap(True)
        self.activity_status.setObjectName("muted")
        activity.addWidget(self.activity_status)
        workspace.addWidget(self.activity_panel)
        content_layout.addLayout(workspace, 1)

        auth = QFrame()
        auth.setObjectName("panel")
        auth_layout = QVBoxLayout(auth)
        auth_layout.setContentsMargins(20, 18, 20, 18)
        self.auth_title = QLabel("Entre na sua conta ATLAS")
        self.auth_title.setObjectName("pageTitle")
        self.email = QLineEdit()
        self.email.setPlaceholderText("E-mail")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Senha (mínimo 8 caracteres)")
        self.password.setEchoMode(QLineEdit.Password)
        auth_buttons = QHBoxLayout()
        self.login_button = QPushButton("Entrar")
        self.signup_button = QPushButton("Criar conta")
        self.login_button.setObjectName("primary")
        self.login_button.clicked.connect(lambda: self.start_auth("login"))
        self.signup_button.clicked.connect(lambda: self.start_auth("signup"))
        auth_buttons.addWidget(self.login_button)
        auth_buttons.addWidget(self.signup_button)
        auth_layout.addWidget(self.auth_title)
        auth_layout.addWidget(self.email)
        auth_layout.addWidget(self.password)
        auth_layout.addLayout(auth_buttons)
        content_layout.addWidget(auth)
        self.auth_panel = auth

        outer.addWidget(content, 1)
        self.setCentralWidget(root)

    def _activity_card(self, symbol: str, title: str, detail: str) -> QFrame:
        card = QFrame()
        card.setObjectName("activityCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        marker = QLabel(f"<span style='color:#FF7900'>{symbol}</span>  <b>{title}</b>")
        marker.setTextFormat(Qt.TextFormat.RichText)
        description = QLabel(detail)
        description.setObjectName("muted")
        description.setWordWrap(True)
        layout.addWidget(marker)
        layout.addWidget(description)
        card.detail_label = description
        return card

    def _set_chat_visible(self, visible: bool) -> None:
        self.chat_panel.setVisible(visible)
        self.activity_panel.setVisible(visible)
        self.quick_button.setVisible(visible)
        self.auth_panel.setVisible(not visible)
        self.new_conversation_button.setVisible(visible and self._auth_mode == "local")
        self.memory_nav.setVisible(visible)
        self.logout_button = getattr(self, "logout_button", None)
        if self.logout_button is not None:
            self.logout_button.setVisible(visible and self._auth_mode == "supabase")

    def check_api(self) -> None:
        try:
            response = httpx.get(f"{API_BASE}/health", timeout=2.0)
            response.raise_for_status()
            payload = response.json()
            self._auth_mode = "local" if payload.get("auth_mode") == "local" else "supabase"
            if self._auth_mode == "local":
                self._set_chat_visible(True)
                self.status.setText("●  ATLAS conectado")
                self.side_state.setText("●  SISTEMA PRONTO")
                self.api_activity.detail_label.setText("Conectado em 127.0.0.1:8000")
                self.memory_activity.detail_label.setText("SQLite · local")
                self._load_history() if self._conversation_id else None
            else:
                self.status.setText("●  Autenticação Supabase")
                self.api_activity.detail_label.setText("API local conectada")
                self.memory_activity.detail_label.setText("Sessão autenticada necessária")
        except (httpx.HTTPError, ValueError):
            self.status.setText("●  API offline")
            self.side_state.setText("●  API DESCONECTADA")
            self.api_activity.detail_label.setText("Inicie o backend local")

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
        email, password = self.email.text().strip(), self.password.text()
        if not email or not password:
            self.status.setText("Informe e-mail e senha.")
            return
        if len(password) < 8:
            self.status.setText("A senha deve ter pelo menos 8 caracteres.")
            return
        self.login_button.setEnabled(False)
        self.signup_button.setEnabled(False)
        self.status.setText("Conectando ao Supabase Auth...")
        self._start_worker(ApiWorker(operation, email=email, password=password, parent=self), operation)

    def send_message(self, message: str | None = None) -> None:
        message = (message if message is not None else self.input.text()).strip()
        if not message or self._worker is not None:
            return
        if self._auth_mode == "supabase" and not self._access_token:
            return
        self._last_question = message
        self.transcript.append(f"<div style='margin-top:16px'><b style='color:#FF9A3D'>VOCÊ</b><br>{_safe_html(message)}</div>")
        self.activity_status.setText("Mensagem enviada · aguardando resposta do modelo.")
        self.input.clear()
        self.send_button.setEnabled(False)
        self.input.setEnabled(False)
        self._start_worker(ApiWorker("chat", message=message, access_token=self._access_token, conversation_id=self._conversation_id, parent=self), "chat")

    def new_conversation(self) -> None:
        if self._worker is None and self._auth_mode == "local":
            self._start_worker(ApiWorker("new_conversation", parent=self), "new_conversation")

    def _load_history(self) -> None:
        if self._worker is None and self._conversation_id and self._auth_mode == "local":
            self._start_worker(ApiWorker("history", conversation_id=self._conversation_id, parent=self), "history")

    def open_memories(self) -> None:
        if self._worker is None:
            MemoryDialog(self._access_token, self).exec()

    def open_settings(self) -> None:
        QMessageBox.information(self, "Configurações", "As configurações avançadas serão adicionadas em uma próxima etapa. As credenciais devem permanecer no arquivo .env local e nunca no repositório.")

    def open_floating(self) -> None:
        if self._floating is None:
            self._floating = FloatingAssistant(self)
            self._floating.send_requested.connect(self.send_message)
        self._floating.show()
        self._floating.raise_()
        self._floating.activateWindow()

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
                self.status.setText("●  ATLAS autenticado")
                self.transcript.clear()
                self._set_chat_visible(True)
                self.input.setFocus()
            elif operation == "signup" and result.get("confirmation_required"):
                self.status.setText("Conta criada. Confirme o e-mail e entre.")
            else:
                self.status.setText("A autenticação não retornou uma sessão válida.")
        elif operation == "new_conversation":
            conversation_id = result.get("conversation_id")
            if isinstance(conversation_id, str):
                self._conversation_id = conversation_id
                self._settings.setValue("active_conversation_id", conversation_id)
                self.transcript.clear()
                self.status.setText("●  Nova conversa iniciada")
                self.activity_status.setText("Conversa nova · contexto anterior separado.")
        elif operation == "history":
            self.transcript.clear()
            for message in result.get("messages", []):
                if isinstance(message, dict):
                    role, content = message.get("role"), message.get("content")
                    if role in ("user", "assistant") and isinstance(content, str):
                        label = "VOCÊ" if role == "user" else "ATLAS"
                        color = "#FF9A3D" if role == "user" else "#F2F2F4"
                        self.transcript.append(f"<div style='margin-top:14px'><b style='color:{color}'>{label}</b><br>{_safe_html(content)}</div>")
            self.status.setText("●  Histórico restaurado")
        elif operation == "chat":
            answer = result.get("response")
            conversation_id = result.get("conversation_id")
            if isinstance(conversation_id, str) and conversation_id:
                self._conversation_id = conversation_id
                self._settings.setValue("active_conversation_id", conversation_id)
            if isinstance(answer, str):
                self.transcript.append(f"<div style='margin-top:16px'><b style='color:#FF7900'>ATLAS</b><br>{_safe_html(answer)}</div>")
                if self._floating is not None and self._floating.isVisible():
                    self._floating.show_answer(self._last_question, answer)
                self.activity_status.setText("Resposta concluída.")
        elif operation == "logout":
            self._set_chat_visible(False)
            self.transcript.clear()
            self.email.clear()
            self.password.clear()
            self.status.setText("Sessão encerrada.")
        self._update_controls()

    def _on_failure(self, message: str) -> None:
        self.status.setText(message)
        self.activity_status.setText("A última operação não foi concluída.")
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

def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AtlasWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
