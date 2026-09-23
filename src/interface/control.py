import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class TabControl(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.modelo = None  # parâmetros vindos da aba de identificação
        self.t = None
        self.y = None

        # Cabeçalho
        titulo = QLabel("Projeto Prático C213 - Sistemas Embarcados")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold;")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo = QLabel("Identificação de Processos & Sintonia de Controladores PID")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Seleção do modo
        self.rb_metodo = QRadioButton("Método")
        self.rb_manual = QRadioButton("Manual")
        self.rb_metodo.setChecked(True)
        self.rb_metodo.toggled.connect(self._atualizar_modo)

        modo = QHBoxLayout()
        modo.addWidget(QLabel("Seleção de Sintonia:"))
        modo.addWidget(self.rb_metodo)
        modo.addWidget(self.rb_manual)
        modo.addStretch()

        # Gráfico
        self.grafico = pg.PlotWidget(title="Resposta do Controle PID")
        self.grafico.setBackground("w")
        self.grafico.showGrid(x=True, y=True, alpha=0.3)

        esquerda = QVBoxLayout()
        esquerda.addLayout(modo)
        esquerda.addWidget(self.grafico)

        # Painel direito
        self.combo = QComboBox()
        self.combo.addItems(["Ziegler-Nichols", "Cohen-Coon", "IMC (Lambda)"])
        self.combo.currentIndexChanged.connect(self._atualizar_modo)

        self.campos = {c: QLineEdit("0.0") for c in ("kp", "ti", "td", "lam", "sp", "tr", "ts", "mp")}
        self.campos["sp"].setText("20")
        for c in ("tr", "ts", "mp"):
            self.campos[c].setReadOnly(True)

        grade = QGridLayout()
        linhas = [("kp", "Kp:"), ("ti", "Ti:"), ("td", "Td:"), ("lam", "λ:")]
        for i, (chave, rotulo) in enumerate(linhas):
            lixeira = QToolButton()
            lixeira.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
            lixeira.clicked.connect(lambda _, c=chave: self.campos[c].setText("0.0"))
            grade.addWidget(QLabel(rotulo), i, 0)
            grade.addWidget(self.campos[chave], i, 1)
            grade.addWidget(lixeira, i, 2)

        self.btn_sintonizar = QPushButton("Sintonizar")
        self.btn_sintonizar.setEnabled(False)
        self.btn_sintonizar.clicked.connect(self._sintonizar)
        self.btn_exportar = QPushButton("Exportar")
        self.btn_exportar.setEnabled(False)
        self.btn_exportar.clicked.connect(self._exportar)

        botoes = QHBoxLayout()
        botoes.addWidget(self.btn_sintonizar)
        botoes.addWidget(self.btn_exportar)

        # Parâmetros de controle: a bolinha tem a mesma cor do marcador no gráfico
        controle = QGridLayout()
        self.cores = {"tr": "#1E88E5", "ts": "#43A047", "mp": "#E53935"}
        for i, (chave, rotulo) in enumerate([("sp", "SP:"), ("tr", "tr:"), ("ts", "ts:"), ("mp", "mp (%):")]):
            controle.addWidget(QLabel(rotulo), i, 0)
            controle.addWidget(self.campos[chave], i, 1)
            if chave in self.cores:
                bolinha = QLabel()
                bolinha.setFixedSize(12, 12)
                bolinha.setStyleSheet(f"background: {self.cores[chave]}; border-radius: 6px;")
                controle.addWidget(bolinha, i, 2)

        direita = QVBoxLayout()
        direita.addWidget(self.combo)
        direita.addLayout(grade)
        direita.addLayout(botoes)
        direita.addWidget(QLabel("Parâmetros de controle:"))
        direita.addLayout(controle)
        direita.addStretch()

        corpo = QHBoxLayout()
        corpo.addLayout(esquerda, 3)
        corpo.addLayout(direita, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addLayout(corpo)

        self._atualizar_modo()

    # Slot que recebe o modelo da aba de identificação
    def receber_modelo(self, dados: dict):
        self.modelo = dados
        self.btn_sintonizar.setEnabled(True)

    def reset(self):
        self.modelo = None
        self.t = None
        self.y = None
        self.btn_sintonizar.setEnabled(False)
        self.btn_exportar.setEnabled(False)
        self.rb_metodo.setChecked(True)
        self.combo.setCurrentIndex(0)
        for c in ("kp", "ti", "td", "lam", "tr", "ts", "mp"):
            self.campos[c].setText("0.0")
        self.campos["sp"].setText("20")
        self.grafico.clear()
        self._atualizar_modo()

    def _atualizar_modo(self):
        manual = self.rb_manual.isChecked()
        self.combo.setEnabled(not manual)
        for c in ("kp", "ti", "td"):
            self.campos[c].setReadOnly(not manual)
        # Lambda só faz sentido no IMC
        self.campos["lam"].setEnabled(not manual and self.combo.currentText().startswith("IMC"))

    def _calcular_ganhos(self):
        k = self.modelo["ks"]
        tau = self.modelo["taus"]
        th = max(self.modelo["thetas"], 1e-3)  # evita divisão por zero
        metodo = self.combo.currentText()

        if metodo.startswith("Ziegler"):
            kp = 1.2 * tau / (k * th)
            ti = 2 * th
            td = 0.5 * th
        elif metodo.startswith("Cohen"):
            r = th / tau
            kp = (1 / (k * r)) * (4 / 3 + r / 4)
            ti = th * (32 + 6 * r) / (13 + 8 * r)
            td = 4 * th / (11 + 2 * r)
        else:
            lam = float(self.campos["lam"].text())
            kp = (tau + th / 2) / (k * (lam + th / 2))
            ti = tau + th / 2
            td = tau * th / (2 * tau + th)

        for c, v in zip(("kp", "ti", "td"), (kp, ti, td)):
            self.campos[c].setText(f"{v:.4f}")

    def _simular(self, kp, ti, td, sp):
        k, tau, th = self.modelo["ks"], self.modelo["taus"], self.modelo["thetas"]
        dt = tau / 200
        n = int(15 * (tau + th) / dt)
        atraso = int(round(th / dt))

        t = np.arange(n) * dt
        y = np.zeros(n)
        u = np.zeros(n)
        integral, e_ant = 0.0, sp

        for i in range(1, n):
            e = sp - y[i - 1]
            integral += e * dt
            termo_i = integral / ti if ti > 0 else 0.0
            u[i] = kp * (e + termo_i + td * (e - e_ant) / dt)
            e_ant = e
            # Planta de primeira ordem com atraso de transporte (Euler)
            y[i] = y[i - 1] + dt * (-y[i - 1] + k * u[max(i - atraso, 0)]) / tau
        return t, y

    def _sintonizar(self):
        try:
            if self.rb_metodo.isChecked():
                self._calcular_ganhos()
            kp, ti, td, sp = (float(self.campos[c].text()) for c in ("kp", "ti", "td", "sp"))
        except (ValueError, ZeroDivisionError):
            QMessageBox.warning(self, "Atenção", "Confira os valores digitados.")
            return

        self.t, self.y = self._simular(kp, ti, td, sp)
        self._mostrar_resultado(sp)
        self.btn_exportar.setEnabled(True)

    def _mostrar_resultado(self, sp):
        t, y = self.t, self.y

        def instante(nivel):
            idx = np.where(y >= nivel * sp)[0]
            return t[idx[0]] if len(idx) else np.nan

        tr = instante(0.9) - instante(0.1)
        fora = np.where(np.abs(y - sp) > 0.02 * abs(sp))[0]  # critério de 2%
        ts = t[min(fora[-1] + 1, len(t) - 1)] if len(fora) else 0.0
        i_pico = int(np.argmax(y))
        mp = max(0.0, (y[i_pico] - sp) / sp * 100)

        self.grafico.clear()
        self.grafico.plot(t, y, pen=pg.mkPen("#1A237E", width=2))
        self.grafico.addItem(pg.InfiniteLine(sp, angle=0, pen=pg.mkPen("gray", style=Qt.PenStyle.DashLine)))
        self.grafico.plot([instante(0.9)], [0.9 * sp], symbol="o", symbolBrush=self.cores["tr"], pen=None)
        self.grafico.plot([ts], [y[np.searchsorted(t, ts).clip(0, len(t) - 1)]], symbol="o", symbolBrush=self.cores["ts"], pen=None)
        self.grafico.plot([t[i_pico]], [y[i_pico]], symbol="o", symbolBrush=self.cores["mp"], pen=None)

        self.campos["tr"].setText(f"{tr:.2f}")
        self.campos["ts"].setText(f"{ts:.2f}")
        self.campos["mp"].setText(f"{mp:.2f}")

    def _exportar(self):
        caminho, _ = QFileDialog.getSaveFileName(self, "Exportar resposta", "resposta_pid.csv", "CSV (*.csv)")
        if caminho:
            np.savetxt(caminho, np.column_stack((self.t, self.y)), delimiter=",", header="tempo,saida", comments="")