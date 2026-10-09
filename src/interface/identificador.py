import streamlit as st
import numpy as np
import pandas as pd
import scipy.io as sio
import matplotlib.pyplot as plt
import control as ctrl


def identificar_metodo(t, y, u_step, metodo):
    y_0 = y[0]
    y_f = y[-1]
    delta_y = y_f - y_0
    kp = delta_y / u_step

    if metodo.lower() == "smith":
        val1 = y_0 + 0.283 * delta_y
        val2 = y_0 + 0.632 * delta_y
        idx1 = np.where(y >= val1)[0]
        idx2 = np.where(y >= val2)[0]
        t1 = t[idx1[0]] if len(idx1) > 0 else t[-1]
        t2 = t[idx2[0]] if len(idx2) > 0 else t[-1]

        tau = 1.5 * (t2 - t1)
        theta = 1.5 * t1 - 0.5 * t2

    elif metodo.lower() == "sundaresan":
        val1 = y_0 + 0.353 * delta_y
        val2 = y_0 + 0.853 * delta_y
        idx1 = np.where(y >= val1)[0]
        idx2 = np.where(y >= val2)[0]
        t1 = t[idx1[0]] if len(idx1) > 0 else t[-1]
        t2 = t[idx2[0]] if len(idx2) > 0 else t[-1]

        tau = 0.67 * (t2 - t1)
        theta = 1.3 * t1 - 0.29 * t2

    else:
        raise ValueError("Método desconhecido. Use 'smith' ou 'sundaresan'.")

    return kp, tau, max(0.0, theta)


def simular_com_control(k, tau, theta, t, du):
    # Simula a resposta ao degrau FOPDT usando a biblioteca control
    sys = ctrl.tf(k, [tau, 1])
    if theta > 0:
        num_p, den_p = ctrl.pade(theta, 1)
        sys = ctrl.series(sys, ctrl.tf(num_p, den_p))

    t_unif = np.linspace(t[0], t[-1], max(len(t), 500))
    _, y_sim = ctrl.step_response(sys, T=t_unif)
    y_ma = np.interp(t, t_unif, y_sim) * du
    return np.where(t < theta, 0.0, y_ma)


def busca(mapa, nomes):
    # Retorna a primeira variável cujo nome estiver na lista
    for n in nomes:
        if n in mapa:
            return mapa[n]
    return None

def ler_arquivo(arquivo):
    if arquivo.name.endswith(".mat"):
        mat = sio.loadmat(arquivo)

        # Guarda só variáveis numéricas, já com vetores 1D
        mapa = {}
        for nome, valor in mat.items():
            if nome.startswith("__"):
                continue
            arr = np.asarray(valor)
            if np.issubdtype(arr.dtype, np.number):
                mapa[nome.lower()] = np.squeeze(arr)

        t = busca(mapa, ["t", "tempo", "time"])
        y = busca(mapa, ["y", "saida", "output", "temperatura", "temp"])
        u = busca(mapa, ["u", "degrau", "input", "sp", "entrada"])

        if t is None or y is None:
            raise ValueError(f"Tempo ou saída não encontrados. Variáveis: {list(mapa.keys())}")

    """ Arquivos CSV ou TXT
    else:
        df = pd.read_csv(arquivo, sep=None, engine="python")
        for c in df.columns:
            if df[c].dtype == object:
                try:
                    df[c] = df[c].astype(str).str.replace(",", ".").astype(float)
                except Exception:
                    pass

        t = df.iloc[:, 0].to_numpy(dtype=float)
        y = df.iloc[:, -1].to_numpy(dtype=float)
        u = df.iloc[:, 1].to_numpy(dtype=float) if df.shape[1] >= 3 else None

    """

    # Amplitude do degrau
    du = 1.0
    if u is not None:
        du = float(u[-1] - u[0])
        if abs(du) < 1e-6:  # não deixar ter divisão por zero na hora de calcular kp
            du = float(u[0])

    y = y - np.mean(y[:max(5, int(len(y) * 0.02))]) # Média para abaixar o offset inicial
    return t, y, du


def mostrar_identificacao(tab):
    with tab:
        st.subheader("Identificação de Sistemas")

        if not st.session_state.logado:
            st.warning("Faça login na aba 'Início' para acessar a identificação.")
            return

        arquivo = st.file_uploader("Escolher Arquivo", type=["csv", "txt", "mat"])
        if not arquivo:
            st.info("Selecione um dataset.")
            return

        t, y, du = ler_arquivo(arquivo)

        # Identificação por Smith e Sundaresan
        resultados = {}
        for m in ["Smith", "Sundaresan"]:
            kp, tau, theta = identificar_metodo(t, y, du, m)
            y_est = simular_com_control(kp, tau, theta, t, du)
            eqm = float(np.sqrt(np.mean((y - y_est) ** 2)))
            resultados[m] = {"k": kp, "tau": tau, "theta": theta, "eqm": eqm, "y_est": y_est}

        melhor = min(resultados.keys(), key=lambda k: resultados[k]["eqm"])

        col_graf, col_lat = st.columns([2.5, 1])

        with col_lat:
            metodo = st.selectbox("Método", ["Smith", "Sundaresan"], index=0 if melhor == "Smith" else 1)
            res = resultados[metodo]
            st.text_input("ks:", value=f"{res['k']:.4f}", disabled=True)
            st.text_input("τs:", value=f"{res['tau']:.4f}", disabled=True)
            st.text_input("θs:", value=f"{res['theta']:.4f}", disabled=True)
            st.text_input("Es:", value=f"{res['eqm']:.4f}", disabled=True)

            # Exibe o erro e justificativa de acordo com o método selecionado
            if metodo == "Smith":
                st.write(f"**Erro de Smith (EQM):** `{resultados['Smith']['eqm']:.4f}`")
                if resultados["Smith"]["eqm"] <= resultados["Sundaresan"]["eqm"]:
                    st.caption(f"Melhor que Sundaresan (EQM: {resultados['Sundaresan']['eqm']:.4f})")
                else:
                    st.caption(f"Sundaresan obteve menor erro (EQM: {resultados['Sundaresan']['eqm']:.4f})")
            elif metodo == "Sundaresan":
                st.write(f"**Erro de Sundaresan (EQM):** `{resultados['Sundaresan']['eqm']:.4f}`")
                if resultados["Sundaresan"]["eqm"] <= resultados["Smith"]["eqm"]:
                    st.caption(f"Melhor que Smith (EQM: {resultados['Smith']['eqm']:.4f})")
                else:
                    st.caption(f"Smith obteve menor erro (EQM: {resultados['Smith']['eqm']:.4f})")

            st.write("Função de Transferência:")
            if res["theta"] > 0:
                st.latex(rf"G(s) = \frac{{{res['k']:.4f}}}{{{res['tau']:.4f} s + 1}} e^{{-{res['theta']:.4f} s}}")
            else:
                st.latex(rf"G(s) = \frac{{{res['k']:.4f}}}{{{res['tau']:.4f} s + 1}}")

            sys = ctrl.tf(res["k"], [res["tau"], 1])
            num_p, den_p = ctrl.pade(res["theta"], 1) # pade aproxima 
            final_system = ctrl.series(sys, ctrl.tf(num_p, den_p))

            st.session_state.dados_ident = {
                "metodo": metodo,
                **res,
                "setpoint": float(y[-1]),
                "sistema": final_system,
            }

        with col_graf:
            fig, ax = plt.subplots(figsize=(6, 3.5))
            ax.plot(t, y, label="Curva Experimental", color="#1f77b4")
            ax.plot(t, res["y_est"], label=f"Modelo {metodo}", color="#d62728", linestyle="--")
            ax.set_xlabel("Tempo (s)")
            ax.set_ylabel("Temperatura do Forno (°C)")
            ax.grid(True, linestyle="--", alpha=0.5)
            ax.legend()
            fig.tight_layout()
            st.pyplot(fig)
