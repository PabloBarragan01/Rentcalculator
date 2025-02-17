# Power BI Rent Calculator Argentina

## 📌 Introduction
This project consists of a Power BI dashboard that calculates rent values in Argentina, using public data from the BCRA API and the government data portal (datos.gob.ar). The solution includes data processing in a Microsoft Fabric notebook, storage in a Fabric Lakehouse, and a final structured model in a Fabric Data Warehouse, which is then visualized in Power BI.

## 🎯 Objetive
The goal of this project is to allow people to easily calculate house rent price adjustments based on the IPC (Consumer Price Index) in Argentina. Inflation in Argentina is among the highest in the world, so most rental contracts are indexed to inflation using the IPC.

## 🏗️ Project Architecture
1. **Data Extraction**: Data is retrieved from the BCRA API and datos.gob.ar.
2. **Data Processing in Fabric Notebook**: The extracted data is processed and cleaned in a Microsoft Fabric notebook.
3. **Storage in Fabric Lakehouse**: The cleaned data is stored in a Fabric Lakehouse.
4. **Data Warehouse in Fabric**: Data is structured and optimized for queries.
5. **Power BI Dashboard**: The Data Warehouse is connected to Power BI for visualization.

## 🚀 Installation and Usage
### Prerequisites
- Python 3.x with the following libraries: `pandas`, `requests`, `pyodbc`
- Microsoft Fabric with a configured Data Warehouse and Lakehouse
- Power BI Desktop to visualize the `.pbix` file

## 📊 Screenshots and Sample Data
BCRA API
![image](https://github.com/user-attachments/assets/5532cd33-b2f0-44b0-922e-af2487627109)

Power BI dashboard
![image](https://github.com/user-attachments/assets/afb5a87a-ff33-4965-978a-e9e191f8717a)
![image](https://github.com/user-attachments/assets/49ff6508-cfd3-40d4-bf8b-4dd7f1695204)

## 🔍 Technical Considerations
- The Fabric notebook is responsible for data extraction, cleaning, and transformation.
- The Lakehouse acts as intermediate storage before structuring the data in the Data Warehouse.
- The Data Warehouse is optimized for efficient querying in Power BI.
