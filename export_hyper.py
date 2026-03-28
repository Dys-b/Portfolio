import os
import time
import pyodbc
from dotenv import load_dotenv
from tableauhyperapi import (
    HyperProcess,
    Connection,
    TableDefinition,
    SqlType,
    Inserter,
    Telemetry,
    CreateMode,
    TableName,
)

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_SCHEMA = os.getenv("SQL_SCHEMA", "dbo")
SQL_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 17 for SQL Server")
TABLE_LIST_FILE = os.getenv("TABLE_LIST_FILE", "config/tables.txt")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50000"))


def connect_sql() -> pyodbc.Connection:
    """Create a trusted connection to SQL Server."""
    if not SQL_SERVER or not SQL_DATABASE:
        raise ValueError(
            "Missing SQL_SERVER or SQL_DATABASE. "
            "Create a .env file based on .env.example."
        )

    conn_str = (
        f"DRIVER={{{SQL_DRIVER}}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str, timeout=300)


def map_sql_to_hyper(
    sql_type: str,
    char_len: int | None,
    precision: int | None,
    scale: int | None,
):
    """Map SQL Server data types to Tableau Hyper types."""
    data_type = (sql_type or "").lower()

    if data_type == "bigint":
        return SqlType.big_int()
    if data_type == "int":
        return SqlType.int()
    if data_type in ("smallint", "tinyint"):
        return SqlType.small_int()
    if data_type == "bit":
        return SqlType.bool()
    if data_type in ("float", "real"):
        return SqlType.double()
    if data_type in ("decimal", "numeric"):
        p = min(max(precision or 18, 1), 38)
        s = min(max(scale or 0, 0), 38)
        s = min(s, p)
        return SqlType.numeric(p, s)
    if data_type in ("money", "smallmoney"):
        return SqlType.numeric(19, 4)
    if data_type == "date":
        return SqlType.date()
    if data_type in ("datetime", "smalldatetime", "datetime2", "datetimeoffset"):
        return SqlType.timestamp()
    if data_type == "time":
        return SqlType.time()
    if data_type == "uniqueidentifier":
        return SqlType.text()
    if data_type in ("varbinary", "binary", "image"):
        return SqlType.bytes()

    # Safe fallback for nvarchar, varchar, char, nchar, xml, etc.
    return SqlType.text()


def get_columns(
    connection: pyodbc.Connection,
    table_name: str,
) -> list[tuple]:
    """Read SQL Server metadata for a table."""
    query = """
        SELECT
            c.name AS column_name,
            t.name AS data_type,
            c.max_length AS character_maximum_length,
            c.precision AS numeric_precision,
            c.scale AS numeric_scale
        FROM sys.columns AS c
        INNER JOIN sys.types AS t
            ON c.user_type_id = t.user_type_id
        INNER JOIN sys.objects AS o
            ON c.object_id = o.object_id
        INNER JOIN sys.schemas AS s
            ON o.schema_id = s.schema_id
        WHERE s.name = ? AND o.name = ?
        ORDER BY c.column_id;
    """
    cursor = connection.cursor()
    rows = cursor.execute(query, (SQL_SCHEMA, table_name)).fetchall()
    return list(rows)


def export_table_to_hyper(
    connection: pyodbc.Connection,
    table_name: str,
) -> int:
    """Export a SQL Server table into a Tableau Hyper file."""
    columns = get_columns(connection, table_name)

    if not columns:
        print(f"[WARN] {table_name}: no metadata found or no access.")
        return 0

    table_definition = TableDefinition(
        table_name=TableName("Extract", table_name),
        columns=[
            TableDefinition.Column(
                column_name,
                map_sql_to_hyper(data_type, char_len, precision, scale),
            )
            for column_name, data_type, char_len, precision, scale in columns
        ],
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    hyper_path = os.path.join(OUTPUT_DIR, f"{table_name}.hyper")
    select_sql = f"SET NOCOUNT ON; SELECT * FROM [{SQL_SCHEMA}].[{table_name}]"

    inserted_rows = 0
    start_time = time.time()

    with HyperProcess(
        telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU
    ) as hyper:
        with Connection(
            endpoint=hyper.endpoint,
            database=hyper_path,
            create_mode=CreateMode.CREATE_AND_REPLACE,
        ) as hyper_connection:
            hyper_connection.catalog.create_schema_if_not_exists("Extract")
            hyper_connection.catalog.create_table(table_definition)

            cursor = connection.cursor()
            cursor.execute(select_sql)

            with Inserter(hyper_connection, table_definition) as inserter:
                while True:
                    batch = cursor.fetchmany(BATCH_SIZE)
                    if not batch:
                        break
                    inserter.add_rows(batch)
                    inserted_rows += len(batch)
                inserter.execute()

    elapsed = time.time() - start_time
    rows_per_second = inserted_rows / elapsed if elapsed > 0 else 0

    print(
        f"[OK] {table_name}: {inserted_rows:,} rows -> {hyper_path} "
        f"({elapsed:.1f}s, {rows_per_second:,.0f} rows/s)"
    )
    return inserted_rows


def load_table_list(file_path: str) -> list[str]:
    """Load table names from a plain text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Table list file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as file:
        tables = [
            line.strip()
            for line in file
            if line.strip() and not line.strip().startswith("#")
        ]
    return tables


def main():
    tables = load_table_list(TABLE_LIST_FILE)
    print(f"[INFO] {len(tables)} table(s) found in {TABLE_LIST_FILE}")

    sql_connection = connect_sql()
    print("[INFO] Connected to SQL Server")

    total_rows = 0
    errors = 0

    for table_name in tables:
        print(f"[INFO] Exporting {SQL_SCHEMA}.{table_name} ...")
        try:
            total_rows += export_table_to_hyper(sql_connection, table_name)
        except Exception as exc:
            errors += 1
            print(f"[ERROR] {table_name}: {exc}")

    print(
        f"\n[SUMMARY] Total rows: {total_rows:,} | "
        f"Tables OK: {len(tables) - errors} | Errors: {errors}"
    )


if __name__ == "__main__":
    main()