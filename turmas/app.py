import base64
import json
import os
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Sistema Alimentação Escolar", layout="wide", page_icon="🍽️"
)


# --- FUNÇÃO DE SALVAMENTO NO GITHUB ---
def salvar_relatorio_github(relatorio, nome_turma):
    try:
        github_token = st.secrets["GITHUB_TOKEN"]
        github_repo = st.secrets["GITHUB_REPO"]
    except KeyError:
        st.error(
            "⚠️ Erro de configuração: GITHUB_TOKEN ou GITHUB_REPO não encontrados nos Secrets!"
        )
        return False

    data_hoje = datetime.now().strftime("%Y-%m-%d")
    
    # NOME FIXO DA TURMA: Sobrescreve o arquivo existente no GitHub a cada novo dia/envio
    nome_arquivo = f"relatorio_{nome_turma}.json"
    caminho_no_repo = f"relatorios/{nome_arquivo}"

    url = f"https://api.github.com/repos/{github_repo}/contents/{caminho_no_repo}"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    conteudo_json = json.dumps(relatorio, ensure_ascii=False, indent=2)
    conteudo_base64 = base64.b64encode(conteudo_json.encode("utf-8")).decode(
        "utf-8"
    )

    resposta_get = requests.get(url, headers=headers)
    sha = (
        resposta_get.json().get("sha") if resposta_get.status_code == 200 else None
    )

    payload = {
        "message": f"Chamada {nome_turma} - {data_hoje}",
        "content": conteudo_base64,
    }
    if sha:
        payload["sha"] = sha

    resposta_put = requests.put(url, headers=headers, json=payload)
    return resposta_put.status_code in [200, 201]


# --- NAVEGAÇÃO DE ABAS ---
aba_chamada, aba_dashboard = st.tabs(
    ["📝 Realizar Chamada (Salas)", "📊 Painel de Controle & Cozinha"]
)

# ==============================================================================
# ABA 1: CHAMADA EM SALA DE AULA
# ==============================================================================
with aba_chamada:
    st.title("🍽️ Chamada da Merenda")

    PASTA_TURMAS = "turmas"
    # Adicionada ordenação alfabética (sorted) nos arquivos de turmas
    arquivos_turmas = (
        sorted([f for f in os.listdir(PASTA_TURMAS) if f.endswith(".json")])
        if os.path.exists(PASTA_TURMAS)
        else []
    )

    if not arquivos_turmas:
        st.error(
            "Nenhuma turma encontrada na pasta 'turmas/'. Adicione arquivos .json lá!"
        )
    else:
        turma_arquivo = st.selectbox("Selecione a Turma:", arquivos_turmas)
        caminho_json = os.path.join(PASTA_TURMAS, turma_arquivo)

        with open(caminho_json, "r", encoding="utf-8") as f:
            alunos = json.load(f)
alunos = sorted(alunos, key=lambda x: x["nome"])
        st.markdown("---")

        respostas = {}
        for aluno in alunos:
            col_nome, col_opcao = st.columns([3, 2])

            with col_nome:
                st.markdown(f"**{aluno['nome']}**")
                st.caption(f"ID: {aluno['id']}")

            with col_opcao:
                escolha = st.segmented_control(
                    label=f"Status {aluno['id']}",
                    options=["VAI COMER", "NÃO VAI"],
                    default="VAI COMER",
                    key=f"status_{aluno['id']}_{turma_arquivo}",
                    label_visibility="collapsed",
                )
                respostas[aluno["id"]] = escolha

        st.markdown("---")

        if st.button(
            "🚀 Finalizar Chamada e Enviar",
            type="primary",
            use_container_width=True,
        ):
            nome_turma_limpo = turma_arquivo.replace(".json", "")
            relatorio = [
                {
                    "id": aluno["id"],
                    "nome": aluno["nome"],
                    "qr": aluno["qr"],
                    "vai_comer": True
                    if respostas.get(aluno["id"], "VAI COMER") == "VAI COMER"
                    else False,
                    "turma": nome_turma_limpo,
                    "data": datetime.now().strftime("%Y-%m-%d"),
                }
                for aluno in alunos
            ]

            with st.spinner("Enviando chamada para a nuvem..."):
                sucesso = salvar_relatorio_github(relatorio, nome_turma_limpo)

            if sucesso:
                st.success(
                    f"✅ Chamada da turma **{nome_turma_limpo}** salva na nuvem com sucesso!"
                )
                st.balloons()

# ==============================================================================
# ABA 2: DASHBOARD EXECUTIVO PARA A DIREÇÃO E COZINHA
# ==============================================================================
with aba_dashboard:
    st.title("📊 Visão Geral da Merenda do Dia")
    st.caption("Consolidação em tempo real das intenções enviadas pelas salas")

    PASTA_RELATORIOS = "relatorios"
    relatorios_locais = (
        sorted([f for f in os.listdir(PASTA_RELATORIOS) if f.endswith(".json")])
        if os.path.exists(PASTA_RELATORIOS)
        else []
    )

    todos_dados = []
    for rel_file in relatorios_locais:
        caminho_rel = os.path.join(PASTA_RELATORIOS, rel_file)
        try:
            with open(caminho_rel, "r", encoding="utf-8") as f:
                dados_turma = json.load(f)
                if isinstance(dados_turma, list):
                    todos_dados.extend(dados_turma)
        except Exception:
            pass

    if not todos_dados:
        st.info(
            "ℹ️ Nenhum relatório do dia foi enviado ainda ou a pasta 'relatorios/' está vazia."
        )
    else:
        df = pd.DataFrame(todos_dados)

        # MÉTRICAS PRINCIPAIS (CARDS)
        total_alunos = len(df)
        total_comer = len(df[df["vai_comer"] == True])
        total_nao_comer = len(df[df["vai_comer"] == False])
        taxa_adesao = (
            (total_comer / total_alunos * 100) if total_alunos > 0 else 0
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Alunos Registrados", total_alunos)
        col2.metric("🍽️ Vão Almoçar/Lanchar", total_comer)
        col3.metric("❌ Não Querem Merenda", total_nao_comer)
        col4.metric("📈 Taxa de Adesão", f"{taxa_adesao:.1f}%")

        st.markdown("---")

        # GRÁFICO COMPARATIVO POR TURMA
        st.subheader("📌 Intenção de Refeição por Turma")
        df_agrupado = (
            df.groupby(["turma", "vai_comer"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )

        if True in df_agrupado.columns and False in df_agrupado.columns:
            df_agrupado.rename(
                columns={True: "VAI COMER", False: "NÃO VAI"}, inplace=True
            )
            st.bar_chart(
                df_agrupado.set_index("turma")[["VAI COMER", "NÃO VAI"]],
                color=["#2e7d32", "#d32f2f"],
            )

        st.markdown("---")

        # TABELA DETALHADA / FILTRO COZINHA
        st.subheader("📋 Lista de Conferência da Cozinha")
        # Turmas organizadas em ordem alfabética no Selectbox do filtro
        turmas_disponiveis = sorted(df["turma"].unique())
        turma_filtro = st.selectbox(
            "Filtrar lista por turma:", ["TODAS"] + list(turmas_disponiveis)
        )

        if turma_filtro != "TODAS":
            df_exibicao = df[df["turma"] == turma_filtro]
        else:
            df_exibicao = df

        df_exibicao["Status"] = df_exibicao["vai_comer"].map(
            {True: "✅ VAI COMER", False: "❌ NÃO VAI"}
        )
        st.dataframe(
            df_exibicao[["turma", "id", "nome", "Status"]],
            use_container_width=True,
            hide_index=True,
        )
