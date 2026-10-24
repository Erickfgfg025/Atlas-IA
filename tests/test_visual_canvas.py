import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from atlas.desktop.visual_canvas import VisualCanvas


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


def test_canvas_starts_hidden_and_accepts_valid_scene(app):
    canvas = VisualCanvas()
    assert not canvas.isVisible()

    canvas.set_scene(
        {
            "title": "Órbita",
            "elements": [
                {
                    "type": "orbit",
                    "x": 120,
                    "y": -5,
                    "size": 99,
                    "color": "#FF8A24",
                    "motion": "spin",
                }
            ],
        }
    )

    element = canvas.stage.elements[0]
    assert element["x"] == 100
    assert element["y"] == 0
    assert element["size"] == 45
    assert element["type"] == "orbit"
    assert element["motion"] == "spin"
    assert canvas.hint.text() == "Órbita"
    assert canvas.isVisible()
    canvas.close()


def test_canvas_discards_unsupported_elements_and_sanitizes_color(app):
    canvas = VisualCanvas()
    canvas.set_scene(
        {
            "elements": [
                {"type": "execute_python", "text": "should not run"},
                {"type": "circle", "color": "not-a-color", "text": "<script>"},
            ]
        }
    )

    assert len(canvas.stage.elements) == 1
    assert canvas.stage.elements[0]["type"] == "circle"
    assert canvas.stage.elements[0]["color"] == "#ff8a24"
    assert canvas.stage.elements[0]["text"] == "<script>"
    canvas.close()


def test_canvas_rejects_empty_or_invalid_scene(app):
    canvas = VisualCanvas()

    with pytest.raises(ValueError, match="Lista de elementos inválida"):
        canvas.set_scene({"elements": "not-a-list"})

    with pytest.raises(ValueError, match="elementos visuais válidos"):
        canvas.set_scene({"elements": [{"type": "execute_python"}]})

    canvas.close()
