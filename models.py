from sqlalchemy import Column, Integer, String, DateTime, Boolean
from database import Base
import datetime

class Partida(Base):
    __tablename__ = "partidas"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, unique=True, index=True, nullable=True) # 🔥 NOVO: Para ligar com os gols
    campeonato = Column(String)
    mandante = Column(String)
    visitante = Column(String)
    gols_mandante = Column(Integer, nullable=True)
    gols_visitante = Column(Integer, nullable=True)
    status = Column(String)
    data_partida = Column(String, nullable=True)
    rodada = Column(String, nullable=True)

class Gol(Base):
    __tablename__ = "gols"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, index=True) # ID do jogo na ESPN
    jogador_nome = Column(String, index=True)
    minuto = Column(String, nullable=True)
    time_goleador = Column(String) # "Vasco" ou o nome do adversário

class ControleCache(Base):
    __tablename__ = "controle_cache"
    endpoint = Column(String, primary_key=True, index=True)
    ultima_atualizacao = Column(DateTime, default=datetime.datetime.now)

class Jogador(Base):
    __tablename__ = "jogadores"
    
    id = Column(Integer, primary_key=True, index=True)
    atleta_id = Column(String, unique=True, index=True) # ID único da ESPN
    nome = Column(String)
    posicao = Column(String, nullable=True)
    camisa = Column(String, nullable=True)
    idade = Column(Integer, nullable=True)

class EstatisticaAtletaPartida(Base):
    __tablename__ = "estatisticas_atleta_partida"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, index=True) # Relacionamento com a Partida
    jogador_nome = Column(String, index=True) # Relacionamento com o Elenco
    
    # Estatísticas Individuais (nem sempre a ESPN manda todas, por isso nullable=True)
    minutos_jogados = Column(String, nullable=True)
    gols = Column(Integer, default=0)
    assistencias = Column(Integer, default=0)
    chutes = Column(Integer, default=0)
    chutes_no_gol = Column(Integer, default=0)
    faltas_cometidas = Column(Integer, default=0)
    faltas_sofridas = Column(Integer, default=0)
    cartao_amarelo = Column(Integer, default=0)
    cartao_vermelho = Column(Integer, default=0)
    salvamentos = Column(Integer, default=0) # Para os goleiros