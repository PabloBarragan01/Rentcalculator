"""CasaPropia Bronze -> Silver pipeline for CasaPropia CSV files.

Summary:
- Find the most recent CasaPropia CSV file in the Bronze lakehouse.
- Load it into Spark, parse the month/date column and cast other columns.
- Deduplicate and filter the cleaned rows.
- Create the Silver Delta table or append new rows incrementally.
- Append an action line to a simple log file in the Bronze files area.

"""

# Configuration


# ── Logical names only — safe for public repo ───────────────────────────────

BRONZE_LAKEHOUSE  = "LH_bronze"
SILVER_LAKEHOUSE  = "LH_silver"

BRONZE_SUBFOLDER  = "CasaPropia"

SILVER_TABLE      = "casapropia_base"

FULL_TABLE_NAME   = SILVER_TABLE

LOG_SUBFOLDER     = "logs"
LOG_FILE_NAME     = "casapropia_silver.log"

DATE_COLUMN       = "Mes"
FILE_PREFIX       = "CASAPROPIA_"


# Paths
# Lakehouse paths and runtime variables — locate bronze and silver locations


import notebookutils
from datetime import datetime, timezone

RUN_TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

lh_bronze = notebookutils.lakehouse.get(BRONZE_LAKEHOUSE)

BRONZE_FILES_PATH = lh_bronze.properties['abfsPath'] + "/Files"

BRONZE_CASAPROPIA_DIR = f"{BRONZE_FILES_PATH}/{BRONZE_SUBFOLDER}"

BRONZE_LOG_DIR  = f"{BRONZE_FILES_PATH}/{LOG_SUBFOLDER}"
BRONZE_LOG_PATH = f"{BRONZE_LOG_DIR}/{LOG_FILE_NAME}"

print(f"Bronze CASAPROPIA dir : {BRONZE_CASAPROPIA_DIR}")
print(f"Silver table          : {FULL_TABLE_NAME}")
print(f"Log path              : {BRONZE_LOG_PATH}")


# Bronze most recent file
# Locate the most recent CasaPropia CSV file in the Bronze directory


all_files = notebookutils.fs.ls(BRONZE_CASAPROPIA_DIR)
casapropia_files = [f for f in all_files if f.name.startswith(FILE_PREFIX) and f.name.endswith(".csv")]

if not casapropia_files:
    raise FileNotFoundError(f"No files found {FILE_PREFIX}*.csv in {BRONZE_CASAPROPIA_DIR}")

print(f"Files in bronze ({len(casapropia_files)}):")
for f in casapropia_files:
    print(f"  {f.name}")

def sort_key(file_info):
    parts = file_info.name.replace(FILE_PREFIX, "").replace(".csv", "")  # → 032026
    mm, yyyy = parts[:2], parts[2:]                                        # → 03, 2026
    return f"{yyyy}{mm}"                                                   # → 202603

latest_file = sorted(casapropia_files, key=sort_key)[-1]
latest_path = f"{BRONZE_CASAPROPIA_DIR}/{latest_file.name}"

print(f"\n→ Most recent file: {latest_file.name}")


# Cleaning
# Read the latest CSV into Spark and perform cleaning and casting


from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, DateType, StringType

COL_MES = "Mes"
COL_COEFICIENTE = "Coeficiente"
COL_INDICE = "Índice"
COL_FORMULA = "Fórmula"

df_raw = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(latest_path)
)

print("Original schema:")
df_raw.printSchema()

df_clean = (
    df_raw

    .withColumn(
        COL_MES,
        F.coalesce(
            F.to_date(F.col(COL_MES), "yyyy-MM-dd"),
            F.to_date(
                F.concat(F.col(COL_MES), F.lit("-01")),
                "yyyy-MM-dd"
            )
        )
    )

    .withColumn(
        COL_COEFICIENTE,
        (F.col(COL_COEFICIENTE).cast(DoubleType()) / 10000)
    )

    .select(
        F.col(COL_MES).cast(DateType()).alias("Mes"),

        F.col(COL_COEFICIENTE)
            .cast(DoubleType())
            .alias("Coeficiente"),

        F.col(COL_INDICE)
            .cast(StringType())
            .alias("Indice"),

        F.col(COL_FORMULA)
            .cast(StringType())
            .alias("Formula"),
    )

    .filter(F.col("Mes").isNotNull())

    .dropDuplicates(["Mes"])
)

bronze_rows = df_clean.count()

print("\nClean schema:")
df_clean.printSchema()

print(f"Rows in bronze: {bronze_rows:,}")


from pyspark.sql import functions as F

table_exists = spark.catalog.tableExists(FULL_TABLE_NAME)

# Create Silver table when it does not exist (overwrite with cleaned data)
if not table_exists:

    print("Silver table does not exist. Creating...")

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

    print(f"Existing table detected: {FULL_TABLE_NAME}")

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

    print(f"New rows to add: {new_rows}")


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

        print(f"✓ Appended {new_rows:,} rows")

    else:

        action = "NO_CHANGE"

        total_rows = existing_rows

        print("No new data")


print(f"\nTotal rows in Silver: {total_rows:,}")


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
    f"{RUN_TS:<25}| NB_02_casapropia_silver | SUCCESS | "
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
    spark.table(FULL_TABLE_NAME)
    .orderBy(F.col(DATE_COLUMN).desc())
    .limit(5)
    .show(truncate=False)
)

