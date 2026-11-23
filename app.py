"""Data Pilot — painel de vendas (Streamlit) com chat sobre os dados.

Rode com ``streamlit run app.py`` (não como script comum). O painel lê apenas o
CSV limpo; o chat usa o agente que, por sua vez, executa as ferramentas de
métrica. Em nenhum ponto o modelo calcula números: ele só escolhe a ferramenta.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from data_pilot.agente import ErroAgente, criar_cliente, responder
from data_pilot.dados import carregar_bruto, carregar_limpo, limpar_vendas, salvar_limpo
from data_pilot.metricas import (
    TODAS_AS_CATEGORIAS,
    clientes_unicos,
    receita_media_por_cliente,
    receita_por_mes,
    receita_total,
    taxa_cancelamento,
    ticket_medio,
    top_cidades,
    total_pedidos,
)

load_dotenv()

RAIZ = Path(__file__).resolve().parent
BRUTO = RAIZ / "data" / "raw" / "sales.csv"
LIMPO = RAIZ / "data" / "processed" / "vendas_limpo.csv"


def moeda(valor: float) -> str:
    """Formata em reais no padrão brasileiro (R$ 1.234,56)."""
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data
def carregar_dados() -> pd.DataFrame:
    """Carrega o CSV limpo; se ainda não existir, deriva do bruto."""
    if not LIMPO.is_file():
        base, _ = limpar_vendas(carregar_bruto(BRUTO))
        salvar_limpo(base, LIMPO)
    return carregar_limpo(LIMPO)


def aba_painel(df: pd.DataFrame, categoria: str) -> None:
    st.subheader("Visão geral")
    colunas = st.columns(3)
    colunas[0].metric("Receita total", moeda(receita_total(df, categoria)))
    colunas[1].metric("Pedidos", total_pedidos(df, categoria))
    colunas[2].metric("Ticket médio", moeda(ticket_medio(df, categoria)))

    colunas = st.columns(3)
    colunas[0].metric("Clientes únicos", clientes_unicos(df, categoria))
    colunas[1].metric("Taxa de cancelamento", f"{taxa_cancelamento(df, categoria):.2f}%")
    colunas[2].metric("Receita média por cliente", moeda(receita_media_por_cliente(df, categoria)))

    st.subheader("Receita por mês")
    mensal = receita_por_mes(df, categoria)
    if mensal.empty:
        st.info("Sem pedidos concluídos para o filtro selecionado.")
    else:
        figura = px.bar(mensal, x="mes", y="receita", text_auto=".2s")
        figura.update_layout(xaxis_title="Mês", yaxis_title="Receita (R$)")
        st.plotly_chart(figura, use_container_width=True)

    st.subheader("Top 5 cidades por receita")
    cidades = top_cidades(df, n=5, categoria=categoria)
    if cidades.empty:
        st.info("Sem dados de cidade para o filtro selecionado.")
    else:
        figura = px.bar(cidades, x="receita", y="cidade", orientation="h")
        figura.update_layout(xaxis_title="Receita (R$)", yaxis_title="Cidade")
        st.plotly_chart(figura, use_container_width=True)


def aba_conversa(df: pd.DataFrame, categoria: str) -> None:
    st.subheader("Converse com os dados")
    st.caption(
        "Pergunte em português. O modelo escolhe a ferramenta; o Python calcula; "
        "a resposta apenas explica o resultado."
    )

    if "mensagens" not in st.session_state:
        st.session_state.mensagens = []

    for mensagem in st.session_state.mensagens:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])

    pergunta = st.chat_input("Ex.: qual foi a receita de Eletronicos?")
    if not pergunta:
        return

    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        try:
            cliente = criar_cliente()
            filtro = None if categoria == TODAS_AS_CATEGORIAS else categoria
            resultado = responder(pergunta, df, cliente=cliente)
            resposta = resultado.resposta
            if resultado.chamadas:
                usadas = ", ".join(chamada["ferramenta"] for chamada in resultado.chamadas)
                st.caption(f"Ferramentas usadas: {usadas}")
            if filtro:
                st.caption(f"Filtro ativo no painel: {filtro}")
        except ErroAgente as erro:
            resposta = f"⚠️ {erro}"
        except Exception as erro:  # falha de rede/limite do modelo gratuito
            resposta = (
                "⚠️ Não consegui responder agora (o modelo gratuito tem limite de uso). "
                f"Detalhe: {erro}"
            )
        st.markdown(resposta)

    st.session_state.mensagens.append({"role": "assistant", "content": resposta})


def main() -> None:
    st.set_page_config(page_title="Data Pilot", page_icon="📊", layout="wide")
    st.title("📊 Data Pilot")

    try:
        df = carregar_dados()
    except FileNotFoundError:
        st.error(
            "Base não encontrada. Rode `python scripts/gerar_dados.py` e "
            "`python scripts/preparar_dados.py` antes de abrir o painel."
        )
        st.stop()

    categorias = [TODAS_AS_CATEGORIAS, *sorted(df["categoria"].unique())]
    categoria = st.sidebar.selectbox("Categoria", categorias)

    painel, conversa = st.tabs(["📊 Painel", "💬 Conversar"])
    with painel:
        aba_painel(df, categoria)
    with conversa:
        aba_conversa(df, categoria)


main()
