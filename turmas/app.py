import base64
import json
import os
from datetime import datetime
import requests
import streamlit as st

st.set_page_config(page_title="Chamada da Merenda", layout="wide")

st.title("🍽️ Chamada da Merenda")


# --- FUNÇÃO PARA SALVAR O JSON DIRETO NA SUA PASTA NO GITHUB ---
def salvar_relatorio_github(relatorio, nome_turma):
    # Puxa o Token e o Repositório salvos nas Secrets do Streamlit Cloud
    try:
        github_token = st.secrets["GITHUB_TOKEN"]
        github_repo = st.secrets["GITHUB_REPO"]
    except KeyError:
        st.error(
            "⚠️ Erro de configuração: GITHUB_TOKEN ou GITHUB_REPO não encontrados nos Secrets!"
        )
        return False

    data_hoje = datetime.now().strftime("%Y%m%d")
    nome_arquivo = f"relatorio_{nome_turma}_{data_hoje}.json"
    caminho_no_repo = f"relatorios/{nome_arquivo}"

    url = f"https://api.github.com/repos/{github_repo}/contents/{caminho_no_repo}"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Transforma o relatório em texto JSON formatado
    conteudo_json = json.dumps(relatorio, ensure_ascii=False, indent=2)

    # O GitHub exige que o arquivo seja enviado codificado em Base64
    conteudo_base64 = base64.b64encode(conteudo_json.encode("utf-8")).decode(
        "utf-8"
    )

    # Verifica se o arquivo já existe na pasta para pegar o SHA (caso seja uma atualização da chamada no mesmo dia)
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

    # Dispara a gravação na pasta relatorios/
    resposta_put = requests.put(url, headers=headers, json=payload)

    if resposta_put.status_code in [200, 201]:
        return True
    else:
        st.error(
            f"❌ Erro ao salvar no GitHub ({resposta_put.status_code}): {resposta_put.text}"
        )
        return False


# 1. Localiza os arquivos da pasta turmas
PASTA_TURMAS = "turmas"

if os.path.exists(PASTA_TURMAS):
    arquivos_turmas = [
        f for f in os.listdir(PASTA_TURMAS) if f.endswith(".json")
    ]
else:
    arquivos_turmas = []

if not arquivos_turmas:
    st.error(
        "Nenhuma turma encontrada na pasta 'turmas/'. Add arquivos .json lá!"
    )
    st.stop()

# 2. Seletor da turma no topo
turma_arquivo = st.selectbox("Selecione a Turma:", arquivos_turmas)
caminho_json = os.path.join(PASTA_TURMAS, turma_arquivo)

with open(caminho_json, "r", encoding="utf-8") as f:
    alunos = json.load(f)

st.markdown("---")

# 3. Exibição da lista para a chamada
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

# 4. Finalização e envio automático para o GitHub
if st.button(
    "🚀 Finalizar Chamada e Enviar", type="primary", use_container_width=True
):
    nome_turma_limpo = turma_arquivo.replace(".json", "")

    relatorio = []
    for aluno in alunos:
        status = respostas.get(aluno["id"], "VAI COMER")
        relatorio.append({
            "id": aluno["id"],
            "nome": aluno["nome"],
            "qr": aluno["qr"],
            "vai_comer": True if status == "VAI COMER" else False,
            "turma": nome_turma_limpo,
            "data": datetime.now().strftime("%Y-%m-%d"),
        })

    with st.spinner("Enviando chamada para a nuvem..."):
        sucesso = salvar_relatorio_github(relatorio, nome_turma_limpo)

    if sucesso:
        st.success(
            f"✅ Chamada da turma **{nome_turma_limpo}** salva na nuvem com sucesso!"
        )
        st.balloons()
