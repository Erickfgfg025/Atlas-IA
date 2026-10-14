import html
import sys

import httpx
from PySide6.QtCore import QThread, Signal
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


def _safe_html(text: str) -> str:
    """Escape untrusted chat content before displaying it in QTextEdit."""
    return html.escape(text).replace("\n", "<br>")


class ChatWorker(QThread):
    response_received = Signal(str)

    def __init__(self, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.message = message

    def run(self) -> None:
        try:
            response = httpx.post(
                "http://127.0.0.1:8000/chat",
                json={"message": self.message},
                timeout=60.0,
            )
            if response.is_success:
                payload = response.json()
                answer = payload.get("response") if isinstance(payload, dict) else None
                if not isinstance(answer, str) or not answer.strip():
                    answer = "A API retornou uma resposta inválida."
            else:
                try:
                    payload = response.json()
                    detail = payload.get("detail", "Falha na API.")
                except ValueError:
                    detail = "Falha na API."
                answer = f"Erro: {detail}"
        except httpx.HTTPError:
            answer = "Não foi possível conectar à API local."
        except ValueError:
            answer = "A API retornou uma resposta inválida."

        self.response_received.emit(answer)


class AtlasWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._chat_worker: ChatWorker | None = None
        self.setWindowTitle("ATLAS AI")
        self.resize(760, 560)
        self.setMinimumSize(600, 420)
        self.status = QLabel("ATLAS API: verificando...")
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Escreva uma mensagem para o ATLAS...")
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.send_message)
        self.input.returnPressed.connect(self.send_message)
        layout = QVBoxLayout()
        layout.addWidget(self.status)
        layout.addWidget(self.transcript, 1)
        layout.addWidget(self.input)
        layout.addWidget(self.send_button)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.check_api()

    def check_api(self) -> None:
        try:
            response = httpx.get("http://127.0.0.1:8000/health", timeout=2.0)
            response.raise_for_status()
            self.status.setText("ATLAS API: conectado")
        except httpx.HTTPError:
            self.status.setText("ATLAS API: offline. Inicie o backend local.")

    def send_message(self) -> None:
        message = self.input.text().strip()
        if not message or self._chat_worker is not None:
            return

        self.transcript.append(f"<b>Você:</b> {_safe_html(message)}")
        self.input.clear()
        self.send_button.setEnabled(False)
        self.input.setEnabled(False)

        worker = ChatWorker(message, self)
        self._chat_worker = worker
        worker.response_received.connect(self._display_response)
        worker.finished.connect(self._chat_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _display_response(self, answer: str) -> None:
        self.transcript.append(f"<b>ATLAS:</b> {_safe_html(answer)}")

    def _chat_finished(self) -> None:
        self.send_button.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
        self._chat_worker = None


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AtlasWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
