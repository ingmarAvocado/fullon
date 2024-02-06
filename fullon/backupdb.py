import psycopg2  # or import pymysql for MySQL
import datetime

def fetch_data(cursor, table_name, date_threshold):
    select_query = f"SELECT * FROM {table_name} WHERE timestamp > '{date_threshold}'"
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
    # Build INSERT query
    column_names = ', '.join(columns)
    values_list = []
    for row in rows:
        formatted_values = [format_value(val) for val in row]
        values_list.append(f"({', '.join(formatted_values)})")
    values_str = ', '.join(values_list)
    query = f"INSERT INTO {table_name} ({column_names}) VALUES {values_str}"
    return query


def backup_ohlcv(db_params, table_name, backup_file, date_threshold, batch_size=1000):
    # Connect to the database
    conn = psycopg2.connect(**db_params)  # or pymysql.connect(**db_params) for MySQL
    cursor = conn.cursor()

    # Fetch data from database
    columns, all_rows = fetch_data(cursor, table_name, date_threshold)

    # Write to file in batches
    with open(backup_file, 'w') as f:
        for i in range(0, len(all_rows), batch_size):
            batch = all_rows[i:i+batch_size]
            query = build_insert_query(table_name, columns, batch)
            f.write(query + ";\n")

    cursor.close()
    conn.close()


# Parameters
db_params = {
    'host': '10.206.35.109',
    'dbname': 'fullon_ohlcv',
    'user': 'fullon',
    'password': 'fullon'
    # Add other parameters as needed
}
table_name = 'kraken_btc_usd.trades'
backup_file = 'backup_btc.usd.sql'
date_threshold = '2023-06-01 00:00:00.000000'  # 

# Call the function
backup_ohlcv(db_params, table_name, backup_file, date_threshold)
