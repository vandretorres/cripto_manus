import pandas as pd
import numpy as np
import argparse
import os
import pickle
from datetime import datetime
from tabulate import tabulate

# Define o caminho base para os dados e modelos
DATA_PATH = 'data'
MODELS_PATH = 'data/models'
BACKTEST_RESULTS_PATH = 'data/backtest_results'

# Garante que o diretório de resultados de backtest existe
os.makedirs(BACKTEST_RESULTS_PATH, exist_ok=True)

def load_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    file_path = os.path.join(DATA_PATH, 'processed', f'{symbol}_merged.csv')
    if not os.path.exists(file_path):
        print(f"[AVISO] Arquivo de dados não encontrado para {symbol}: {file_path}")
        return None

    df = pd.read_csv(file_path, parse_dates=['date'])  # <-- aqui o ajuste
    df.set_index('date', inplace=True)                # <-- aqui também

    df_filtered = df.loc[start_date:end_date].copy()

    if df_filtered.empty:
        print(f"[AVISO] Nenhum dado encontrado para {symbol} no período de {start_date} a {end_date}")
        return None

    return df_filtered

def load_model(symbol: str):
    """
    Carrega o modelo treinado para um dado símbolo.
    """
    #model_path = os.path.join(MODELS_PATH, f'model_xgb_{symbol}.pkl')
    model_path = os.path.join(MODELS_PATH, f"{symbol}_xgb_model_refinado.pkl")
    if not os.path.exists(model_path):
        print(f"[AVISO] Modelo não encontrado para {symbol}: {model_path}")
        return None

    with open(model_path, 'rb') as f:
        model_info = pickle.load(f)
    return {
        "model": model_info["model"],
        "features_names": model_info["features"]
    }

    return model

def run_backtest(
    capital: float,
    start_date: str,
    end_date: str,
    threshold: float = 0.5,
    allocation_per_trade_pct: float = 0.1,
    crypto_pairs: list[str] | None = None
):
    """
    Executa o backtest da estratégia de compra na segunda e venda na sexta.
    """
    print(f"\n🧠 Iniciando backtest com capital inicial de R$ {capital:,.2f} de {start_date} a {end_date}...".replace(",", "X").replace(".", ",").replace("X", "."))

    # Se nenhum par for especificado, tenta carregar todos os dados processados
    if crypto_pairs is None:
        processed_files = [f for f in os.listdir(os.path.join(DATA_PATH, 'processed')) if f.endswith('_merged.csv')]
        crypto_pairs = [f.replace('_merged.csv', '') for f in processed_files]

    if not crypto_pairs:
        print("[ERRO] Nenhuma criptomoeda encontrada para backtest. Certifique-se de que os dados mesclados foram gerados.")
        return

    all_data = {}
    all_models = {}

    # Carregar dados e modelos para todos os pares
    for symbol in crypto_pairs:
        data = load_data(symbol, start_date, end_date)
        model_data = load_model(symbol)
        if data is not None and model_data is not None:
            all_data[symbol] = data
            all_models[symbol] = model_data

    if not all_data:
        print("[ERRO] Nenhum dado ou modelo carregado com sucesso para o período e pares especificados.")
        return

    # Obter todas as datas únicas no período de backtest a partir dos dados carregados
    all_dates = sorted(list(set(date for data in all_data.values() for date in data.index)))

    portfolio = {
        'capital': capital,
        'positions': {},
        'trade_log': []
    }

    initial_capital = capital

    for current_date in all_dates:
        day_of_week = current_date.dayofweek # Segunda=0, Sexta=4

        # Lógica de Compra (Segunda-feira)
        if day_of_week == 0: # Segunda-feira
            print(f"\n📅 {current_date.strftime('%Y-%m-%d')} - Segunda-feira: Avaliando sinais de compra...")
            available_capital_for_trades = portfolio['capital'] * allocation_per_trade_pct

            for symbol, data in all_data.items():
                # Garantir que temos dados até o dia anterior para predição
                data_until_yesterday = data.loc[data.index < current_date]
                if data_until_yesterday.empty:
        continue
    continue
# Usar o último dia disponível para predição
                latest_data_point = data_until_yesterday.iloc[-1]

                # Fazer predição usando o modelo de 5 dias
                # O modelo espera features, excluir colunas de label e timestamp
                features = latest_data_point[features_names]

                # Garantir que a ordem das features é a mesma do treinamento
                # Isso pode exigir carregar as colunas usadas no treinamento ou garantir consistência
                # Por enquanto, assumimos que a ordem está correta ou que o modelo lida com isso.
                # Uma implementação mais robusta carregaria as colunas de features usadas no treino.


                model_data = all_models.get(symbol)
                if model_data is None:
                continue
                model = model_data["model"]
                features_names = model_data["features_names"]

                try:
                    # A predição de 5 dias usaria a label 'label_5d'
                    # O modelo prediz a probabilidade da label ser 1
                    prediction_proba = model.predict_proba(features.values.reshape(1, -1))[:, 1]
                    signal = prediction_proba[0]

                    print(f"  - {symbol}: Sinal de 5 dias = {signal:.4f}")

                    if signal >= threshold and symbol not in portfolio['positions']:
                        # Obter o preço de compra (preço de abertura do dia atual, se disponível)
                        if current_date in data.index:
                            buy_price = data.loc[current_date]['open']
                            if pd.notna(buy_price) and available_capital_for_trades > 0:
                                # Calcular quantidade fracionária a comprar
                                quantity_to_buy = available_capital_for_trades / buy_price

                                # Simular a compra
                                cost = quantity_to_buy * buy_price
                                portfolio['capital'] -= cost
                                portfolio['positions'][symbol] = {
                                    'quantity': quantity_to_buy,
                                    'buy_price': buy_price,
                                    'buy_date': current_date
                                }
                                portfolio['trade_log'].append({
                                    'date': current_date,
                                    'symbol': symbol,
                                    'type': 'BUY',
                                    'quantity': quantity_to_buy,
                                    'price': buy_price,
                                    'total_value': cost,
                                    'capital_after_trade': portfolio['capital']
                                })
                                print(f"    ✅ COMPRA: {quantity_to_buy:.8f} de {symbol} @ {buy_price:,.8f} (Custo: {cost:,.2f})".replace(",", "X").replace(".", ",").replace("X", "."))
                                available_capital_for_trades = 0 # Aloca capital apenas para um trade por segunda-feira para simplificar
                        else:
                             print(f"    [AVISO] Dados de preço de abertura não disponíveis para {symbol} em {current_date.strftime('%Y-%m-%d')}. Pulando compra.")

                except Exception as e:
                    print(f"    [ERRO] Falha ao fazer predição ou simular compra para {symbol}: {e}")

        # Lógica de Venda (Sexta-feira)
        elif day_of_week == 4: # Sexta-feira
            print(f"\n📅 {current_date.strftime('%Y-%m-%d')} - Sexta-feira: Avaliando posições para venda...")
            positions_to_sell = list(portfolio['positions'].keys())

            for symbol in positions_to_sell:
                 if current_date in all_data[symbol].index:
                    sell_price = all_data[symbol].loc[current_date]['close']
                    if pd.notna(sell_price):
                        position = portfolio['positions'][symbol]
                        quantity = position['quantity']
                        buy_price = position['buy_price']
                        buy_date = position['buy_date']

                        # Simular a venda
                        revenue = quantity * sell_price
                        profit = revenue - (quantity * buy_price)
                        portfolio['capital'] += revenue

                        portfolio['trade_log'].append({
                            'date': current_date,
                            'symbol': symbol,
                            'type': 'SELL',
                            'quantity': quantity,
                            'price': sell_price,
                            'total_value': revenue,
                            'capital_after_trade': portfolio['capital']
                        })
                        print(f"    ✅ VENDA: {quantity:.8f} de {symbol} @ {sell_price:,.8f} (Receita: {revenue:,.2f}, Lucro: {profit:,.2f})".replace(",", "X").replace(".", ",").replace("X", "."))

                        # Remover posição
                        del portfolio['positions'][symbol]
                    else:
                         print(f"    [AVISO] Dados de preço de fechamento não disponíveis para {symbol} em {current_date.strftime('%Y-%m-%d')}. Pulando venda.")

    # Calcular métricas finais
    final_capital = portfolio['capital']
    total_value_held = 0
    for symbol, position in portfolio['positions'].items():
        # Se houver posições abertas no final do período, usar o último preço disponível para calcular o valor
        if symbol in all_data and not all_data[symbol].empty:
             last_price = all_data[symbol].iloc[-1]['close']
             if pd.notna(last_price):
                total_value_held += position['quantity'] * last_price

    final_portfolio_value = final_capital + total_value_held
    total_profit = final_portfolio_value - initial_capital
    total_return_pct = (total_profit / initial_capital) * 100 if initial_capital != 0 else 0

    print("\n📊 Resumo do Backtest:")
    print(f"- Capital Inicial:   R$ {initial_capital:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    print(f"- Capital Final:     R$ {final_portfolio_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    print(f"- Lucro/Prejuízo:    R$ {total_profit:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    print(f"- Retorno Total:     {total_return_pct:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."))
    print(f"- Total de Trades:   {len([t for t in portfolio['trade_log'] if t['type'] == 'BUY'])}")

    # Salvar log de trades
    if portfolio['trade_log']:
        trade_log_df = pd.DataFrame(portfolio['trade_log'])
        trade_log_filename = f'backtest_trade_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv'
        trade_log_path = os.path.join(BACKTEST_RESULTS_PATH, trade_log_filename)
        trade_log_df.to_csv(trade_log_path, index=False)
        print(f"\n📄 Log de trades salvo em: {trade_log_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capital", type=float, default=10000.0, help="Capital inicial para o backtest")
    parser.add_argument("--start_date", type=str, required=True, help="Data de início do backtest (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, required=True, help="Data de fim do backtest (YYYY-MM-DD)")
    parser.add_argument("--threshold", type=float, default=0.5, help="Threshold de probabilidade para sinal de compra")
    parser.add_argument("--allocation_per_trade_pct", type=float, default=0.1, help="Porcentagem do capital alocado por trade")
    # Adicionar argumento opcional para especificar pares de criptomoedas
    parser.add_argument("--crypto_pairs", nargs='+', help="Lista de pares de criptomoedas para backtest (ex: BTCUSDT ETHUSDT)")

    args = parser.parse_args()

    run_backtest(
        capital=args.capital,
        start_date=args.start_date,
        end_date=args.end_date,
        threshold=args.threshold,
        allocation_per_trade_pct=args.allocation_per_trade_pct,
        crypto_pairs=args.crypto_pairs
    )