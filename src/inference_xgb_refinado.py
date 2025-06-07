import os
import pandas as pd
import argparse
import xgboost as xgb
import pickle
from datetime import datetime

# Caminhos diretos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
PROCESSED_PATH = os.path.join(ROOT_DIR, "data", "processed")
MODEL_PATH = os.path.join(ROOT_DIR, "data", "models")
SIGNALS_PATH = os.path.join(ROOT_DIR, "data", "signals")
HORIZON = 5

def detectar_coluna_target(df):
    """Tenta detectar automaticamente a coluna de label usada para previsão."""
    opcoes = [f"label_{HORIZON}d", "target"]
    for col in opcoes:
        if col in df.columns:
            return col
    raise ValueError(f"Nenhuma coluna de label encontrada. Esperado: {opcoes}")

def carregar_modelo(model_path):
    with open(model_path, "rb") as f:
        model = pickle.load(f)
        if isinstance(model, tuple):
            model = model[0]  # Assume (model, score)
    return model

def prever_e_rankear(threshold=0.3):
    sinais = []
    arquivos = [f for f in os.listdir(PROCESSED_PATH) if f.endswith("_merged.csv")]
    print(f"📁 {len(arquivos)} arquivos de dados processados encontrados.")

    for arquivo in arquivos:
        ticker = arquivo.split("_")[0]
        try:
            df = pd.read_csv(os.path.join(PROCESSED_PATH, arquivo))
            coluna_label = detectar_coluna_target(df)
            df = df.dropna(subset=[coluna_label]).copy()
            if df.empty:
                continue

            model_file = os.path.join(MODEL_PATH, f"{ticker}_xgb_model_refinado.pkl")
            if not os.path.exists(model_file):
                continue

            model = carregar_modelo(model_file)
            X = df.drop(columns=["date", coluna_label], errors="ignore").iloc[-1]
            proba = model.predict_proba([X])[0][1]

            if proba >= threshold:
                sinais.append({"ticker": ticker, "score": proba})

        except Exception as e:
            print(f"❌ Erro ao processar {ticker}: {e}")

    if sinais:
        df_sinais = pd.DataFrame(sinais)
        df_sinais = df_sinais.sort_values("score", ascending=False)
        os.makedirs(SIGNALS_PATH, exist_ok=True)
        output_file = os.path.join(SIGNALS_PATH, f"signals_ranked_{datetime.now().date()}.csv")
        df_sinais.to_csv(output_file, index=False)
        print(f"✅ Sinais salvos em: {output_file}")
        return df_sinais
    else:
        print("📭 Nenhum sinal gerado. Simulação não executada.")
        return pd.DataFrame()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.3, help="Probabilidade mínima para gerar sinal")
    args = parser.parse_args()

    print(f"🔍 Lendo modelo salvo de: {MODEL_PATH}")
    prever_e_rankear(threshold=args.threshold)
