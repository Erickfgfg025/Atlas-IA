"""Manage saved memories in a separate non-blocking dialog."""
import httpx
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget

API_BASE = "http://127.0.0.1:8000"


class MemoryWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, action, token="", memory_id="", content="", parent=None):
        super().__init__(parent)
        self.action, self.token = action, token
        self.memory_id, self.content = memory_id, content

    def run(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            if self.action == "list":
                response = httpx.get(f"{API_BASE}/memories", params={"limit": 100}, headers=headers, timeout=10)
            elif self.action == "update":
                response = httpx.put(f"{API_BASE}/memories/{self.memory_id}", json={"content": self.content}, headers=headers, timeout=10)
            else:
                response = httpx.delete(f"{API_BASE}/memories/{self.memory_id}", headers=headers, timeout=10)
                if response.status_code == 204:
                    self.succeeded.emit({"action": "delete"})
                    return
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            if not response.is_success:
                self.failed.emit(str(payload.get("detail", "A operação falhou.")))
            elif self.action == "list" and isinstance(payload, list):
                self.succeeded.emit({"action": "list", "memories": payload})
            elif self.action == "update" and isinstance(payload, dict):
                self.succeeded.emit({"action": "update"})
            else:
                self.failed.emit("Resposta inválida da API.")
        except httpx.HTTPError:
            self.failed.emit("Não foi possível conectar à API local.")


class MemoryDialog(QDialog):
    def __init__(self, token="", parent=None):
        super().__init__(parent)
        self.token = token
        self.worker = None
        self.records = {}
        self.setWindowTitle("Memórias do ATLAS")
        self.resize(620, 440)
        self.items = QListWidget()
        self.status = QLabel("Carregando memórias...")
        self.refresh_button = QPushButton("Atualizar")
        self.edit_button = QPushButton("Editar")
        self.delete_button = QPushButton("Excluir")
        close_button = QPushButton("Fechar")
        self.refresh_button.clicked.connect(self.refresh)
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        close_button.clicked.connect(self.accept)
        actions = QHBoxLayout()
        for button in (self.refresh_button, self.edit_button, self.delete_button, close_button):
            actions.addWidget(button)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Revise, corrija ou exclua as informações salvas."))
        layout.addWidget(self.items)
        layout.addWidget(self.status)
        layout.addLayout(actions)
        self.items.currentItemChanged.connect(lambda *_: self._controls())
        self.refresh()

    def _controls(self):
        busy = self.worker is not None
        self.refresh_button.setEnabled(not busy)
        self.edit_button.setEnabled(not busy and self.items.currentItem() is not None)
        self.delete_button.setEnabled(not busy and self.items.currentItem() is not None)

    def _start(self, action, memory_id="", content=""):
        if self.worker is not None:
            return
        self.worker = MemoryWorker(action, self.token, memory_id, content, self)
        self.worker.succeeded.connect(self._success)
        self.worker.failed.connect(self.status.setText)
        self.worker.finished.connect(self._finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self._controls()
        self.worker.start()

    def refresh(self):
        self.status.setText("Carregando memórias...")
        self._start("list")

    def _selected(self):
        item = self.items.currentItem()
        return self.records.get(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def edit_selected(self):
        record = self._selected()
        if not record or self.worker is not None:
            return
        value, ok = QInputDialog.getMultiLineText(self, "Editar memória", "Conteúdo:", record.get("content", ""))
        value = value.strip()
        if ok and value:
            self.status.setText("Salvando...")
            self._start("update", str(record["id"]), value)
        elif ok:
            QMessageBox.warning(self, "Conteúdo vazio", "A memória não pode ficar vazia.")

    def delete_selected(self):
        record = self._selected()
        if not record or self.worker is not None:
            return
        answer = QMessageBox.question(self, "Excluir memória", "Excluir esta memória permanentemente?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.status.setText("Excluindo...")
            self._start("delete", str(record["id"]))

    def _success(self, result):
        if result.get("action") == "list":
            self.items.clear()
            self.records.clear()
            for record in result["memories"]:
                if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                    continue
                memory_id = record["id"]
                self.records[memory_id] = record
                content = str(record.get("content", ""))
                item = QListWidgetItem(f'[{record.get("kind", "memória")}] {content.replace(chr(10), " ")[:160]}')
                item.setData(Qt.ItemDataRole.UserRole, memory_id)
                item.setToolTip(content)
                self.items.addItem(item)
            self.status.setText(f"{len(self.records)} memória(s).")
        else:
            self.status.setText("Memória atualizada." if result.get("action") == "update" else "Memória excluída.")
            self.refresh()

    def _finished(self):
        self.worker = None
        self._controls()
