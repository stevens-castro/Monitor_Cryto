# Desafio Final: A Plataforma de Inteligência de Mercado (Ecossistema NoSQL)

| **Disciplina** | Banco de Dados NoSQL |
| :--- | :--- |
| **Tecnologias** | Python, Redis, MongoDB, (Cassandra ou ScyllaDB ), Neo4j, Docker |
| **Conceito** | Persistência Poliglota (O banco certo para o problema certo) |

---

## O Objetivo
Você foi contratado por uma Fintech para desenvolver o backend de uma **Plataforma de Inteligência de Mercado em Tempo Real**. O sistema precisa ler cotações financeiras, armazená-las de diferentes formas para diferentes propósitos e gerir os investidores interessados.

Para que o sistema seja altamente escalável, você deverá orquestrar **quatro bancos de dados NoSQL** simultaneamente:

1.  Entregar a cotação atual com **baixíssima latência** para o site (Uso do **Redis**).
2.  Armazenar o **log bruto (Data Lake)** para auditorias futuras (Uso do **MongoDB**).
3.  Armazenar a **série temporal de preços** otimizada para gráficos (Uso do **Cassandra | ScyllaDB**).
4.  Mapear a **rede de investidores** para o sistema de alertas (Uso do **Neo4j**).

---

## A Arquitetura do Sistema

Seu script Python deve seguir rigorosamente este fluxo lógico a cada ciclo para economizar recursos e garantir performance:

1.  **Verificação de Cache (Redis):** Antes de ir à internet, verifique se a cotação já está salva no Redis.
    * *Cache Hit:* Se estiver no Redis e dentro da validade (TTL), exiba o valor recuperado de lá.
    * *Cache Miss:* Se não estiver (ou expirou), faça a requisição `GET` na API escolhida e atualize o Redis com o novo valor e um TTL adequado.
2.  **Data Lake (MongoDB):** Salve o documento JSON bruto retornado pela API contendo: `Moeda`, `Valor`, `Variação` e adicione o campo `data_coleta` com o timestamp atual (`datetime.now()`).
3.  **Série Temporal (Cassandra || ScyllaDB):** Insira uma linha na tabela `historico_precos`. A tabela deve ser modelada para buscas rápidas por moeda e ordenadas por data/hora decrescente.
4.  **Sistema de Alertas (Neo4j):** No Grafo, devem existir previamente nós `:Investidor` ligados às `:Moedas`. A cada atualização de preço, faça uma consulta Cypher para descobrir: *"Quais investidores acompanham esta moeda e devem ser notificados?"* e imprima os nomes no terminal.

---

## Dicas de Implementação e Lógica

Para o **Neo4j**, não é necessário criar um sistema complexo de cadastro de utilizadores. O foco é a orquestração e a modelagem. Divida a sua lógica em duas fases no seu script Python:

* **Fase 1: Setup Inicial (Fora do Loop Principal)**
  Crie uma lista estática (array) no Python com alguns nomes fictícios (ex: *Alice, Bob, Carlos*). Antes do seu `while True` começar, envie uma query ao Neo4j iterando sobre essa lista para garantir que esses nós `:Investidor` sejam criados e que todos tenham um relacionamento `[:ACOMPANHA]` apontando para o nó da `:Moeda` que você escolheu monitorar.
* **Fase 2: O Monitoramento (Dentro do Loop Principal)**
  Quando o script for à API (ou ao Redis) buscar o preço novo, o preço em si **não** precisa ir para o Neo4j (ele já vai para o Cassandra e Mongo). Dentro do loop, o seu script deve apenas fazer um `MATCH` no grafo perguntando: *"Quem são os investidores que têm uma seta apontando para a moeda X?"*. Recupere esses nomes e simule um alerta imprimindo-os no terminal.

---

## Escolha o seu Caminho

Você deve escolher **uma** das duas APIs abaixo para realizar o trabalho. Ambas são públicas, gratuitas e não requerem autenticação.

### Opção A: Mercado Tradicional (Dólar & Euro)
*Ideal para quem quer simular um sistema bancário ou casa de câmbio.*

* **API:** AwesomeAPI (Economia)
* **Comportamento:** As cotações variam a cada 30 segundos ou mais. Fora do horário comercial e finais de semana, os valores **não mudam**.
* **Endpoint:** `https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL`
* **TTL Recomendado no Redis:** 30 a 60 segundos.

**Exemplo de Retorno JSON:**
```json
{
  "USDBRL": {
    "code": "USD",
    "bid": "5.1543",
    "create_date": "2023-10-24 15:00:00"
  }
}
```

### Opção B: Mercado Cripto (Bitcoin & Ethereum)
*Ideal para quem quer ver volatilidade, gráficos mudando rápido e "telas piscando".*

* **API:** Binance Public Data
* **Comportamento**: O mercado nunca fecha (24/7). Os preços mudam na casa dos milissegundos.
* **Endpoints:**
  * Bitcoin: `https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT`
  * Ethereum: `https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT`
* **TTL Recomendado no Redis:** 5 a 10 segundos.

**Exemplo de Retorno JSON:**
```json
{
  "symbol": "BTCUSDT",
  "price": "34500.12000000"
}
```

---

## Requisitos Técnicos do Código

Seu script `monitor.py` deve conter obrigatoriamente:

* **Setup Inicial Automático:** O script deve tentar criar o Keyspace/Tabela no Cassandra e os Nós/Relacionamentos iniciais no Neo4j caso ainda não existam.
* **Conexão Robusta:** Tratamento de erro (`try/except`) caso algum container do Docker (Redis, Mongo, Cassandra ou Neo4j) não esteja rodando.
* **Loop de Monitoramento:** O script deve rodar continuamente (ex: `while True`) verificando os preços a cada X segundos.
* **Log Visual Completo:** O terminal deve deixar claro a ação em cada banco. Exemplo:

> Consultando preço do Bitcoin (BTCUSDT)...
> [REDIS] Cache Miss! Fui na API da Binance.
> [MONGO] Payload bruto salvo no Data Lake.
> [CASSANDRA] Preço de $34,500.00 gravado na série temporal.
> [NEO4J] Notificando investidores: João, Ana e Carlos.

---

## Formato de Entrega e Prazo

O trabalho deverá ser hospedado no **GitHub** contendo rigorosamente os seguintes arquivos no repositório:

1. **`monitor.py`**: O código-fonte principal em Python devidamente comentado.
2. **`docker-compose.yml`**: O arquivo de configuração do Docker utilizado para subir os quatro bancos de dados simultaneamente.
3. **`requirements.txt`**: Um arquivo listando todas as bibliotecas externas do Python necessárias (ex: `redis`, `pymongo`, `cassandra-driver`, `neo4j`, `requests`).

**Instruções de Envio:**
* **E-mail:** Envie para `juliocartier@gmail.com`
* **Assunto do E-mail:** `Trabalho Final NoSQL - [Seu Nome Completo]`
* **Corpo do E-mail:** Deve conter obrigatoriamente o seu **Nome Completo** e o **Link público do repositório no GitHub**.
* **Data Limite de Entrega:** **06 de Março**

**Regra de Ouro (Atenção):** O projeto precisa estar **executando**. Projetos que não subirem pelo `docker-compose up` ou que o script Python quebrar imediatamente por erros de sintaxe sofrerão penalidades severas. Teste seu código antes de enviar!

---

## Critérios de Avaliação (Nota: 0 a 10)

A avaliação será técnica e baseada no funcionamento prático da arquitetura proposta:

* **(2,0 pts) Execução e Orquestração:** O `docker-compose.yml` subiu os 4 bancos corretamente. O Python roda em loop sem quebrar
* **(2,0 pts) Implementação Redis:** A lógica de *Cache Hit* e *Cache Miss* foi implementada respeitando o TTL.
* **(2,0 pts) Implementação Cassandra || ScyllaDB:** A tabela de série temporal possui Partition Key e Clustering Key adequadas.
* **(1,5 pts) Implementação Neo4j:** Os nós de Investidor/Moeda foram criados e a query Cypher identifica quem acompanha a moeda.
* **(1,5 pts) Implementação MongoDB:** O payload da API foi salvo com sucesso com o timestamp (`data_coleta`).
* **(1,0 pt) Qualidade e Logs:** O código possui `try/except` e os logs no terminal refletem as ações nos quatro bancos.

---

### Desafio Extra (Bônus para os fortes)
Implemente uma **lógica visual de volatilidade** e de última atualização. Compare o preço novo retornado pela API com o último preço que estava no Redis antes de sobrescrever, e adicione uma seta indicativa no terminal:

* Bitcoin: $ 34,500.00 🟢 (Subiu)
* Bitcoin: $ 34,490.00 🔴 (Caiu)

*(Dica: Ao atualizar o preço, use também o Neo4j para gravar uma propriedade `ultima_notificacao` com o horário de agora dentro da seta `[:ACOMPANHA]` do investidor!)*