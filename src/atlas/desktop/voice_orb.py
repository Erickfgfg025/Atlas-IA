"""Animated ATLAS voice orb inspired by a living, reactive assistant interface."""
from __future__ import annotations

import math
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QRadialGradient, QPen
from PySide6.QtWidgets import QWidget


class VoiceOrb(QWidget):
    """Lightweight animated orb with idle, listening, thinking and speaking states."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._phase = 0.0
        self._state = "idle"
        self.setMinimumHeight(220)
        self.setMaximumHeight(300)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_state(self, state: str) -> None:
        if state not in {"idle", "listening", "thinking", "speaking"}:
            state = "idle"
        self._state = state
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + (0.105 if self._state == "speaking" else 0.045)) % (math.tau)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        cx, cy = self.width() / 2, self.height() / 2
        base = min(self.width() * 0.32, self.height() * 0.39)
        pulse = math.sin(self._phase * (2.8 if self._state == "speaking" else 1.0))
        intensity = {"idle": 0.10, "listening": 0.28, "thinking": 0.19, "speaking": 0.42}[self._state]
        radius = base * (1.0 + intensity * 0.10 * pulse)
        glow = QRadialGradient(cx, cy, radius * 1.65)
        glow.setColorAt(0.0, QColor(0, 132, 255, 105 if self._state == "speaking" else 65))
        glow.setColorAt(0.48, QColor(0, 74, 210, 30))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(int(cx - radius * 1.65), int(cy - radius * 1.65), int(radius * 3.3), int(radius * 3.3))

        # Several gently shifting orbital curves create the living cyan/blue energy ring.
        for index in range(7):
            phase = self._phase + index * 0.37
            scale = 0.78 + index * 0.045 + pulse * intensity * 0.05
            rx = radius * scale
            ry = radius * (0.82 + (index % 3) * 0.07)
            color = QColor(64 + index * 7, 190 + min(index * 7, 55), 255, 150 + (index % 3) * 30)
            pen = QPen(color, 1.1 if self._state != "speaking" else 1.55)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(math.sin(phase * 0.65) * 18 + index * 9)
            painter.drawEllipse(int(-rx), int(-ry), int(rx * 2), int(ry * 2))
            painter.restore()

        core = QRadialGradient(cx - radius * 0.12, cy - radius * 0.14, radius * 0.9)
        core.setColorAt(0.0, QColor(45, 153, 255, 155))
        core.setColorAt(0.55, QColor(0, 87, 225, 45))
        core.setColorAt(1.0, QColor(0, 20, 70, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(core)
        painter.drawEllipse(int(cx - radius * 0.8), int(cy - radius * 0.8), int(radius * 1.6), int(radius * 1.6))
        painter.end()
