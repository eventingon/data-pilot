# 📊 Data Pilot

Painel de vendas em Python que **também conversa**: você pergunta em português e
um agente escolhe qual função do código chamar para responder com as métricas
reais. A regra que segura tudo: **o Python calcula, a IA só explica**.

## O que ele faz

- **Painel** (Streamlit): receita total, pedidos, ticket médio, clientes únicos,
  taxa de cancelamento e receita média por cliente, com filtro por categoria;
  gráfico de receita mensal (Plotly) e Top 5 cidades por receita.
- **Conversa** (OpenRouter): um chat que recebe a pergunta, decide qual
  ferramenta chamar, executa a função Python e explica o resultado — sem
  inventar número.

## De onde vêm os dados

A base é **100% sintética** (`data/raw/sales.csv`, gerada por
`scripts/gerar_dados.py`): 240 pedidos fictícios de uma loja ao longo de 2025,
com categorias, cidades e status variados. Nada de pessoa, CNPJ ou valor real.
A base bruta é propositalmente "suja" (datas em dois formatos, status com
caixa/acento inconsistentes, duplicatas) para exercitar a limpeza.

O fluxo do dado:

```
data/raw/sales.csv
   └─ scripts/preparar_dados.py  (limpa: datas, status, duplicatas, receita)
        └─ data/processed/vendas_limpo.csv   (separador ';', decimal ',')
             └─ app.py  (painel + chat)
```

## Passo a passo: instalar, configurar e rodar

Pré-requisitos: **Python 3.12+** e acesso à internet (só para o chat). Todos os
comandos abaixo são para PowerShell no Windows; no Linux/macOS troque
`.\venv\Scripts\python.exe` por `venv/bin/python`.

### 1. Criar e ativar um ambiente virtual (opcional, mas recomendado)

```powershell
cd data-pilot
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Se aparecer erro de política de execução no PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Instalar as dependências

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Isso instala `pandas`, `plotly`, `streamlit`, `openai` e `python-dotenv`.
Para rodar os testes, instale também as dependências de desenvolvimento:

```powershell
python -m pip install -r requirements-dev.txt
```

### 3. Configurar a chave do OpenRouter (`.env`)

```powershell
Copy-Item .env.example .env
```

Abra o `.env` e preencha a chave (só o `.env.example` é versionado; o `.env`
está no `.gitignore`):

```ini
OPENROUTER_API_KEY=sua_chave_aqui
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Crie a chave gratuita em <https://openrouter.ai>. O modelo `openrouter/free` tem
limite de uso e pode falhar às vezes — o app avisa em vez de quebrar. Sem a
chave, **o painel continua funcionando**; só a conversa fica indisponível.

### 4. Gerar e preparar os dados

```powershell
python scripts/gerar_dados.py      # cria data/raw/sales.csv (sintético)
python scripts/preparar_dados.py   # cria data/processed/vendas_limpo.csv
```

Saída esperada do segundo comando: algo como `bruto: 245 linhas` e
`limpo: 240 linhas` (as duplicatas são removidas e contadas).

### 5. Rodar o Streamlit

```powershell
python -m streamlit run app.py
```

> ⚠️ Rode com `streamlit run`, **não** com `python app.py`. O `python app.py`
> apenas importa o arquivo e não inicia o servidor da interface.

O terminal mostrará um endereço como `http://localhost:8501`; abra no navegador.
Para parar, pressione `Ctrl+C`.

### 6. Usar o painel

- Na barra lateral, escolha a **categoria** (ou `Todas`).
- Os cards mostram: receita total, pedidos, ticket médio, clientes únicos, taxa
  de cancelamento e receita média por cliente.
- Abaixo, o gráfico de **receita por mês** e o **Top 5 cidades por receita**.

### 7. Usar a conversa

1. Abra a aba **Conversar**.
2. Digite a pergunta em português e pressione Enter.
3. O modelo escolhe uma ferramenta, o Python calcula e a resposta aparece em
   texto. Quando houver chamada de ferramenta, uma legenda mostra
   **“Ferramentas usadas: …”** — é a prova de que o número veio do código.

Exemplos e a ferramenta que cada pergunta tende a acionar:

| Pergunta | Ferramenta esperada |
| --- | --- |
| “Qual a receita total?” | `receita_total` |
| “Quantos pedidos tivemos?” | `total_pedidos` |
| “Qual o ticket médio?” | `ticket_medio` |
| “Quantos clientes únicos?” | `clientes_unicos` |
| “Qual a taxa de cancelamento?” | `taxa_cancelamento` |
| “Qual a receita média por cliente?” | `receita_media_por_cliente` |
| “Quais as 3 cidades que mais vendem?” | `top_cidades` (`n=3`) |
| “Qual a receita de Eletronicos?” | `receita_total` (`categoria=Eletronicos`) |

O filtro da barra lateral vale para o **painel**. No chat, a categoria vai como
argumento quando o modelo entender que faz sentido (ex.: “receita de Moveis”).

Para conferir a paridade, compare: o card “Receita total” do painel e a resposta
do chat para “receita total” devem trazer **o mesmo número**.

### Problemas comuns

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `streamlit` não é reconhecido | dependências não instaladas na venv ativa | refaça o passo 2 com a venv ativada |
| Página abre, mas o chat dá erro de chave | `OPENROUTER_API_KEY` vazia | preencha o `.env` e reinicie o `streamlit` |
| `Address already in use` | porta 8501 ocupada | `python -m streamlit run app.py --server.port 8502` |
| Resposta “não consegui responder agora” | limite do modelo gratuito | aguarde e pergunte de novo, ou troque `OPENROUTER_MODEL` |
| Erro de política de execução | PowerShell bloqueando scripts | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

## As ferramentas que o modelo pode chamar

Cada métrica é uma ferramenta com `name`, `description` e `parameters`
(veja `data_pilot/ferramentas.py`). O modelo escolhe; o Python executa pelo nome.

| Ferramenta | Responde a perguntas sobre | Parâmetros |
| --- | --- | --- |
| `receita_total` | receita/faturamento em R$ | `categoria` (opcional) |
| `total_pedidos` | quantos pedidos concluídos | `categoria` |
| `ticket_medio` | valor médio por pedido | `categoria` |
| `clientes_unicos` | quantos clientes distintos | `categoria` |
| `taxa_cancelamento` | % de pedidos cancelados | `categoria` |
| `receita_media_por_cliente` ✨ | receita média por cliente | `categoria` |
| `top_cidades` ✨ | N cidades que mais vendem | `n`, `categoria` |

Todas as métricas de receita consideram apenas pedidos **concluídos**. A taxa de
cancelamento é a exceção natural: usa o total de pedidos como denominador.

### Melhoria escolhida

Além do núcleo do desafio, foram incluídas **duas** melhorias da lista:

1. **Métrica nova:** `receita_media_por_cliente` (receita ÷ clientes distintos).
2. **Gráfico novo:** **Top 5 cidades por receita**, com ferramenta `top_cidades`
   que aceita o parâmetro `n` — um exemplo de ferramenta com argumento.

## Como o agente funciona (sem framework)

1. `data_pilot/ferramentas.py` descreve as funções e mapeia `nome → execução`.
2. `data_pilot/agente.py` envia a pergunta + `tools` ao OpenRouter.
3. Se o modelo pedir uma ferramenta (`tool_calls`), o Python executa e devolve o
   resultado como mensagem `role=tool`; o modelo então **explica** o número.
4. O resultado final é texto; os números vêm sempre da execução Python.

Esse desenho é testável sem rede: `tests/test_agente.py` usa um cliente falso
que simula as respostas do modelo.

## Como testar a escolha das ferramentas

A descrição de cada ferramenta é o único "manual" que o modelo recebe: se ele
escolhe errado, o problema quase sempre está no texto do `name`/`description`,
não no Python. Por isso existe um medidor objetivo:

```powershell
python scripts/avaliar_ferramentas.py            # tabela de acertos por pergunta
python scripts/avaliar_ferramentas.py --json out/avaliacao.json
python scripts/avaliar_ferramentas.py --estrito  # sai com código 1 se errar
```

Ele roda uma lista fixa de perguntas (`CASOS`, em `scripts/avaliar_ferramentas.py`)
e mostra o que o modelo escolheu de fato:

```
OK      Qual a receita média por cliente? -> esperada=receita_media_por_cliente obtida=receita_media_por_cliente
PARCIAL Quais as 3 cidades que mais vendem? -> esperada=top_cidades obtida=top_cidades   # n diferente
```

`OK` = ferramenta e argumentos corretos; `PARCIAL` = ferramenta certa, argumento
diferente; `FALHOU` = ferramenta errada; `ERRO` = limite/queda do provedor
(contado à parte, para não mascarar a qualidade da descrição).

O ciclo de melhoria é: rode, veja qual caso falha, ajuste a `description`
(inclua as frases que o usuário usaria e a unidade: R$, %, 0–100, "concluídos"),
rode de novo e compare. Assim a decisão deixa de ser "achismo" e vira medição.

## Estrutura

```
data-pilot/
├── app.py                     # painel + chat (streamlit run app.py)
├── data_pilot/
│   ├── dados.py               # carregar/limpar/salvar (CSV ';', decimal ',')
│   ├── metricas.py            # uma função por pergunta de negócio
│   ├── ferramentas.py         # esquemas + roteador (nome → função)
│   └── agente.py              # laço de tool calling no OpenRouter
├── scripts/
│   ├── gerar_dados.py         # cria data/raw/sales.csv (sintético)
│   ├── preparar_dados.py      # gera data/processed/vendas_limpo.csv
│   └── avaliar_ferramentas.py # mede se o modelo escolhe a ferramenta certa
├── data/
│   ├── raw/sales.csv
│   └── processed/vendas_limpo.csv
├── docs/prints/               # capturas de tela (evidências)
├── tests/                     # dados, métricas, ferramentas, agente e avaliação
├── .env.example
├── .gitignore
├── pyproject.toml             # metadados + config de lint/teste
├── requirements.txt           # dependências do app
├── requirements-dev.txt       # dependências de teste
└── README.md
```

## Testes

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Cobrem: limpeza (datas mistas, duplicadas, valores inválidos, ida-e-volta do
CSV), as sete métricas com números conhecidos, o contrato das ferramentas e o
laço do agente com um modelo falso — **sem rede**.

## Prints

As capturas ficam em `docs/prints/` (veja `docs/prints/README.md`). Elas são a
evidência que mais pesa no portfólio:

- `docs/prints/painel.png` — cards, filtro e receita mensal;
- `docs/prints/chat.png` — uma pergunta respondida pela IA.

## Segurança

- `.env` fica no `.gitignore`; só o `.env.example` é versionado.
- Nenhuma credencial, cadastro real ou dado sensível no repositório.
