import pandas as pd
import yfinance as yf
import argparse
import os
from binance.client import Client

# Configurações da Binance API (substituir por suas chaves ou variáveis de ambiente)
# Recomenda-se usar variáveis de ambiente para segurança
API_KEY = os.environ.get('BINANCE_API_KEY', 'UdABeqMnq7OY0qKmNTEg5RbnndIAXrRivBHU1odwOlMoB9rVHfN1SpbxgN1CnFvO')
API_SECRET = os.environ.get('BINANCE_API_SECRET', 'HhkJCzPKdh9s8RURD4wL0nbkMZxJQYTWGhsnOEB7xBjJxDidueevvYjOwonaCPDv')

# Inicializa o cliente da Binance
client = Client(API_KEY, API_SECRET)

def get_current_price_binance(symbol: str) -> float | None:
    """
    Busca o preço atual de um par de criptomoedas na Binance.
    Retorna None em caso de erro.
    """
    # Certifique-se de configurar suas chaves de API da Binance
    if 'SUA_API_KEY' in API_KEY or 'SUA_API_SECRET' in API_SECRET:
        print("\n[AVISO] Chaves de API da Binance não configuradas. Não será possível obter preços reais para avaliação.\n")
        return None
        
    try:
        ticker_info = client.get_symbol_ticker(symbol=symbol)
        return float(ticker_info["price"])
    except Exception as e:
        print(f"[ERRO] Falha ao obter preço de {symbol} da Binance: {e}")
        return None

def format_currency(value):
    """
    Formata um valor numérico como moeda brasileira (R$), tratando valores None.
    """
    if value is None:
        return "N/A"
    # Garantir que o valor é numérico antes de formatar
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "N/A"
        
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_percent(value):
    """
    Formata um valor numérico como porcentagem, tratando valores None.
    """
    if value is None:
        return "N/A"
    # Garantir que o valor é numérico antes de formatar
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "N/A"
        
    return f"{value:.2f}%".replace(".", ",")

def evaluate_simulation(input_file):
    df = pd.read_csv(input_file)
    
    # Usar a função que busca preço na Binance
    df["current_price"] = df["symbol"].apply(get_current_price_binance)
    
    # Calcular valores e lucros apenas para linhas onde o current_price não é None
    df_calculo = df.dropna(subset=["current_price"]).copy()
    df_calculo["current_value"] = df_calculo["quantity"] * df_calculo["current_price"]
    df_calculo["profit"] = df_calculo["current_value"] - df_calculo["total_cost"]
    # Evitar divisão por zero se total_cost for 0
    total_cost_sum = df_calculo["total_cost"].sum()
    df_calculo["profit_pct"] = 100 * df_calculo["profit"] / df_calculo["total_cost"] if total_cost_sum != 0 else 0

    # Mesclar os resultados calculados de volta ao DataFrame original para manter todas as linhas
    df = df.merge(df_calculo[["symbol", "current_value", "profit", "profit_pct"]], on="symbol", how="left")

    # Aplicar formatações, agora tratando Nones
    df_fmt = df[["symbol", "quantity", "purchase_price", "total_cost", "current_price", "current_value", "profit", "profit_pct"]].copy()
    df_fmt["purchase_price"] = df_fmt["purchase_price"].apply(format_currency)
    df_fmt["total_cost"] = df_fmt["total_cost"].apply(format_currency)
    df_fmt["current_price"] = df_fmt["current_price"].apply(format_currency)
    df_fmt["current_value"] = df_fmt["current_value"].apply(format_currency)
    df_fmt["profit"] = df_fmt["profit"].apply(format_currency)
    df_fmt["profit_pct"] = df_fmt["profit_pct"].apply(format_percent)

    # Redefinir largura das colunas com alinhamento
    print("\n📊 Resultado da Simulação:\n")
    # Ajustar largura da coluna Qtd para acomodar decimais
    header = f"{'Ativo':<8} {'Qtd':>15} {'Preço Compra':>15} {'Total Compra':>15} {'Preço Atual':>15} {'Valor Atual':>15} {'Lucro':>12} {'Rentab.':>10}"
    print(header)
    print("-" * len(header))

    for _, row in df_fmt.iterrows():
        # Ajustar formatação da quantidade para permitir decimais e alinhar
        quantity_str = f"{row['quantity']:.8f}".rstrip('0').rstrip('.') if pd.notna(row['quantity']) else "N/A"
        print(f"{row['symbol']:<8} {quantity_str:>15} {row['purchase_price']:>15} {row['total_cost']:>15} {row['current_price']:>15} {row['current_value']:>15} {row['profit']:>12} {row['profit_pct']:>10}")

    # Totais (calcular apenas com valores não None)
    total_cost = df_calculo["total_cost"].sum() if not df_calculo.empty else 0
    total_value = df_calculo["current_value"].sum() if not df_calculo.empty else 0
    total_profit = total_value - total_cost
    total_profit_pct = 100 * total_profit / total_cost if total_cost != 0 else 0

    print("\n📈 Resumo da Carteira:")
    print(f"- Valor Investido: {format_currency(total_cost)}")
    print(f"- Valor Atual:     {format_currency(total_value)}")
    print(f"- Lucro Total:     {format_currency(total_profit)}")
    print(f"- Rentabilidade:   {format_percent(total_profit_pct)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Caminho para o CSV de simulação")
    args = parser.parse_args()
    evaluate_simulation(args.input)
