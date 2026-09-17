import os
import json
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Chamada da Merenda", layout="wide")

st.title("🍽️ Chamada da Merenda")

# 1. Localiza os arquivos da pasta turmas
PASTA_TURMAS = "turmas"

if os.path.exists(PASTA_TURMAS):
    arquivos_turmas = [f for f in os.listdir(PASTA_TURMAS) if f.endswith(".json")]
else:
    arquivos_turmas = []

if not arquivos_turmas:
    st.error("Nenhuma turma encontrada na pasta 'turmas/'. Add arquivos .json lá!")
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
            label_visibility="collapsed"
        )
        respostas[aluno['id']] = escolha

st.markdown("---")

# 4. Finalização e geração do JSON de saída
if st.button("🚀 Finalizar Chamada da Turma", type="primary", use_container_width=True):
    relatorio = []
    for aluno in alunos:
        status = respostas.get(aluno['id'], "VAI COMER")
        relatorio.append({
            "id": aluno["id"],
            "nome": aluno["nome"],
            "qr": aluno["qr"],
            "vai_comer": True if status == "VAI COMER" else False,
            "turma": turma_arquivo.replace(".json", ""),
            "data": datetime.now().strftime("%Y-%m-%d")
        })
    
    st.success("✅ Chamada concluída com sucesso!")
    
    # Gera o botão de download do relatório limpo em JSON
    st.download_button(
        label="📥 Baixar Relatório JSON do Dia",
        data=json.dumps(relatorio, ensure_ascii=False, indent=2),
        file_name=f"relatorio_{turma_arquivo.replace('.json', '')}_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json"
    )
