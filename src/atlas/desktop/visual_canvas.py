"""Safe local canvas for declarative AI-authored motion scenes."""
from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class VisualCanvas(QFrame):
    """Render a bounded scene description without executing generated code."""

    ALLOWED = {"circle", "ring", "line", "rect", "text", "orbit", "dot"}
    MOTIONS = {"float", "pulse", "spin", "none"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("VisualCanvas")
        self.setMinimumHeight(260)
        self.setStyleSheet(
            "QFrame#VisualCanvas { background:#0B0D11; border:1px solid #34302C; "
            "border-radius:16px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        title = QLabel("CANVAS GENERATIVO · TEMPO REAL")
        title.setStyleSheet(
            "color:#FF8A24; font-size:9px; font-weight:700; "
            "letter-spacing:2px; border:0;"
        )
        layout.addWidget(title)
        self.hint = QLabel("Descreva uma cena para a IA construir a composição.")
        self.hint.setStyleSheet("color:#858B98; font-size:11px; border:0;")
        layout.addWidget(self.hint)
        self.stage = _SceneStage(self)
        layout.addWidget(self.stage, 1)
        self.hide()

    @staticmethod
    def _safe_color(value: Any) -> str:
        color = QColor(str(value))
        return color.name() if color.isValid() else "#FF8A24"

    def set_scene(self, scene: dict[str, Any]) -> None:
        items = scene.get("elements", [])
        if not isinstance(items, list):
            raise ValueError("Lista de elementos inválida.")
        clean: list[dict[str, Any]] = []
        for item in items[:32]:
            if not isinstance(item, dict) or item.get("type") not in self.ALLOWED:
                continue
            try:
                clean.append(
                    {
                        "type": item["type"],
                        "x": max(0.0, min(100.0, float(item.get("x", 50)))),
                        "y": max(0.0, min(100.0, float(item.get("y", 50)))),
                        "size": max(2.0, min(45.0, float(item.get("size", 12)))),
                        "color": self._safe_color(item.get("color", "#FF8A24")),
                        "text": str(item.get("text", ""))[:100],
                        "motion": (
                            item.get("motion")
                            if item.get("motion") in self.MOTIONS
                            else "float"
                        ),
                    }
                )
            except (TypeError, ValueError):
                continue
        if not clean:
            raise ValueError("A IA não produziu elementos visuais válidos.")
        self.stage.elements = clean
        self.stage.phase = 0.0
        self.stage.update()
        self.hint.setText(str(scene.get("title", "Cena criada pela IA"))[:120])
        self.show()


class _SceneStage(QWidget):
    """Small QPainter-based animation stage."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.elements: list[dict[str, Any]] = []
        self.phase = 0.0
        self.setMinimumHeight(205)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _tick(self) -> None:
        self.phase = (self.phase + 0.025) % math.tau
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0B0D11"))
        width, height = self.width(), self.height()
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
        for x in range(0, width, 28):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, 28):
            painter.drawLine(0, y, width, y)

        for index, element in enumerate(self.elements):
            x = width * element["x"] / 100
            y = height * element["y"] / 100
            size = min(width, height) * element["size"] / 100
            motion = element["motion"]
            if motion == "float":
                y += math.sin(self.phase + index * 0.7) * min(12, size * 0.22)
            elif motion == "pulse":
                size *= 0.88 + 0.12 * math.sin(self.phase * 2 + index)
            elif motion == "spin":
                x += math.cos(self.phase + index) * min(10, size * 0.25)

            color = QColor(element["color"])
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            kind = element["type"]
            if kind == "dot":
                painter.setBrush(color)
                painter.drawEllipse(
                    int(x - size * 0.12),
                    int(y - size * 0.12),
                    int(size * 0.24),
                    int(size * 0.24),
                )
            elif kind == "circle":
                painter.drawEllipse(
                    int(x - size), int(y - size), int(size * 2), int(size * 2)
                )
            elif kind == "ring":
                painter.drawEllipse(
                    int(x - size), int(y - size), int(size * 2), int(size * 2)
                )
                painter.drawEllipse(
                    int(x - size * 0.68),
                    int(y - size * 0.68),
                    int(size * 1.36),
                    int(size * 1.36),
                )
            elif kind == "orbit":
                painter.save()
                painter.translate(x, y)
                painter.rotate(math.degrees(self.phase))
                painter.drawEllipse(
                    int(-size * 1.4),
                    int(-size * 0.48),
                    int(size * 2.8),
                    int(size * 0.96),
                )
                painter.setBrush(color)
                painter.drawEllipse(
                    int(size * 1.15),
                    int(-size * 0.08),
                    int(size * 0.16),
                    int(size * 0.16),
                )
                painter.restore()
            elif kind == "line":
                painter.drawLine(
                    int(x - size * 1.5), int(y), int(x + size * 1.5), int(y)
                )
            elif kind == "rect":
                painter.drawRoundedRect(
                    int(x - size),
                    int(y - size * 0.55),
                    int(size * 2),
                    int(size * 1.1),
                    8,
                    8,
                )
            elif kind == "text" and element["text"]:
                painter.setFont(
                    QFont("Segoe UI", max(9, int(size * 0.42)), QFont.Weight.DemiBold)
                )
                painter.drawText(
                    int(x - size * 2),
                    int(y - size * 0.4),
                    int(size * 4),
                    int(size * 0.8),
                    Qt.AlignmentFlag.AlignCenter,
                    element["text"],
                )
        painter.end()
