import streamlit as st
import numpy as np
import pandas as pd
import scipy.io as sio

NOMES_SAIDA = ["y", "saida", "output", "temperatura", "temp"]


def carregar_mat(arquivo):
    # Guarda só variáveis numéricas, com vetores 1D
    mat = sio.loadmat(arquivo)
    mapa = {}
    for nome, valor in mat.items():
        if nome.startswith("__"):
            continue
        arr = np.squeeze(np.asarray(valor)) # 1D
        if np.issubdtype(arr.dtype, np.number): # obrigatório ser numérico
            mapa[nome] = arr 
    return mapa


def resumir_vetor(nome, v):
    return {
        "Coluna / Variável": nome,
        "Tipo": str(v.dtype),
        "Mínimo": f"{np.nanmin(v):.4f}",
        "Máximo": f"{np.nanmax(v):.4f}",
        "Média": f"{np.nanmean(v):.4f}",
    }


def achar_saida_mat(mapa):
    for nome_busca in NOMES_SAIDA:
        for nome, v in mapa.items():
            if nome.lower() == nome_busca:
                return nome, v

    raise ValueError(f"Variável de saída não encontrada. Variáveis: {list(mapa.keys())}")


def extrair_mat(arquivo):
    mapa = carregar_mat(arquivo)

    colunas_info = []
    for nome, v in mapa.items():
        if v.ndim == 1 and v.size > 0: # Obrigatoriamente vetor 1d não vazio
            colunas_info.append(resumir_vetor(nome, v))

    nome_saida, y = achar_saida_mat(mapa)
    return colunas_info, nome_saida, y


def extrair_csv(arquivo):
    df = pd.read_csv(arquivo, sep=None, engine="python")

    colunas_info = []
    for c in df.columns:
        # Troca vírgula decimal por ponto, quando for texto
        if df[c].dtype == object:
            try:
                df[c] = df[c].astype(str).str.replace(",", ".").astype(float)
            except Exception:
                pass

        serie = pd.to_numeric(df[c], errors="coerce")
        colunas_info.append({
            "Coluna / Variável": str(c),
            "Tipo": str(df[c].dtype),
            "Tamanho": len(df),
            "Mínimo": f"{serie.min():.4f}",
            "Máximo": f"{serie.max():.4f}",
            "Média": f"{serie.mean():.4f}",
        })

    nome_saida = str(df.columns[-1])
    y = df.iloc[:, -1].to_numpy(dtype=float) # busca a última coluna como saída
    return colunas_info, nome_saida, y


def extrair_dados(arquivo):
    # Extrai as informações de todas as colunas/variáveis e identifica a saída
    if arquivo.name.endswith(".mat"):
        colunas_info, nome_saida, y = extrair_mat(arquivo)
    else:
        colunas_info, nome_saida, y = extrair_csv(arquivo)

    y = np.array(y, dtype=float).squeeze()
    return colunas_info, nome_saida, y


def mostrar_dados(tab):
    with tab:
        st.subheader("Dados do Arquivo")

        if not st.session_state.logado:
            st.warning("Faça login na aba 'Início' para visualizar os dados.")
            return

        arquivo = st.file_uploader("Escolher Arquivo", type=["mat", "csv", "txt"], key="uploader_dados")
        if not arquivo:
            st.info("Selecione um arquivo (.mat, .csv ou .txt) para visualizar os dados.")
            return

        colunas_info, nome_saida, y = extrair_dados(arquivo)

        st.write("**Colunas / Variáveis no Arquivo:**")
        st.dataframe(pd.DataFrame(colunas_info), width="stretch", hide_index=True)

        st.write(f"**Distribuição da Saída (`{nome_saida}`):**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Coluna de Saída", nome_saida)
        col2.metric("Mínimo", f"{np.nanmin(y):.4f}")
        col3.metric("Máximo", f"{np.nanmax(y):.4f}")
        col4.metric("Média", f"{np.nanmean(y):.4f}")

        st.write(f"**Primeiros valores:** `{np.round(y[:5], 4)}`")
        st.write(f"**Últimos valores:** `{np.round(y[-5:], 4)}`")

        st.write("**Tabela da Saída:**")
        df_saida = pd.DataFrame({"Índice": np.arange(len(y)), nome_saida: y}) # índices separados de forma igual
        st.dataframe(df_saida, width="stretch", hide_index=True, height=350)