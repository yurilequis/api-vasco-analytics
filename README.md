# ⚽ Vasco Analytics API

Uma API RESTful de alta performance construída em Python com FastAPI para extração, processamento e análise de dados desportivos em tempo real. Desenvolvido inicialmente como um motor estatístico focado no Vasco da Gama, o projeto evoluiu para abranger todas as equipas do Campeonato Brasileiro (Série A).

Este projeto tem um foco vincado em modelação de bases de dados relacionais, engenharia reversa de APIs públicas e arquitetura de software resiliente.

---

## 🚀 Funcionalidades

A API atua como um *Gateway* e motor de engenharia de dados, oferecendo respostas na casa dos milissegundos graças ao uso inteligente de cache numa base de dados local.

* **🏆 Tabela do Brasileirão:** Consumo em tempo real da tabela de classificação, calculando dinamicamente as zonas de qualificação (Libertadores, Sul-Americana, Despromoção).
* **🔥 Forma Recente (Guia de Forma):** Cálculo do termómetro de desempenho (V-E-D) dos últimos 5 jogos de qualquer equipa do campeonato, com ordenação cronológica inteligente.
* **⚔️ Confronto Direto (Head-to-Head):** Motor matemático que analisa o histórico entre dois clubes fornecidos, calculando vitórias, empates e saldo de golos agregado.
* **📅 Próximo Jogo:** Identificação instantânea do compromisso futuro mais próximo de qualquer equipa na linha do tempo.
* **🚜 Povoamento em Lote (Upsert):** Rota administrativa inteligente capaz de varrer a agenda de 20 clubes na ESPN, aplicando estratégias de contenção (*fallback routing* e pausas contra *rate limits*) para popular a base de dados sem duplicar registos.

---

## 📂 Estrutura do Projeto

A arquitetura foi dividida seguindo o padrão de separação de responsabilidades (*Separation of Concerns*):

```text
api-vasco-analytics/
│
├── api/                    # Lógica adicional e organização de rotas (Endpoints)
├── database/               # Ficheiros e configurações da base de dados
├── scrapers/               # Motor de extração, limpeza e padronização dos dados
│   └── cbf_scraper.py      # Lógica de consumo da ESPN API
├── main.py                 # Ponto de entrada da aplicação e definição de rotas principais
├── models.py               # Modelação Entidade-Relacionamento (MER) do SQLAlchemy (Tabelas)
├── schemas.py              # Moldes do Pydantic para validação e tipagem dos JSONs
├── database.py             # Configuração da ligação à base de dados SQLite local
├── utils.py                # Funções utilitárias e auxiliares
├── requirements.txt        # Lista de dependências do projeto
├── SETUP.md                # Instruções secundárias de configuração
└── README.md               # Documentação principal
💻 Pré-requisitos
Antes de começares, certifica-te de que tens instalado na tua máquina:

Python 3.8 ou superior.

Gestor de pacotes pip.

🛠️ Instalação e Configuração
Segue os passos abaixo para configurares o ambiente de desenvolvimento na tua máquina local:

1. Clonar o repositório

Bash
git clone [https://github.com/yurilequis/api-vasco-analytics.git](https://github.com/yurilequis/api-vasco-analytics.git)
cd api-vasco-analytics
2. Criar o Ambiente Virtual (venv)
Isto garante que as dependências do projeto não entram em conflito com o teu sistema operativo.

Windows:

Bash
python -m venv venv
Linux/Mac:

Bash
python3 -m venv venv
3. Ativar o Ambiente Virtual

Windows:

Bash
venv\Scripts\activate
Linux/Mac:

Bash
source venv/bin/activate
4. Instalar as Dependências

Bash
pip install -r requirements.txt
⚙️ Execução
Com o ambiente virtual ativado e as dependências instaladas, inicia o servidor local do Uvicorn:

Bash
uvicorn main:app --reload
A API estará a correr localmente no porto 8000.

Aceder à Documentação Interativa (Swagger UI): Abre o teu navegador e acede a http://127.0.0.1:8000/docs.

📖 Como Usar (Guia Rápido)
Ao iniciares o projeto pela primeira vez, a tua base de dados local (SQLite) estará vazia. Para testares o poder da API, segue esta ordem na documentação do Swagger:

Popular a Base de Dados: Executa a rota POST /api/admin/popular-brasileirao. O sistema irá iterar pelos 20 clubes da Série A e fará a extração do calendário completo para a tua base de dados local de forma inteligente. Aguarda cerca de 1 minuto.

Consumir as Estatísticas: Com a base de dados alimentada, podes testar as rotas de leitura (GET), como /api/v1/vasco/forma-recente ou /api/v1/vasco/confronto, passando o nome das equipas pretendidas como parâmetros no pedido.

🛠 Tecnologias Utilizadas
FastAPI: Framework web moderno e ultrarrápido para a construção de APIs.

SQLAlchemy: Ferramenta SQL e Mapeador Objeto-Relacional (ORM) para Python.

SQLite: Base de dados relacional leve e embutida, ideal para persistência local rápida.

Requests: Biblioteca elegante e simples para pedidos HTTP em Python.

Uvicorn: Servidor web ASGI para correr aplicações assíncronas.
