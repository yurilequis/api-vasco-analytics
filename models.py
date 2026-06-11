from sqlalchemy import Column, Integer, String, DateTime
from database import Base
import datetime

class Partida(Base):
    __tablename__ = "partidas"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, unique=True, index=True, nullable=True) # ID da Partida no Sofascore
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
    game_id = Column(String, index=True) # Relacionamento com a Partida
    jogador_nome = Column(String, index=True)
    minuto = Column(String, nullable=True)
    time_goleador = Column(String)

class ControleCache(Base):
    __tablename__ = "controle_cache"
    endpoint = Column(String, primary_key=True, index=True)
    ultima_atualizacao = Column(DateTime, default=datetime.datetime.now)

class EstatisticaAtletaPartida(Base):
    __tablename__ = "estatisticas_atleta_partida"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, index=True) # Relacionamento com a Partida
    jogador_nome = Column(String, index=True) 
    
    # Estatísticas do Sofascore
    minutos_jogados = Column(String, nullable=True)
    gols = Column(Integer, default=0)
    assistencias = Column(Integer, default=0)
    chutes = Column(Integer, default=0)
    chutes_no_gol = Column(Integer, default=0)
    faltas_cometidas = Column(Integer, default=0)
    faltas_sofridas = Column(Integer, default=0)
    cartao_amarelo = Column(Integer, default=0)
    cartao_vermelho = Column(Integer, default=0)
    salvamentos = Column(Integer, default=0)