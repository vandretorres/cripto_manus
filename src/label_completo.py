import os
import pandas as pd
import numpy as np
import logging
import argparse
from typing import Literal

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def create_labels(df: pd.DataFrame, horizon: int, strategy: Literal['binary', 'triple', 'continuous'], threshold: float = 0.02) -> pd.DataFrame:
    """
    Cria labels com base na variação percentual futura.
    - binary: 1 se retorno > threshold, senão 0
    - triple: 1 se retorno > th, -1 se < -th, 0 caso contrário
    - continuous: retorna o valor contínuo do retorno futuro
    """
    df = df.copy()
    df = df.sort_index()  # Garante ordenação temporal
    #future_return = df['close'].pct_change(periods=horizon).shift(-horizon)
    future_return = df['close'].pct_change(periods=horizon, fill_method=None).shift(-horizon)

    if strategy == 'binary':
        label = (future_return > threshold).astype(int)
    elif strategy == 'triple':
        label = np.select(
            [future_return > threshold, future_return < -threshold],
            [1, -1],
            default=0
        )
    elif strategy == 'continuous':
        label = future_return
    else:
        raise ValueError(f"Estratégia inválida: {strategy}")

    return pd.DataFrame({
        'future_return': future_return,
        f'label_{horizon}d': label
    })

def calculate_dynamic_threshold(df: pd.DataFrame, horizon: int, multiplier: float = 1.0) -> float:
    """
    Calcula o threshold com base na volatilidade histórica.
    """
    daily_return = df['close'].pct_change()
    std_daily = daily_return.std()
    return std_daily * np.sqrt(horizon) * multiplier

def gerar_labels_para_arquivo(path: str, output_dir: str, horizons: list[int], strategy: str, threshold: float, use_dynamic: bool = False):
    """
    Lê um arquivo de features e gera labels salvos em CSV.
    """
    try:
        df = pd.read_csv(path, parse_dates=["date"])
        df.set_index("date", inplace=True)
        ticker = os.path.basename(path).replace("_feat.csv", "")

        for h in horizons:
            th = calculate_dynamic_threshold(df, h) if use_dynamic else threshold
            labels_df = create_labels(df, horizon=h, strategy=strategy, threshold=th)
            output_path = os.path.join(output_dir, f"{ticker}_label_{h}d.csv")
            labels_df.to_csv(output_path)
            logging.info(f"[OK] Labels {h}d salvos para {ticker} (threshold={th:.4f})")
    except Exception as e:
        logging.error(f"[ERRO] {path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador de labels para ML financeiro")
    parser.add_argument("--input_dir", type=str, default="data/features", help="Diretório de entrada com arquivos _feat.csv")
    parser.add_argument("--output_dir", type=str, default="data/labels", help="Diretório de saída")
    parser.add_argument("--horizons", type=int, nargs="+", default=[3, 5, 10], help="Horizontes em dias")
    parser.add_argument("--strategy", type=str, choices=["binary", "triple", "continuous"], default="binary", help="Tipo de label")
    parser.add_argument("--threshold", type=float, default=0.02, help="Threshold fixo (%)")
    parser.add_argument("--dynamic", action="store_true", help="Usar threshold dinâmico baseado na volatilidade")

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    arquivos = [f for f in os.listdir(args.input_dir) if f.endswith("_feat.csv")]
    for arquivo in arquivos:
        path = os.path.join(args.input_dir, arquivo)
        gerar_labels_para_arquivo(
            path=path,
            output_dir=args.output_dir,
            horizons=args.horizons,
            strategy=args.strategy,
            threshold=args.threshold,
            use_dynamic=args.dynamic
        )
