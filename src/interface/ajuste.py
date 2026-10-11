import io
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from scipy.ndimage import median_filter
from scipy.optimize import least_squares

def modelo_fopdt(k, tau, theta, t, du):
    t = np.asarray(t, dtype=float)
    tau = max(float(tau), 1e-6)
    return np.where(
        t >= theta,
        k * du * (1 - np.exp(-(t - theta) / tau)),
        0.0
    )

def calcular_erros(y, y_est):
    erro = np.asarray(y) - np.asarray(y_est)
    rmse = float(np.sqrt(np.mean(erro ** 2)))
    erro_max = float(np.max(np.abs(erro)))
    return rmse, erro_max

def estimar_ruido(y, janela=31):
    y = np.asarray(y, dtype=float)
    if len(y) < 3:
        return 0.0
    janela = min(janela, len(y))
    if janela % 2 == 0:
        janela -= 1
    suavizado = median_filter(y, size=janela, mode="nearest")
    return float(np.sqrt(np.mean((y - suavizado) ** 2)))

def ajustar_automatico(t, y, du, k0, tau0, theta0):

    def residuo(p):
        y_estimado = modelo_fopdt(p[0], p[1], p[2], t, du)
        return y_estimado - y

    resultado = least_squares(
        residuo,
        x0=[max(k0, 1e-6), max(tau0, 1e-3), max(theta0, 0.0)],
        bounds=([1e-9, 1e-3, 0.0], [np.inf, np.inf, max(float(np.max(t)), 1e-3)])
    )
    return resultado.x

# interface
def mostrar_ajuste(tab):
    with tab:
        st.subheader("Comparação e ajuste fino")
        if not st.session_state.get("logado", False):
            st.warning(
                "Faça login na aba 'Início' para acessar o ajuste fino."
            )
            return

        dados = st.session_state.get("dados_ident")

        if not dados:
            st.info(
                "Realize primeiro a identificação do sistema "
                "na aba 'Identificação'."
            )
            return

        campos_necessarios = ["t", "y", "du", "metodo", "k", "tau", "theta" ]

        faltando = [
            campo
            for campo in campos_necessarios
            if campo not in dados
        ]

        if faltando:
            st.error(
                "A identificação ainda não disponibilizou todos "
                "os dados necessários para o ajuste fino.\n\n"
                f"Dados ausentes: {', '.join(faltando)}"
            )
            return

        t = np.asarray(dados["t"], dtype=float)
        y = np.asarray(dados["y"], dtype=float)
        du = float(dados["du"])
        metodo = dados["metodo"]
        k0 = float(dados["k"])
        tau0 = float(dados["tau"])
        theta0 = float(dados["theta"])

        if k0 <= 0 or tau0 <= 0:
            st.error(
                "O ganho e a constante de tempo "
                "identificados devem ser positivos."
            )
            return

        chave = f"ajuste_{metodo}"
        chave_k = f"{chave}_k"
        chave_tau = f"{chave}_tau"
        chave_theta = f"{chave}_theta"
        chave_auto = f"{chave}_resultado_auto"

        if chave_k not in st.session_state:
            st.session_state[chave_k] = k0

        if chave_tau not in st.session_state:
            st.session_state[chave_tau] = tau0

        if chave_theta not in st.session_state:
            st.session_state[chave_theta] = theta0

        def restaurar_parametros():
            st.session_state[chave_k] = k0
            st.session_state[chave_tau] = tau0
            st.session_state[chave_theta] = theta0

        def aplicar_automatico():
            auto = st.session_state.get(chave_auto)

            if auto:
                st.session_state[chave_k] = float(auto["k"])
                st.session_state[chave_tau] = float(auto["tau"])
                st.session_state[chave_theta] = float(auto["theta"])

        y_ident = modelo_fopdt(k0, tau0, theta0, t, du)
        rmse_i, emax_i = calcular_erros(y, y_ident)
        amplitude = float(np.max(y) - np.min(y))
        ruido = estimar_ruido(y)
        rmse_ident_pct = (
            100 * rmse_i / amplitude
            if amplitude > 1e-12
            else np.nan
        )

        st.write(
            f"""
            Comparação da resposta experimental com o modelo
            identificado pelo método **{metodo}**.

            Os parâmetros podem ser ajustados para verificar
            o efeito das alterações na resposta do sistema.
            """
        )

        st.markdown(
            "#### Avaliação da aproximação inicial"
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Método", metodo)
        c2.metric("RMSE", f"{rmse_i:.4f} °C")
        c3.metric("Erro máximo", f"{emax_i:.4f} °C")
        c4.metric("RMSE / amplitude", f"{rmse_ident_pct:.2f}%"        )

        if rmse_ident_pct <= 5:
            st.success(
                "A aproximação inicial pode ser considerada "
                "satisfatória."
            )

        elif rmse_ident_pct <= 10:
            st.warning(
                "A aproximação inicial é razoável, mas pode "
                "ser melhorada com ajuste fino."
            )

        else:
            st.error(
                "A aproximação apresenta diferença significativa "
                "em relação aos dados experimentais."
            )

        st.divider()


        col_graf, col_ajuste = st.columns([2.5, 1])

        with col_ajuste:

            st.markdown("### Ajuste fino")

            st.caption(
                "Altere os parâmetros e observe "
                "o efeito no gráfico."
            )

            k = st.slider(
                "Ganho k",
                min_value=float(
                    max(k0 * 0.8, 1e-6)
                ),
                max_value=float(
                    k0 * 1.2
                ),
                step=float(
                    max(k0 * 0.005, 1e-5)
                ),
                key=chave_k
            )

            tau = st.slider(
                "Constante de tempo τ (s)",
                min_value=float(
                    max(tau0 * 0.7, 1e-3)
                ),
                max_value=float(
                    tau0 * 1.3
                ),
                step=float(
                    max(tau0 * 0.01, 0.01)
                ),
                key=chave_tau
            )

            theta = st.slider(
                "Tempo morto θ (s)",
                min_value=0.0,
                max_value=float(
                    max(2 * theta0, 1.0)
                ),
                step=float(
                    max(
                        float(np.max(t)) / 1000,
                        0.01
                    )
                ),
                key=chave_theta
            )

            st.markdown(
                "#### Reflexo das alterações"
            )

            alteracoes = []

            if not np.isclose(k, k0):

                variacao_k = (
                    100 * (k - k0) / k0
                )

                if variacao_k > 0:
                    alteracoes.append(
                        f"**k ↑ {abs(variacao_k):.1f}%**  \n"
                        "Aumenta o valor final da resposta."
                    )
                else:
                    alteracoes.append(
                        f"**k ↓ {abs(variacao_k):.1f}%**  \n"
                        "Reduz o valor final da resposta."
                    )

            if not np.isclose(tau, tau0):

                variacao_tau = (
                    100 * (tau - tau0) / tau0
                )

                if variacao_tau > 0:
                    alteracoes.append(
                        f"**τ ↑ {abs(variacao_tau):.1f}%**  \n"
                        "A resposta fica mais lenta."
                    )
                else:
                    alteracoes.append(
                        f"**τ ↓ {abs(variacao_tau):.1f}%**  \n"
                        "A resposta fica mais rápida."
                    )

            if not np.isclose(theta, theta0):

                if theta > theta0:
                    alteracoes.append(
                        "**θ aumentou**  \n"
                        "A resposta começa mais tarde."
                    )
                else:
                    alteracoes.append(
                        "**θ diminuiu**  \n"
                        "A resposta começa mais cedo."
                    )

            if alteracoes:
                for alteracao in alteracoes:
                    st.info(alteracao)

            else:
                st.caption(
                    "Os parâmetros ainda possuem os valores "
                    "originalmente identificados."
                )

            st.button(
                "Restaurar valores identificados",
                key=f"{chave}_restaurar",
                on_click=restaurar_parametros,
                use_container_width=True
            )

            st.markdown(
                "#### Ajuste automático"
            )

            if st.button(
                "Calcular ajuste automático",
                key=f"{chave}_automatico",
                use_container_width=True
            ):

                ka, taua, thetaa = ajustar_automatico(t, y, du, k0, tau0, theta0)
                st.session_state[chave_auto] = {
                    "k": float(ka),
                    "tau": float(taua),
                    "theta": float(thetaa)
                }
            auto = st.session_state.get(chave_auto)
            if auto:
                y_auto = modelo_fopdt(
                    auto["k"],
                    auto["tau"],
                    auto["theta"],
                    t,
                    du
                )

                rmse_auto, emax_auto = calcular_erros(y, y_auto)
                st.caption("Parâmetros encontrados:")
                st.write(f"**k:** {auto['k']:.5f}")
                st.write(f"**τ:** {auto['tau']:.3f} s")
                st.write(f"**θ:** {auto['theta']:.3f} s")
                st.metric("RMSE automático",f"{rmse_auto:.4f} °C")
                st.button(
                    "Aplicar ajuste automático",
                    key=f"{chave}_aplicar_auto",
                    on_click=aplicar_automatico,
                    use_container_width=True
                )

        k = float(st.session_state[chave_k])
        tau = float(st.session_state[chave_tau])
        theta = float(st.session_state[chave_theta])

        #modelo ajustado
        y_ajust = modelo_fopdt(k, tau, theta, t, du)
        rmse_a, emax_a = calcular_erros(y, y_ajust)

        reducao = (
            100
            * (rmse_i - rmse_a)
            / rmse_i
            if rmse_i > 1e-12
            else 0.0
        )

        rmse_pct = (
            100 * rmse_a / amplitude
            if amplitude > 1e-12
            else np.nan
        )

        with col_graf:

            st.markdown(
                "### Comparação das respostas"
            )

            fig, ax = plt.subplots(
                figsize=(10, 5)
            )

            ax.plot(
                t,
                y,
                label="Resposta original",
                color="tab:blue",
                alpha=0.7
            )

            ax.plot(
                t,
                y_ident,
                label="Resposta estimada",
                color="tab:orange",
                linestyle="--"
            )

            ax.plot(
                t,
                y_ajust,
                label="Resposta após ajuste fino",
                color="tab:green",
                linewidth=2
            )

            ax.set_xlabel(
                "Tempo (s)"
            )

            ax.set_ylabel(
                "Variação da temperatura ΔT (°C)"
            )

            ax.set_title(
                f"Resposta original x estimada — {metodo}"
            )

            ax.grid(
                True,
                linestyle="--",
                alpha=0.4
            )

            ax.legend()

            fig.tight_layout()

            st.pyplot(
                fig,
                use_container_width=True
            )

            g1, g2, g3 = st.columns(3)

            g1.metric("RMSE identificado", f"{rmse_i:.4f} °C")
            g2.metric("RMSE ajustado", f"{rmse_a:.4f} °C")
            g3.metric("Redução do RMSE", f"{reducao:.2f}%")

            buffer = io.BytesIO()

            fig.savefig(
                buffer,
                format="png",
                dpi=300,
                bbox_inches="tight"
            )

            buffer.seek(0)

            st.download_button(
                "Baixar gráfico comparativo",
                data=buffer.getvalue(),
                file_name=(
                    f"comparacao_{metodo.lower()}.png"
                ),
                mime="image/png",
                key=f"{chave}_download"
            )

            plt.close(fig)


            st.markdown(
                "### Erro"
            )

            fig_erro, ax_erro = plt.subplots(
                figsize=(10, 4)
            )

            ax_erro.plot(
                t,
                y - y_ident,
                label="Modelo identificado"
            )

            ax_erro.plot(
                t,
                y - y_ajust,
                label="Modelo ajustado"
            )

            ax_erro.axhline(
                0,
                linestyle="--",
                color="black"
            )

            ax_erro.set_xlabel(
                "Tempo (s)"
            )

            ax_erro.set_ylabel(
                "Erro (°C)"
            )

            ax_erro.set_title(
                "Erro de estimação ao longo do tempo"
            )

            ax_erro.grid(
                True,
                alpha=0.4
            )

            ax_erro.legend()
            fig_erro.tight_layout()
            st.pyplot(
                fig_erro,
                use_container_width=True
            )

            buffer_erro = io.BytesIO()

            fig_erro.savefig(
                buffer_erro,
                format="png",
                dpi=300,
                bbox_inches="tight"
            )

            buffer_erro.seek(0)

            st.download_button(
                "Baixar gráfico dos erros",
                data=buffer_erro.getvalue(),
                file_name="erros_modelo.png",
                mime="image/png",
                key=f"{chave}_download_erro"
            )

            plt.close(fig_erro)

        st.divider()
        st.markdown(
            "### Comparação antes e depois"
        )

        tabela = pd.DataFrame([
            {
                "Modelo": "Identificado",
                "k": k0,
                "τ (s)": tau0,
                "θ (s)": theta0,
                "RMSE (°C)": rmse_i,
                "Erro máximo (°C)": emax_i
            },

            {
                "Modelo": "Ajustado",
                "k": k,
                "τ (s)": tau,
                "θ (s)": theta,
                "RMSE (°C)": rmse_a,
                "Erro máximo (°C)": emax_a
            }
        ])

        st.dataframe(
            tabela.round(4),
            hide_index=True,
            use_container_width=True
        )

        st.markdown(
            "### Resultado do ajuste"
        )

        r1, r2 = st.columns(2)

        r1.metric("RMSE ajustado / amplitude", f"{rmse_pct:.2f}%")
        r2.metric("Ruído estimado", f"{ruido:.4f} °C")

        if reducao > 0.01:

            st.success(
                f"O ajuste fino melhorou a aproximação. "
                f"O RMSE foi reduzido em "
                f"**{reducao:.2f}%**."
            )

        elif reducao < -0.01:

            st.warning(
                f"O ajuste realizado não melhorou o modelo. "
                f"O RMSE aumentou "
                f"**{abs(reducao):.2f}%**."
            )

        else:

            st.info(
                "O ajuste praticamente não modificou o erro. "
                "Os parâmetros originalmente identificados "
                "já produzem uma resposta semelhante."
            )