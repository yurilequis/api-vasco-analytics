import requests
from datetime import datetime, timedelta

# Dicionário Oficial de IDs da ESPN (Série A - 2026)
TIMES_SERIE_A = {
    "Palmeiras": "2029",
    "Flamengo": "819",
    "Fluminense": "3445",
    "São Paulo": "3173",
    "Athletico Paranaense": "3449",
    "Red Bull Bragantino": "6061",
    "Bahia": "3451",
    "Coritiba": "3465",
    "Botafogo": "3448",
    "Atlético-MG": "3174",
    "Internacional": "3444",
    "Vasco da Gama": "3454",
    "Cruzeiro": "3175",
    "Vitória": "3456",
    "Grêmio": "3442",
    "Santos": "3446",
    "Corinthians": "3172",
    "Remo": "3486",
    "Mirassol": "6051",
    "Chapecoense": "10486"
}

class CbfScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def puxar_jogos_time(self, team_id: str):
        # Rota principal (Todas as competições)
        url_primaria = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/{team_id}/schedule"
        # Rota de segurança (Apenas Brasileirão)
        url_fallback = f"https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/teams/{team_id}/schedule"
        
        try:
            print(f"A procurar dados vitais do time ID {team_id} (ESPN API)...")
            response = requests.get(url_primaria, headers=self.headers, timeout=10)
            
            # 🔥 ESTRATÉGIA DE FALLBACK: Se a ESPN der tela azul, tentamos a rota alternativa
            if response.status_code == 500:
                print(f"⚠️ Erro 500 na rota principal. Tentando Fallback (bra.1) para o ID {team_id}...")
                response = requests.get(url_fallback, headers=self.headers, timeout=10)

            if response.status_code != 200:
                print(f"Erro persistente na ESPN. Status: {response.status_code}")
                return []

            dados = response.json()
            eventos_brutos = dados.get("events", [])
            
            # Garante ordem cronológica
            eventos_ordenados = sorted(eventos_brutos, key=lambda e: e.get("date", ""))
            resultados = []
            
            for index, evento in enumerate(eventos_ordenados):
                competicao = evento["competitions"][0]
                competidores = competicao["competitors"]
                
                nome_campeonato = evento.get("league", {}).get("name")
                if not nome_campeonato:
                    nome_campeonato = evento.get("season", {}).get("name", "Temporada 2026")
                
                time_casa = next(c for c in competidores if c["homeAway"] == "home")
                time_fora = next(c for c in competidores if c["homeAway"] == "away")
                
                mandante = time_casa["team"]["displayName"]
                visitante = time_fora["team"]["displayName"]
                status_jogo = competicao["status"]["type"]["state"]
                
                # ⏰ Tratamento da Data
                data_bruta = evento.get("date") or competicao.get("date")
                data_formatada = "A definir"
                if data_bruta:
                    try:
                        data_obj = datetime.strptime(data_bruta, "%Y-%m-%dT%H:%MZ")
                        data_obj = data_obj - timedelta(hours=3)
                        data_formatada = data_obj.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        data_formatada = data_bruta
                
                # Tratamento da Rodada
                rodada_num = evento.get("week", {}).get("number")
                if not rodada_num:
                    notas = competicao.get("notes", [])
                    if notas:
                        rodada_num = notas[0].get("headline", "Sem rodada")
                    else:
                        rodada_num = f"{index + 1}ª Rodada"
                
                def extrair_placar(time_dados):
                    placar = time_dados.get("score", 0)
                    if isinstance(placar, dict):
                        return int(placar.get("value", 0))
                    elif placar is not None:
                        return int(placar)
                    return 0

                gols_m = extrair_placar(time_casa) if status_jogo == "post" else None
                gols_v = extrair_placar(time_fora) if status_jogo == "post" else None
                
                resultados.append({
                    "mandante": mandante,
                    "visitante": visitante,
                    "gols_mandante": gols_m,
                    "gols_visitante": gols_v,
                    "status": "Encerrado" if status_jogo == "post" else "Agendado",
                    "data_partida": data_formatada,
                    "rodada": rodada_num,
                    "campeonato": nome_campeonato,
                    "game_id": str(evento.get("id")),
                })

            return resultados

        except Exception as e:
            print(f"⚠️ Erro ao conectar com a ESPN: {e}")
            return []
    
    # Adicionado parâmetro default para não quebrar rotas antigas e permitir escalar
    def puxar_elenco_time(self, team_id: str = "3454"):
        url_elenco = f"https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/teams/{team_id}/roster"
        
        try:
            print(f"A procurar dados do elenco ID {team_id} (ESPN API)...")
            response = requests.get(url_elenco, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Erro na ESPN ao buscar elenco. Status: {response.status_code}")
                return []

            dados = response.json()
            jogadores = dados.get("athletes", [])
            resultados = []
            
            for jog in jogadores:
                atleta_id = jog.get("id")
                nome = jog.get("fullName")
                posicao = jog.get("position", {}).get("displayName", "Não informada")
                camisa = jog.get("jersey", "S/N")
                idade = jog.get("age", 0)
                
                resultados.append({
                    "atleta_id": str(atleta_id),
                    "nome": nome,
                    "posicao": posicao,
                    "camisa": str(camisa),
                    "idade": int(idade) if idade else None
                })
                    
            return resultados

        except Exception as e:
            print(f"⚠️ Erro ao conectar com a ESPN (Elenco): {e}")
            return []
        
    def puxar_detalhes_partida(self, game_id: str):
        """Acessa o resumo (summary) da ESPN para capturar os autores dos gols através dos keyEvents"""
        url_summary = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={game_id}"
        gols_encontrados = []
        
        try:
            response = requests.get(url_summary, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return []
                
            dados = response.json()
            eventos = dados.get("keyEvents", [])
            
            for evento in eventos:
                tipo_evento = evento.get("type", {}).get("text", "")
                
                if "Goal" in tipo_evento or "Penalty" in tipo_evento:
                    minuto = evento.get("clock", {}).get("displayValue", "")
                    time_nome = evento.get("team", {}).get("displayName", "")
                    
                    participantes = evento.get("participants", [])
                    jogador_nome = ""
                    if participantes:
                        jogador_nome = participantes[0].get("athlete", {}).get("displayName", "")
                    
                    if jogador_nome:
                        gols_encontrados.append({
                            "game_id": game_id,
                            "jogador_nome": jogador_nome,
                            "minuto": minuto,
                            "time_goleador": time_nome
                        })
                        
            return gols_encontrados
            
        except Exception as e:
            print(f"⚠️ Erro ao buscar detalhes do jogo {game_id}: {e}")
            return []
        
    def puxar_estatisticas_jogadores(self, game_id: str, time_alvo: str = "Vasco"):
        """Acessa o resumo da ESPN para capturar passes, desarmes, chutes, etc."""
        url_summary = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={game_id}"
        stats_encontradas = []
        
        try:
            response = requests.get(url_summary, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return []
                
            dados = response.json()
            rosters = dados.get("rosters", [])
            
            for time_roster in rosters:
                time_nome = time_roster.get("team", {}).get("displayName", "")
                
                # Só queremos gastar espaço no banco com os jogadores do time alvo!
                if time_alvo not in time_nome:
                    continue
                    
                jogadores = time_roster.get("roster", [])
                
                for p in jogadores:
                    nome = p.get("athlete", {}).get("displayName", "")
                    if not nome:
                        continue
                        
                    stats_brutas = p.get("stats", [])
                    dic_stats = {s.get("name"): s.get("value") for s in stats_brutas}
                    
                    stats_encontradas.append({
                        "game_id": game_id,
                        "jogador_nome": nome,
                        "gols": int(dic_stats.get("totalGoals", 0) or 0),
                        "assistencias": int(dic_stats.get("goalAssists", 0) or 0),
                        "chutes": int(dic_stats.get("totalShots", 0) or 0),
                        "chutes_no_gol": int(dic_stats.get("shotsOnTarget", 0) or 0),
                        "faltas_cometidas": int(dic_stats.get("foulsCommitted", 0) or 0),
                        "faltas_sofridas": int(dic_stats.get("foulsDrawn", 0) or 0),
                        "cartao_amarelo": int(dic_stats.get("yellowCards", 0) or 0),
                        "cartao_vermelho": int(dic_stats.get("redCards", 0) or 0),
                        "salvamentos": int(dic_stats.get("saves", 0) or 0)
                    })
                    
            return stats_encontradas
            
        except Exception as e:
            print(f"⚠️ Erro ao buscar stats individuais do jogo {game_id}: {e}")
            return []
        
    def puxar_tabela_brasileirao(self):
        """Busca a tabela de classificação em tempo real na API pública da ESPN"""
        url_standings = "https://site.api.espn.com/apis/v2/sports/soccer/bra.1/standings"
        
        try:
            response = requests.get(url_standings, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return []
                
            dados = response.json()
            tabela_bruta = dados.get("children", [])[0].get("standings", {}).get("entries", [])
            classificacao = []
            
            for i, linha in enumerate(tabela_bruta, start=1):
                estatisticas = {stat.get("abbreviation"): stat.get("value") for stat in linha.get("stats", [])}
                
                # Regras oficiais de zonas de classificação da CBF
                zona = None
                if i <= 4:
                    zona = "Libertadores"
                elif i <= 6:
                    zona = "Pré-Libertadores"
                elif i <= 12:
                    zona = "Sul-Americana"
                elif i >= 17:
                    zona = "Rebaixamento"

                classificacao.append({
                    "posicao": i,
                    "Equipe": linha.get("team", {}).get("displayName", "Desconhecido"),
                    "Pts": estatisticas.get("P", 0),
                    "PJ": estatisticas.get("GP", 0),
                    "VIT": estatisticas.get("W", 0),
                    "E": estatisticas.get("D", 0),
                    "DER": estatisticas.get("L", 0),
                    "GP": estatisticas.get("F", 0),  # F = Goals For (Pró)
                    "GC": estatisticas.get("A", 0),  # A = Goals Against (Contra)
                    "SG": estatisticas.get("GD", 0),
                    "zona_classificacao": zona
                })
                
            return classificacao
            
        except Exception as e:
            print(f"⚠️ Erro ao buscar tabela de classificação: {e}")
            return []