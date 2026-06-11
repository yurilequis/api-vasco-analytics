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