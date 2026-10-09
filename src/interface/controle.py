import streamlit as st


def mostrar_controle(tab):
    # Aba de controle PID
    with tab:
        if not st.session_state.logado:
            st.warning("Faça o login para continuar.")
        elif st.session_state.dados_ident is None:
            st.warning("Carregue e identifique um dataset na aba 'Identificação' para liberar o Controle PID.")
        else:
            m = st.session_state.dados_ident
            st.success(
                f"Aba de Controle PID liberada. Modelo carregado: {m['metodo']} "
                f"(k={m['k']:.4f}, τ={m['tau']:.4f}, θ={m['theta']:.4f})"
            )
