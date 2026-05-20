from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Cria um arquivo local chamado vasco_analytics.db na pasta do projeto
SQLALCHEMY_DATABASE_URL = "sqlite:///./vasco_analytics.db"

# connect_args={"check_same_thread": False} é necessário apenas no SQLite para o FastAPI rodar liso
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependência que o FastAPI vai usar para abrir e fechar a conexão a cada requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()