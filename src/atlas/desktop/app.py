import sys
import httpx
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget


class AtlasWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
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
        if not message:
            return
        self.transcript.append(f"<b>Você:</b> {message}")
        self.input.clear()
        self.send_button.setEnabled(False)
        try:
            response = httpx.post("http://127.0.0.1:8000/chat", json={"message": message}, timeout=60.0)
            if response.is_success:
                answer = response.json()["response"]
            else:
                answer = f"Erro: {response.json().get('detail', 'Falha na API.')}"
        except httpx.HTTPError:
            answer = "Não foi possível conectar à API local."
        self.transcript.append(f"<b>ATLAS:</b> {answer}")
        self.send_button.setEnabled(True)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AtlasWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
