# # IPC  Índice de Precios al Consumidor
# **Source:** datos.gob.ar  Base diciembre 2016, frecuencia mensual  
# 
# **What this notebook does:**
# 1. Resolves the target Lakehouse path dynamically via `notebookutils` (no hardcoded IDs  safe for public repos)
# 2. Downloads the CSV from the official URL
# 3. Reads it with pandas to inspect the last `indice_tiempo` value
# 4. Builds a filename like `IPC_mmyyyy` from that date
# 5. Saves the file to the target Lakehouse (overwriting if it already exists)
# 
# > **Pre-requisite:** `LH_bronze` must be added to this notebook's Lakehouse list (it does NOT need to be the default one).

# ## 1  Configuration


# ── Solo nombres lógicos  seguro para repo público ───────────────────────────

SOURCE_URL = (
    "https://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.3/"
    "download/indice-precios-al-consumidor-nivel-general-base-diciembre-2016-mensual.csv"
)

BRONZE_LAKEHOUSE  = "LH_bronze"
TARGET_SUBFOLDER  = "IPC"
LOG_SUBFOLDER     = "logs"
LOG_FILE_NAME     = "ipc_bronze.log"
DATE_COLUMN       = "indice_tiempo"

# Tolerancia de validación: cuántos meses de retraso se aceptan en la fuente
# 1 = se acepta que el último dato sea del mes anterior (comportamiento normal del IPC)
# 2 = se acepta hasta 2 meses de retraso antes de lanzar un warning
MAX_LAG_MONTHS    = 2


# ## 2  Resolve Lakehouse path at runtime
# `notebookutils.lakehouse.get()` looks up the Lakehouse by name within the current workspace context and returns its metadata  including the `abfss://` path  without ever storing sensitive IDs in the code.


import notebookutils

lh_bronze = notebookutils.lakehouse.get(BRONZE_LAKEHOUSE)
BRONZE_FILES_PATH = lh_bronze.properties['abfsPath'] + "/Files"

BRONZE_IPC_DIR  = f"{BRONZE_FILES_PATH}/{TARGET_SUBFOLDER}"
BRONZE_LOG_DIR  = f"{BRONZE_FILES_PATH}/{LOG_SUBFOLDER}"
BRONZE_LOG_PATH = f"{BRONZE_LOG_DIR}/{LOG_FILE_NAME}"

print(f"Lakehouse : {lh_bronze.displayName}")
print(f"IPC dir   : {BRONZE_IPC_DIR}")
print(f"Log path  : {BRONZE_LOG_PATH}")


# ## 3  Download & inspect


import io, os, requests
import pandas as pd
from datetime import datetime, timezone

RUN_TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

print(f"[{RUN_TS}] Downloading:\n  {SOURCE_URL}\n")
response = requests.get(SOURCE_URL, timeout=60)
response.raise_for_status()
csv_bytes = response.content
print(f"OK  {len(csv_bytes):,} bytes")

df = pd.read_csv(io.BytesIO(csv_bytes))
print(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"Columns: {list(df.columns)}")


# ## 4  Build filename from last date


last_date_raw = df[DATE_COLUMN].dropna().iloc[-1].strip()
parsed_date   = pd.to_datetime(last_date_raw)
file_name     = f"IPC_{parsed_date.strftime('%m%Y')}.csv"

print(f"Latest period : {last_date_raw}")
print(f"File name : {file_name}")


# ## 5 - Source Validation


from dateutil.relativedelta import relativedelta

today         = datetime.now(timezone.utc)
expected_from = today - relativedelta(months=MAX_LAG_MONTHS)

# Compare only year and month
last_ym     = (parsed_date.year, parsed_date.month)
expected_ym = (expected_from.year, expected_from.month)
current_ym  = (today.year, today.month)

lag_months = (current_ym[0] - last_ym[0]) * 12 + (current_ym[1] - last_ym[1])

print(f"Downloaded period : {parsed_date.strftime('%Y-%m')}")
print(f"Current month         : {today.strftime('%Y-%m')}")
print(f"Lag            : {lag_months} month(s)")

if lag_months < 0:
    raise ValueError(
        f"ERROR: The file has a future period ({parsed_date.strftime('%Y-%m')}). "
        f"Verify the source."
    )
elif lag_months > MAX_LAG_MONTHS:
    raise ValueError(
        f"ERROR: The latest available period ({parsed_date.strftime('%Y-%m')}) "
        f"has {lag_months} months of lag (maximum accepted: {MAX_LAG_MONTHS}). "
        f"Verify if the source was updated."
    )
else:
    print(f"✓ Validation OK  lag within accepted range ({MAX_LAG_MONTHS} months max.)")


# ## 6  Save to Lakehouse bronze (overwrite if exists)


dest_path = f"{BRONZE_IPC_DIR}/{file_name}"

notebookutils.fs.mkdirs(BRONZE_IPC_DIR)

# Delete if already exists
try:
    notebookutils.fs.rm(dest_path)
    print(f"Previous file deleted: {file_name}")
except:
    pass

local_tmp = f"/tmp/{file_name}"
with open(local_tmp, "wb") as f:
    f.write(csv_bytes)

notebookutils.fs.cp(f"file:{local_tmp}", dest_path)
os.remove(local_tmp)

print(f"✓ Saved in: {dest_path}")


# ## 7 - Logging


# ── Read existing log or initialize a new one ───────────────────────────────
local_log = "/tmp/ipc_bronze.log"

try:
    notebookutils.fs.cp(BRONZE_LOG_PATH, f"file:{local_log}")
    with open(local_log, "r") as f:
        existing_log = f.read()
except:
    existing_log = "timestamp_utc            | notebook       | status  | period     | file                 | details\n"
    existing_log += "-" * 110 + "\n"

# ── Add new line ──────────────────────────────────────────────────────
log_line = (
    f"{RUN_TS:<25}| NB_01_IPC_bronze | SUCCESS | "
    f"{parsed_date.strftime('%Y-%m'):<11}| {file_name:<21}| "
    f"lag={lag_months}m bytes={len(csv_bytes):,}\n"
)
updated_log = existing_log + log_line

# ── Write updated log to bronze ──────────────────────────────────
notebookutils.fs.mkdirs(BRONZE_LOG_DIR)

with open(local_log, "w") as f:
    f.write(updated_log)

try:
    notebookutils.fs.rm(BRONZE_LOG_PATH)
except:
    pass

notebookutils.fs.cp(f"file:{local_log}", BRONZE_LOG_PATH)
os.remove(local_log)

print(f"✓ Log updated: {BRONZE_LOG_PATH}")
print(f"\nLatest entry:\n  {log_line.strip()}")


# ## 8  Quick preview


print("=== First 5 rows ===")
display(df.head())

print("\n=== Last 5 rows ===")
display(df.tail())

