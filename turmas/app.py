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

    # NOME FIXO DA TURMA: Sobrescreve o relatório da mesma turma a cada novo dia/envio
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
    st.title("🍽️ Chamada da Merenda & Frequência")

    PASTA_TURMAS = "turmas"
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

        alunos = sorted(alunos, key=lambda x: str(x.get("nome", "")).lower())

        st.markdown("---")

        respostas = {}
        for aluno in alunos:
            col_nome, col_opcao = st.columns([3, 2])

            with col_nome:
                st.markdown(f"**{aluno.get('nome', '')}**")
                st.caption(f"ID: {aluno.get('id', '')}")

            with col_opcao:
                escolha = st.segmented_control(
                    label=f"Status {aluno.get('id', '')}",
                    options=["VAI COMER", "NÃO VAI", "FALTOU"],
                    default="VAI COMER",
                    key=f"status_{aluno.get('id', '')}_{turma_arquivo}",
                    label_visibility="collapsed",
                )
                respostas[aluno.get("id")] = escolha

        st.markdown("---")

        if st.button(
            "🚀 Finalizar Chamada e Enviar",
            type="primary",
            use_container_width=True,
        ):
            nome_turma_limpo = turma_arquivo.replace(".json", "")
            relatorio = []

            for aluno in alunos:
                status_opcao = respostas.get(aluno.get("id"), "VAI COMER")
                status_presenca = "AUSENTE" if status_opcao == "FALTOU" else "PRESENTE"
                vai_comer = True if status_opcao == "VAI COMER" else False

                relatorio.append(
                    {
                        "id": aluno.get("id"),
                        "nome": aluno.get("nome"),
                        "qr": aluno.get("qr"),
                        "status": status_opcao,
                        "presenca": status_presenca,
                        "vai_comer": vai_comer,
                        "turma": nome_turma_limpo,
                        "data": datetime.now().strftime("%Y-%m-%d"),
                    }
                )

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
    st.title("📊 Painel da Cozinha & Coordenação")
    st.caption("Consolidação em tempo real das intenções e faltas enviadas pelas salas")

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

        if "status" not in df.columns:
            df["status"] = df["vai_comer"].map({True: "VAI COMER", False: "NÃO VAI"})

        # MÉTRICAS PRINCIPAIS
        total_alunos = len(df)
        total_comer = len(df[df["status"] == "VAI COMER"])
        total_nao_comer = len(df[df["status"] == "NÃO VAI"])
        total_faltosos = len(df[df["status"] == "FALTOU"])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Alunos Registrados", total_alunos)
        col2.metric("🍽️ Vão Comer", total_comer)
        col3.metric("❌ Não Querem Merenda", total_nao_comer)
        col4.metric("🚨 Total de Faltosos", total_faltosos)

        st.markdown("---")

        # GRÁFICO COMPARATIVO POR TURMA
        st.subheader("📌 Distribuição por Turma (Comer, Desistente, Faltoso)")
        
        df_agrupado = (
            df.groupby(["turma", "status"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )

        cols_grafico = [c for c in ["VAI COMER", "NÃO VAI", "FALTOU"] if c in df_agrupado.columns]
        st.bar_chart(
            df_agrupado.set_index("turma")[cols_grafico],
            color=["#2e7d32", "#f57c00", "#d32f2f"][:len(cols_grafico)],
        )

        st.markdown("---")

        # SEÇÃO UNIFICADA DE FALTOSOS
        st.subheader("🚨 Controle Unificado de Alunos Faltosos (Imediato)")
        
        df_faltosos = df[df["status"] == "FALTOU"].sort_values(
            by=["turma", "nome"], key=lambda col: col.str.lower()
        )

        if df_faltosos.empty:
            st.success("🎉 Nenhum aluno faltoso registrado até o momento!")
        else:
            st.warning(f"⚠️ Atenção: {len(df_faltosos)} aluno(s) faltoso(s) identificado(s) hoje.")
            
            st.dataframe(
                df_faltosos[["turma", "id", "nome"]],
                use_container_width=True,
                hide_index=True,
            )

            csv_faltosos = df_faltosos[["turma", "id", "nome"]].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Lista Unificada de Faltosos (CSV)",
                data=csv_faltosos,
                file_name=f"faltosos_unificados_{datetime.now().strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
            )

        st.markdown("---")

        # TABELA DETALHADA PARA A COZINHA
        st.subheader("📋 Lista de Conferência Geral / Cozinha")
        turmas_disponiveis = sorted(df["turma"].unique())
        turma_filtro = st.selectbox(
            "Filtrar lista da cozinha por turma:", ["TODAS"] + list(turmas_disponiveis)
        )

        if turma_filtro != "TODAS":
            df_exibicao = df[df["turma"] == turma_filtro]
        else:
            df_exibicao = df

        df_exibicao = df_exibicao.sort_values(
            by=["turma", "nome"], key=lambda col: col.str.lower()
        )

        status_map = {
            "VAI COMER": "✅ VAI COMER",
            "NÃO VAI": "🟠 NÃO VAI",
            "FALTOU": "🔴 FALTOU À ESCOLA"
        }
        df_exibicao["Status Detalhado"] = df_exibicao["status"].map(status_map)

        st.dataframe(
            df_exibicao[["turma", "id", "nome", "Status Detalhado"]],
            use_container_width=True,
            hide_index=True,
        )
