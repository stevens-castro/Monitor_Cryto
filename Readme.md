### **Projeto:** Plataforma de Inteligência de Mercado para Cryto Moedas 

### **Objetivo Criar um monitor de variação de preço para cryto moedas que utilize banco de dados NoSQL.**

    - A solução utiliza a api da plataforma Binance para coletar das variações de preço em tempo real.
    - A solução está dividida em 3 blocos de código
        * Bloco 1 --> Testes de conexão com os banco de dados (Redis, Mongodb, Cassandra, Neo4j) com tratamento de exceção para capturar possíveis erros de conexão.
        * Bloco 2 --> Setup Inical dos bancos onde são criadas as tabelas, keyspace. 
        * Bloco 3 --> Loop que conecta na api da Binance retornado os valores das cryto moedas e salvando nos bancos de dados.

### **Escalabilidade**
    O sistema é altamente escalável orquestrando **quatro bancos de dados NoSQL** simultaneamente:

    1.Entregar a cotação atual com **baixíssima latência** para o site (Uso do **Redis**).

    2.Armazenar o **log bruto (Data Lake)** para auditorias futuras (Uso do **MongoDB**).

    3.Armazenar a **série temporal de preços** otimizada para gráficos (Uso do **Cassandra | ScyllaDB**).

    4.Mapear a **rede de investidores** para o sistema de alertas (Uso do **Neo4j**).

### ** Requisitos**
    * Python 3.10.8
    * Conteiner Docker 4.60+
    * Linux ou Windows 11+

|**Tecnologias**| Python, Redis, MongoDB, (Cassandra ou ScyllaDB ), Neo4j, Docker |

###  **Execução**
OBS:No caso do seu sistema operacional for windows, ao instalar as bibliotecas python para os banco Scylla ou Cassandra devemos instalar os drivers
para ignorar as bibliotecas C, pois no windows não temos suportes para drivers que compliam em C.

    * Para Scylladb = pip install scylla-driver --no-binary scylla-driver**

    * Para Cassandra = pip install cassandra-driver --no-binary cassandra-driver**

OBS: Tente não instalar as bibliotecas do Scylla e cassadra no juntas no mesmo ambiete. POde gerar conflito pois as duas usam o mesmo namespace.

### **Executando o monitor de cryto moeda**
  * 1 - Abra o aplicativo do docker no seu windows
        * Inicialize o container criado para os banco de dados
  * 2 - Abra o console do windwos (cmd) e digite o comando: "python monitor_variacao.py"
  * 3 - No console serão exibidas as informações a cada 5s do valor de variação das moedas Bitcoin e Etheriun 
  * 4 - Para encerrar o monitor basta pressionar ctrl + c no terminal.
