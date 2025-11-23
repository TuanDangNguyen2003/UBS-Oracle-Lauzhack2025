# UBS — Oracle Agent Spec: Fraud & Money Laundering Detection

Project applying Oracle's Agent Spec to detect fraudulent activity and money laundering patterns in a transaction dataset provided by UBS.

## Purpose
- Prototype an agent-driven pipeline that combines Oracle Agent Spec orchestration with data science and ML techniques to:  
    - detect anomalies and suspicious transaction patterns  
    - prioritize alerts for analyst review  
    - provide explainable signals to support compliance workflows

## Key Features
- Agent-based orchestration using Oracle Agent Spec principles (modular agents for ingestion, feature engineering, detection, and explainability)
- Supervised and unsupervised detection models (rule-based, anomaly detection, graph analysis, classifiers)
- Explainability artifacts for flagged cases (feature importances, counterfactual hints)
- Audit-friendly logging and data handling to meet compliance/privacy requirements

## Dataset
- Uses the transaction dataset provided by UBS (sensitive; access restricted)
- All data processing follows privacy and compliance constraints (anonymization, minimal retention, role-based access)
- Do not commit raw data to the repo

## Architecture (high-level)
- Ingestion Agent: validates and normalizes incoming transaction feeds
- Feature Agent: computes time-window features, aggregations, network/graph features
- Detection Agent(s): ensemble of detectors (rules, clustering/anomaly, supervised models)
- Triage Agent: scores and ranks alerts, attaches explanations
- Orchestration: agents communicate via standard Agent Spec messages; retries and audit logs

## Evaluation
- Metrics: precision, recall, F1, ROC-AUC for labeled cases; precision@k and alert workload for operational tuning
- Backtesting on historical labeled incidents; synthetic scenarios for edge cases
- Human-in-the-loop validation and feedback loop to retrain models

## Quickstart
1. Place UBS dataset in a secure, local directory (do NOT commit).
2. Create a virtual environment and install dependencies:
     - python >= 3.9
     - pip install -r requirements.txt
3. Configure credentials and sensitive paths in config/.env (examples provided in config/.env.example)
4. Run ingestion and a short pipeline run:
     - python -m agents.ingest --input /path/to/data
     - python -m agents.run_pipeline --config config/pipeline.yaml

(See docs/ for full deployment and agent-spec mapping.)

## Ethics & Compliance
- Designed for lawful, privacy-preserving use only
- Sensitive-data handling, access control, and explainability prioritized
- Intended to assist analysts — final decisions remain human responsibility

## Contributing & License
- Contributing: follow internal compliance and data handling guidelines before submitting code or experiments
- License: MIT (or internal UBS license as required)

Contact: project owners and compliance team listed in docs/OWNERS
