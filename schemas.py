from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union, Dict, Any
from datetime import datetime

# ==========================================
# 1. SCHEMAS BASE (Entidades Isoladas)
# ==========================================

class TimeSchema(BaseModel):
    id: Optional[int] = Field(default=None, description="ID interno da API")
    nome_popular: str = Field(..., examples=["Vasco"])
    nome_oficial: Optional[str] = Field(default=None, examples=["Club de Regatas Vasco da Gama"])
    slug: str = Field(..., examples=["vasco-da-gama"])

    model_config = ConfigDict(from_attributes=True)


class JogadorSimplesSchema(BaseModel):
    """Schema alternativo para listagens simples de jogadores com gols na temporada"""
    id: Optional[int] = None
    nome_popular: str = Field(..., examples=["Vegetti"])
    posicao: str = Field(..., examples=["Atacante", "Goleiro"])
    gols_temporada: int = Field(default=0, description="Total de gols no ano atual")
    time_atual: Optional[str] = Field(default="Vasco", description="Nome do clube atual")

    model_config = ConfigDict(from_attributes=True)


class JogadorSchema(BaseModel):
    """Schema oficial do Elenco estruturado com os dados da ESPN"""
    atleta_id: str = Field(..., description="ID único do atleta na ESPN")
    nome: str
    posicao: str = Field(default="Não informada")
    camisa: str = Field(default="S/N")
    idade: Optional[int] = Field(default=None)
    
    model_config = ConfigDict(from_attributes=True)


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


# ==========================================
# 2. SCHEMAS DE DETALHE E ESTATÍSTICAS
# ==========================================

class EstatisticasVascoSchema(BaseModel):
    jogos_disputados: int = Field(default=0, description="Total de partidas encerradas")
    pontos: int = Field(default=0, description="3 pts por vitória, 1 por empate")
    vitorias: int = Field(default=0)
    empates: int = Field(default=0)
    derrotas: int = Field(default=0)
    gols_marcados: int = Field(default=0)
    gols_sofridos: int = Field(default=0)
    saldo_gols: int = Field(default=0)
    aproveitamento: float = Field(default=0.0, description="Percentual de pontos ganhos")
    
    model_config = ConfigDict(from_attributes=True)


class EstatisticasCariocaDetalhado(BaseModel):
    """Molde específico para a divisão detalhada do Campeonato Carioca"""
    fase_de_grupos: EstatisticasVascoSchema
    playoffs: EstatisticasVascoSchema
    total_geral: EstatisticasVascoSchema


class ArtilheiroSchema(BaseModel):
    jogador: str
    gols: int
    posicao: str = Field(default="Não informada")

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


class PosicaoTabelaSchema(BaseModel):
    posicao: int
    Equipe: str
    Pts: int
    PJ: int
    VIT: int
    E: int
    DER: int
    GP: int
    GC: int
    SG: int
    zona_classificacao: Optional[str] = None


class JogoFormaSchema(BaseModel):
    data_partida: str
    campeonato: str
    mandante: str
    visitante: str
    gols_mandante: int
    gols_visitante: int
    resultado_alvo: str


class PartidaConfrontoSchema(BaseModel):
    data_partida: str
    campeonato: str
    mandante: str
    visitante: str
    gols_mandante: int
    gols_visitante: int


class ResumoConfrontoSchema(BaseModel):
    jogos_disputados: int
    vitorias_time_a: int
    vitorias_time_b: int
    empates: int
    gols_time_a: int
    gols_time_b: int


class ProximoJogoSchema(BaseModel):
    campeonato: str
    mandante: str
    visitante: str
    data_partida: str
    rodada: Optional[str] = None


# ==========================================
# 3. SCHEMAS DE ENVELOPE (A Resposta Final)
# ==========================================

class MetaDados(BaseModel):
    fonte: str = Field(..., examples=["ESPN API", "Banco de Dados Relacional"])
    ultima_atualizacao: datetime = Field(default_factory=datetime.now)
    tempo_processamento_ms: float = Field(default=0.0)


class RespostaListaPartidas(BaseModel):
    status_api: str = Field(default="sucesso", examples=["sucesso", "erro", "cache"])
    meta: MetaDados
    dados: List[PartidaSchema]


class RespostaListaJogadores(BaseModel):
    status_api: str = Field(default="sucesso")
    meta: MetaDados
    dados: List[JogadorSimplesSchema]


class RespostaEstatisticas(BaseModel):
    status_api: str = Field(default="sucesso")
    competicao: str = Field(default="Geral (Todas as competições)")
    meta: MetaDados
    dados: Union[EstatisticasVascoSchema, EstatisticasCariocaDetalhado, Dict[str, Any]]


class RespostaElenco(BaseModel):
    status_api: str = Field(default="sucesso")
    meta: MetaDados
    dados: List[JogadorSchema]


class RespostaArtilharia(BaseModel):
    status_api: str = Field(default="sucesso")
    meta: MetaDados
    dados: List[ArtilheiroSchema]


class RespostaEstatisticasElenco(BaseModel):
    status_api: str = Field(default="sucesso")
    meta: MetaDados
    dados: List[EstatisticaAgregadaSchema]


class RespostaTabela(BaseModel):
    status_api: str = Field(default="sucesso")
    campeonato: str = Field(default="Campeonato Brasileiro (Série A)")
    meta: MetaDados
    dados: List[PosicaoTabelaSchema]


class RespostaFormaRecente(BaseModel):
    status_api: str = Field(default="sucesso")
    meta: MetaDados
    forma_array: List[str] = Field(description="Ex: ['D', 'V', 'E', 'V', 'V']")
    ultimos_jogos: List[JogoFormaSchema]


class RespostaConfrontoDireto(BaseModel):
    status_api: str = Field(default="sucesso")
    meta: MetaDados
    time_a: str
    time_b: str
    resumo: ResumoConfrontoSchema
    historico: List[PartidaConfrontoSchema]


class RespostaProximoJogo(BaseModel):
    status_api: str = Field(default="sucesso")
    meta: MetaDados
    dados: Optional[ProximoJogoSchema] = Field(default=None, description="Retorna null se a temporada do time já tiver acabado")