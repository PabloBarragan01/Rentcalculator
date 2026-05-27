"""IPC Bronze -> Silver pipeline for IPC CSV files.

Summary:
- Find the most recent IPC CSV file in the Bronze lakehouse.
- Load it into Spark, parse the date column and cast numeric columns.
- Deduplicate and filter the cleaned rows.
- Create the Silver Delta table or append new rows incrementally.
- Optionally run Delta OPTIMIZE after changes.
- Append an action line to a simple log file in the Bronze files area.

"""

# Configuration


# ── Logical names only — safe for public repo ───────────────────────────────

BRONZE_LAKEHOUSE  = "LH_bronze"
SILVER_LAKEHOUSE  = "LH_silver"

BRONZE_SUBFOLDER  = "IPC"

# ── Silver table ────────────────────────────────────────────────────────────
SILVER_SCHEMA     = "default"
SILVER_TABLE      = "ipc_base"
FULL_TABLE_NAME   = SILVER_TABLE

LOG_SUBFOLDER     = "logs"
LOG_FILE_NAME     = "ipc_silver.log"

DATE_COLUMN       = "indice_tiempo"
FILE_PREFIX       = "IPC_"


# Lakehouse paths and runtime variables — locate bronze and silver locations


import notebookutils
from datetime import datetime, timezone

RUN_TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

lh_bronze = notebookutils.lakehouse.get(BRONZE_LAKEHOUSE)

BRONZE_FILES_PATH = lh_bronze.properties['abfsPath'] + "/Files"

BRONZE_IPC_DIR  = f"{BRONZE_FILES_PATH}/{BRONZE_SUBFOLDER}"

BRONZE_LOG_DIR  = f"{BRONZE_FILES_PATH}/{LOG_SUBFOLDER}"
BRONZE_LOG_PATH = f"{BRONZE_LOG_DIR}/{LOG_FILE_NAME}"

lh_silver = notebookutils.lakehouse.get(SILVER_LAKEHOUSE)

SILVER_TABLE_PATH = (
    lh_silver.properties['abfsPath']
    + f"/Tables/{SILVER_TABLE}"
)

print(f"Silver table path: {SILVER_TABLE_PATH}")

print(f"Bronze IPC dir : {BRONZE_IPC_DIR}")
print(f"Silver table   : {FULL_TABLE_NAME}")
print(f"Log path       : {BRONZE_LOG_PATH}")


# Locate the most recent IPC CSV file in the Bronze directory


all_files = notebookutils.fs.ls(BRONZE_IPC_DIR)
ipc_files = [f for f in all_files if f.name.startswith(FILE_PREFIX) and f.name.endswith(".csv")]

if not ipc_files:
    raise FileNotFoundError(f"No files found {FILE_PREFIX}*.csv in {BRONZE_IPC_DIR}")

print(f"Files in bronze ({len(ipc_files)}):")
for f in ipc_files:
    print(f"  {f.name}")


def sort_key(file_info):
    parts = file_info.name.replace(FILE_PREFIX, "").replace(".csv", "")
    mm, yyyy = parts[:2], parts[2:]
    return f"{yyyy}{mm}"


latest_file = sorted(ipc_files, key=sort_key)[-1]
latest_path = f"{BRONZE_IPC_DIR}/{latest_file.name}"

print(f"\n→ Most recent file: {latest_file.name}")


# Read the latest CSV into Spark and infer schema


from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, DateType


df_raw = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(latest_path)
)

print("Original schema:")
df_raw.printSchema()


# Clean and normalize data: parse the date, cast numeric columns, drop nulls/dupes

df_clean = (
    df_raw
    .withColumn(
        DATE_COLUMN,
        F.coalesce(
            F.to_date(F.col(DATE_COLUMN), "yyyy-MM-dd"),
            F.to_date(F.concat(F.col(DATE_COLUMN), F.lit("-01")), "yyyy-MM-dd")
        )
    )
    .select(
        F.col(DATE_COLUMN).cast(DateType()),
        *[
            F.col(c).cast(DoubleType())
            for c in df_raw.columns
            if c != DATE_COLUMN
        ]
    )
    .filter(F.col(DATE_COLUMN).isNotNull())
    .dropDuplicates([DATE_COLUMN])
)

bronze_rows = df_clean.count()

print("\nClean schema:")
df_clean.printSchema()

print(f"Rows in bronze: {bronze_rows:,}")


# Create or incrementally append cleaned data into the Silver Delta table


from delta.tables import DeltaTable
from pyspark.sql import functions as F


table_exists = spark.catalog.tableExists(FULL_TABLE_NAME)


# Create Silver table when it does not exist (overwrite with cleaned data)

if not table_exists:

    print("Creating Silver table...")

    (
        df_clean
        .orderBy(DATE_COLUMN)
        .write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(FULL_TABLE_NAME)
    )

    action = "CREATE"

    new_rows = bronze_rows

    total_rows = bronze_rows

    print(f"✓ Created table {FULL_TABLE_NAME}")


# If the Silver table exists: identify and append only new rows

else:

    print(f"Loading existing table {FULL_TABLE_NAME}")

    df_existing = spark.table(FULL_TABLE_NAME)

    existing_rows = df_existing.count()

    existing_dates = (
        df_existing
        .select(DATE_COLUMN)
        .distinct()
    )

    df_new_rows = (
        df_clean
        .join(existing_dates, on=DATE_COLUMN, how="left_anti")
    )

    new_rows = df_new_rows.count()

    print(f"Rows to append: {new_rows}")


    if new_rows > 0:

        (
            df_new_rows
            .write
            .format("delta")
            .mode("append")
            .saveAsTable(FULL_TABLE_NAME)
        )

        action = "APPEND"

        total_rows = existing_rows + new_rows

        print(f"✓ Appended {new_rows} rows")

    else:

        action = "NO_CHANGE"

        total_rows = existing_rows

        print("No new rows")


print(f"Total rows: {total_rows:,}")


# Optimize Silver Delta table after CREATE or APPEND actions


if action in ("CREATE", "APPEND"):

    print("Running Delta optimization...")

    deltaTable = DeltaTable.forPath(
    spark,
    SILVER_TABLE_PATH
)

spark.sql(f"""
OPTIMIZE delta.`{SILVER_TABLE_PATH}`
""")


# Write action log to the Bronze log file


# Ensure log directory exists
notebookutils.fs.mkdirs(BRONZE_LOG_DIR)


# Read existing log if present; otherwise initialize header
try:

    existing_log = notebookutils.fs.head(
        BRONZE_LOG_PATH,
        1000000
    )

except:

    existing_log = (
        "timestamp_utc            | notebook        | status  | accion     | "
        "archivo_bronze       | filas_nuevas | total_silver\n"
    )

    existing_log += "-" * 115 + "\n"


# Format a new log entry for this run
log_line = (
    f"{RUN_TS:<25}| NB_02_IPC_silver | SUCCESS | "
    f"{action:<11}| {latest_file.name:<21}| "
    f"{new_rows:<13}| {total_rows:,}\n"
)


updated_log = existing_log + log_line


# Save the updated log back to Bronze
notebookutils.fs.put(
    BRONZE_LOG_PATH,
    updated_log,
    True
)

print(f"✓ Updated log: {BRONZE_LOG_PATH}")

print("\nLast entry:")
print(log_line)


# Preview: show last 5 rows from the Silver table


from pyspark.sql import functions as F

print("=== Last 5 rows in Silver ===")

(
    spark.read.format("delta").load(SILVER_TABLE_PATH)
    .orderBy(F.col(DATE_COLUMN).desc())
    .limit(5)
    .show(truncate=False)
)

