
# ## CasaPropia_Download_to_Lakehouse
# Scrapes the Casa Propia coefficient table from ikiwi.net.ar and saves it as a CSV in `LH_bronze/Files/CasaPropia/`.
# 
# **What this notebook does:**
# 1. Resolves the target Lakehouse path dynamically via `notebookutils` (no hardcoded IDs — safe for public repos)
# 2. Scrapes the HTML table from the source URL
# 3. Standardizes the `Mes` column to ISO 8601 date format (`yyyy-MM-dd`)
# 4. Saves the file as `CASAPROPIA_mmyyyy.csv`, overwriting if it already exists for the same period
# 5. Logs each execution to `LH_bronze/Files/logs/casapropia_bronze.log`
# 
# > **Pre-requisite:** the notebook must be able to resolve `LH_bronze` in the workspace via `notebookutils`.

# ## 1 Configuration
# Logical names only 

SOURCE_URL       = "SOURCE"

BRONZE_LAKEHOUSE = "LH_bronze"
TARGET_SUBFOLDER = "CasaPropia"
LOG_SUBFOLDER    = "logs"
LOG_FILE_NAME    = "casapropia_bronze.log"

DATE_COLUMN      = "Mes"
FILE_PREFIX      = "CASAPROPIA_"

# Spanish / english month name → number mapping for date parsing
MESES_MAP = {
    # Español
    'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4,
    'Mayo': 5, 'Junio': 6, 'Julio': 7, 'Agosto': 8,
    'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12,
    # English
    'January': 1, 'February': 2, 'March': 3, 'April': 4,
    'May': 5, 'June': 6, 'July': 7, 'August': 8,
    'September': 9, 'October': 10, 'November': 11, 'December': 12
}


# ## 2 Resolve Lakehouse path at runtime

import os
import notebookutils
import pandas as pd
from datetime import datetime, timezone

RUN_TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

lh_bronze = notebookutils.lakehouse.get(BRONZE_LAKEHOUSE)
BRONZE_FILES_PATH = lh_bronze.properties['abfsPath'] + "/Files"

BRONZE_DIR  = f"{BRONZE_FILES_PATH}/{TARGET_SUBFOLDER}"
LOG_DIR     = f"{BRONZE_FILES_PATH}/{LOG_SUBFOLDER}"
LOG_PATH    = f"{LOG_DIR}/{LOG_FILE_NAME}"

print(f"Lakehouse  : {lh_bronze.displayName}")
print(f"Target dir : {BRONZE_DIR}")
print(f"Log path   : {LOG_PATH}")


# ## 3 Scrape & parse
# Downloads the HTML table and standardizes the `Mes` column to ISO 8601 (`yyyy-MM-dd`).

import requests
import pandas as pd
### Nueva ###

def parse_mes(mes_str: str) -> str:
    """Converts 'Mayo 2026' → '2026-05-01'."""

    nombre, año = mes_str.strip().split()

    return f"{int(año):04d}-{MESES_MAP[nombre]:02d}-01"


print(f"Scraping: {SOURCE_URL}")


# Browser-like headers

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml",
}


# Download page 

response = requests.get(
    SOURCE_URL,
    headers=headers,
    timeout=30
)

response.raise_for_status()

html_content = response.text


# Parse HTML tables 

tables = pd.read_html(html_content)

if not tables:
    raise ValueError("No HTML tables found")


df = tables[0].copy()

df[DATE_COLUMN] = df[DATE_COLUMN].apply(parse_mes)


print(f"Shape  : {df.shape[0]:,} rows × {df.shape[1]} columns")

print(f"Columns: {list(df.columns)}")

print(f"\nSample (first 3 rows):")

print(df.head(3).to_string(index=False))




# ## 4 Build filename from latest period

# The table is sorted descending most recent period is at row 0
last_date_str = df[DATE_COLUMN].iloc[0]
parsed_date   = pd.to_datetime(last_date_str)
file_name     = f"{FILE_PREFIX}{parsed_date.strftime('%m%Y')}.csv"

print(f"Latest period : {last_date_str}")
print(f"File name     : {file_name}")
print(f"Total records : {len(df):,}")


# ## 5 Save to LH_bronze (overwrite if exists)
# Writes to a local `/tmp` file first, then copies to OneLake via `notebookutils.fs.cp`.

dest_path = f"{BRONZE_DIR}/{file_name}"
local_tmp = f"/tmp/{file_name}"

notebookutils.fs.mkdirs(BRONZE_DIR)

# Remove previous file if it exists
try:
    notebookutils.fs.rm(dest_path)
    print(f"Previous file removed: {file_name}")
except:
    pass

df.to_csv(local_tmp, index=False)
notebookutils.fs.cp(f"file:{local_tmp}", dest_path)
os.remove(local_tmp)

print(f"✓ Saved to: {dest_path}")


# ## 6  Logging

local_log = "/tmp/casapropia_bronze.log"

# Read existing log or start a new one
try:
    notebookutils.fs.cp(LOG_PATH, f"file:{local_log}")
    with open(local_log, "r") as f:
        existing_log = f.read()
except:
    existing_log = "timestamp_utc            | notebook                | status  | periodo    | archivo                      | rows\n"
    existing_log += "-" * 110 + "\n"

#  Append new entry
log_line = (
    f"{RUN_TS:<25}| NB_01_casapropia_bronze | SUCCESS | "
    f"{parsed_date.strftime('%Y-%m'):<11}| {file_name:<29}| {len(df):,}\n"
)

with open(local_log, "w") as f:
    f.write(existing_log + log_line)

#  Write back to OneLake (overwrite directly, no rm needed)
notebookutils.fs.cp(f"file:{local_log}", LOG_PATH)
os.remove(local_log)

print(f"✓ Log updated: {LOG_PATH}")
print(f"\nLatest entry:\n  {log_line.strip()}")


# ## 7  Preview


print("=== First 5 rows ===")
display(df.head())

print("\n=== Last 5 rows ===")
display(df.tail())

