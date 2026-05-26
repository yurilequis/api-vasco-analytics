from curl_cffi import requests

class SofascoreScraper:
    def __init__(self):
        self.base_url = "https://api.sofascore.com/api/v1"
        self.team_id = "1974" # ID Oficial do Vasco da Gama no Sofascore
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
            "Cache-Control": "max-age=0",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/",
        }

    def _fazer_requisicao(self, endpoint: str):
        url = f"{self.base_url}{endpoint}"
        try:
            # impersonate="chrome120" burla a proteção do Cloudflare
            resposta = requests.get(url, headers=self.headers, impersonate="chrome120", timeout=15)
            if resposta.status_code == 200:
                return resposta.json()
            print(f"⚠️ Erro {resposta.status_code} ao acessar {url}")
            return None
        except Exception as e:
            print(f"❌ Erro de conexão no Sofascore: {e}")
            return None

    def puxar_jogos(self):
        """Busca as partidas do ano inteiro (últimas páginas) e próximos jogos"""
        print("📊 Buscando calendário completo no Sofascore...")
        eventos = []

        # Busca as últimas 3 páginas (0, 1 e 2) para garantir o histórico desde Janeiro
        for pagina in range(3):
            jogos_encerrados = self._fazer_requisicao(f"/team/{self.team_id}/events/last/{pagina}")
            if jogos_encerrados and "events" in jogos_encerrados:
                eventos.extend(jogos_encerrados["events"])
            else:
                break # Se a página não existir, sai do loop

        # Busca os próximos jogos agendados
        jogos_agendados = self._fazer_requisicao(f"/team/{self.team_id}/events/next/0")
        if jogos_agendados and "events" in jogos_agendados:
            eventos.extend(jogos_agendados["events"])

        return eventos

    def puxar_estatisticas_partida(self, event_id: int):
        """Busca estatísticas técnicas (Posse, xG, Chutes, etc)"""
        print(f"📊 Buscando estatísticas do jogo {event_id}...")
        dados = self._fazer_requisicao(f"/event/{event_id}/statistics")
        if not dados or "statistics" not in dados:
            return []
        
        # Filtramos pelo período "ALL" (Jogo Completo)
        stats_completas = [s for s in dados["statistics"] if s.get("period") == "ALL"]
        return stats_completas[0].get("groups", []) if stats_completas else []

    def puxar_elenco_partida(self, event_id: int):
        """Busca formações, titulares, reservas e notas individuais"""
        print(f"📋 Buscando escalações do jogo {event_id}...")
        return self._fazer_requisicao(f"/event/{event_id}/lineups")