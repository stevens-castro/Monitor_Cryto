import time
import requests
from datetime import datetime

# Importações dos drivers NoSQL
import redis
from pymongo import MongoClient
from neo4j import GraphDatabase

#Importando drivers para o Scylladb, mais rápido que o Cassandra
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import RoundRobinPolicy, TokenAwarePolicy
from cassandra.auth import PlainTextAuthProvider

import dotenv 
import os


# ============================================================================
# CONFIGURAÇÕES GERAIS E CONSTANTES
# ============================================================================
# Carrega e lê variáveis de ambiente do arquivo .env
dotenv.load_dotenv()
mongouser = os.environ['MONGODB_USER']
mongopass = os.environ['MONGODB_PASS']


# Lista com múltiplas moedas (Bitcoin e Ethereum)
SYMBOLS = ["BTCUSDT", "ETHUSDT"] 
REDIS_TTL = 5  # Segundos recomendados para o mercado cripto volátil
LOOP_INTERVAL = 5 # Tempo de espera entre cada ciclo completo

# Dicionário para armazenar o último preço de CADA moeda separadamente
last_price_memory = {
    "BTCUSDT": None,
    "ETHUSDT": None
}



# ============================================================================
# CONEXÕES COM OS BANCOS DE DADOS (Testes Com tratamento de erros )
# ============================================================================
print("Iniciando conexões com os bancos de dados...")

# Check de conexao com banco Redis
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
    print("[OK] Redis conectado.")
except Exception as e:
    print(f"[ERRO] Falha ao conectar no Redis: {e}")
    exit(1)

# Check de conexao com banco Mongodb
try:
    mongo_client = MongoClient('mongodb://localhost:27017/', username=mongouser, password=mongopass) # username='admin', password='password'
    mongo_db = mongo_client['crypto_datalake']
    mongo_collection = mongo_db['raw_logs']
    mongo_client.server_info() 
    print("[OK] MongoDB conectado.")
except Exception as e:
    print(f"[ERRO] Falha ao conectar no MongoDB: {e}")
    exit(1)

# Check de conexao com banco Scylladb
try:
    # Definindo um perfil de execução para otimizar o ScyllaDB
    profile = ExecutionProfile(
        load_balancing_policy=TokenAwarePolicy(RoundRobinPolicy()),        
        request_timeout=15 # ScyllaDB é rápido, mas para evitar erro de conexão no setup inicial aumentamos o tempo de
    )

    scylla_cluster = Cluster(
        ['localhost'], 
        protocol_version=4,
        port=9042, 
        address_translator="127.0.0.1",   # Parâmetro para traduzir o endereço ip interno do docker utilizado pelo Scylla para localhost
        execution_profiles={EXEC_PROFILE_DEFAULT: profile}
    )
    
    scylla_session = scylla_cluster.connect()
    print("[OK] ScyllaDB conectado e otimizado (Shard-Aware).")
except Exception as e:
    print(f"[ERRO] Falha ao conectar no ScyllaDB: {e}")
    exit(1)

# Conectando com Neo4j
try:
    neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "aluno123"))
    neo4j_driver.verify_connectivity()
    print("[OK] Neo4j conectado.")
except Exception as e:
    print(f"[ERRO] Falha ao conectar no Neo4j: {e}")
    exit(1)

# ============================================================================
# FASE 1: SETUP INICIAL AUTOMÁTICO
# ============================================================================
print("\nIniciando Setup Automático dos Bancos...")

# --- Setup Scyllabd ---
try:
    scylla_session.execute("""
        CREATE KEYSPACE IF NOT EXISTS market_data 
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
    """)
    scylla_session.set_keyspace('market_data')
    
    scylla_session.execute("""
        CREATE TABLE IF NOT EXISTS historico_precos (
            simbolo text,
            data_hora timestamp,
            preco double,
            PRIMARY KEY (simbolo, data_hora)
        ) WITH CLUSTERING ORDER BY (data_hora DESC)
    """)
    print("[SETUP] Cassandra configurado com sucesso.")
except Exception as e:
    print(f"[ERRO SETUP] Falha ao configurar Cassandra: {e}")

# --- Setup Neo4j ---
def setup_neo4j(tx):
    # Dicionário mapeando quais investidores acompanham quais moedas
    carteiras = {
        "BTCUSDT": ["João", "Ana"],
        "ETHUSDT": ["Carlos", "Maria"]
    }
    
    for symbol, investidores in carteiras.items():
        # Cria a moeda no grafo
        tx.run("MERGE (m:Moeda {nome: $symbol})", symbol=symbol)
        
        # Cria os investidores e o relacionamento específico
        for inv in investidores:
            tx.run("""
                MERGE (i:Investidor {nome: $nome})
                WITH i
                MATCH (m:Moeda {nome: $symbol})
                MERGE (i)-[r:ACOMPANHA]->(m)
            """, nome=inv, symbol=symbol)

try:
    with neo4j_driver.session() as session:
        session.execute_write(setup_neo4j)
    print("[SETUP] Neo4j configurado. Carteiras de BTC e ETH separadas.\n")
except Exception as e:
    print(f"[ERRO SETUP] Falha ao configurar Neo4j: {e}")


# ============================================================================
# FASE 2: LOOP DE MONITORAMENTO MULTI-MOEDA
# ============================================================================
print("="*60)
print("INICIANDO PLATAFORMA DE INTELIGÊNCIA DE MERCADO (MULTI-ASSET)")
print("="*60)

while True:
    try:
        agora = datetime.now()
        
        # Iteramos sobre a lista de moedas configurada
        for symbol in SYMBOLS:
            print(f"\n--- Analisando {symbol} ---")
            api_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            
            # 1. VERIFICAÇÃO DE CACHE (REDIS)
            cached_price = redis_client.get(symbol)
            
            if cached_price:
                print(f"[REDIS] Cache Hit! Preço atual: $ {float(cached_price):,.2f}")
            else:
                print("[REDIS] Cache Miss! Fui na API da Binance.")
                
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    current_price = float(data['price'])
                    
                    # LÓGICA DE VARIAÇÃO DAS MOEDAS ("BTCUSDT" e "ETHUSDT")
                    indicador_visual = ""
                    last_price = last_price_memory[symbol]
                    
                    if last_price is not None:
                        if current_price > last_price:
                            indicador_visual = " 🟢 (Subiu)"
                        elif current_price < last_price:
                            indicador_visual = " 🔴 (Caiu)"
                        else:
                            indicador_visual = " ⚪ (Estável)"
                    
                    # Atualiza a memória para a próxima iteração
                    last_price_memory[symbol] = current_price
                    
                    # Salva no Redis
                    redis_client.setex(symbol, REDIS_TTL, str(current_price))
                    
                    nome_exibicao = "Bitcoin" if symbol == "BTCUSDT" else "Ethereum"
                    print(f"{nome_exibicao}: $ {current_price:,.2f}{indicador_visual}")

                    # 2. DATA LAKE (MONGODB)
                    payload_mongo = data.copy()
                    payload_mongo['data_coleta'] = agora
                    mongo_collection.insert_one(payload_mongo)
                    print("[MONGO] Payload bruto salvo no Data Lake.")
                    
                    # 3. SÉRIE TEMPORAL (Scylla)
                    scylla_session.execute(
                        """
                        INSERT INTO historico_precos (simbolo, data_hora, preco) 
                        VALUES (%s, %s, %s)
                        """,
                        (symbol, agora, current_price)
                    )
                    print(f"[SCYLLADB] Preço gravado na série temporal.")
                    
                    # 4. SISTEMA DE ALERTAS (NEO4J)
                    def notificar_investidores(tx, moeda_alvo, horario):
                        query = """
                            MATCH (i:Investidor)-[r:ACOMPANHA]->(m:Moeda {nome: $moeda_alvo})
                            SET r.ultima_notificacao = $horario
                            RETURN i.nome AS nome
                        """
                        result = tx.run(query, moeda_alvo=moeda_alvo, horario=str(horario))
                        return [record["nome"] for record in result]

                    with neo4j_driver.session() as session:
                        notificados = session.execute_write(notificar_investidores, symbol, agora)
                        if notificados:
                            nomes_formatados = ", ".join(notificados)
                            print(f"[NEO4J] Notificando investidores de {symbol}: {nomes_formatados}.")
                        else:
                            print(f"[NEO4J] Nenhum investidor acompanhando {symbol}.")
                        
                else:
                    print(f"[ERRO API] Código HTTP: {response.status_code} para {symbol}")

    except Exception as e:
         print(f"[ERRO GERAL] Ocorreu um erro no ciclo principal: {e}")

    # Pausa antes do próximo ciclo de verificação para as duas moedas
    print(f"\nAguardando {LOOP_INTERVAL} segundos para o próximo ciclo...")
    time.sleep(LOOP_INTERVAL)