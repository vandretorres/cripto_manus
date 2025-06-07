import os
import math
import csv
import argparse
from datetime import datetime
from tabulate import tabulate
from binance.client import Client

# Configurações da Binance API (substituir por suas chaves ou variáveis de ambiente)
# Recomenda-se usar variáveis de ambiente para segurança
API_KEY = os.environ.get('BINANCE_API_KEY', 'UdABeqMnq7OY0qKmNTEg5RbnndIAXrRivBHU1odwOlMoB9rVHfN1SpbxgN1CnFvO')
API_SECRET = os.environ.get('BINANCE_API_SECRET', 'HhkJCzPKdh9s8RURD4wL0nbkMZxJQYTWGhsnOEB7xBjJxDidueevvYjOwonaCPDv')

# Inicializa o cliente da Binance
client = Client(API_KEY, API_SECRET)

def fetch_price_binance(symbol: str) -> float:
    """
    Busca o preço atual de um par de criptomoedas na Binance.
    """
    try:
        ticker_info = client.get_symbol_ticker(symbol=symbol)
        return float(ticker_info["price"])
    except Exception as e:
        raise Exception(f"Falha ao obter preço de {symbol} da Binance: {e}")

def simulate_purchase_from_csv(capital_total: float, signals_csv: str):
    if not os.path.exists(signals_csv):
        print(f"[ERRO] Arquivo {signals_csv} não encontrado.")
        return

    with open(signals_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Filtrar tickers com score > 0 e garantir que o ticker existe
        tickers = [row["ticker"] for row in reader if float(row.get("score", 0)) > 0 and "ticker" in row]

    if not tickers:
        print("[ERRO] Nenhum sinal válido encontrado no arquivo CSV.")
        return

    capital_por_ativo = capital_total / len(tickers)
    resultados = []
    total_investido = 0.0

    for ticker in tickers:
        try:
            preco_atual = fetch_price_binance(ticker)
        except Exception as e:
            print(f"[ERRO] {e}")
            continue

        # Calcular a quantidade fracionária com base no capital alocado
        # Remover math.floor para permitir quantidades fracionárias
        qtd = capital_por_ativo / preco_atual
        
        # Verificar se a quantidade é maior que zero
        if qtd <= 0:
             print(f"[AVISO] Capital insuficiente para comprar {ticker}")
             continue

        custo_total = qtd * preco_atual
        total_investido += custo_total
        resultados.append({
            "ticker": ticker,
            "quantidade": round(qtd, 8), # Manter precisão para quantidades fracionárias
            "preco_compra": round(preco_atual, 8), # Aumentar precisão para criptomoedas
            "custo_total": round(custo_total, 8) # Aumentar precisão para criptomoedas
        })

    if not resultados:
        print("[ERRO] Nenhuma compra realizada com o capital e sinais fornecidos.")
        return

    hoje = datetime.today().strftime("%Y-%m-%d_%H%M%S")
    os.makedirs("data/simulations", exist_ok=True)
    out_path = f"data/simulations/purchase_{hoje}.csv"

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "quantity", "purchase_price", "total_cost"])
        for r in resultados:
            writer.writerow([r["ticker"], r["quantidade"], r["preco_compra"], r["custo_total"]])

    print(f"[✅ SALVO] Simulação salva em: {out_path}")
    print(f"Total investido: R$ {total_investido:,.2f}")
    print(f"Capital restante: R$ {capital_total - total_investido:,.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capital", type=float, default=10000.0, help="Capital total disponível para investimento")
    parser.add_argument("--signals_csv", type=str, required=True, help="Caminho para o arquivo de sinais CSV")
    args = parser.parse_args()

    # Certifique-se de configurar suas chaves de API da Binance
    if 'SUA_API_KEY' in API_KEY or 'SUA_API_SECRET' in API_SECRET:
        print("\n[AVISO] Por favor, configure suas chaves de API da Binance no arquivo ou variáveis de ambiente para obter preços reais.\n")
        # Para simulação offline sem chaves, pode-se mockar a função fetch_price_binance ou usar dados históricos.
        # Como o objetivo é usar dados da Binance, a configuração das chaves é necessária para preços atuais.
    
    simulate_purchase_from_csv(args.capital, args.signals_csv)

