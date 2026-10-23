"""Safe local canvas for declarative motion scenes."""
from __future__ import annotations
import math
from typing import Any
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

class VisualCanvas(QFrame):
    ALLOWED = {"circle", "ring", "line", "rect", "text", "orbit", "dot"}
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VisualCanvas")
        self.setMinimumHeight(260)
        self.setStyleSheet("QFrame#VisualCanvas{background:#0B0D11;border:1px solid #34302C;border-radius:16px}")
        layout=QVBoxLayout(self); layout.setContentsMargins(14,12,14,12)
        title=QLabel("CANVAS GENERATIVO · TEMPO REAL")
        title.setStyleSheet("color:#FF8A24;font-size:9px;font-weight:700;letter-spacing:2px;border:0")
        layout.addWidget(title)
        self.hint=QLabel("Descreva uma cena para a IA construir a composição.")
        self.hint.setStyleSheet("color:#858B98;font-size:11px;border:0")
        layout.addWidget(self.hint)
        self.stage=_SceneStage(self); layout.addWidget(self.stage,1)
        self.hide()
    @staticmethod
    def _color(value):
        c=QColor(str(value))
        return c.name() if c.isValid() else "#FF8A24"
    def set_scene(self, scene: dict[str, Any]):
        items=scene.get("elements",[])
        if not isinstance(items,list): raise ValueError("Lista de elementos inválida.")
        clean=[]
        for item in items[:32]:
            if not isinstance(item,dict) or item.get("type") not in self.ALLOWED: continue
            try:
                clean.append({"type":item["type"],"x":max(0,min(100,float(item.get("x",50)))),
                    "y":max(0,min(100,float(item.get("y",50)))),
                    "size":max(2,min(45,float(item.get("size",12)))),
                    "color":self._color(item.get("color","#FF8A24")),
                    "text":str(item.get("text",""))[:100],
                    "motion":item.get("motion") if item.get("motion") in {"float","pulse","spin","none"} else "float"})
            except (TypeError,ValueError): continue
        if not clean: raise ValueError("A IA não produziu elementos visuais válidos.")
        self.stage.elements=clean; self.stage.phase=0; self.stage.update()
        self.hint.setText(str(scene.get("title","Cena criada pela IA"))[:120]); self.show()

class _SceneStage(QWidget):
    def __init__(self,parent):
        super().__init__(parent); self.elements=[]; self.phase=0.0
        self.setMinimumHeight(205)
        self.timer=QTimer(self); self.timer.setInterval(33); self.timer.timeout.connect(self.tick); self.timer.start()
    def tick(self):
        self.phase=(self.phase+0.025)%math.tau; self.update()
    def paintEvent(self,event):
        del event
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.fillRect(self.rect(),QColor("#0B0D11"))
        w,h=self.width(),self.height()
        p.setPen(QPen(QColor(255,255,255,12),1))
        for x in range(0,w,28): p.drawLine(x,0,x,h)
        for y in range(0,h,28): p.drawLine(0,y,w,y)
        for i,e in enumerate(self.elements):
            x=w*e["x"]/100; y=h*e["y"]/100; size=min(w,h)*e["size"]/100
            if e["motion"]=="float": y+=math.sin(self.phase+i*.7)*min(12,size*.22)
            elif e["motion"]=="pulse": size*=.88+.12*math.sin(self.phase*2+i)
            elif e["motion"]=="spin": x+=math.cos(self.phase+i)*min(10,size*.25)
            c=QColor(e["color"]); p.setPen(QPen(c,1.5)); p.setBrush(Qt.BrushStyle.NoBrush); kind=e["type"]
            if kind in {"circle","dot"}:
                if kind=="dot": p.setBrush(c); p.drawEllipse(int(x-size*.12),int(y-size*.12),int(size*.24),int(size*.24))
                else: p.drawEllipse(int(x-size),int(y-size),int(size*2),int(size*2))
            elif kind=="ring":
                p.drawEllipse(int(x-size),int(y-size),int(size*2),int(size*2)); p.drawEllipse(int(x-size*.68),int(y-size*.68),int(size*1.36),int(size*1.36))
            elif kind=="orbit":
                p.save(); p.translate(x,y); p.rotate(math.degrees(self.phase)); p.drawEllipse(int(-size*1.4),int(-size*.48),int(size*2.8),int(size*.96)); p.setBrush(c); p.drawEllipse(int(size*1.15),int(-size*.08),int(size*.16),int(size*.16)); p.restore()
            elif kind=="line": p.drawLine(int(x-size*1.5),int(y),int(x+size*1.5),int(y))
            elif kind=="rect": p.drawRoundedRect(int(x-size),int(y-size*.55),int(size*2),int(size*1.1),8,8)
            elif kind=="text" and e["text"]:
                p.setFont(QFont("Segoe UI",max(9,int(size*.42)),QFont.Weight.DemiBold))
                p.drawText(int(x-size*2),int(y-size*.4),int(size*4),int(size*.8),Qt.AlignmentFlag.AlignCenter,e["text"])
        p.end()
