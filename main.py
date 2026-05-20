from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import or_, func, and_
import time
from typing import Optional

# Importações dos seus arquivos
from database import engine, Base, get_db
import models
import schemas
from scrapers.cbf_scraper import CbfScraper, TIMES_SERIE_A

# Cria as tabelas no arquivo vasco_analytics.db assim que o código rodar
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Vasco Analytics Data API")
scraper = CbfScraper()

# Definimos que o cache dura 12 horas
TEMPO_CACHE_HORAS = 12


# ==========================================
# ROTAS PRINCIPAIS (PRODUÇÃO)
# ==========================================

@app.get("/api/v1/vasco/jogos", response_model=schemas.RespostaListaPartidas, tags=["Jogos"])
def listar_jogos_vasco(db: Session = Depends(get_db)):
    inicio = time.time()
    
    cache = db.query(models.ControleCache).filter(models.ControleCache.endpoint == "jogos_vasco").first()
    
    precisa_raspar = False
    if not cache:
        precisa_raspar = True
    else:
        tempo_passado = datetime.now() - cache.ultima_atualizacao
        if tempo_passado > timedelta(hours=TEMPO_CACHE_HORAS):
            precisa_raspar = True
            
    if precisa_raspar:
        print("Dados desatualizados ou vazios. Iniciando Web Scraping...")
        # 🔥 CORREÇÃO: Chamando o novo método dinâmico do scraper
        dados_brutos = scraper.puxar_jogos_time("3454")
        
        if len(dados_brutos) > 0:
            db.query(models.Partida).delete() 
            
            for jogo in dados_brutos:
                nova_partida = models.Partida(
                    game_id=jogo["game_id"],
                    campeonato=jogo.get("campeonato", "Temporada 2026"),
                    mandante=jogo["mandante"],
                    visitante=jogo["visitante"],
                    gols_mandante=jogo["gols_mandante"],
                    gols_visitante=jogo["gols_visitante"],
                    status=jogo["status"],
                    data_partida=jogo.get("data_partida"),
                    rodada=jogo.get("rodada"),
                )
                db.add(nova_partida)
            
            if not cache:
                cache = models.ControleCache(endpoint="jogos_vasco", ultima_atualizacao=datetime.now())
                db.add(cache)
            else:
                cache.ultima_atualizacao = datetime.now()
                
            db.commit()

    partidas_db = db.query(models.Partida).all()
    lista_schemas = []
    
    for p in partidas_db:
        lista_schemas.append(schemas.PartidaSchema(
            id=p.id,
            campeonato=p.campeonato,
            mandante=p.mandante,
            visitante=p.visitante,
            gols_mandante=p.gols_mandante,
            gols_visitante=p.gols_visitante,
            status=p.status,
            data_partida=p.data_partida,  
            rodada=p.rodada              
        ))
        
    tempo_execucao = round((time.time() - inicio) * 1000, 2)
    fonte_usada = "Banco de Dados (Cache)" if not precisa_raspar else "ESPN API"
    
    return schemas.RespostaListaPartidas(
        status_api="sucesso",
        meta=schemas.MetaDados(
            fonte=fonte_usada,
            ultima_atualizacao=cache.ultima_atualizacao if cache else datetime.now(),
            tempo_processamento_ms=tempo_execucao
        ),
        dados=lista_schemas
    )

@app.get("/api/v1/vasco/estatisticas", response_model=schemas.RespostaEstatisticas, tags=["Estatísticas"])
def listar_estatisticas_vasco(
    campeonato: Optional[str] = Query(None, description="Filtre pelo nome do campeonato (ex: Carioca, Brasileiro)"),
    db: Session = Depends(get_db)
):
    inicio = time.time()
    query_banco = db.query(models.Partida)
    nome_exibicao = "Geral (Todas as competições)" 
    
    if campeonato:
        termo = campeonato.lower().strip()
        if termo in ["brasileiro", "brasileirao", "brasileirão", "série a", "serie a"]:
            query_banco = query_banco.filter(models.Partida.campeonato.ilike("%Serie A%"))
            nome_exibicao = "Campeonato Brasileiro"
        elif termo in ["sulamericana", "sul-americana", "sudamericana"]:
            query_banco = query_banco.filter(
                (models.Partida.campeonato.ilike("%Sudamericana%")) |
                (models.Partida.campeonato.ilike("%Sulamericana%"))
            )
            nome_exibicao = "Copa Sul-Americana"
        elif termo in ["copa do brasil", "copa"]:
            query_banco = query_banco.filter(models.Partida.campeonato.ilike("%Copa do Brasil%"))
            nome_exibicao = "Copa do Brasil"
        else:
            query_banco = query_banco.filter(models.Partida.campeonato.ilike(f"%{campeonato}%"))
            nome_exibicao = campeonato.title()
            
        if termo == "carioca":
            nome_exibicao = "Campeonato Carioca"
            
    partidas_db = query_banco.all()

    if campeonato and campeonato.lower().strip() == "carioca":
        fases = {
            "fase_de_grupos": {"jogos": 0, "pontos": 0, "v": 0, "e": 0, "d": 0, "gp": 0, "gc": 0},
            "playoffs": {"jogos": 0, "pontos": 0, "v": 0, "e": 0, "d": 0, "gp": 0, "gc": 0},
            "total_geral": {"jogos": 0, "pontos": 0, "v": 0, "e": 0, "d": 0, "gp": 0, "gc": 0}
        }

        for p in partidas_db:
            if p.status != "Encerrado":
                continue
                
            vasco_mandante = "Vasco" in p.mandante
            gols_vasco = p.gols_mandante if vasco_mandante else p.gols_visitante
            gols_oponente = p.gols_visitante if vasco_mandante else p.gols_mandante
            
            if gols_vasco is not None and gols_oponente is not None:
                rodada_lower = p.rodada.lower() if p.rodada else ""
                
                if "semifinal" in rodada_lower or "final" in rodada_lower or "rodada" not in rodada_lower:
                    fase_atual = "playoffs"
                else:
                    fase_atual = "fase_de_grupos"

                for f in [fase_atual, "total_geral"]:
                    fases[f]["jogos"] += 1
                    fases[f]["gp"] += gols_vasco
                    fases[f]["gc"] += gols_oponente
                    
                    if gols_vasco > gols_oponente:
                        fases[f]["v"] += 1
                        if f == "fase_de_grupos": 
                            fases[f]["pontos"] += 3
                    elif gols_vasco == gols_oponente:
                        fases[f]["e"] += 1
                        if f == "fase_de_grupos":
                            fases[f]["pontos"] += 1
                    else:
                        fases[f]["d"] += 1

        dados_finais = {
            "fase_de_grupos": {
                "jogos_disputados": fases["fase_de_grupos"]["jogos"],
                "pontos": fases["fase_de_grupos"]["pontos"],
                "vitorias": fases["fase_de_grupos"]["v"],
                "empates": fases["fase_de_grupos"]["e"],
                "derrotas": fases["fase_de_grupos"]["d"],
                "gols_marcados": fases["fase_de_grupos"]["gp"],
                "gols_sofridos": fases["fase_de_grupos"]["gc"],
                "saldo_gols": fases["fase_de_grupos"]["gp"] - fases["fase_de_grupos"]["gc"],
                "aproveitamento": round((fases["fase_de_grupos"]["pontos"] / (fases["fase_de_grupos"]["jogos"] * 3)) * 100, 1) if fases["fase_de_grupos"]["jogos"] > 0 else 0.0
            },
            "playoffs": {
                "jogos_disputados": fases["playoffs"]["jogos"],
                "pontos": 0, 
                "vitorias": fases["playoffs"]["v"],
                "empates": fases["playoffs"]["e"],
                "derrotas": fases["playoffs"]["d"],
                "gols_marcados": fases["playoffs"]["gp"],
                "gols_sofridos": fases["playoffs"]["gc"],
                "saldo_gols": fases["playoffs"]["gp"] - fases["playoffs"]["gc"],
                "aproveitamento": round(((fases["playoffs"]["v"] * 3 + fases["playoffs"]["e"]) / (fases["playoffs"]["jogos"] * 3)) * 100, 1) if fases["playoffs"]["jogos"] > 0 else 0.0
            },
            "total_geral": {
                "jogos_disputados": fases["total_geral"]["jogos"],
                "pontos": fases["fase_de_grupos"]["pontos"], 
                "vitorias": fases["total_geral"]["v"],
                "empates": fases["total_geral"]["e"],
                "derrotas": fases["total_geral"]["d"],
                "gols_marcados": fases["total_geral"]["gp"],
                "gols_sofridos": fases["total_geral"]["gc"],
                "saldo_gols": fases["total_geral"]["gp"] - fases["total_geral"]["gc"],
                "aproveitamento": round(((fases["total_geral"]["v"] * 3 + fases["total_geral"]["e"]) / (fases["total_geral"]["jogos"] * 3)) * 100, 1) if fases["total_geral"]["jogos"] > 0 else 0.0
            }
        }
        fonte_meta = "Banco de Dados (Estatísticas Detalhadas do Carioca)"

    else:
        vitorias = 0
        empates = 0
        derrotas = 0
        gols_pro = 0
        gols_contra = 0
        jogos_validos_para_pontos = 0
        pontos = 0

        for p in partidas_db:
            if p.status != "Encerrado":
                continue
                
            vasco_mandante = "Vasco" in p.mandante
            gols_vasco = p.gols_mandante if vasco_mandante else p.gols_visitante
            gols_oponente = p.gols_visitante if vasco_mandante else p.gols_mandante
            
            if gols_vasco is not None and gols_oponente is not None:
                gols_pro += gols_vasco
                gols_contra += gols_oponente
                
                is_vitoria = gols_vasco > gols_oponente
                is_empate = gols_vasco == gols_oponente

                if is_vitoria:
                    vitorias += 1
                elif is_empate:
                    empates += 1
                else:
                    derrotas += 1

                acumula_pontos = True
                nome_camp = p.campeonato.lower() if p.campeonato else ""
                
                if "copa do brasil" in nome_camp or "copa" in nome_camp:
                    acumula_pontos = False

                if acumula_pontos:
                    jogos_validos_para_pontos += 1
                    if is_vitoria:
                        pontos += 3
                    elif is_empate:
                        pontos += 1

        jogos_totais = vitorias + empates + derrotas
        saldo_gols = gols_pro - gols_contra

        if not campeonato:
            pontos = 0
            pontos_virtuais = (vitorias * 3) + empates
            aproveitamento = round((pontos_virtuais / (jogos_totais * 3)) * 100, 1) if jogos_totais > 0 else 0.0
            fonte_meta = "Banco de Dados (Geral - Filtre por campeonato para ver pontos reais)"
        else:
            aproveitamento = round((pontos / (jogos_validos_para_pontos * 3)) * 100, 1) if jogos_validos_para_pontos > 0 else 0.0
            fonte_meta = "Banco de Dados (Filtro Dinâmico)"

        dados_finais = {
            "jogos_disputados": jogos_totais,
            "pontos": pontos,
            "vitorias": vitorias,
            "empates": empates,
            "derrotas": derrotas,
            "gols_marcados": gols_pro,
            "gols_sofridos": gols_contra,
            "saldo_gols": saldo_gols,
            "aproveitamento": aproveitamento
        }

    tempo_execucao = round((time.time() - inicio) * 1000, 2)
    
    # 🔥 CORREÇÃO: Duplicação do bloco de retorno foi removida
    return schemas.RespostaEstatisticas(
        status_api="sucesso",
        competicao=nome_exibicao,
        meta=schemas.MetaDados(
            fonte=fonte_meta,
            ultima_atualizacao=datetime.now(),
            tempo_processamento_ms=tempo_execucao
        ),
        dados=dados_finais
    )

@app.get("/api/v1/vasco/elenco", response_model=schemas.RespostaElenco, tags=["Elenco"])
def listar_elenco_vasco(db: Session = Depends(get_db)):
    inicio = time.time()
    
    cache = db.query(models.ControleCache).filter(models.ControleCache.endpoint == "elenco_vasco").first()
    
    precisa_raspar = False
    if not cache:
        precisa_raspar = True
    else:
        tempo_passado = datetime.now() - cache.ultima_atualizacao
        if tempo_passado > timedelta(hours=24):
            precisa_raspar = True
            
    if precisa_raspar:
        print("Dados do elenco desatualizados. Iniciando Web Scraping...")
        # 🔥 CORREÇÃO: Chamando o novo método dinâmico
        dados_elenco = scraper.puxar_elenco_time("3454")
        
        if len(dados_elenco) > 0:
            db.query(models.Jogador).delete() 
            
            for jog in dados_elenco:
                novo_jogador = models.Jogador(
                    atleta_id=jog["atleta_id"],
                    nome=jog["nome"],
                    posicao=jog["posicao"],
                    camisa=jog["camisa"],
                    idade=jog["idade"]
                )
                db.add(novo_jogador)
            
            if not cache:
                cache = models.ControleCache(endpoint="elenco_vasco", ultima_atualizacao=datetime.now())
                db.add(cache)
            else:
                cache.ultima_atualizacao = datetime.now()
                
            db.commit()

    jogadores_db = db.query(models.Jogador).all()
    lista_schemas = [schemas.JogadorSchema.model_validate(j) for j in jogadores_db]
        
    tempo_execucao = round((time.time() - inicio) * 1000, 2)
    fonte_usada = "Banco de Dados (Cache 24h)" if not precisa_raspar else "ESPN API"
    
    return schemas.RespostaElenco(
        status_api="sucesso",
        meta=schemas.MetaDados(
            fonte=fonte_usada,
            ultima_atualizacao=cache.ultima_atualizacao if cache else datetime.now(),
            tempo_processamento_ms=tempo_execucao
        ),
        dados=lista_schemas
    )

@app.get("/api/v1/vasco/artilharia", response_model=schemas.RespostaArtilharia, tags=["Estatísticas"])
def obter_artilharia_vasco(db: Session = Depends(get_db)):
    inicio = time.time()
    partidas_encerradas = db.query(models.Partida).filter(models.Partida.status == "Encerrado").all()
    
    for partida in partidas_encerradas:
        if not partida.game_id:
            continue
            
        ja_tem_gols = db.query(models.Gol).filter(models.Gol.game_id == partida.game_id).first()
        gols_totais = (partida.gols_mandante or 0) + (partida.gols_visitante or 0)
        
        if not ja_tem_gols and gols_totais > 0:
            print(f"🕵️‍♂️ Caçando gols perdidos do jogo ID: {partida.game_id} na ESPN...")
            gols_raspados = scraper.puxar_detalhes_partida(partida.game_id)
            
            for gol in gols_raspados:
                novo_gol = models.Gol(
                    game_id=gol["game_id"],
                    jogador_nome=gol["jogador_nome"],
                    minuto=gol["minuto"],
                    time_goleador=gol["time_goleador"]
                )
                db.add(novo_gol)
            db.commit()

    todos_gols_vasco = db.query(models.Gol).filter(models.Gol.time_goleador.ilike("%Vasco%")).all()
    
    contagem_gols = {}
    for gol in todos_gols_vasco:
        nome = gol.jogador_nome
        contagem_gols[nome] = contagem_gols.get(nome, 0) + 1
        
    dados_artilheiros = []
    for jogador_nome, total_gols in contagem_gols.items():
        atleta_db = db.query(models.Jogador).filter(models.Jogador.nome.ilike(f"%{jogador_nome}%")).first()
        posicao = atleta_db.posicao if atleta_db else "Não informada"
        
        dados_artilheiros.append({
            "jogador": jogador_nome,
            "gols": total_gols,
            "posicao": posicao
        })
        
    dados_artilheiros = sorted(dados_artilheiros, key=lambda x: x["gols"], reverse=True)
    tempo_execucao = round((time.time() - inicio) * 1000, 2)
    
    return schemas.RespostaArtilharia(
        status_api="sucesso",
        meta=schemas.MetaDados(
            fonte="Banco de Dados com Cache Híbrido",
            ultima_atualizacao=datetime.now(),
            tempo_processamento_ms=tempo_execucao
        ),
        dados=dados_artilheiros
    )

@app.get("/api/v1/vasco/estatisticas-jogadores", response_model=schemas.RespostaEstatisticasElenco, tags=["Estatísticas"])
def obter_estatisticas_individuais(db: Session = Depends(get_db)):
    inicio = time.time()
    
    partidas_encerradas = db.query(models.Partida).filter(models.Partida.status == "Encerrado").all()
    
    for partida in partidas_encerradas:
        if not partida.game_id:
            continue
            
        ja_tem_stats = db.query(models.EstatisticaAtletaPartida).filter(models.EstatisticaAtletaPartida.game_id == partida.game_id).first()
        
        if not ja_tem_stats:
            print(f"📊 Baixando stats individuais do jogo ID: {partida.game_id}...")
            stats_raspadas = scraper.puxar_estatisticas_jogadores(partida.game_id)
            
            for st in stats_raspadas:
                nova_stat = models.EstatisticaAtletaPartida(
                    game_id=st["game_id"],
                    jogador_nome=st["jogador_nome"],
                    gols=st["gols"],
                    assistencias=st["assistencias"],
                    chutes=st["chutes"],
                    chutes_no_gol=st["chutes_no_gol"],
                    faltas_cometidas=st["faltas_cometidas"],
                    faltas_sofridas=st["faltas_sofridas"],
                    cartao_amarelo=st["cartao_amarelo"],
                    cartao_vermelho=st["cartao_vermelho"],
                    salvamentos=st["salvamentos"]
                )
                db.add(nova_stat)
            db.commit()

    agregacao = db.query(
        models.EstatisticaAtletaPartida.jogador_nome,
        func.count(models.EstatisticaAtletaPartida.id).label("jogos"),
        func.sum(models.EstatisticaAtletaPartida.gols).label("gols"),
        func.sum(models.EstatisticaAtletaPartida.assistencias).label("assistencias"),
        func.sum(models.EstatisticaAtletaPartida.chutes).label("chutes"),
        func.sum(models.EstatisticaAtletaPartida.chutes_no_gol).label("chutes_no_gol"),
        func.sum(models.EstatisticaAtletaPartida.faltas_cometidas).label("faltas_cometidas"),
        func.sum(models.EstatisticaAtletaPartida.faltas_sofridas).label("faltas_sofridas"),
        func.sum(models.EstatisticaAtletaPartida.cartao_amarelo).label("amarelos"),
        func.sum(models.EstatisticaAtletaPartida.cartao_vermelho).label("vermelhos"),
        func.sum(models.EstatisticaAtletaPartida.salvamentos).label("salvamentos")
    ).group_by(models.EstatisticaAtletaPartida.jogador_nome).all()

    dados_finais = []
    for linha in agregacao:
        dados_finais.append({
            "jogador": linha.jogador_nome,
            "jogos_disputados": linha.jogos,
            "gols": linha.gols or 0,
            "assistencias": linha.assistencias or 0,
            "chutes": linha.chutes or 0,
            "chutes_no_gol": linha.chutes_no_gol or 0,
            "faltas_cometidas": linha.faltas_cometidas or 0,
            "faltas_sofridas": linha.faltas_sofridas or 0,
            "cartoes_amarelos": linha.amarelos or 0,
            "cartoes_vermelhos": linha.vermelhos or 0,
            "salvamentos": linha.salvamentos or 0
        })
        
    # 🔥 CORREÇÃO: Duplicação do bloco de retorno foi removida
    dados_finais = sorted(dados_finais, key=lambda x: x["jogos_disputados"], reverse=True)
    tempo_execucao = round((time.time() - inicio) * 1000, 2)
    
    return schemas.RespostaEstatisticasElenco(
        status_api="sucesso",
        meta=schemas.MetaDados(
            fonte="Banco de Dados Relacional",
            ultima_atualizacao=datetime.now(),
            tempo_processamento_ms=tempo_execucao
        ),
        dados=dados_finais
    )

@app.get("/api/v1/vasco/classificacao", response_model=schemas.RespostaTabela, tags=["Brasileirão"])
def obter_tabela_brasileirao():
    """Busca a tabela de classificação do Campeonato Brasileiro em tempo real"""
    inicio = time.time()
    tabela = scraper.puxar_tabela_brasileirao()
    tempo_execucao = round((time.time() - inicio) * 1000, 2)
    
    return schemas.RespostaTabela(
        status_api="sucesso",
        campeonato="Campeonato Brasileiro (Série A)",
        meta=schemas.MetaDados(
            fonte="ESPN Live API (Tempo Real)",
            ultima_atualizacao=datetime.now(),
            tempo_processamento_ms=tempo_execucao
        ),
        dados=tabela
    )

@app.get("/api/v1/vasco/forma-recente", response_model=schemas.RespostaFormaRecente, tags=["Jogos"])
def obter_forma_recente(time_alvo: str = "Vasco", db: Session = Depends(get_db)):
    """Busca a sequência (V-E-D) das últimas 5 partidas de qualquer time do campeonato"""
    inicio = time.time()
    
    jogos_encerrados = db.query(models.Partida).filter(
        models.Partida.status == "Encerrado",
        or_(
            models.Partida.mandante.contains(time_alvo),
            models.Partida.visitante.contains(time_alvo)
        )
    ).all()
    
    def converter_para_datetime(jogo):
        if not jogo.data_partida: return datetime.min
        try: return datetime.strptime(jogo.data_partida, "%d/%m/%Y %H:%M")
        except ValueError:
            try: return datetime.strptime(jogo.data_partida, "%d/%m/%Y")
            except ValueError: return datetime.min

    jogos_encerrados.sort(key=converter_para_datetime, reverse=True)
    ultimos_5 = jogos_encerrados[:5]
    
    forma_array = []
    detalhes_jogos = []
    
    for jogo in ultimos_5:
        alvo_mandante = time_alvo.lower() in jogo.mandante.lower()
        gols_alvo = jogo.gols_mandante if alvo_mandante else jogo.gols_visitante
        gols_oponente = jogo.gols_visitante if alvo_mandante else jogo.gols_mandante
        
        if gols_alvo > gols_oponente:
            resultado = "V"
        elif gols_alvo == gols_oponente:
            resultado = "E"
        else:
            resultado = "D"
            
        forma_array.append(resultado)
        
        detalhes_jogos.append({
            "data_partida": jogo.data_partida or "Data Desconhecida",
            "campeonato": jogo.campeonato,
            "mandante": jogo.mandante,
            "visitante": jogo.visitante,
            "gols_mandante": jogo.gols_mandante,
            "gols_visitante": jogo.gols_visitante,
            "resultado_alvo": resultado
        })
        
    forma_array.reverse()
    detalhes_jogos.reverse()

    tempo_execucao = round((time.time() - inicio) * 1000, 2)
    
    return schemas.RespostaFormaRecente(
        status_api="sucesso",
        meta=schemas.MetaDados(
            fonte="Banco de Dados Relacional",
            ultima_atualizacao=datetime.now(),
            tempo_processamento_ms=tempo_execucao
        ),
        forma_array=forma_array,
        ultimos_jogos=detalhes_jogos
    )

@app.post("/api/admin/popular-brasileirao", tags=["Admin"])
def popular_banco_brasileirao(db: Session = Depends(get_db)):
    """Rota Trator: Varre os 20 times da Série A e popula o banco de dados"""
    inicio = time.time()
    jogos_adicionados = 0
    jogos_atualizados = 0
    
    for nome_time, team_id in TIMES_SERIE_A.items():
        print(f"🚜 Puxando calendário do: {nome_time}...")
        jogos = scraper.puxar_jogos_time(team_id)
        
        for jogo in jogos:
            if not jogo.get("game_id"):
                continue
                
            jogo_existente = db.query(models.Partida).filter(models.Partida.game_id == jogo["game_id"]).first()
            
            if jogo_existente:
                if jogo_existente.status != jogo["status"]:
                    jogo_existente.status = jogo["status"]
                    jogo_existente.gols_mandante = jogo["gols_mandante"]
                    jogo_existente.gols_visitante = jogo["gols_visitante"]
                    jogos_atualizados += 1
            else:
                nova_partida = models.Partida(
                    campeonato=jogo["campeonato"],
                    mandante=jogo["mandante"],
                    visitante=jogo["visitante"],
                    gols_mandante=jogo["gols_mandante"],
                    gols_visitante=jogo["gols_visitante"],
                    status=jogo["status"],
                    data_partida=jogo["data_partida"],
                    rodada=jogo["rodada"],
                    game_id=jogo["game_id"]
                )
                db.add(nova_partida)
                jogos_adicionados += 1
                
        db.commit()
        time.sleep(2)

    tempo_execucao = round(time.time() - inicio, 2)
    
    return {
        "status": "Banco de dados populado com sucesso!",
        "tempo_execucao_segundos": tempo_execucao,
        "estatisticas": {
            "novos_jogos_adicionados": jogos_adicionados,
            "jogos_atualizados": jogos_atualizados,
            "total_times_processados": len(TIMES_SERIE_A)
        }
    }

@app.get("/api/v1/vasco/confronto", response_model=schemas.RespostaConfrontoDireto, tags=["Estatísticas"])
def obter_confronto_direto(time_a: str = "Vasco", time_b: str = "Flamengo", db: Session = Depends(get_db)):
    """Analisa o histórico de confrontos diretos (Head-to-Head) entre duas equipes na temporada"""
    inicio = time.time()
    
    confrontos = db.query(models.Partida).filter(
        models.Partida.status == "Encerrado",
        or_(
            and_(models.Partida.mandante.contains(time_a), models.Partida.visitante.contains(time_b)),
            and_(models.Partida.mandante.contains(time_b), models.Partida.visitante.contains(time_a))
        )
    ).all()
    
    vitorias_a = 0
    vitorias_b = 0
    empates = 0
    gols_a = 0
    gols_b = 0
    historico_jogos = []
    
    for jogo in confrontos:
        a_is_mandante = time_a.lower() in jogo.mandante.lower()
        
        gols_do_a = jogo.gols_mandante if a_is_mandante else jogo.gols_visitante
        gols_do_b = jogo.gols_visitante if a_is_mandante else jogo.gols_mandante
        
        gols_a += gols_do_a
        gols_b += gols_do_b
        
        if gols_do_a > gols_do_b:
            vitorias_a += 1
        elif gols_do_b > gols_do_a:
            vitorias_b += 1
        else:
            empates += 1
            
        historico_jogos.append({
            "data_partida": jogo.data_partida or "Data Desconhecida",
            "campeonato": jogo.campeonato,
            "mandante": jogo.mandante,
            "visitante": jogo.visitante,
            "gols_mandante": jogo.gols_mandante,
            "gols_visitante": jogo.gols_visitante
        })
        
    def converter_para_datetime(jogo_dict):
        dp = jogo_dict["data_partida"]
        if dp == "Data Desconhecida": return datetime.min
        try: return datetime.strptime(dp, "%d/%m/%Y %H:%M")
        except ValueError:
            try: return datetime.strptime(dp, "%d/%m/%Y")
            except ValueError: return datetime.min

    historico_jogos.sort(key=converter_para_datetime, reverse=True)
    tempo_execucao = round((time.time() - inicio) * 1000, 2)
    
    return schemas.RespostaConfrontoDireto(
        status_api="sucesso",
        meta=schemas.MetaDados(
            fonte="Banco de Dados Relacional",
            ultima_atualizacao=datetime.now(),
            tempo_processamento_ms=tempo_execucao
        ),
        time_a=time_a,
        time_b=time_b,
        resumo={
            "jogos_disputados": len(confrontos),
            "vitorias_time_a": vitorias_a,
            "vitorias_time_b": vitorias_b,
            "empates": empates,
            "gols_time_a": gols_a,
            "gols_time_b": gols_b
        },
        historico=historico_jogos
    )

@app.get("/api/v1/vasco/proximo-jogo", response_model=schemas.RespostaProximoJogo, tags=["Jogos"])
def obter_proximo_jogo(time_alvo: str = "Vasco", db: Session = Depends(get_db)):
    """Busca a próxima partida agendada de qualquer time do campeonato"""
    inicio = time.time()
    
    jogos_futuros = db.query(models.Partida).filter(
        models.Partida.status != "Encerrado",
        or_(
            models.Partida.mandante.contains(time_alvo),
            models.Partida.visitante.contains(time_alvo)
        )
    ).all()
    
    def converter_para_datetime(jogo):
        if not jogo.data_partida: 
            return datetime.max
        try: 
            return datetime.strptime(jogo.data_partida, "%d/%m/%Y %H:%M")
        except ValueError:
            try: 
                return datetime.strptime(jogo.data_partida, "%d/%m/%Y")
            except ValueError: 
                return datetime.max

    jogos_futuros.sort(key=converter_para_datetime)
    proximo_jogo = jogos_futuros[0] if jogos_futuros else None
    
    dados_jogo = None
    if proximo_jogo:
        dados_jogo = {
            "campeonato": proximo_jogo.campeonato,
            "mandante": proximo_jogo.mandante,
            "visitante": proximo_jogo.visitante,
            "data_partida": proximo_jogo.data_partida,
            "rodada": proximo_jogo.rodada
        }
        
    tempo_execucao = round((time.time() - inicio) * 1000, 2)
    
    return schemas.RespostaProximoJogo(
        status_api="sucesso",
        meta=schemas.MetaDados(
            fonte="Banco de Dados Relacional",
            ultima_atualizacao=datetime.now(),
            tempo_processamento_ms=tempo_execucao
        ),
        dados=dados_jogo
    )


# ==========================================
# ROTAS DE DEBUG / ENGENHARIA REVERSA
# (Podem ser ignoradas ou ocultadas em Produção)
# ==========================================

@app.get("/api/v1/vasco/teste-raio-x", tags=["Debug"])
def teste_raio_x():
    """Rota de Debug: Devolve o dado cru direto do Scraper para a tela."""
    return scraper.puxar_jogos_time("3454")

@app.get("/api/v1/vasco/teste-raio-x-elenco", tags=["Debug"])
def teste_raio_x_elenco():
    import requests
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/teams/3454/roster"
    headers = {"User-Agent": "Mozilla/5.0"}
    resposta = requests.get(url, headers=headers)
    return resposta.json()

@app.get("/api/v1/vasco/teste-raio-x-gols", tags=["Debug"])
def teste_raio_x_gols():
    import requests
    url_jogos = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/3454/schedule"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    dados_jogos = requests.get(url_jogos, headers=headers).json()
    jogo_com_gol_id = None
    for evento in dados_jogos.get("events", []):
        status = evento["competitions"][0]["status"]["type"]["state"]
        if status == "post":
            placar1 = evento["competitions"][0]["competitors"][0].get("score", {}).get("value", 0)
            placar2 = evento["competitions"][0]["competitors"][1].get("score", {}).get("value", 0)
            if int(placar1) + int(placar2) > 0:
                jogo_com_gol_id = evento["id"]
                break
                
    if not jogo_com_gol_id:
        return {"erro": "Nenhum jogo com gol encontrado."}
    
    url_summary = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={jogo_com_gol_id}"
    dados_summary = requests.get(url_summary, headers=headers).json()
    
    return {
        "id_do_jogo": jogo_com_gol_id,
        "chaves_principais": list(dados_summary.keys()),
        "exemplo_scoring": dados_summary.get("scoring", "A chave scoring não existe"),
        "exemplo_details": dados_summary.get("details", "A chave details não existe")[:3] if "details" in dados_summary else "Não tem details"
    }

@app.get("/api/v1/vasco/teste-raio-x-sofascore", tags=["Debug"])
def teste_raio_x_sofascore():
    import requests
    url = "https://api.sofascore.com/api/v1/team/1974/events/last/0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/",
        "Connection": "keep-alive"
    }
    
    try:
        resposta = requests.get(url, headers=headers, timeout=10)
        if resposta.status_code == 200:
            dados = resposta.json()
            eventos = dados.get("events", [])
            
            if eventos:
                primeiro_jogo = eventos[0]
                return {
                    "status_acesso": "🟢 SUCESSO TOTAL! O Sofascore abriu a porta.",
                    "id_jogo_sofascore": primeiro_jogo.get("id"),
                    "campeonato": primeiro_jogo.get("tournament", {}).get("name"),
                    "mandante": primeiro_jogo.get("homeTeam", {}).get("name"),
                    "visitante": primeiro_jogo.get("awayTeam", {}).get("name")
                }
            return {"status_acesso": "🟢 Acesso liberado, mas sem eventos na lista."}
        else:
            return {
                "status_acesso": f"🔴 BLOQUEADO! Código de Erro: {resposta.status_code}",
                "detalhes": resposta.text[:200]
            }
    except Exception as e:
        return {"erro_interno": str(e)}

@app.get("/api/v1/vasco/teste-raio-x-stats-roster", tags=["Debug"])
def teste_raio_x_stats_roster():
    import requests
    url_jogos = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/3454/schedule"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    dados_jogos = requests.get(url_jogos, headers=headers).json()
    jogo_encerrado_id = None
    
    for evento in dados_jogos.get("events", []):
        if evento["competitions"][0]["status"]["type"]["state"] == "post":
            jogo_encerrado_id = evento["id"]
            break
            
    if not jogo_encerrado_id:
        return {"erro": "Nenhum jogo encerrado encontrado."}

    url_summary = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={jogo_encerrado_id}"
    dados_summary = requests.get(url_summary, headers=headers).json()
    
    for time_roster in dados_summary.get("rosters", []):
        if "Vasco" in time_roster.get("team", {}).get("displayName", ""):
            for p in time_roster.get("roster", []):
                nome = p.get("athlete", {}).get("displayName", "")
                stats = p.get("stats", [])
                if stats:
                    return {
                        "jogador_analisado": nome,
                        "chaves_disponiveis_na_espn": [s.get("name") for s in stats],
                        "dados_brutos": stats
                    }
                    
    return {"erro": "Nenhum jogador com estatísticas encontrado nesse jogo."}