import streamlit as st


def render_login(tab):
    # Aba de login e controle de acesso
    with tab:
        st.subheader("Acesso ao Sistema")

        if not st.session_state.logado:
            user = st.text_input("Usuário", key="login_user")
            pwd = st.text_input("Senha", type="password", key="login_pass")

            if st.button("Entrar"):
                if user == "admin" and pwd == "admin":
                    st.session_state.logado = True
                    st.session_state.aba_alvo = 1
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        else:
            st.success("Bem-vindo, admin!")
            if st.button("Sair da Conta"):
                st.session_state.logado = False
                st.session_state.dados_ident = None
                st.session_state.aba_alvo = 0
                st.rerun()
