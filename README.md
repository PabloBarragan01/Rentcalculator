![Microsoft Fabric](https://img.shields.io/badge/Microsoft-Fabric-blue)
![Power BI](https://img.shields.io/badge/PowerBI-Analytics-yellow)
![Spark](https://img.shields.io/badge/Apache-Spark-orange)
![Delta Lake](https://img.shields.io/badge/Delta-Lake-green)

# Rent Calculator Argentina

End-to-end analytics engineering project built on Microsoft Fabric for calculating rental adjustments in Argentina using inflation indexes and the Casa Propia coefficient.
The solution implements a Medallion Architecture with automated ingestion pipelines, Delta Lake processing, semantic modeling, and interactive reporting in Power BI.

## Project Overview
This project automates the ingestion, transformation, storage, and visualization of Argentine economic indicators used for rental contract adjustments.
The platform integrates multiple public data sources, processes them through a Lakehouse architecture in Microsoft Fabric, and exposes curated analytical tables through a Power BI semantic model.
The final solution combines:
* Data Engineering
* Lakehouse Architecture
* Incremental ETL Pipelines
* Delta Lake Tables
* Semantic Modeling
* Business Intelligence Visualization

## Architecture
<img width="1722" height="222" alt="Screenshot 2026-05-21 165138" src="https://github.com/user-attachments/assets/9be62c9e-1c59-4627-8365-d9c3c4ee32d2" />
1. External Sources
2. Fabric Data Factory Pipelines
3. Bronze Lakehouse (Raw Files)
4. Fabric Spark Notebooks
5. Silver Lakehouse (Delta Tables)
6. Fabric SQL Endpoint
7. Power BI Semantic Model (PBIP)
8. Interactive Dashboard

## Tech Stack
* Microsoft Fabric
* Fabric Lakehouse
* Fabric Data Factory
* Apache Spark
* Delta Lake
* Python
* Power BI
* PBIP (Power BI Project)
* SQL Endpoint

## Data Sources
The project currently integrates:
* Argentine Inflation Index (IPC)
* Casa Propia Coefficient
These datasets are automatically ingested from publicly available sources and transformed into curated analytical tables.

## Engineering Features
### Medallion Architecture
The solution follows a layered Lakehouse design:
#### Bronze Layer
* Raw ingestion
* Source preservation
* Historical snapshots
#### Silver Layer
* Curated Delta tables
* Standardized schemas
* Incremental processing
* Deduplication logic
* Type enforcement

## Incremental ETL Processing
The Silver layer implements idempotent incremental ingestion using business date validation and anti-join strategies to prevent duplicate processing.
Example features:
* Incremental append logic
* Duplicate prevention
* Schema standardization
* Atomic write patterns

## Delta Lake Integration
Curated datasets are persisted as Delta Tables in Fabric Lakehouse to support:
* SQL Endpoint querying
* Power BI connectivity
* Transactional consistency
* Scalable analytical workloads

## Operational Logging
All ETL notebooks generate execution logs including:
* Execution timestamp
* Process status
* Source file processed
* Rows ingested
* Total rows in Silver layer

## Pipeline Orchestration
ETL execution is orchestrated through Fabric Data Factory pipelines, enabling automated and repeatable data refresh workflows.
<img width="1014" height="299" alt="image" src="https://github.com/user-attachments/assets/911ee0f1-0942-4e3f-a16b-82bdbb1b9635" />

## Repository Structure

```text
fabric-rent-calculator-argentina/
│
├── README.md
│
├── architecture/
│   ├── medallion_architecture.png
│   ├── data_flow.png
│   └── semantic_model.png
│
├── notebooks/
│   ├── bronze/
│   │   ├── ipc_download.py
│   │   └── casapropia_download.py
│   │
│   └── silver/
│       ├── ipc_silver.py
│       └── casapropia_silver.py
│
├── powerbi/
│   ├── RentCalculatorArgentina.pbip
│   ├── semantic_model/
│   └── reports/
│
├── screenshots/
│   ├── fabric_pipeline.png
│   ├── lakehouse_tables.png
│   ├── sql_endpoint.png
│   ├── semantic_model.png
│   └── dashboard.png
│
└── docs/
    ├── architecture.md
    ├── orchestration.md
    └── data_model.md
```

## Power BI Integration
The curated Silver Delta tables are exposed through the Fabric SQL Endpoint and consumed by a Power BI semantic model developed using PBIP.
The reporting layer provides:
* Rental adjustment calculations
* Inflation trend analysis
* Casa Propia coefficient evolution
* Comparative metrics

## Future Improvements
Potential future enhancements include:
* MERGE-based upsert logic
* Historical versioning
* Gold analytical layer
* Automated testing
* CI/CD integration
* Data quality validation framework
* Partition optimization
* Near real-time ingestion

## Dashboard Preview
<img width="1425" height="792" alt="image" src="https://github.com/user-attachments/assets/63ef6783-7222-4490-8b7a-823b2cc1f79b" />
<img width="1422" height="790" alt="image" src="https://github.com/user-attachments/assets/d82e339a-f903-4752-94b5-9a5fdba5243f" />



