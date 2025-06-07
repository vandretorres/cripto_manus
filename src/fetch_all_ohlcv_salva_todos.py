import os
import logging
from datetime import datetime
from binance.client import Client
import pandas as pd
from typing import Dict
from concurrent.futures import ThreadPoolExecutor
from config import API_KEY as API_KEY
from config import API_SECRET as API_SECRET

# Setup básico de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Configurações da Binance API (substituir por suas chaves ou variáveis de ambiente)
# Recomenda-se usar variáveis de ambiente para segurança

# Inicializa o cliente da Binance
client = Client(API_KEY, API_SECRET)

# Pares de criptomoedas (exemplo: BTCUSDT, ETHUSDT - adicione ou remova conforme desejar)
CRYPTO_PAIRS = [
    "BTCUSDT", "ETHUSDT", "XRPUSDT", "LTCUSDT", "ADAUSDT", "DOTUSDT", "SOLUSDT",
    "BNBUSDT", "DOGEUSDT", "MATICUSDT", "AVAXUSDT", "TRXUSDT", "LINKUSDT", "ATOMUSDT",
    "UNIUSDT", "XLMUSDT", "FILUSDT", "ICPUSDT", "AAVEUSDT", "NEARUSDT", "VETUSDT",
    "ALGOUSDT", "FTMUSDT", "SANDUSDT", "EGLDUSDT", "HBARUSDT", "XTZUSDT", "THETAUSDT"
]


# Intervalo de tempo (exemplo: Client.KLINE_INTERVAL_1d para dados diários)
INTERVAL = '1d'
''
# Datas (ajustar conforme a necessidade de dados históricos)
START_DATE = "1 Jan, 2017"
END_DATE = datetime.today().strftime("%d %b, %Y") # Formato compatível com python-binance

OUTPUT_DIR = "data/ohlcv"

def fetch_ohlcv_binance(symbol: str) -> pd.DataFrame:
    """
    Baixa dados OHLCV de um par de criptomoedas da Binance e formata o DataFrame.
    """
    try:
        # Obtém dados históricos
        klines = client.get_historical_klines(symbol, INTERVAL, START_DATE, END_DATE)

        if not klines:
            raise ValueError(f"Nenhum dado encontrado para {symbol}")

        # Converte para DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])

        # Converte timestamp para datetime e define como índice
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')

        # Seleciona e renomeia colunas relevantes e converte para tipo numérico
        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

        df.index.name = 'date'

        return df
    except Exception as e:
        logging.warning(f"[{symbol}] Erro ao baixar dados da Binance: {e}")
        return pd.DataFrame()  # Retorna vazio se falhar

def fetch_all_ohlcv(symbols: list[str]) -> Dict[str, pd.DataFrame]:
    """
    Coleta os dados OHLCV para todos os símbolos fornecidos em paralelo da Binance.
    """
    logging.info("Iniciando coleta dos dados OHLCV da Binance...")
    data = {}

    def process_symbol(s):
        df = fetch_ohlcv_binance(s)
        if not df.empty:
            data[s] = df

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_symbol, symbols)

    return data

def salvar_dados_ohlcv(data: Dict[str, pd.DataFrame], output_dir: str) -> None:
    """
    Salva os dados coletados em arquivos CSV.
    """
    os.makedirs(output_dir, exist_ok=True)
    for symbol, df in data.items():
        path = os.path.join(output_dir, f"{symbol}.csv")
        df.to_csv(path)
        logging.info(f"[{symbol}] salvo em {path}")

if __name__ == "__main__":
    # Certifique-se de configurar suas chaves de API da Binance
    if 'SUA_API_KEY' in API_KEY or 'SUA_API_SECRET' in API_SECRET:
        logging.warning("Por favor, configure suas chaves de API da Binance no arquivo ou variáveis de ambiente.")
    else:
        ohlcv_data = fetch_all_ohlcv(CRYPTO_PAIRS)
        salvar_dados_ohlcv(ohlcv_data, OUTPUT_DIR)

