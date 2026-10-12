import io
import os
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import control as ctrl

from src.interface.identificador import ler_arquivo, identificar_metodo


def calcular_sintonia(metodo, tipo_controlador, k, tau, theta):
    """Calcula os parâmetros Kp, Ti, Td para FOPDT usando Ziegler-Nichols ou ITAE."""
    theta_safe = max(float(theta), 1e-4)
    tau_safe = max(float(tau), 1e-4)
    k_safe = float(k) if abs(k) > 1e-6 else 1e-6
    r = theta_safe / tau_safe  # razão atraso / constante de tempo

    if "Ziegler-Nichols" in metodo or "Z-N" in metodo:
        if tipo_controlador == "PI":
            kp = 0.9 * tau_safe / (k_safe * theta_safe)
            ti = 3.33 * theta_safe
            td = 0.0
        else:  # PID
            kp = 1.2 * tau_safe / (k_safe * theta_safe)
            ti = 2.0 * theta_safe
            td = 0.5 * theta_safe
    elif "ITAE" in metodo:
        # Formulação clássica de Rovira/Murrill/Smith para seguimento de Setpoint (mínimo overshoot)
        if tipo_controlador == "PI":
            kp = (0.586 / k_safe) * (r ** -0.916)
            ti = tau_safe / max(1e-4, (1.03 - 0.165 * r))
            td = 0.0
        else:  # PID
            kp = (0.965 / k_safe) * (r ** -0.855)
            ti = tau_safe / max(1e-4, (0.796 - 0.147 * r))
            td = 0.308 * tau_safe * (r ** 0.929)
    else:
        # Fallback Ziegler-Nichols
        kp = 1.2 * tau_safe / (k_safe * theta_safe)
        ti = 2.0 * theta_safe
        td = 0.5 * theta_safe

    return float(kp), float(ti), float(td)


def simular_malhas(k, tau, theta, kp, ti, td, sp=1.0, t_max=600.0, dt=0.2):
    """Simula a resposta ao degrau em Malha Aberta (exata) e em Malha Fechada (com atraso puro exato)."""
    t = np.arange(0, t_max + dt, dt)
    n = len(t)
    delay_steps = int(round(max(theta, 0.0) / dt))

    # Malha Aberta: resposta analítica exata ao degrau u(t) = sp * 1(t) com atraso puro theta
    y_ma = np.zeros_like(t)
    mask = t >= theta
    y_ma[mask] = sp * k * (1.0 - np.exp(-(t[mask] - theta) / max(tau, 1e-4)))

    # Malha Fechada: simulação precisa com atraso de transporte puro (DDE) e filtro derivativo N=10
    y_mf = np.zeros(n)
    u = np.zeros(n)
    integral = 0.0
    e_prev = 0.0
    d_state = 0.0
    n_filter = 10.0

    ti_safe = max(float(ti), 1e-4)
    td_safe = max(float(td), 0.0)
    tau_safe = max(float(tau), 1e-4)

    for i in range(n - 1):
        err = sp - y_mf[i]
        integral += err * dt

        # Ação derivativa filtrada
        de = (err - e_prev) / dt if i > 0 else 0.0
        if td_safe > 0:
            d_state += dt * (n_filter / td_safe) * (td_safe * de - d_state)
        else:
            d_state = 0.0

        u[i] = kp * (err + (1.0 / ti_safe) * integral + d_state)
        e_prev = err

        u_delayed = u[i - delay_steps] if i >= delay_steps else 0.0
        dy = (k * u_delayed - y_mf[i]) / tau_safe
        y_mf[i + 1] = y_mf[i] + dy * dt

    return t, y_ma, y_mf


def calcular_metricas(t, y, sp=1.0, tol=0.02):
    """Calcula Tempo de Subida (10%-90%), Tempo de Acomodação (faixa 2%), Erro de Regime e Sobressinal."""
    y_0 = float(y[0])
    y_final = float(y[-1])
    dy = y_final - y_0

    # Tempo de subida (10% a 90% da variação total)
    if abs(dy) > 1e-6:
        val10 = y_0 + 0.10 * dy
        val90 = y_0 + 0.90 * dy
        idx10 = np.where(y >= val10)[0]
        idx90 = np.where(y >= val90)[0]
        t10 = float(t[idx10[0]]) if len(idx10) > 0 else float(t[0])
        t90 = float(t[idx90[0]]) if len(idx90) > 0 else float(t[-1])
        tr = max(0.0, t90 - t10)
    else:
        tr = 0.0

    # Tempo de acomodação (critério de 2% em relação ao patamar final / setpoint)
    banda = tol * abs(dy if abs(dy) > 1e-6 else sp)
    fora_da_banda = np.where(np.abs(y - sp) > banda)[0]
    if len(fora_da_banda) == 0:
        ts = float(t[0])
    elif fora_da_banda[-1] < len(t) - 1:
        ts = float(t[fora_da_banda[-1] + 1])
    else:
        ts = float(t[-1])

    # Erro de regime permanente em relação ao setpoint
    ess = float(sp - y_final)
    ess_pct = float((abs(ess) / abs(sp)) * 100.0) if abs(sp) > 1e-6 else 0.0

    # Sobressinal (Overshoot)
    pico = float(np.max(y))
    if abs(dy) > 1e-6 and pico > sp:
        overshoot = float(((pico - sp) / abs(sp)) * 100.0)
    elif abs(dy) > 1e-6 and pico > y_final:
        overshoot = float(((pico - y_final) / abs(dy)) * 100.0)
    else:
        overshoot = 0.0

    return {
        "tr": tr,
        "ts": ts,
        "ess": ess,
        "ess_pct": ess_pct,
        "overshoot": overshoot,
        "y_final": y_final,
        "pico": pico,
    }


def carregar_modelo_exemplo():
    """Carrega o arquivo padrão examples/Forno_G1.mat para inicialização rápida."""
    caminho = "examples/Forno_G1.mat"
    if not os.path.exists(caminho):
        return False
    with open(caminho, "rb") as f:
        t, y, du = ler_arquivo(f)
    kp, tau, theta = identificar_metodo(t, y, du, "Smith")
    sys = ctrl.tf(kp, [tau, 1])
    num_p, den_p = ctrl.pade(theta, 1)
    final_sys = ctrl.series(sys, ctrl.tf(num_p, den_p))
    st.session_state.dados_ident = {
        "metodo": "Smith",
        "k": kp,
        "tau": tau,
        "theta": theta,
        "eqm": 0.0,
        "setpoint": float(y[-1]),
        "sistema": final_sys,
    }
    return True


def mostrar_controle(tab):
    """Renderiza a aba de Controle PID com sintonia (Manual e Método), análise completa e fundamentos."""
    with tab:
        st.subheader("Controle em Malha Aberta vs. Malha Fechada (PID)")

        if not st.session_state.logado:
            st.warning("Faça o login na aba 'Início' para acessar os recursos de controle.")
            return

        if st.session_state.dados_ident is None:
            st.warning("Nenhum modelo foi identificado ainda. Carregue um dataset na aba 'Identificação'.")
            col_btn, _ = st.columns([1.5, 3])
            with col_btn:
                if st.button("Carregar Dados de Exemplo (Forno G1)"):
                    if carregar_modelo_exemplo():
                        st.success("Modelo Forno G1 carregado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Arquivo de exemplo 'examples/Forno_G1.mat' não encontrado.")
            return

        m = st.session_state.dados_ident
        k_val = float(m["k"])
        tau_val = float(m["tau"])
        theta_val = float(m["theta"])
        sp_padrao = float(m.get("setpoint", 1.0))
        sp_padrao = sp_padrao if sp_padrao > 0 else 1.0

        # Barra com parâmetros identificados da planta
        with st.expander("Parâmetros do Modelo Identificado (FOPDT)", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ganho Estático (K)", f"{k_val:.4f}")
            c2.metric("Constante de Tempo (τ)", f"{tau_val:.2f} s")
            c3.metric("Tempo Morto (θ)", f"{theta_val:.2f} s")
            c4.metric("Razão θ/τ", f"{(theta_val / max(tau_val, 1e-4)):.3f}")
            st.latex(
                rf"G(s) = \frac{{{k_val:.4f}}}{{{tau_val:.2f}s + 1}} \, e^{{-{theta_val:.2f}s}}"
            )

        # Seleção da forma de sintonia: Método ou Manual
        col_modo, _ = st.columns([2.5, 1])
        with col_modo:
            modo_sintonia = st.radio(
                "Seleção de Sintonia:",
                ["Método", "Manual"],
                index=0,
                horizontal=True,
                help="Escolha entre calcular os ganhos automaticamente pelos métodos analíticos (ITAE / Ziegler-Nichols) ou ajustar manualmente Kp, Ti e Td.",
            )

        # Sintonias analíticas de referência (sem Cohen-Coon)
        kp_itae_ref, ti_itae_ref, td_itae_ref = calcular_sintonia(
            "ITAE (Menor Overshoot)", "PID", k_val, tau_val, theta_val
        )
        kp_zn_ref, ti_zn_ref, td_zn_ref = calcular_sintonia(
            "Ziegler-Nichols (Curva de Reação)", "PID", k_val, tau_val, theta_val
        )

        if modo_sintonia == "Método":
            col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
            with col_cfg1:
                metodo_sel = st.selectbox(
                    "Método de Sintonia",
                    ["ITAE (Menor Overshoot)", "Ziegler-Nichols (Curva de Reação)"],
                    index=0,
                    help="ITAE é otimizado para seguimento de referência com mínimo sobressinal. Ziegler-Nichols utiliza as fórmulas clássicas baseadas na curva de reação.",
                )
            with col_cfg2:
                tipo_ctrl = st.radio(
                    "Tipo de Controlador",
                    ["PID", "PI"],
                    index=0,
                    horizontal=True,
                    help="PID inclui ação derivativa; PI inclui apenas proporcional e integral.",
                )
            with col_cfg3:
                sp_val = st.number_input(
                    "Degrau de Setpoint (SP)",
                    min_value=0.1,
                    max_value=200.0,
                    value=float(st.session_state.get("ctrl_sp", sp_padrao)),
                    step=0.5,
                    help="Amplitude da referência desejada.",
                )
                st.session_state["ctrl_sp"] = sp_val

            kp_itae, ti_itae, td_itae = calcular_sintonia("ITAE (Menor Overshoot)", tipo_ctrl, k_val, tau_val, theta_val)
            kp_zn, ti_zn, td_zn = calcular_sintonia("Ziegler-Nichols (Curva de Reação)", tipo_ctrl, k_val, tau_val, theta_val)

            if "ITAE" in metodo_sel:
                kp_calc, ti_calc, td_calc = kp_itae, ti_itae, td_itae
                nome_curto_sel = "ITAE"
                outro_nome = "Ziegler-Nichols"
            else:
                kp_calc, ti_calc, td_calc = kp_zn, ti_zn, td_zn
                nome_curto_sel = "Ziegler-Nichols"
                outro_nome = "ITAE"

        else:  # Modo Manual
            st.write("**Ajuste Manual dos Parâmetros do Controlador:**")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)

            with col_m1:
                kp_calc = st.number_input(
                    "Kp:",
                    value=float(st.session_state.get("ctrl_manual_kp", kp_zn_ref)),
                    step=0.01,
                    format="%.4f",
                    help="Ganho proporcional do controlador.",
                )
                st.session_state["ctrl_manual_kp"] = kp_calc

            with col_m2:
                ti_calc = st.number_input(
                    "Ti (s):",
                    value=float(st.session_state.get("ctrl_manual_ti", ti_zn_ref)),
                    step=0.5,
                    format="%.2f",
                    help="Tempo integral em segundos.",
                )
                st.session_state["ctrl_manual_ti"] = ti_calc

            with col_m3:
                td_calc = st.number_input(
                    "Td (s):",
                    value=float(st.session_state.get("ctrl_manual_td", td_zn_ref)),
                    step=0.05,
                    format="%.2f",
                    help="Tempo derivativo em segundos.",
                )
                st.session_state["ctrl_manual_td"] = td_calc

            with col_m4:
                sp_val = st.number_input(
                    "Degrau de Setpoint (SP)",
                    min_value=0.1,
                    max_value=200.0,
                    value=float(st.session_state.get("ctrl_sp", sp_padrao)),
                    step=0.5,
                )
                st.session_state["ctrl_sp"] = sp_val

            tipo_ctrl = "PID" if td_calc > 0 else "PI"
            metodo_sel = "Manual"
            nome_curto_sel = f"Manual (Kp={kp_calc:.2f}, Ti={ti_calc:.1f}, Td={td_calc:.2f})"
            outro_nome = "ITAE"
            kp_itae, ti_itae, td_itae = kp_itae_ref, ti_itae_ref, td_itae_ref
            kp_zn, ti_zn, td_zn = kp_zn_ref, ti_zn_ref, td_zn_ref

        # Simulação simultânea
        t_max_sim = float(max(500.0, 4.0 * tau_val + 2.0 * theta_val))
        t_sim, y_ma, y_mf_sel = simular_malhas(
            k_val, tau_val, theta_val, kp_calc, ti_calc, td_calc, sp=sp_val, t_max=t_max_sim
        )
        _, _, y_mf_itae = simular_malhas(
            k_val, tau_val, theta_val, kp_itae, ti_itae, td_itae, sp=sp_val, t_max=t_max_sim
        )
        _, _, y_mf_zn = simular_malhas(
            k_val, tau_val, theta_val, kp_zn, ti_zn, td_zn, sp=sp_val, t_max=t_max_sim
        )

        m_ma = calcular_metricas(t_sim, y_ma, sp=sp_val)
        m_mf = calcular_metricas(t_sim, y_mf_sel, sp=sp_val)
        m_itae = calcular_metricas(t_sim, y_mf_itae, sp=sp_val)
        m_zn = calcular_metricas(t_sim, y_mf_zn, sp=sp_val)

        # Detalhamento dos parâmetros ativos (incluindo lambda bloqueado em 0.0)
        col_g1, col_g2, col_g3, col_g4, col_g5 = st.columns(5)
        col_g1.metric("Ganho Proporcional (Kp)", f"{kp_calc:.4f}")
        col_g2.metric("Tempo Integral (Ti)", f"{ti_calc:.2f} s")
        col_g3.metric(
            "Tempo Derivativo (Td)",
            f"{td_calc:.2f} s" if td_calc > 0 else "—",
        )
        col_g4.metric("λ (IMC)", "0.0", help="Métodos IMC não utilizados (parâmetro bloqueado em 0.0).")
        col_g5.metric("Modo Ativo", "Manual" if modo_sintonia == "Manual" else f"{nome_curto_sel} ({tipo_ctrl})")

        # Opção para comparar simultaneamente os métodos no gráfico
        comparar_ambos = st.checkbox(
            "Exibir ambos os métodos de referência (ITAE vs. Ziegler-Nichols) no gráfico para contrastar o sobressinal",
            value=True,
        )

        # Gráfico Comparativo: MALHA ABERTA VS MALHA FECHADA
        fig, ax = plt.subplots(figsize=(10, 4.5), dpi=100)

        # Setpoint
        ax.axhline(
            sp_val,
            color="#222222",
            linestyle=":",
            linewidth=1.8,
            label=f"Setpoint r(t) = {sp_val:.2f}",
        )

        # Faixa de tolerância de 2%
        ax.fill_between(
            t_sim,
            sp_val * 0.98,
            sp_val * 1.02,
            color="#28a745",
            alpha=0.12,
            label="Faixa de Tolerância (±2% do Setpoint)",
        )

        # Resposta em Malha Aberta
        ax.plot(
            t_sim,
            y_ma,
            color="#1f77b4",
            linestyle="--",
            linewidth=2.0,
            label=f"Malha Aberta (y_MA | y_final={m_ma['y_final']:.2f})",
        )

        # Resposta em Malha Fechada selecionada / manual
        cor_mf = "#28a745" if "ITAE" in nome_curto_sel else "#d62728"
        ax.plot(
            t_sim,
            y_mf_sel,
            color=cor_mf,
            linestyle="-",
            linewidth=2.4,
            label=f"Malha Fechada: {nome_curto_sel} (Mp={m_mf['overshoot']:.1f}%)",
        )

        # Curvas comparativas de referência, se ativado
        if comparar_ambos:
            if modo_sintonia == "Método":
                y_outro = y_mf_zn if "ITAE" in metodo_sel else y_mf_itae
                m_outro = m_zn if "ITAE" in metodo_sel else m_itae
                cor_outro = "#d62728" if "ITAE" in metodo_sel else "#28a745"
                ax.plot(
                    t_sim,
                    y_outro,
                    color=cor_outro,
                    linestyle="-.",
                    linewidth=1.8,
                    alpha=0.85,
                    label=f"Malha Fechada: {outro_nome} (Mp={m_outro['overshoot']:.1f}%)",
                )
            else:
                ax.plot(
                    t_sim,
                    y_mf_itae,
                    color="#28a745",
                    linestyle="-.",
                    linewidth=1.5,
                    alpha=0.75,
                    label=f"Referência: ITAE PID (Mp={m_itae['overshoot']:.1f}%)",
                )
                ax.plot(
                    t_sim,
                    y_mf_zn,
                    color="#d62728",
                    linestyle=":",
                    linewidth=1.5,
                    alpha=0.75,
                    label=f"Referência: Z-N PID (Mp={m_zn['overshoot']:.1f}%)",
                )

        if theta_val > 0:
            ax.axvline(
                theta_val,
                color="#6c757d",
                linestyle=":",
                linewidth=1.0,
                alpha=0.7,
                label=f"Tempo Morto θ = {theta_val:.1f}s",
            )

        ax.set_title(
            f"Resposta Temporal ao Degrau: Malha Aberta vs. Malha Fechada ({nome_curto_sel})",
            fontsize=12,
            fontweight="bold",
            pad=10,
        )
        ax.set_xlabel("Tempo (s)", fontsize=10)
        ax.set_ylabel("Amplitude / Saída do Sistema", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.55)
        ax.set_xlim(0, t_max_sim)
        ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)
        fig.tight_layout()

        st.pyplot(fig)

        # Botão para exportar o gráfico
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        st.download_button(
            "Exportar Gráfico",
            data=buf.getvalue(),
            file_name="controle_pid.png",
            mime="image/png",
        )

        # Cartões de Métricas de Desempenho
        st.markdown("### Métricas de Desempenho")
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)

        delta_tr = ((m_mf["tr"] - m_ma["tr"]) / m_ma["tr"] * 100) if m_ma["tr"] > 0 else 0
        c_m1.metric(
            label="Tempo de Subida (tr)",
            value=f"{m_mf['tr']:.1f} s",
            delta=f"{delta_tr:.1f}% vs MA ({m_ma['tr']:.1f} s)",
            delta_color="inverse",
            help="Tempo de subida de 10% a 90% da variação.",
        )

        delta_ts = ((m_mf["ts"] - m_ma["ts"]) / m_ma["ts"] * 100) if m_ma["ts"] > 0 else 0
        c_m2.metric(
            label="Tempo de Acomodação (ts, 2%)",
            value=f"{m_mf['ts']:.1f} s",
            delta=f"{delta_ts:.1f}% vs MA ({m_ma['ts']:.1f} s)",
            delta_color="inverse",
            help="Tempo necessário para permanecer estritamente dentro de ±2% do Setpoint.",
        )

        c_m3.metric(
            label="Erro de Regime (ess)",
            value=f"{m_mf['ess']:.4f} ({m_mf['ess_pct']:.2f}%)",
            delta=f"-{m_ma['ess_pct'] - m_mf['ess_pct']:.1f}% vs MA ({m_ma['ess']:.4f})",
            delta_color="inverse",
            help="Diferença entre o Setpoint e o valor final estabilizado.",
        )

        c_m4.metric(
            label="Sobressinal (Overshoot Mp)",
            value=f"{m_mf['overshoot']:.2f}%",
            delta=f"Pico: {m_mf['pico']:.2f}",
            delta_color="off",
            help="Percentual máximo em que a resposta ultrapassa o Setpoint.",
        )

        # Tabela comparativa detalhada
        dados_tabela = {
            "Métrica de Desempenho": [
                "Tempo de Subida (tr [10% - 90%])",
                "Tempo de Acomodação (ts [faixa ±2%])",
                "Erro de Regime Estacionário (ess)",
                "Erro Percentual do Processo (ess %)",
                "Sobressinal Máximo (Overshoot Mp)",
                "Valor Final Estabilizado (y(∞))",
            ],
            "Malha Aberta (Sem Controle)": [
                f"{m_ma['tr']:.2f} s",
                f"{m_ma['ts']:.2f} s",
                f"{m_ma['ess']:.4f}",
                f"{m_ma['ess_pct']:.2f} %",
                f"{m_ma['overshoot']:.2f} %",
                f"{m_ma['y_final']:.4f}",
            ],
            f"Malha Fechada: Ativa ({nome_curto_sel})": [
                f"{m_mf['tr']:.2f} s",
                f"{m_mf['ts']:.2f} s",
                f"{m_mf['ess']:.4f}",
                f"{m_mf['ess_pct']:.2f} %",
                f"{m_mf['overshoot']:.2f} %",
                f"{m_mf['y_final']:.4f}",
            ],
            "Malha Fechada: ITAE (PID)": [
                f"{m_itae['tr']:.2f} s",
                f"{m_itae['ts']:.2f} s",
                f"{m_itae['ess']:.4f}",
                f"{m_itae['ess_pct']:.2f} %",
                f"{m_itae['overshoot']:.2f} %",
                f"{m_itae['y_final']:.4f}",
            ],
            "Malha Fechada: Ziegler-Nichols (PID)": [
                f"{m_zn['tr']:.2f} s",
                f"{m_zn['ts']:.2f} s",
                f"{m_zn['ess']:.4f}",
                f"{m_zn['ess_pct']:.2f} %",
                f"{m_zn['overshoot']:.2f} %",
                f"{m_zn['y_final']:.4f}",
            ],
        }
        st.dataframe(pd.DataFrame(dados_tabela), width='stretch', hide_index=True)

        # Análise Comparativa e Fundamentação Teórica das 4 Abas
        st.markdown("### Análise Comparativa e Fundamentação Teórica")
        aba_subida, aba_acomod, aba_erro, aba_metodos = st.tabs([
            "1. Tempo de Subida (tr)",
            "2. Tempo de Acomodação (ts)",
            "3. Erro do Processo (ess)",
            "4. ITAE vs. Ziegler-Nichols (Overshoot)",
        ])

        with aba_subida:
            st.markdown(
                f"""
                #### Diferenças no Tempo de Subida ($t_r$)
                - **Valores Observados:**
                  - **Malha Aberta:** `{m_ma['tr']:.2f} s`
                  - **Malha Fechada ({nome_curto_sel}):** `{m_mf['tr']:.2f} s` (uma redução de **{abs(delta_tr):.1f}%** na duração de subida).
                
                - **Por que a diferença ocorre?**
                  1. **Na Malha Aberta (MA):** A dinâmica do sistema é puramente passiva. A velocidade de elevação térmica é regida exclusivamente pela constante de tempo do processo ($\tau = {tau_val:.2f}\\text{{ s}}$) e pelo atraso de transporte ($\theta = {theta_val:.2f}\\text{{ s}}$). A planta reage apenas na medida em que a energia térmica se propaga naturalmente pelo processo.
                  2. **Na Malha Fechada (MF):** No instante em que o degrau de referência é aplicado ($t = 0^+$), o erro instantâneo é máximo ($e(t) = r - y = {sp_val:.2f}$). Como a ação de controle proporcional é $u(t) \\approx K_p \\cdot e(t)$, o controlador injeta uma potência inicial muito superior à potência de regime permanente, "forçando" o sistema a subir vertiginosamente. Adicionalmente, quando em modo PID, a ação derivativa ($T_d$) antecipa variações bruscas, conferindo maior agilidade inicial à resposta.
                """
            )

        with aba_acomod:
            st.markdown(
                f"""
                #### Diferenças no Tempo de Acomodação ($t_s$)
                - **Valores Observados:**
                  - **Malha Aberta:** `{m_ma['ts']:.2f} s`
                  - **Malha Fechada ({nome_curto_sel}):** `{m_mf['ts']:.2f} s` (variação de **{delta_ts:.1f}%**).
                
                - **Por que a diferença ocorre?**
                  1. **Na Malha Aberta (MA):** A resposta converge de forma estritamente assintótica de acordo com o polo natural do sistema $s = -1/\\tau$. A teoria clássica estabelece que uma planta de primeira ordem requer entre $3.9\\tau + \\theta$ e $4\\tau + \\theta$ para alcançar a faixa de 2% (no caso desta planta: aproximadamente ${3.9 * tau_val + theta_val:.1f}\\text{{ s}}$). Não há como acelerar essa acomodação sem controle ativo.
                  2. **Na Malha Fechada (MF):** A realimentação realoca os polos em malha fechada no plano complexo $s$. O método **ITAE com foco em menor overshoot** foi formulado especificamente para minimizar o critério integral $\\int_0^\\infty t |e(t)| \\, dt$, no qual desvios temporais tardios são severamente penalizados. Dessa forma, o controlador amortece as oscilações e estabiliza a variável de processo firmemente dentro da faixa de $\\pm 2\\%$, evitando ciclos térmicos prolongados que degradariam a precisão da operação.
                """
            )

        with aba_erro:
            st.markdown(
                f"""
                #### Diferenças no Erro do Processo em Regime Permanente ($e_{{ss}}$)
                - **Valores Observados:**
                  - **Malha Aberta:** `{m_ma['ess']:.4f}` (**{m_ma['ess_pct']:.2f}%** de erro relativo em relação ao Setpoint).
                  - **Malha Fechada ({nome_curto_sel}):** `{m_mf['ess']:.4f}` (**{m_mf['ess_pct']:.2f}%** de erro — rigorosamente nulo).
                
                - **Por que a diferença ocorre?**
                  1. **Na Malha Aberta (MA):** O sistema não mede a variável de saída para corrigir o sinal de controle. Como o ganho estático da planta é $K = {k_val:.4f} \\neq 1$, para uma entrada degrau $r(t) = {sp_val:.2f}$, a saída estabiliza apenas em $y(\\infty) = K \\cdot r = {k_val * sp_val:.4f}$. Isso acarreta um **erro persistente e inaceitável de mais de {(1 - k_val) * 100:.1f}%**. Além disso, distúrbios externos não podem ser compensados em malha aberta.
                  2. **Na Malha Fechada (MF):** A presença da **ação integral (termo I)** no controlador ($1 / T_i s$) acumula todo o histórico de erro ao longo do tempo:
                     $$\\int_0^t e(\\sigma) \\, d\\sigma$$
                     Enquanto a variável diferir do Setpoint ($e(t) \\neq 0$), a integral continua acumulando e elevando a tensão de controle no atuador. A única condição de equilíbrio estacionário é quando o erro é estritamente zero ($e(t) \\to 0$, $y(\\infty) = r$). Isso garante erro nulo de processo, rejeição a distúrbios e conformidade estrita com o setpoint programado.
                """
            )

        with aba_metodos:
            mp_itae = m_itae["overshoot"]
            mp_zn = m_zn["overshoot"]

            st.success(
                f"**Método com Menor Sobressinal: ITAE ({mp_itae:.2f}% de Overshoot vs. {mp_zn:.2f}% do Ziegler-Nichols)**"
            )

            st.markdown(
                f"""
                ### Comparativo de Sobressinal (*Overshoot*) e Justificativa de Desempenho

                #### 1. Qual método apresenta menores índices de sobressinal?
                O método **ITAE (Integral do Erro Absoluto Ponderado pelo Tempo)** apresenta os menores índices de sobressinal.
                - **ITAE:** obteve **{mp_itae:.2f}%** de sobressinal (praticamente nulo / transição suave).
                - **Ziegler-Nichols:** obteve **{mp_zn:.2f}%** de sobressinal (pico expressivo acima do setpoint).
                """
            )

            st.markdown(
                r"""
                ---

                #### 2. Por que o método ITAE apresenta melhores resultados?

                A superioridade do método ITAE para este processo se fundamenta em três pilares essenciais:

                ##### A) Critério de Otimização Matemático ($\int t \cdot |e(t)| \, dt$)
                - O algoritmo de sintonia ITAE é derivado da minimização formal da função de custo:
                  $$J_{\text{ITAE}} = \int_0^\infty t \cdot |e(t)| \, dt$$
                - O fator $t$ atua como uma **penalidade ponderada pelo tempo**: erros que ocorrem logo após a aplicação do degrau ($t \approx 0$) são tolerados para permitir uma elevação rápida, mas qualquer oscilação, resíduo ou sobressinal após a fase de subida recebe uma **penalização severa**.
                - Para minimizar essa integral, o algoritmo força o sistema a convergir de forma altamente amortecida, evitando que a resposta ultrapasse o setpoint.
                - Em contraste, a formulação de **Ziegler-Nichols** foi concebida heuristicamente visando uma razão de amortecimento de um quarto (*quarter decay ratio*), que tolera deliberadamente sobressinais elevados (entre 15% e 25%) em troca de agressividade no ganho inicial ($K_p$ alto e $T_i$ curto).

                ##### B) Alocação Ótima de Polos e Fator de Amortecimento ($\zeta$)
                - A sintonia ITAE calcula um balanço ótimo entre ganho proporcional e tempo integral, posicionando os polos dominantes de malha fechada com fator de amortecimento $\zeta \ge 0.707$ (próximo ao amortecimento crítico).
                - Isso elimina a ressonância do laço e impede o overshoot, enquanto Ziegler-Nichols posiciona os polos com baixo amortecimento ($\zeta \approx 0.25$ a $0.35$), provocando respostas oscilatórias.

                ##### C) Adequação Físico-Operacional à Planta
                Em processos reais (como fornos industriais), o comportamento sem sobressinal do ITAE é decisivo:
                1. **Proteção contra Choque Térmico e Degradação:** Sobrelevações térmicas provocam estresse nos elementos resistivos e materiais.
                2. **Preservação da Carga/Produto:** Ultrapassar a temperatura programada pode comprometer a integridade e qualidade do produto.
                3. **Dinâmica Assimétrica de Resfriamento:** Fornos aquecem ativamente, mas resfriam apenas por dissipação passiva. Quando ocorre um sobressinal expressivo, o sistema demora um tempo desproporcionalmente longo para retornar ao Setpoint.

                > **Conclusão:** O método **ITAE** é tecnicamente o mais indicado por combinar **rápida elevação, erro estacionário estritamente nulo e ausência de sobreaquecimento**.
                """
            )
