from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal

class TabLogin(QWidget):
    # Sinal emitido quando o login é aprovado (envia o nome do usuário)
    login_sucesso = Signal(str)
    # Sinal emitido quando o usuário desloga
    logout_realizado = Signal() 

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Card de Login centralizado
        card_login = QGroupBox("Acesso ao Sistema")
        card_login.setFixedWidth(350)
        card_layout = QVBoxLayout(card_login)
        card_layout.setSpacing(12)

        # Usuário
        card_layout.addWidget(QLabel("Usuário:"))
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Digite seu usuário")
        card_layout.addWidget(self.input_user)

        # Senha
        card_layout.addWidget(QLabel("Senha:"))
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_pass.setPlaceholderText("Digite sua senha")
        card_layout.addWidget(self.input_pass)

        # Botão Entrar
        self.btn_entrar = QPushButton("Entrar")
        self.btn_entrar.clicked.connect(self.execute_login)
        self.input_pass.returnPressed.connect(self.execute_login)
        card_layout.addWidget(self.btn_entrar)

        # Mensagem de status
        self.status_login = QLabel("")
        self.status_login.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_login)

        # Botão Logout
        self.btn_logout = QPushButton("Sair da Conta")
        self.btn_logout.hide()
        self.btn_logout.clicked.connect(self.execute_logout)
        card_layout.addWidget(self.btn_logout)

        main_layout.addWidget(card_login)

    def execute_login(self):
        user = self.input_user.text().strip()
        password = self.input_pass.text().strip()

        if user == "admin" and password == "admin":
            self.input_user.setEnabled(False)
            self.input_pass.setEnabled(False)
            self.btn_entrar.hide()
            self.btn_logout.show()
            self.status_login.setText(f"Bem-vindo, {user}!")

            self.login_sucesso.emit(user)
        else:
            QMessageBox.warning(self, "Erro de Login", "Usuário ou senha incorretos.")
            self.input_pass.clear()
            self.input_pass.setFocus()


    def execute_logout(self):
        self.input_user.setEnabled(True)
        self.input_pass.setEnabled(True)
        self.input_user.clear()
        self.input_pass.clear()
        self.status_login.setText("Você saiu da conta.")
        self.btn_logout.hide()
        self.btn_entrar.show()
        self.input_user.setFocus()
        
        self.logout_realizado.emit()
    