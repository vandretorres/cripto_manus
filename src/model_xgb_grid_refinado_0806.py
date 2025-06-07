import os
import pandas as pd
import numpy as np
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import f1_score, make_scorer, roc_auc_score, precision_score, recall_score

print("🧠 Iniciando treinamento refinado dos modelos XGBoost...")

processed_dir = "data/processed"
model_dir = "data/models"
os.makedirs(model_dir, exist_ok=True)

resultados = []

for file in os.listdir(processed_dir):
    if not file.endswith("_merged.csv"):
        continue

    ticker = file.replace("_merged.csv", "")
    df = pd.read_csv(os.path.join(processed_dir, file))

    if "target" not in df.columns:
        print(f"⚠️  {ticker}: coluna 'target' não encontrada.")
        continue

    # Definir X e y
    X = df.drop(columns=["date", "target"], errors="ignore")
    y = df["target"]

    if y.nunique() < 2:
        print(f"⚠️  {ticker}: apenas uma classe presente no target.")
        continue

    # Cálculo do peso para lidar com desbalanceamento
    ratio = (y == 0).sum() / max((y == 1).sum(), 1)
    scale_pos_weight = round(ratio, 2)

    # Definir modelo base
    xgb = XGBClassifier(
        objective="binary:logistic",
        use_label_encoder=False,
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbosity=0
    )

    # Grade de parâmetros refinada
    param_grid = {
        "max_depth": [3, 5],
        "learning_rate": [0.01, 0.1],
        "n_estimators": [100, 200],
        "subsample": [0.8],
        "colsample_bytree": [0.8],
        "gamma": [0, 1]
    }

    # Validação temporal
    tscv = TimeSeriesSplit(n_splits=5)
    scorer = make_scorer(f1_score)

    grid_search = GridSearchCV(
        xgb,
        param_grid,
        scoring=scorer,
        cv=tscv,
        n_jobs=-1,
        verbose=0
    )

    try:
        grid_search.fit(X, y)
        best_model = grid_search.best_estimator_

        # Avaliação no conjunto completo
        y_pred = best_model.predict(X)
        f1 = f1_score(y, y_pred)
        roc = roc_auc_score(y, best_model.predict_proba(X)[:, 1])
        precision = precision_score(y, y_pred)
        recall = recall_score(y, y_pred)

        joblib.dump({'model': best_model, 'features': list(X.columns)}, os.path.join(model_dir, f"{ticker}_xgb_model_refinado.pkl"))

        print(f"✅ Modelo treinado e salvo para {ticker} — F1: {f1:.4f} ROC AUC: {roc:.4f}")

        resultados.append({
            "ticker": ticker,
            "f1_score": round(f1, 4),
            "roc_auc": round(roc, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "scale_pos_weight": scale_pos_weight,
            "melhores_parametros": grid_search.best_params_
        })

    except Exception as e:
        print(f"❌ Erro ao treinar {ticker}: {e}")

# Salvar resultados
if resultados:
    df_resultados = pd.DataFrame(resultados)
    df_resultados.to_csv(os.path.join(model_dir, "modelo_refinado_resultados.csv"), index=False)
    print("📄 Resultados salvos em modelo_refinado_resultados.csv")
