import os

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from scipy.io import loadmat


class TabID(QWidget):
    dados_identificados = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tempo = None
        self.saida = None

        # Lado esquerdo: controles
        self.btn_arquivo = QPushButton("Importar arquivo (.mat)")
        self.btn_arquivo.clicked.connect(self._escolher_arquivo)
        self.lbl_status = QLabel("Nenhum arquivo selecionado")

        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems(["Smith", "Sundaresan"])
        self.combo_metodo.currentIndexChanged.connect(self._processar_dados)

        # Campos só de leitura para mostrar os parâmetros
        self.campos = {}
        form = QFormLayout()
        for chave, rotulo in [
            ("ks", "Ganho (ks):"),
            ("taus", "Tempo (τs):"),
            ("thetas", "Atraso (θs):"),
            ("es", "Erro (Es):"),
        ]:
            campo = QLineEdit("-")
            campo.setReadOnly(True)
            campo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.campos[chave] = campo
            form.addRow(rotulo, campo)

        grp_params = QGroupBox("Parâmetros FOPDT")
        grp_params.setLayout(form)

        lateral = QVBoxLayout()
        lateral.addWidget(self.btn_arquivo)
        lateral.addWidget(self.lbl_status)
        lateral.addWidget(QLabel("Método de ajuste:"))
        lateral.addWidget(self.combo_metodo)
        lateral.addWidget(grp_params)
        lateral.addStretch()

        # Lado direito: gráfico
        self.grafico = pg.PlotWidget()
        self.grafico.showGrid(x=True, y=True, alpha=0.25)
        self.grafico.setLabel("left", "Saída da planta")
        self.grafico.setLabel("bottom", "Tempo (s)")
        self.grafico.addLegend()

        layout = QHBoxLayout(self)
        layout.addLayout(lateral, 1)
        layout.addWidget(self.grafico, 3)

    def _escolher_arquivo(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Selecionar arquivo", "", "Arquivos MATLAB (*.mat)"
        )
        if not caminho:
            return

        try:
            # squeeze_me já tira as dimensões extras dos vetores
            mat = loadmat(caminho, squeeze_me=True)
            dados = {k: v for k, v in mat.items() if not k.startswith("__")}
            nomes = list(dados)

            if len(nomes) >= 2:
                # Procura pelos nomes mais comuns, senão pega as duas primeiras variáveis
                t = next((n for n in nomes if n.lower() in ("t", "time", "tempo")), nomes[0])
                y = next((n for n in nomes if n.lower() in ("y", "saida", "out")), nomes[1])
                self.tempo, self.saida = dados[t], dados[y]
            else:
                # Uma matriz só: coluna 0 = tempo, coluna 1 = saída
                matriz = dados[nomes[0]]
                self.tempo, self.saida = matriz[:, 0], matriz[:, 1]

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível ler o arquivo:\n{e}")
            return

        self.lbl_status.setText(f"Carregado: {os.path.basename(caminho)}")
        self._processar_dados()

    def _processar_dados(self):
        if self.tempo is None:
            return

        y0 = self.saida[0]
        delta = np.mean(self.saida[-10:]) - y0
        ks = delta  # considerando degrau unitário

        subindo = delta >= 0
        if self.combo_metodo.currentText() == "Smith":
            t1 = self._tempo_em(y0 + 0.283 * delta, subindo)
            t2 = self._tempo_em(y0 + 0.632 * delta, subindo)
            taus = 1.5 * (t2 - t1)
            thetas = t2 - taus
        else:
            t1 = self._tempo_em(y0 + 0.353 * delta, subindo)
            t2 = self._tempo_em(y0 + 0.853 * delta, subindo)
            taus = (2 / 3) * (t2 - t1)
            thetas = 1.3 * t1 - 0.29 * t2

        thetas = max(thetas, 0.0)
        taus = max(taus, 1e-9)

        # Modelo: y = y0 + ks * (1 - exp(-(t - theta) / tau)) para t >= theta
        y_mod = y0 + ks * (1 - np.exp(-(self.tempo - thetas) / taus)) * (self.tempo >= thetas)
        es = float(np.mean((self.saida - y_mod) ** 2))

        self.grafico.clear()
        if getattr(self.grafico.plotItem, "legend", None) is not None:
            self.grafico.plotItem.legend.clear()
        self.grafico.plot(self.tempo, self.saida, pen=pg.mkPen("c", width=2), name="Medido")
        self.grafico.plot(
            self.tempo, y_mod, pen=pg.mkPen("y", width=2, style=Qt.PenStyle.DashLine), name="FOPDT"
        )

        self.campos["ks"].setText(f"{ks:.3f}")
        self.campos["taus"].setText(f"{taus:.2f}")
        self.campos["thetas"].setText(f"{thetas:.2f}")
        self.campos["es"].setText(f"{es:.4e}")

        self.dados_identificados.emit(
            {"ks": ks, "taus": taus, "thetas": thetas, "es": es}
        )

    def reset(self):
        self.tempo = None
        self.saida = None
        self.lbl_status.setText("Nenhum arquivo selecionado")
        self.combo_metodo.blockSignals(True)
        self.combo_metodo.setCurrentIndex(0)
        self.combo_metodo.blockSignals(False)
        for campo in self.campos.values():
            campo.setText("-")
        self.grafico.clear()
        if getattr(self.grafico.plotItem, "legend", None) is not None:
            self.grafico.plotItem.legend.clear()

    def _tempo_em(self, y_alvo, subindo=True):
        # Primeiro instante em que a saída atinge o valor alvo
        if subindo:
            idx = np.where(self.saida >= y_alvo)[0]
        else:
            idx = np.where(self.saida <= y_alvo)[0]
        return float(self.tempo[idx[0]]) if len(idx) else float(self.tempo[-1])