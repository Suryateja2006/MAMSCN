# # test_synthetic_attacks_hybrid_with_mysql.py
# import os
# import json
# import joblib
# import numpy as np
# import pandas as pd
# from datetime import datetime
# from dotenv import load_dotenv
# import mysql.connector

# # --- Load environment variables (optional .env) ---
# load_dotenv()

# # --- Load model artifacts ---
# print("[INFO] Loading models...")
# scaler_if = joblib.load("models/scaler.pkl")
# model_if = joblib.load("models/isolation_forest_model.pkl")
# feature_order = joblib.load("models/feature_order.pkl")

# # classification model artifacts
# model_cls = joblib.load("models/anomaly_classifier.pkl")
# scaler_cls = joblib.load("models/classifier_scaler.pkl")
# label_encoder = joblib.load("models/label_encoder.pkl")

# print("[INFO] Models loaded successfully ✅")

# # --- Base normal sample ---
# def base_sample():
#     s = {f: 0.0 for f in feature_order}
#     if 'ifInOctets11' in s: s['ifInOctets11'] = 1_000_000
#     if 'ifOutOctets11' in s: s['ifOutOctets11'] = 900_000
#     if 'tcpInSegs' in s: s['tcpInSegs'] = 1000
#     if 'udpInDatagrams' in s: s['udpInDatagrams'] = 100
#     if 'ipInReceives' in s: s['ipInReceives'] = 1200
#     if 'icmpInMsgs' in s: s['icmpInMsgs'] = 5
#     return s

# # --- Synthetic attack generators ---
# def synth_udp_flood(base, intensity=50):
#     s = base.copy()
#     if 'udpInDatagrams' in s: s['udpInDatagrams'] *= intensity
#     if 'ifInOctets11' in s: s['ifInOctets11'] *= intensity
#     if 'ipInReceives' in s: s['ipInReceives'] *= intensity
#     return s

# def synth_tcp_syn_flood(base, intensity=50):
#     s = base.copy()
#     if 'tcpInSegs' in s: s['tcpInSegs'] *= intensity
#     if 'tcpPassiveOpens' in s: s['tcpPassiveOpens'] *= intensity
#     if 'tcpRetransSegs' in s: s['tcpRetransSegs'] *= intensity / 5
#     return s

# def synth_http_flood(base, intensity=30):
#     s = base.copy()
#     if 'ipOutRequests' in s: s['ipOutRequests'] *= intensity
#     if 'ifInUcastPkts11' in s: s['ifInUcastPkts11'] *= intensity
#     if 'ifInOctets11' in s: s['ifInOctets11'] *= (intensity // 2)
#     return s

# # --- Testing helper ---
# def test_sample(sample_dict):
#     df = pd.DataFrame([sample_dict]).reindex(columns=feature_order, fill_value=0)

#     # Scale for Isolation Forest
#     X_if = scaler_if.transform(df)
#     score = float(model_if.decision_function(X_if)[0])
#     pred = int(model_if.predict(X_if)[0])  # 1 = normal, -1 = anomaly
#     flag = "Normal" if pred == 1 else "Anomaly"

#     anomaly_type = None
#     if flag == "Anomaly":
#         # Also scale for classifier
#         X_cls = scaler_cls.transform(df)
#         pred_cls = model_cls.predict(X_cls)
#         anomaly_type = label_encoder.inverse_transform(pred_cls)[0]

#     # return score as float for JSON/DB friendliness
#     return score, flag, anomaly_type

# # --- MySQL helper: create connection & ensure table exists ---
# def get_db_connection():
#     db = mysql.connector.connect(
#         host=os.getenv("DB_HOST", "localhost"),
#         user=os.getenv("DB_USER", "root"),
#         password=os.getenv("DB_PASSWORD", "Aakash10"),
#         database=os.getenv("DB_NAME", "mon"),
#         autocommit=False
#     )
#     return db

# def ensure_table(cursor):
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS snmp_metrics_ai1 (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         host VARCHAR(255),
#         ip VARCHAR(50),
#         collector_hostname VARCHAR(255),
#         timestamp VARCHAR(30),
#         results JSON,
#         anomaly_score FLOAT,
#         anomaly_flag VARCHAR(20),
#         anomaly_type VARCHAR(50),
#         anomaly_timestamp VARCHAR(30)
#     )
#     """)

# def insert_sample_into_db(cursor, rec):
#     cursor.execute("""
#         INSERT INTO snmp_metrics_ai1 (
#             host, ip, collector_hostname, timestamp, results,
#             anomaly_score, anomaly_flag, anomaly_type, anomaly_timestamp
#         )
#         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#     """, (
#         rec.get("host"),
#         rec.get("ip"),
#         rec.get("collector_hostname"),
#         rec.get("timestamp"),
#         json.dumps(rec.get("results")),  # stored as JSON text
#         rec.get("anomaly_score"),
#         rec.get("anomaly_flag"),
#         rec.get("anomaly_type"),
#         rec.get("anomaly_timestamp")
#     ))

# # --- Main test block ---
# if __name__ == "__main__":
#     # Connect to DB and ensure table exists
#     try:
#         db = get_db_connection()
#         cursor = db.cursor()
#         ensure_table(cursor)
#         db.commit()
#         print("[DB] Connected and table ensured")
#     except Exception as e:
#         print(f"[DB] Connection or table creation failed: {e}")
#         db = None
#         cursor = None

#     base = base_sample()

#     # function to log to db (if available) for a given sample and prediction results
#     def log_sample_to_db(sample_dict, score, flag, anomaly_type, host="synthetic_host", ip="127.0.0.1", collector="synth_collector"):
#         rec = {
#             "host": host,
#             "ip": ip,
#             "collector_hostname": collector,
#             "timestamp": datetime.now().isoformat(),
#             "results": sample_dict,
#             "anomaly_score": score,
#             "anomaly_flag": flag,
#             "anomaly_type": anomaly_type,
#             "anomaly_timestamp": datetime.now().isoformat() if flag == "Anomaly" else None
#         }
#         if cursor:
#             try:
#                 insert_sample_into_db(cursor, rec)
#                 db.commit()
#                 print(f"[DB] Inserted record for {rec['ip']} (flag={flag}, type={anomaly_type})")
#             except Exception as e:
#                 db.rollback()
#                 print(f"[DB] Insert failed: {e}")
#         else:
#             print("[DB] No DB connection - skipping insert")

#     # test base sample
#     s_score, s_flag, s_type = test_sample(base)
#     print(f"Base: Score={s_score:.4f}, Flag={s_flag}, Type={s_type or 'N/A'}")
#     log_sample_to_db(base, s_score, s_flag, s_type)

#     # UDP flood
#     udp = synth_udp_flood(base, intensity=100)
#     score_udp, flag_udp, type_udp = test_sample(udp)
#     print(f"UDP: Score={score_udp:.4f}, Flag={flag_udp}, Type={type_udp or 'N/A'}")
#     log_sample_to_db(udp, score_udp, flag_udp, type_udp, host="synthetic_udp_host", ip="10.0.0.100")

#     # SYN flood
#     syn = synth_tcp_syn_flood(base, intensity=80)
#     score_syn, flag_syn, type_syn = test_sample(syn)
#     print(f"SYN: Score={score_syn:.4f}, Flag={flag_syn}, Type={type_syn or 'N/A'}")
#     log_sample_to_db(syn, score_syn, flag_syn, type_syn, host="synthetic_syn_host", ip="10.0.0.101")

#     # HTTP flood
#     print("\n=== SYNTHETIC HTTP FLOOD ===")
#     http = synth_http_flood(base, intensity=60)
#     score_http, flag_http, type_http = test_sample(http)
#     print(f"HTTP: Score={score_http:.4f}, Flag={flag_http}, Type={type_http or 'N/A'}")
#     log_sample_to_db(http, score_http, flag_http, type_http, host="synthetic_http_host", ip="10.0.0.102")

#     # Close DB connection cleanly
#     if db:
#         cursor.close()
#         db.close()
#         print("[DB] Connection closed")


import random
import joblib
import numpy as np
import pandas as pd

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
DATASET_PATH = "datasets/all_data (3).csv"
MODEL_DIR = "models"

# ------------------------------------------------------------
# LOAD DATASET
# ------------------------------------------------------------
print("\n[INFO] Loading dataset...")

df = pd.read_csv(DATASET_PATH)

print(f"[INFO] Dataset Shape: {df.shape}")
print(f"[INFO] Classes Found: {df['class'].unique()}")

# ------------------------------------------------------------
# FEATURES
# ------------------------------------------------------------
TARGET_COLUMN = "class"

feature_columns = [
    col for col in df.columns
    if col != TARGET_COLUMN
]

print(f"[INFO] Total Features/OIDs: {len(feature_columns)}")

# ------------------------------------------------------------
# LOAD MODELS
# ------------------------------------------------------------
print("\n[INFO] Loading models...")

scaler_if = joblib.load(f"{MODEL_DIR}/scaler.pkl")
isolation_model = joblib.load(f"{MODEL_DIR}/isolation_forest_model.pkl")
feature_order = joblib.load(f"{MODEL_DIR}/feature_order.pkl")

classifier_model = joblib.load(f"{MODEL_DIR}/anomaly_classifier.pkl")
classifier_scaler = joblib.load(f"{MODEL_DIR}/classifier_scaler.pkl")
label_encoder = joblib.load(f"{MODEL_DIR}/label_encoder.pkl")

print("[INFO] Models loaded successfully ✅")

# ------------------------------------------------------------
# GET ANOMALY CLASSES
# ------------------------------------------------------------
anomaly_classes = [
    c for c in df[TARGET_COLUMN].unique()
    if c.lower() != "normal"
]

print("\n[INFO] Anomaly Classes:")
for c in anomaly_classes:
    print("   -", c)

# ------------------------------------------------------------
# BETTER SYNTHETIC GENERATOR
# ------------------------------------------------------------
# IDEA:
# Instead of multiplying random numbers blindly,
# we learn from REAL attack rows.
#
# Steps:
# 1. Pick a real row from that attack class
# 2. Add small noise
# 3. Scale important traffic features naturally
# 4. Keep realistic relationships between OIDs
# ------------------------------------------------------------


def generate_synthetic_sample(class_name):

    class_df = df[df[TARGET_COLUMN] == class_name]

    # Pick one REAL attack row
    base_row = class_df.sample(1).iloc[0]

    synthetic = {}

    for col in feature_columns:

        value = float(base_row[col])

        # Small realistic noise
        noise_percent = random.uniform(-0.15, 0.15)
        noisy_value = value + (value * noise_percent)

        # Prevent negatives
        noisy_value = max(noisy_value, 0)

        synthetic[col] = noisy_value

    # --------------------------------------------------------
    # ATTACK-SPECIFIC AMPLIFICATION
    # --------------------------------------------------------

    if class_name == "udp-flood":

        boost_cols = [
            "udpInDatagrams",
            "ipInReceives",
            "ifInOctets11",
            "ifInUcastPkts11"
        ]

        for col in boost_cols:
            if col in synthetic:
                synthetic[col] *= random.uniform(1.3, 2.2)

    elif class_name == "tcp-syn":

        boost_cols = [
            "tcpInSegs",
            "tcpPassiveOpens",
            "tcpRetransSegs",
            "tcpOutRsts"
        ]

        for col in boost_cols:
            if col in synthetic:
                synthetic[col] *= random.uniform(1.5, 2.5)

    elif class_name == "httpFlood":

        boost_cols = [
            "ipOutRequests",
            "ifInOctets11",
            "ifOutOctets11",
            "tcpInSegs"
        ]

        for col in boost_cols:
            if col in synthetic:
                synthetic[col] *= random.uniform(1.4, 2.3)

    elif class_name == "icmp-echo":

        boost_cols = [
            "icmpInMsgs",
            "icmpOutMsgs",
            "icmpInEchos",
            "icmpOutEchoReps"
        ]

        for col in boost_cols:
            if col in synthetic:
                synthetic[col] *= random.uniform(1.6, 3.0)

    elif class_name == "slowloris":

        boost_cols = [
            "tcpPassiveOpens",
            "tcpCurrEstab",
            "tcpInSegs"
        ]

        for col in boost_cols:
            if col in synthetic:
                synthetic[col] *= random.uniform(1.2, 1.8)

    elif class_name == "slowpost":

        boost_cols = [
            "tcpInSegs",
            "ipInReceives",
            "tcpCurrEstab"
        ]

        for col in boost_cols:
            if col in synthetic:
                synthetic[col] *= random.uniform(1.2, 1.9)

    elif class_name == "bruteForce":

        boost_cols = [
            "tcpPassiveOpens",
            "tcpAttemptFails",
            "tcpInSegs"
        ]

        for col in boost_cols:
            if col in synthetic:
                synthetic[col] *= random.uniform(1.5, 2.4)

    return synthetic


# ------------------------------------------------------------
# MODEL TEST FUNCTION
# ------------------------------------------------------------
def test_sample(sample_dict):

    sample_df = pd.DataFrame([sample_dict])

    # Ensure same feature order
    sample_df = sample_df.reindex(columns=feature_order, fill_value=0)

    # --------------------------------------------------------
    # ISOLATION FOREST
    # --------------------------------------------------------
    scaled_if = scaler_if.transform(sample_df)

    anomaly_score = float(
        isolation_model.decision_function(scaled_if)[0]
    )

    anomaly_prediction = int(
        isolation_model.predict(scaled_if)[0]
    )

    anomaly_flag = (
        "Anomaly"
        if anomaly_prediction == -1
        else "Normal"
    )

    # --------------------------------------------------------
    # CLASSIFIER
    # --------------------------------------------------------
    predicted_attack = "normal"

    if anomaly_flag == "Anomaly":

        scaled_cls = classifier_scaler.transform(sample_df)

        cls_prediction = classifier_model.predict(scaled_cls)

        predicted_attack = label_encoder.inverse_transform(
            cls_prediction
        )[0]

    return {
        "score": anomaly_score,
        "flag": anomaly_flag,
        "predicted_attack": predicted_attack
    }


# ------------------------------------------------------------
# GENERATE SYNTHETIC DATA
# ------------------------------------------------------------
print("\n[INFO] Generating synthetic attacks...")

synthetic_rows = []

for attack_class in anomaly_classes:

    print(f"\n[CLASS] {attack_class}")

    for i in range(2):

        sample = generate_synthetic_sample(attack_class)

        result = test_sample(sample)

        sample["expected_class"] = attack_class
        sample["predicted_class"] = result["predicted_attack"]
        sample["anomaly_flag"] = result["flag"]
        sample["anomaly_score"] = result["score"]

        synthetic_rows.append(sample)

        print(
            f"   Sample {i+1} | "
            f"Expected={attack_class} | "
            f"Predicted={result['predicted_attack']} | "
            f"Flag={result['flag']} | "
            f"Score={result['score']:.4f}"
        )


# ------------------------------------------------------------
# SAVE RESULTS
# ------------------------------------------------------------
synthetic_df = pd.DataFrame(synthetic_rows)

OUTPUT_FILE = "synthetic_attack_test_results.csv"

synthetic_df.to_csv(OUTPUT_FILE, index=False)

print("\n==========================================")
print("[DONE] Synthetic testing completed ✅")
print(f"[DONE] Saved File: {OUTPUT_FILE}")
print("==========================================")


# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------
print("\n[SUMMARY]")

summary = synthetic_df[[
    "expected_class",
    "predicted_class",
    "anomaly_flag",
    "anomaly_score"
]]

print(summary)


# ------------------------------------------------------------
# OPTIONAL ACCURACY CHECK
# ------------------------------------------------------------
correct = (
    synthetic_df["expected_class"]
    == synthetic_df["predicted_class"]
).sum()

total = len(synthetic_df)

print(f"\nCorrect Classifications: {correct}/{total}")
print(f"Accuracy: {(correct / total) * 100:.2f}%")