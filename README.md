## MAMSCN: Multi-Agent Monitoring System with SNMP + AI Anomaly Detection

This repository implements a full network monitoring pipeline that:

1. Polls SNMP metrics from devices.
2. Streams metrics to Kafka.
3. Consumes and scores the stream with AI models.
4. Stores enriched anomaly results in MySQL and CSV.
5. Supports visualization through Grafana.

The project combines unsupervised anomaly detection (Isolation Forest) with supervised anomaly type classification (Random Forest classifier).

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Setup and Run (End-to-End)](#setup-and-run-end-to-end)
- [Model Training](#model-training)
- [Data Contracts (CSV/JSON/DB)](#data-contracts-csvjsondb)
- [SNMP Simulator Notes](#snmp-simulator-notes)
- [Testing with Synthetic Attacks](#testing-with-synthetic-attacks)
- [Outputs and Artifacts](#outputs-and-artifacts)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)

## What This Project Does

The pipeline continuously collects SNMP OID counters from target devices listed in `inventory.csv`. Each poll cycle creates a Kafka message containing all OID values for one device. The consumer then:

- maps raw OIDs to model feature names,
- aligns/normalizes feature vectors,
- computes an anomaly score using Isolation Forest,
- classifies anomaly type (only for detected anomalies),
- persists results in MySQL and CSV.

## Architecture

High-level flow:

```text
SNMP Device(s) / SNMP Simulator
						|
						v
		 snmp_producer.py
 (async SNMP poll + Kafka publish)
						|
						v
			Kafka topic: snmp_metrics
						|
						v
	consumer_writer_snmp.py
 (OID mapping + IF score + class label)
						|
						+----> MySQL table: snmp_metrics_ai
						|
						+----> CSV: snmp_consumed_ai.csv
						|
						+----> Grafana dashboards (via MySQL datasource)
```

Infrastructure services are defined in `docker-compose.yml`:

- Zookeeper: `localhost:2181`
- Kafka broker: `localhost:9092`
- MySQL: `localhost:3307` (container 3306)
- Grafana: `localhost:3001`

## Repository Structure

- `snmp_producer.py`: asynchronous SNMP poller and Kafka producer.
- `consumer_writer_snmp.py`: Kafka consumer, anomaly scoring/classification, DB + CSV writer.
- `isolation_forest_train.py`: trains and saves Isolation Forest artifacts.
- `classification.py`: trains and saves supervised anomaly classifier artifacts.
- `test_synthetic_attack.py`: injects synthetic attack-like samples and logs outputs into DB.
- `train_anomaly.py`: older standalone training script (different dataset path convention).
- `inventory.csv`: device inventory and OID list to poll.
- `datasets/all_data (3).csv`: training dataset.
- `models/`: serialized model artifacts used at inference time.
- `snmp-sim-data/`, `snmpsim-data/`: SNMP simulator record files.
- `docker-compose.yml`: local infra stack for Kafka/MySQL/Grafana.

## Prerequisites

- Python 3.9+
- Docker Desktop
- (Optional) SNMP simulator tooling if you want simulated agents

Install Python dependencies:

```bash
pip install pandas numpy scikit-learn joblib tqdm matplotlib kafka-python pysnmp mysql-connector-python python-dotenv
```

Optional simulator package:

```bash
pip install snmpsim
```

## Environment Configuration

`consumer_writer_snmp.py` and `test_synthetic_attack.py` read DB configuration from `.env`.

Create a `.env` in the project root:

```env
DB_HOST=localhost
DB_USER=snmpuser
DB_PASSWORD=snmppass
DB_NAME=snmp_db
```

Why this is important:

- The Docker Compose MySQL service creates `snmp_db` with user `snmpuser`.
- Script defaults currently point to different credentials/database if `.env` is absent.
- Providing `.env` keeps runtime aligned with your container setup.

## Setup and Run (End-to-End)

### 1. Start infrastructure

```bash
docker compose up -d
```

### 2. Train or verify model artifacts

If `models/` already contains required files, you can skip this. Otherwise run:

```bash
python isolation_forest_train.py
python classification.py
```

Required inference artifacts:

- `models/isolation_forest_model.pkl`
- `models/scaler.pkl`
- `models/feature_order.pkl`
- `models/anomaly_classifier.pkl`
- `models/classifier_scaler.pkl`
- `models/label_encoder.pkl`

### 3. Configure inventory and SNMP targets

`inventory.csv` format:

```csv
hostname,ip,community,oids
localhost,127.0.0.1:161,public,OID1;OID2;OID3
```

Notes:

- `ip` must include port (`host:port`).
- `oids` must be semicolon-separated.

### 4. Start consumer

```bash
python consumer_writer_snmp.py
```

### 5. Start producer

```bash
python snmp_producer.py
```

The producer polls every 10 seconds (`POLL_INTERVAL=10`) and publishes to Kafka topic `snmp_metrics`.

### 6. Visualize in Grafana (optional)

- Open `http://localhost:3001`
- Login: `admin / admin`
- Add MySQL datasource using your `.env` DB credentials
- Build panels from `snmp_metrics_ai`

## Model Training

### Isolation Forest (`isolation_forest_train.py`)

- Loads `datasets/all_data (3).csv`.
- Uses numeric columns only.
- Standardizes features with `StandardScaler`.
- Trains `IsolationForest(contamination=0.05, random_state=42)`.
- Optionally evaluates if a label column exists (`class`, `Class`, `label`, `Label`).
- Saves model, scaler, and feature order.

### Classification (`classification.py`)

- Loads same dataset and detects label column.
- Uses numeric features and label encoding.
- Splits train/test with stratification.
- Trains `RandomForestClassifier`.
- Saves classifier scaler + model + label encoder.

### Runtime logic in consumer

1. Convert OIDs to canonical feature names via `OID_TO_FEATURE`.
2. Reindex input to `feature_order` (missing values filled with 0).
3. Score with Isolation Forest.
4. If score below threshold (`ANOMALY_THRESHOLD=-0.1`), classify anomaly type.
5. Persist enriched record.

## Data Contracts (CSV/JSON/DB)

### Kafka message schema (`snmp_metrics`)

Produced by `snmp_producer.py`:

```json
{
	"host": "localhost",
	"ip": "127.0.0.1:161",
	"collector_hostname": "local-producer",
	"timestamp": "2026-03-27T10:00:00.000000",
	"results": {
		"1.3.6.1.2.1.2.2.1.10.11": "12345",
		"1.3.6.1.2.1.6.10.0": "678"
	}
}
```

### Producer CSV output

`snmp_polled_data.csv` columns:

- `hostname`
- `ip`
- `port`
- `community`
- `collector_hostname`
- `timestamp`
- `oid`
- `value`

### Consumer CSV output

`snmp_consumed_ai.csv` columns:

- `host`, `ip`, `collector_hostname`, `timestamp`
- `feature`, `value`
- `anomaly_score`, `anomaly_flag`, `anomaly_type`, `anomaly_timestamp`

### MySQL table

`snmp_metrics_ai` fields:

- identity/context: `id`, `host`, `ip`, `collector_hostname`, `timestamp`
- payload: `results` (JSON)
- AI outputs: `anomaly_score`, `anomaly_flag`, `anomaly_type`, `anomaly_timestamp`

## SNMP Simulator Notes

This repository includes simulator datasets under:

- `snmp-sim-data/`
- `snmpsim-data/`

Use these files with your preferred `snmpsim` command to emulate devices and map matching community/port settings in `inventory.csv`.

## Testing with Synthetic Attacks

Run:

```bash
python test_synthetic_attack.py
```

What it does:

- Loads both trained models and scalers.
- Generates synthetic baseline, UDP flood, SYN flood, and HTTP flood patterns.
- Evaluates anomaly score + anomaly type.
- Inserts test records into `snmp_metrics_ai` for validation.

## Outputs and Artifacts

Generated/updated during execution:

- `snmp_polled_data.csv`: raw polled OID rows from producer.
- `snmp_consumed_ai.csv`: feature-level scored output rows.
- `models/*.pkl`: serialized training artifacts.

## Troubleshooting

### Kafka connection errors

- Verify `docker compose ps` shows Kafka running.
- Confirm broker is reachable on `localhost:9092`.

### MySQL authentication/database errors

- Ensure `.env` values match Docker Compose values.
- Use host port `3307` externally (container maps `3307 -> 3306`).

### Missing model files

- Re-run training scripts:
	- `python isolation_forest_train.py`
	- `python classification.py`

### Consumer skips records with conversion errors

- Ensure SNMP values mapped in `OID_TO_FEATURE` are numeric.
- Validate OIDs in `inventory.csv` are consistent with those expected by the model feature map.

### No anomalies detected

- Adjust `ANOMALY_THRESHOLD` in `consumer_writer_snmp.py`.
- Revisit contamination setting during Isolation Forest training.

## Future Enhancements

- AI alert prioritization using sequence models (e.g., Transformer-based ranking).
- Analyst feedback loop from dashboard labels to automatic retraining.
- Automated remediation hooks (e.g., quarantine, firewall updates) after confirmed alerts.

---

