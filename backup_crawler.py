import psycopg2
import datetime

def fetch_data(cursor, table_name):
    select_query = f"SELECT * FROM {table_name}"
    cursor.execute(select_query)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return columns, rows

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

def adjust_sequence(cursor, table_name, primary_key):
    sequence_query = f"SELECT setval(pg_get_serial_sequence('{table_name}', '{primary_key}'), MAX({primary_key})) FROM {table_name};"
    cursor.execute(sequence_query)
    return cursor.fetchone()[0]

def backup_full_database(db_params, tables_to_backup, primary_keys, backup_file, batch_size=1000):
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    with open(backup_file, 'w') as f:
        for table_name in tables_to_backup:
            columns, all_rows = fetch_data(cursor, table_name)
            for i in range(0, len(all_rows), batch_size):
                batch = all_rows[i:i+batch_size]
                query = build_insert_query(table_name, columns, batch)
                f.write(query + ";\n")
            if table_name in primary_keys:
                sequence_query = adjust_sequence(cursor, table_name, primary_keys[table_name])
                f.write(f"{sequence_query}" + ";\n")
    cursor.close()
    conn.close()

# Parameters
db_params = {
    'host': '10.206.35.109',
    'dbname': 'fullon_crawler',
    'user': 'fullon',
    'password': 'fullon'
}

tables_to_backup = [
    'public.post_analyzers',
    'public.sites_follows',
    'public.follows_analyzers',
    'public.sites_posts',
    'public.engine_scores',
]

primary_keys = {
    'public.sites_posts': 'post_id',
    'public.sites_follows': 'fid',
    # Add primary keys for other tables if necessary
}

backup_file = 'crawler_backup.sql'
backup_full_database(db_params, tables_to_backup, primary_keys, backup_file)
