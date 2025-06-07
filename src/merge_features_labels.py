import os
import pandas as pd

FEATURE_DIR = "data/features"
LABEL_DIR = "data/labels"
OUTPUT_DIR = "data/processed"
HORIZON = "5d"  # Pode ser "3d", "10d", etc.

os.makedirs(OUTPUT_DIR, exist_ok=True)

def merge_features_labels(ticker):
    feat_path = os.path.join(FEATURE_DIR, f"{ticker}_feat.csv")
    label_path = os.path.join(LABEL_DIR, f"{ticker}_label_{HORIZON}.csv")

    if not os.path.exists(feat_path):
        print(f"❌ Features não encontradas: {feat_path}")
        return
    if not os.path.exists(label_path):
        print(f"❌ Labels não encontradas: {label_path}")
        return

    df_feat = pd.read_csv(feat_path, parse_dates=["date"])
    df_label = pd.read_csv(label_path, parse_dates=["date"])

    # Detecta automaticamente a coluna de label correta
    label_cols = [col for col in df_label.columns if col.startswith("label_")]
    expected_label = f"label_{HORIZON}"
    if expected_label not in label_cols:
        print(f"⚠️ Coluna esperada '{expected_label}' não encontrada em {label_path}. Colunas disponíveis: {label_cols}")
        return

    # Merge e renomeação
    df_merged = pd.merge(df_feat, df_label[["date", expected_label]], on="date", how="left")
    df_merged = df_merged.rename(columns={expected_label: "target"})

    output_path = os.path.join(OUTPUT_DIR, f"{ticker}_merged.csv")
    df_merged.to_csv(output_path, index=False)
    print(f"✅ Merge salvo: {output_path}")

def main():
    files = [f for f in os.listdir(FEATURE_DIR) if f.endswith("_feat.csv")]
    tickers = [f.replace("_feat.csv", "") for f in files]

    print(f"🔍 Iniciando merge para {len(tickers)} ativos...")
    for ticker in tickers:
        merge_features_labels(ticker)

    print("🏁 Processo finalizado.")

if __name__ == "__main__":
    main()
