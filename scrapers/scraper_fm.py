from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import requests
import json
import time

# O Dicionário Mestre (Mantido intacto)
MAPA_ATRIBUTOS = {
    # Técnicos
    'Corners': 'escanteios', 'Crossing': 'cruzamento', 'Dribbling': 'drible',
    'Finishing': 'finalizacao', 'First Touch': 'primeiroToque',
    'Free Kick Taking': 'cobrancaFalta', 'Heading': 'cabeceamento',
    'Long Shots': 'chutesLonge', 'Long Throws': 'laterais',
    'Marking': 'marcacao', 'Passing': 'passe', 'Penalty Taking': 'penaltis',
    'Tackling': 'desarme', 'Technique': 'tecnica',
    # Mentais
    'Aggression': 'agressividade', 'Anticipation': 'antecipacao',
    'Bravery': 'bravura', 'Composure': 'compostura', 'Concentration': 'concentracao',
    'Decisions': 'decisoes', 'Determination': 'determinacao',
    'Flair': 'imprevisibilidade', 'Leadership': 'lideranca',
    'Off The Ball': 'semBola', 'Positioning': 'posicionamento',
    'Teamwork': 'trabalhoEquipe', 'Vision': 'visaoJogo', 'Work Rate': 'indiceTrabalho',
    # Físicos
    'Acceleration': 'aceleracao', 'Agility': 'agilidade', 'Balance': 'equilibrio',
    'Jumping Reach': 'impulsao', 'Natural Fitness': 'aptidaoNatural',
    'Pace': 'velocidade', 'Stamina': 'resistencia', 'Strength': 'forca',
    # Goleiros
    'Aerial Reach': 'alcanceAereo', 'Command Of Area': 'comandoArea', 
    'Communication': 'comunicacao', 'Eccentricity': 'excentricidade', 
    'Handling': 'jogoMaos', 'Kicking': 'reposicao', 
    'One On Ones': 'umContraUm', 'Reflexes': 'reflexos', 
    'Rushing Out (Tendency)': 'saidaGol', 'Punching (Tendency)': 'socos', 
    'Throwing': 'lancamentos'
}

def extrair_atributos_com_playwright(url_jogador):
    print(f"\n🚀 Iniciando navegador invisível para varrer: {url_jogador}")
    
    perfil_extraido = {}
    
    with sync_playwright() as p:
        # Lança um Chrome invisível (headless)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        try:
            # Entra na página e espera o carregamento inicial
            page.goto(url_jogador, timeout=30000)
            
            # TRUQUE DE MESTRE: O FMInside usa spans para as notas.
            # Vamos esperar a página carregar e dar um tempo extra pro JavaScript desenhar as notas
            print("⏳ Aguardando o JavaScript do site carregar os atributos...")
            time.sleep(3) # Espera 3 segundos cravados para garantir
            
            # Agora sim, pegamos o HTML da tela exatamente como você vê no navegador
            html_final = page.content()
            soup = BeautifulSoup(html_final, 'html.parser')
            
            print("✅ HTML renderizado capturado. Buscando dados...")
            
            # Varredura inteligente
            for atributo_ingles, coluna_banco in MAPA_ATRIBUTOS.items():
                # Busca a palavra exata
                elemento = soup.find(string=re.compile(rf'\b{atributo_ingles}\b', re.IGNORECASE))
                
                if elemento:
                    # Sobe no HTML (geralmente a estrutura é uma div de linha contendo o nome e o número ao lado)
                    linha = elemento.parent.parent
                    
                    if linha:
                        textos = linha.stripped_strings
                        for texto in textos:
                            if texto.isdigit() and 1 <= int(texto) <= 20:
                                perfil_extraido[coluna_banco] = int(texto)
                                break
                                
        except Exception as e:
            print(f"❌ Erro de navegação: {e}")
        finally:
            browser.close()
            
    return perfil_extraido

# ==========================================
# PAINEL DE CONTROLE (Envio para o Backend)
# ==========================================
if __name__ == "__main__":
    print("🤖 Agente de Scouting AVANÇADO (Playwright) Ativado")
    
    ID_JOGADOR_BANCO = int(input("🆔 Digite o ID do jogador no seu banco (NestJS): "))
    url_teste = input("🔗 Cole a URL do jogador (ex: FMInside.net): ").strip()
    
    if url_teste:
        dados = extrair_atributos_com_playwright(url_teste)
        
        if dados and len(dados) > 0:
            print(f"\n✅ SUCESSO ABSOLUTO! {len(dados)} atributos encontrados.")
            print("Resumo extraído:", json.dumps(dados, indent=2, ensure_ascii=False))
            print("Injetando no Vasco Analytics...")
            
            # Envia pro NestJS
            payload_dados = {"jogadorId": ID_JOGADOR_BANCO}
            payload_dados.update(dados)
            query_graphql = """mutation AtualizarPerfilFM($dados: AtualizarPerfilFMInput!) { atualizarPerfilFM(dados: $dados) }"""

            try:
                resposta = requests.post(
                    "http://localhost:3001/graphql",
                    json={"query": query_graphql, "variables": {"dados": payload_dados}}
                )
                if resposta.status_code == 200 and "errors" not in resposta.json():
                    print("🚀 GOL! Perfil tático injetado no banco de dados!")
                else:
                    print("❌ O NestJS recusou os dados:", resposta.json())
            except Exception as e:
                print("❌ Falha de conexão com o NestJS. O backend está rodando?")
                
        else:
            print("\n⚠️ O navegador abriu, esperou, mas as notas continuam invisíveis para a lógica de busca.")