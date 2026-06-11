from fastapi import FastAPI, HTTPException
from scrapers.sofascore_scraper import SofascoreScraper
from datetime import datetime

app = FastAPI(title="Vasco Analytics - Sofascore Engine")
scraper = SofascoreScraper()

# ==========================================
# ROTAS FASTAPI (ENDPOINTS)
# ==========================================

@app.get("/api/v1/vasco/jogos", tags=["Calendário"])
def listar_jogos():
    eventos_brutos = scraper.puxar_jogos()
    if not eventos_brutos:
        raise HTTPException(status_code=500, detail="Falha ao buscar jogos no Sofascore.")
    
    jogos_limpos = []
    for evento in eventos_brutos:
        status_desc = evento.get("status", {}).get("description", "")
        # Se estiver Cancelado ou Adiado no limbo, ignoramos e passamos para o próximo
        if status_desc in ["Canceled", "Postponed", "Abandoned"]:
            continue
        
        status_code = evento.get("status", {}).get("code")
        status = "Encerrada" if status_code in [100, 120] else "Agendada"

        # 1. TRATA A DATA
        timestamp = evento.get("startTimestamp")
        if timestamp:
            data_formatada = datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")
        else:
            data_formatada = "A definir"

        # 2. TRATA OS GOLS E PÊNALTIS
        home_score = evento.get("homeScore", {})
        away_score = evento.get("awayScore", {})
            
        def extrair_placares(score_dict):
            penaltis = score_dict.get("penalty", score_dict.get("penalties"))
            tempo_normal = score_dict.get("normaltime")
            
            if tempo_normal is None:
                current = score_dict.get("current")
                if current is not None and penaltis is not None:
                    tempo_normal = int(current) - int(penaltis)
                else:
                    tempo_normal = current
            
            return tempo_normal, penaltis

        gols_m, penaltis_m = extrair_placares(home_score)
        gols_v, penaltis_v = extrair_placares(away_score)

        # 3. SALVA O JOGO
        jogos_limpos.append({
            "event_id": evento.get("id"),
            "campeonato": evento.get("tournament", {}).get("name"),
            "data_partida": data_formatada,
            "mandante": evento.get("homeTeam", {}).get("name"),
            "visitante": evento.get("awayTeam", {}).get("name"),
            "gols_mandante": gols_m,
            "gols_visitante": gols_v,
            "gols_penaltis_mandante": penaltis_m,
            "gols_penaltis_visitante": penaltis_v,
            "status": status
        })
        
    return {"status_api": "sucesso", "dados": jogos_limpos}


@app.get("/api/v1/vasco/jogos/{event_id}/estatisticas", tags=["Estatísticas Gerais do Time"])
def estatisticas_partida(event_id: int):
    grupos_stats = scraper.puxar_estatisticas_partida(event_id)
    if not grupos_stats:
        raise HTTPException(status_code=404, detail="Estatísticas não encontradas para este jogo.")
    
    resumo_tecnico = {}
    for grupo in grupos_stats:
        for item in grupo.get("statisticsItems", []):
            nome_stat = item.get("name")
            # Filtro limpo apenas com o que importa para o banco relacional
            if nome_stat in ["Ball possession", "Expected goals", "Total shots", "Passes", "Accurate passes"]:
                resumo_tecnico[nome_stat] = {
                    "mandante": item.get("home"),
                    "visitante": item.get("away")
                }

    return {"status_api": "sucesso", "event_id": event_id, "dados": resumo_tecnico}


@app.get("/api/v1/vasco/jogos/{event_id}/detalhes", tags=["Detalhamento Completo da Partida"])
def obter_detalhes_partida(event_id: int):
    """Agrega todas as informações táticas, linha do tempo e escalações completas de uma partida"""
    
    # 1. Busca os dados gerais da partida (Árbitro, Estádio, Treinadores)
    detalhes_evento = scraper._fazer_requisicao(f"/event/{event_id}")
    if not detalhes_evento:
        raise HTTPException(status_code=404, detail="Partida não encontrada no Sofascore.")
        
    evento = detalhes_evento.get("event", {})
    
    juiz = evento.get("referee", {}).get("name")
    estadio = evento.get("venue", {}).get("name")
    treinador_casa = evento.get("homeManager", {}).get("name")
    treinador_vis = evento.get("awayManager", {}).get("name")
    
    # 2. Busca os incidentes (Linha do Tempo: Gols, Cartões, Substituições)
    incidentes_brutos = scraper._fazer_requisicao(f"/event/{event_id}/incidents")
    linha_tempo = []
    if incidentes_brutos and "incidents" in incidentes_brutos:
        # Lemos de trás para frente (reversed) para ficar na ordem cronológica
        for inc in reversed(incidentes_brutos["incidents"]):
            tipo = inc.get("incidentType")
            
            if tipo in ["goal", "card", "substitution"]:
                linha_tempo.append({
                    "minuto": inc.get("time"),
                    "acrescimo": inc.get("addedTime", 0),
                    "periodo": "1T" if inc.get("isHome") else "2T",
                    "tipo": tipo.upper(),
                    "descricao": inc.get("text", ""),
                    "jogador_principal_id": inc.get("player", {}).get("id"),
                    "jogador_secundario_id": inc.get("assist1", {}).get("id") if tipo == "goal" else inc.get("playerIn", {}).get("id") if tipo == "substitution" else None,
                    "is_mandante": inc.get("isHome")
                })

    # 3. Busca o posicionamento médio dos jogadores (Para desenhar o campinho depois)
    posicoes_brutas = scraper._fazer_requisicao(f"/event/{event_id}/average-positions")
    posicoes_medias = {}
    if posicoes_brutas:
        for lado in ["home", "away"]:
            for pos in posicoes_brutas.get(lado, []):
                player_id = pos.get("player", {}).get("id")
                posicoes_medias[player_id] = {
                    "x": pos.get("averageX"),
                    "y": pos.get("averageY")
                }

    # 4. Busca as escalações e estatísticas individuais
    lineups = scraper._fazer_requisicao(f"/event/{event_id}/lineups")
    escalacoes_formatadas = {"mandante": [], "visitante": []}
    
    if lineups and "home" in lineups:
        for lado in ["home", "away"]:
            chave_destino = "mandante" if lado == "home" else "visitante"
            dados_time = lineups.get(lado, {})
            
            for p in dados_time.get("players", []):
                player_obj = p.get("player", {})
                player_id = player_obj.get("id")
                stats = p.get("statistics", {})
                
                escalacoes_formatadas[chave_destino].append({
                    "sofascore_id": player_id,
                    "nome_completo": player_obj.get("name"),
                    "nome_popular": player_obj.get("shortName"),
                    "posicao_geral": player_obj.get("position"),
                    "posicao_partida": p.get("position"),
                    "titular": p.get("substitute") is False,
                    "numero_camisa": p.get("shirtNumber"),
                    "nota": stats.get("rating"),
                    "minutos_jogados": stats.get("minutesPlayed", 0),
                    "gols": stats.get("goals", 0),
                    "assistencias": stats.get("goalAssist", 0),
                    "chutes": stats.get("totalShots", 0),
                    "chutes_gol": stats.get("shotsOnTarget", 0),
                    "passes_tentados": stats.get("totalPass", 0),
                    "passes_completos": stats.get("accuratePass", 0),
                    "dribles_tentados": stats.get("totalContest", 0),
                    "dribles_completos": stats.get("wonContest", 0),
                    "desarmes": stats.get("totalTackle", 0),
                    "interceptacoes": stats.get("interceptionWon", 0),
                    "faltas_cometidas": stats.get("fouls", 0),
                    "faltas_sofridas": stats.get("wasFouled", 0),
                    "posicao_media": posicoes_medias.get(player_id, {"x": None, "y": None}),
                    "heatmap_url": f"https://api.sofascore.app/api/v1/event/{event_id}/player/{player_id}/heatmap"
                })

    return {
        "status_api": "sucesso",
        "event_id": event_id,
        "arbitro": juiz,
        "estadio": estadio,
        "treinador_mandante": treinador_casa,
        "treinador_visitante": treinador_vis,
        "linha_do_tempo": linha_tempo,
        "escalacoes": escalacoes_formatadas
    }

# ==========================================
# INICIALIZAÇÃO DO SERVIDOR
# ==========================================
if __name__ == "__main__":
    print("--- Rotas registradas ---")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"Rota: {route.path}")
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)