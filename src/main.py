import streamlit as st

from src.interface.login import mostrar_login
from src.interface.identificador import mostrar_identificacao
from src.interface.dados import mostrar_dados
from src.interface.controle import mostrar_controle

st.set_page_config(page_title="Identificação & Controle PID", layout="wide")

# estado da sessão
if "logado" not in st.session_state:
    st.session_state.logado = False
if "dados_ident" not in st.session_state:
    st.session_state.dados_ident = None
if "aba_alvo" not in st.session_state:
    st.session_state.aba_alvo = None

# Abas da aplicação
tab_login, tab_ident, tab_dados, tab_pid = st.tabs(["Início", "Identificação", "Dados", "Controle PID"])

mostrar_login(tab_login)
mostrar_identificacao(tab_ident)
mostrar_dados(tab_dados)
mostrar_controle(tab_pid)

# Permite rodar com python src/main.py
if __name__ == "__main__" and not st.runtime.exists():
    import sys
    from streamlit.web import cli as stcli
    sys.argv = ["streamlit", "run", "src/main.py"]
    sys.exit(stcli.main())

# Para rodar: python -m src.main -- warnings vão aparecer, mas não atrapalham a execução
# Temos que baixar as dependências também: pip install -r requirements.txt
# login: admin / admin