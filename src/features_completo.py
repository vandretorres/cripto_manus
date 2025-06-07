import os
import logging
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
from typing import Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona indicadores técnicos ao DataFrame OHLCV.
    """
    df = df.copy()

    try:
        # Momentum
        df['rsi_14'] = RSIIndicator(close=df['close'], window=14).rsi()

        # Tendência
        macd = MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()

        df['adx'] = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).adx()

        # Volatilidade
        bb = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_hband'] = bb.bollinger_hband()
        df['bb_lband'] = bb.bollinger_lband()
        df['atr_14'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()

        # Médias móveis
        df['ma_10'] = df['close'].rolling(window=10).mean()
        df['ma_50'] = df['close'].rolling(window=50).mean()

        # Volume
        df['obv'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()

        return df
    except Exception as e:
        logging.error(f"Erro ao adicionar indicadores: {e}")
        return pd.DataFrame()

def processar_arquivo_ohlcv(input_path: str, output_path: str) -> Optional[str]:
    """
    Lê um arquivo OHLCV, adiciona indicadores e salva o resultado.
    """
    try:
        df = pd.read_csv(input_path, parse_dates=['date'])
        df.set_index('date', inplace=True)
        df_feat = add_technical_indicators(df)
        if not df_feat.empty:
            df_feat.to_csv(output_path)
            logging.info(f"[OK] {os.path.basename(input_path)} → {output_path}")
            return output_path
        else:
            logging.warning(f"[AVISO] Nenhum dado gerado para {input_path}.")
    except Exception as e:
        logging.error(f"[ERRO] {input_path}: {e}")
    return None

if __name__ == "__main__":
    input_dir = "data/ohlcv"
    output_dir = "data/features"
    os.makedirs(output_dir, exist_ok=True)

    arquivos_csv = [f for f in os.listdir(input_dir) if f.endswith(".csv")]
    for arquivo in arquivos_csv:
        input_path = os.path.join(input_dir, arquivo)
        output_path = os.path.join(output_dir, arquivo.replace(".csv", "_feat.csv"))
        processar_arquivo_ohlcv(input_path, output_path)
