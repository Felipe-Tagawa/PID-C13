import streamlit as st
import streamlit.components.v1 as components

from src.interface.login import render_login
from src.interface.identificador import render_identificador
from src.interface.controle import render_controle

st.set_page_config(page_title="Identificação & Controle PID", layout="wide")

# Inicialização de estado da sessão
if "logado" not in st.session_state:
    st.session_state.logado = False
if "dados_ident" not in st.session_state:
    st.session_state.dados_ident = None
if "aba_alvo" not in st.session_state:
    st.session_state.aba_alvo = None

# Abas da aplicação
tab_login, tab_ident, tab_pid = st.tabs(["Início", "Identificação", "Controle PID"])

# Transição de aba automática se requisitada
if st.session_state.aba_alvo is not None:
    alvo = st.session_state.aba_alvo
    st.session_state.aba_alvo = None
    components.html(
        f"""<script>
        setTimeout(() => {{
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"], button[role="tab"]');
            if (tabs.length > {alvo}) tabs[{alvo}].click();
        }}, 100);
        </script>""",
        height=0,
        width=0,
    )

# Renderização dos módulos
render_login(tab_login)
render_identificador(tab_ident)
render_controle(tab_pid)

# Permite rodar com python src/main.py
if __name__ == "__main__" and not st.runtime.exists():
    import sys
    from streamlit.web import cli as stcli
    sys.argv = ["streamlit", "run", "src/main.py"]
    sys.exit(stcli.main())