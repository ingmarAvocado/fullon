import psycopg2
import pandas as pd

# PostgreSQL connection parameters
# PostgreSQL connection parameters
HOST = '10.206.35.109'
DATABASE = 'fullon_ohlcv'
USER = 'fullon'
PASSWORD = 'fullon'
#TABLES = ['kraken_btc_usd.trades', 'kraken_eth_usd.trades', 'kraken_eth_btc.trades']
TABLES = ['kraken_btc_usd.trades', 'kraken_eth_btc.trades']


def connect_to_database():
    conn = psycopg2.connect(
        host=HOST,
        database=DATABASE,
        user=USER,
        password=PASSWORD
    )
    return conn


def write_data(table_name, df, file):
    columns = ', '.join(df.columns)
    df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    values_list = df.apply(lambda row: str(tuple(row)), axis=1).tolist()
    chunk_size = 1000
    for i in range(0, len(values_list), chunk_size):
        chunk_values_str = ', '.join(values_list[i:i+chunk_size])
        sql_insert = "INSERT INTO {table} ({columns}) VALUES {values};".format(table=table_name, columns=columns, values=chunk_values_str)
        file.write(sql_insert + "\n")


def fetch_data(conn, table_name):
    with conn.cursor(f'{table_name}_cursor') as cur:
        sql = f'SELECT * FROM {table_name}'
        cur.execute(sql)
        with open(f"{table_name.replace('/', '_')}_inserts.sql", "a") as f:
            while True:
                records = cur.fetchmany(size=1000)
                if not records:
                    break
                df = pd.DataFrame(records, columns=[desc[0] for desc in cur.description])
                write_data(table_name=table_name, df=df, file=f)


def main():
    conn = connect_to_database()

    for table_name in TABLES:
        fetch_data(conn, table_name)

    conn.close()


if __name__ == '__main__':
    main()
