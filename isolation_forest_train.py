# # ============================================
# # Network Anomaly Detection (Isolation Forest)
# # ============================================

# import pandas as pd
# import numpy as np
# import os
# from tqdm import tqdm
# import matplotlib.pyplot as plt
# from sklearn.preprocessing import StandardScaler
# from sklearn.ensemble import IsolationForest
# from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
# import joblib

# # -----------------------------
# # 1. Load Dataset
# # -----------------------------
# print("[INFO] Loading dataset...")
# base_path = "./datasets"
# file_name = "all_data (3).csv"
# df = pd.read_csv(os.path.join(base_path, file_name))

# print("[INFO] Dataset loaded:", df.shape)
# print("[INFO] Columns:", df.columns.tolist())

# # -----------------------------
# # 2. Identify label column (optional)
# # -----------------------------
# label_col = None
# for col in ["class", "Class", "label", "Label"]:
#     if col in df.columns:
#         label_col = col
#         break

# if label_col:
#     print(f"[INFO] Detected label column: '{label_col}'")
#     print(df[label_col].value_counts())

# # -----------------------------
# # 3. Select numeric columns only
# # -----------------------------
# df_num = df.select_dtypes(include=['float64', 'int64'])
# print(f"[INFO] Using {df_num.shape[1]} numeric features")

# # -----------------------------
# # 4. Scale the data
# # -----------------------------
# scaler = StandardScaler()
# X = scaler.fit_transform(df_num)

# # -----------------------------
# # 5. Train Isolation Forest (always)
# # -----------------------------
# print("\n[MODE] Unsupervised Isolation Forest")

# # Adjust contamination to a safe value if dataset is imbalanced
# contamination = 0.05
# iso = IsolationForest(contamination=contamination, random_state=42)

# print("[INFO] Training Isolation Forest...")
# for _ in tqdm(range(1), desc="Fitting Model"):
#     iso.fit(X)

# print("[INFO] Predicting anomalies...")
# y_pred = iso.predict(X)
# df['anomaly'] = np.where(y_pred == -1, 1, 0)

# # -----------------------------
# # 6. Evaluate (optional) if label exists
# # -----------------------------
# if label_col:
#     # Convert labels to 0/1 if needed
#     y_true = np.where(df[label_col] == 'normal', 0, 1)
#     print("\n[INFO] Evaluation against ground truth:")
#     print("Accuracy:", accuracy_score(y_true, df['anomaly']))
#     print("\nConfusion Matrix:\n", confusion_matrix(y_true, df['anomaly']))
#     print("\nClassification Report:\n", classification_report(y_true, df['anomaly']))

# # -----------------------------
# # 7. Visualize anomaly results
# # -----------------------------
# plt.figure(figsize=(6, 4))
# df['anomaly'].value_counts().plot(kind='bar', color=['green', 'red'])
# plt.title("Anomaly Distribution")
# plt.xticks(rotation=0)
# plt.xlabel("0 = Normal, 1 = Anomaly")
# plt.ylabel("Count")
# plt.tight_layout()
# plt.show()

# # -----------------------------
# # 8. Save Isolation Forest model, scaler, and feature order
# # -----------------------------
# os.makedirs("models", exist_ok=True)

# # Model
# model_path = "models/isolation_forest_model.pkl"
# joblib.dump(iso, model_path)

# # Scaler
# scaler_path = "models/scaler.pkl"
# joblib.dump(scaler, scaler_path)

# # Feature order
# feature_order_path = "models/feature_order.pkl"
# joblib.dump(df_num.columns.tolist(), feature_order_path)

# print(f"\n[INFO] Model saved at '{model_path}'")
# print(f"[INFO] Scaler saved at '{scaler_path}'")
# print(f"[INFO] Feature order saved at '{feature_order_path}'")

# print("\n[INFO] Training complete ✅")


# ============================================
# Network Anomaly Detection using Isolation Forest
# Proper Unsupervised Workflow
# ============================================

import pandas as pd
import numpy as np
import os
from tqdm import tqdm
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

import joblib

# =========================================================
# 1. LOAD DATASET
# =========================================================

print("\n[INFO] Loading dataset...")

base_path = "./datasets"
file_name = "all_data (3).csv"

file_path = os.path.join(base_path, file_name)

df = pd.read_csv(file_path)
df = df.head(3000)

print(f"[INFO] Dataset Loaded Successfully")
print(f"[INFO] Shape : {df.shape}")

# =========================================================
# 2. DETECT LABEL COLUMN
# =========================================================

label_col = None

possible_labels = ["class", "Class", "label", "Label", "attack", "Attack"]

for col in possible_labels:
    if col in df.columns:
        label_col = col
        break

if label_col is None:
    raise Exception(
        "[ERROR] No label column found.\n"
        "Expected one of: class, Class, label, Label"
    )

print(f"\n[INFO] Label Column Detected : {label_col}")

print("\n[INFO] Label Distribution:")
print(df[label_col].value_counts())

# =========================================================
# 3. CREATE BINARY GROUND TRUTH
# =========================================================
# 0 = Normal
# 1 = Attack / Anomaly

df[label_col] = df[label_col].astype(str).str.lower()

y_true = np.where(df[label_col] == "normal", 0, 1)

# =========================================================
# 4. SELECT NUMERIC FEATURES ONLY
# =========================================================

print("\n[INFO] Selecting Numeric Features...")

df_num = df.select_dtypes(include=["int64", "float64"]).copy()

# Remove label column if accidentally numeric
if label_col in df_num.columns:
    df_num.drop(columns=[label_col], inplace=True)

print(f"[INFO] Number of Features Used : {df_num.shape[1]}")

print("\n[INFO] Features:")
print(df_num.columns.tolist())

# =========================================================
# 5. HANDLE MISSING VALUES
# =========================================================

print("\n[INFO] Handling Missing Values...")

df_num = df_num.fillna(df_num.median())

# =========================================================
# 6. TRAIN ONLY ON NORMAL TRAFFIC
# =========================================================
# VERY IMPORTANT:
# Isolation Forest should learn NORMAL behavior only

print("\n[INFO] Preparing Normal Traffic for Training...")

normal_df = df[df[label_col] == "normal"]

X_train = normal_df[df_num.columns]

print(f"[INFO] Normal Training Samples : {X_train.shape[0]}")

# =========================================================
# 7. FEATURE SCALING
# =========================================================

print("\n[INFO] Scaling Features...")

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)

# Scale FULL dataset for testing
X_test_scaled = scaler.transform(df_num)

# =========================================================
# 8. TRAIN ISOLATION FOREST
# =========================================================

print("\n[INFO] Training Isolation Forest...")

# Since anomalies are rare in real networks,
# use a LOW contamination value

iso = IsolationForest(
    n_estimators=200,
    contamination=0.01,
    random_state=42,
    n_jobs=-1
)

for _ in tqdm(range(1), desc="Training Model"):
    iso.fit(X_train_scaled)

print("[INFO] Model Training Completed")

# =========================================================
# 9. PREDICT ANOMALIES
# =========================================================

print("\n[INFO] Detecting Anomalies...")

y_pred = iso.predict(X_test_scaled)

# IsolationForest:
#  1  = Normal
# -1  = Anomaly

df["anomaly"] = np.where(y_pred == -1, 1, 0)

# =========================================================
# 10. EVALUATION
# =========================================================

print("\n===================================")
print("MODEL EVALUATION")
print("===================================")

accuracy = accuracy_score(y_true, df["anomaly"])
precision = precision_score(y_true, df["anomaly"])
recall = recall_score(y_true, df["anomaly"])
f1 = f1_score(y_true, df["anomaly"])

print(f"\nAccuracy  : {accuracy:.4f}")
print(f"Precision : {precision:.4f}")
print(f"Recall    : {recall:.4f}")
print(f"F1 Score  : {f1:.4f}")

print("\nConfusion Matrix:")
print(confusion_matrix(y_true, df["anomaly"]))

print("\nClassification Report:")
print(classification_report(y_true, df["anomaly"]))

# =========================================================
# 11. SAVE MODEL
# =========================================================

print("\n[INFO] Saving Model Files...")

os.makedirs("models", exist_ok=True)

# Save model
joblib.dump(
    iso,
    "models/isolation_forest_model.pkl"
)

# Save scaler
joblib.dump(
    scaler,
    "models/scaler.pkl"
)

# Save feature order
joblib.dump(
    df_num.columns.tolist(),
    "models/feature_order.pkl"
)

print("\n[INFO] Files Saved Successfully")

print(" - models/isolation_forest_model.pkl")
print(" - models/scaler.pkl")
print(" - models/feature_order.pkl")

# =========================================================
# 12. SAVE RESULTS
# =========================================================

output_file = "models/anomaly_results.csv"

df.to_csv(output_file, index=False)

print(f"\n[INFO] Results Saved : {output_file}")

# =========================================================
# 14. FINAL SUMMARY
# =========================================================

print("\n===================================")
print("TRAINING COMPLETE")
print("===================================")

print(f"Total Samples     : {len(df)}")
print(f"Normal Samples    : {(y_true == 0).sum()}")
print(f"Attack Samples    : {(y_true == 1).sum()}")

print(f"\nDetected Anomalies : {df['anomaly'].sum()}")
print(f"Detected Normal    : {(df['anomaly'] == 0).sum()}")

print("\n[INFO] Isolation Forest Pipeline Completed Successfully")