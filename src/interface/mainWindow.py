from PySide6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QLineEdit, QGroupBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt

from src.interface.id import TabID
from src.interface.login import TabLogin
from src.interface.control import TabControl

class Window(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controlador PID")
        self.resize(900, 600)

        self.tab_login = TabLogin()
        self.tab_identificacao = TabID()
        self.tab_controle = TabControl()

        self.addTab(self.tab_login, "Início")
        self.addTab(self.tab_identificacao, "Identificação")
        self.addTab(self.tab_controle, "Controle PID")

        self.tab_login.login_sucesso.connect(self.in_login)
        self.tab_login.logout_realizado.connect(self.in_logout)
        self.tab_identificacao.dados_identificados.connect(self.in_dados_identificados)

        self.setTabEnabled(1, False)
        self.setTabEnabled(2, False)

    def in_login(self, user: str):
        self.setTabEnabled(1, True)
        self.setCurrentIndex(1)  # Muda para a aba de Identificação
        self.tab_login.btn_logout.show()
        self.tab_login.btn_entrar.hide()
        self.tab_login.status_login.setText(f"Bem-vindo, {user}!")

    def in_logout(self):
        self.setTabEnabled(1, False)
        self.setTabEnabled(2, False)
        self.setCurrentIndex(0)  # Muda para a aba de Login
        self.tab_login.btn_logout.hide()
        self.tab_login.btn_entrar.show()
        self.tab_login.status_login.setText("Você saiu da conta.")
        self.tab_identificacao.reset()
        self.tab_controle.reset()

    def in_dados_identificados(self, dados: dict):
        self.tab_controle.receber_modelo(dados)
        self.setTabEnabled(2, True)
    