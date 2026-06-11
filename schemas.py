from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union, Dict, Any
from datetime import datetime

# ==========================================
# 1. SCHEMAS DE PARTIDAS E ESTATÍSTICAS
# ==========================================
class PartidaSchema(BaseModel):
    id: Optional[int] = None
    campeonato: str = Field(..., examples=["Campeonato Brasileiro Série A"])
    rodada: Optional[str] = Field(default=None)
    data_partida: Optional[str] = Field(default=None)
    mandante: str = Field(...)
    visitante: str = Field(...)
    gols_mandante: Optional[int] = Field(default=None)
    gols_visitante: Optional[int] = Field(default=None)
    status: str = Field(...)
    model_config = ConfigDict(from_attributes=True)

class EstatisticasVascoSchema(BaseModel):
    jogos_disputados: int = Field(default=0)
    pontos: int = Field(default=0)
    vitorias: int = Field(default=0)
    empates: int = Field(default=0)
    derrotas: int = Field(default=0)
    gols_marcados: int = Field(default=0)
    gols_sofridos: int = Field(default=0)
    saldo_gols: int = Field(default=0)
    aproveitamento: float = Field(default=0.0)
    model_config = ConfigDict(from_attributes=True)

class EstatisticaAgregadaSchema(BaseModel):
    jogador: str
    jogos_disputados: int
    gols: int
    assistencias: int
    chutes: int
    chutes_no_gol: int
    faltas_cometidas: int
    faltas_sofridas: int
    cartoes_amarelos: int
    cartoes_vermelhos: int
    salvamentos: int
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 2. SCHEMAS DE ENVELOPE (Respostas da API)
# ==========================================
class MetaDados(BaseModel):
    fonte: str = Field(..., examples=["Sofascore API", "Banco de Dados Relacional"])
    ultima_atualizacao: datetime = Field(default_factory=datetime.now)
    tempo_processamento_ms: float = Field(default=0.0)

class RespostaListaPartidas(BaseModel):
    status_api: str = Field(default="sucesso")
    meta: MetaDados
    dados: List[PartidaSchema]

class RespostaEstatisticas(BaseModel):
    status_api: str = Field(default="sucesso")
    competicao: str = Field(default="Geral")
    meta: MetaDados
    dados: Union[EstatisticasVascoSchema, Dict[str, Any]]

class RespostaEstatisticasElenco(BaseModel):
    status_api: str = Field(default="sucesso")
    meta: MetaDados
    dados: List[EstatisticaAgregadaSchema]