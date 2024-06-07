import psycopg2
import datetime

def fetch_data_in_batches(cursor, table_name, batch_size):
    offset = 0
    while True:
        select_query = f"SELECT * FROM {table_name} WHERE TIMESTAMP > '2023-11-01' LIMIT {batch_size} OFFSET {offset}"
        cursor.execute(select_query)
        rows = cursor.fetchall()
        if not rows:
            break
        yield rows
        offset += batch_size

def format_value(value):
    """Format a Python value as a string for SQL."""
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"  # Escape single quotes in strings
    elif isinstance(value, datetime.datetime):
        return "'" + value.strftime("%Y-%m-%d %H:%M:%S.%f") + "'"  # Format datetime objects
    elif value is None:
        return "NULL"
    else:
        return str(value)

def build_insert_query(table_name, columns, rows):
    column_names = ', '.join(columns)
    values_list = []
    for row in rows:
        formatted_values = [format_value(val) for val in row]
        values_list.append(f"({', '.join(formatted_values)})")
    values_str = ', '.join(values_list)
    query = f"INSERT INTO {table_name} ({column_names}) VALUES {values_str}"
    return query

def fetch_tables_with_pattern(cursor, pattern):
    fetch_query = f"""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema LIKE '{pattern}'
    AND table_type = 'BASE TABLE';
    """
    cursor.execute(fetch_query)
    return cursor.fetchall()

def get_create_table_statement(cursor, schema, table):
    cursor.execute(f"SELECT table_schema, table_name, column_name, data_type, character_maximum_length "
                   f"FROM information_schema.columns "
                   f"WHERE table_schema = '{schema}' AND table_name = '{table}' "
                   f"ORDER BY ordinal_position;")
    columns = cursor.fetchall()
    create_table_query = f"CREATE SCHEMA IF NOT EXISTS {schema};\n"
    create_table_query += f"CREATE TABLE {schema}.{table} (\n"
    column_definitions = []
    for column in columns:
        column_def = f"    {column[2]} {column[3]}"
        if column[3] in ['character varying', 'varchar'] and column[4]:
            column_def += f"({column[4]})"
        column_definitions.append(column_def)
    create_table_query += ",\n".join(column_definitions)
    create_table_query += "\n);\n"
    # Add TimescaleDB hypertable conversion
    create_table_query += f"SELECT create_hypertable('{schema}.{table}', 'timestamp', if_not_exists => TRUE);\n"
    return create_table_query

def backup_full_database(db_params, schema_pattern, backup_file, schema_file, batch_size=1000):
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    tables_to_backup = fetch_tables_with_pattern(cursor, schema_pattern)
    with open(backup_file, 'w') as f_data, open(schema_file, 'w') as f_schema:
        f_schema.write("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;\n\n")
        for schema, table_name in tables_to_backup:
            if 'trades' in table_name:
                full_table_name = f"{schema}.{table_name}"
                # Write CREATE TABLE statement to schema file
                create_table_query = get_create_table_statement(cursor, schema, table_name)
                f_schema.write(create_table_query + "\n\n")
                # Backup data
                cursor.execute(f"SELECT * FROM {full_table_name} LIMIT 1")
                columns = [desc[0] for desc in cursor.description]
                for rows in fetch_data_in_batches(cursor, full_table_name, batch_size):
                    query = build_insert_query(full_table_name, columns, rows)
                    f_data.write(query + ";\n")
    cursor.close()
    conn.close()

# Parameters
db_params = {
    'host': '10.206.35.109',
    'dbname': 'fullon_ohlcv',
    'user': 'fullon',
    'password': 'fullon'
}

schema_pattern = 'kraken%'
backup_file = 'fullon_ohlcv.sql'
schema_file = 'fullon_ohlcv_schema.sql'
backup_full_database(db_params, schema_pattern, backup_file, schema_file)
