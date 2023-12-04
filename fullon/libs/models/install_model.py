import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from libs import settings, log
logger = log.fullon_logger(__name__)


class Database:

    def clean_base(self):
        try:
            con = psycopg2.connect(dbname="postgres", user=settings.DBUSER, password=settings.DBPASSWD, host=settings.DBHOST)
            with con.cursor() as cur:
                # set connection to autocommit
                con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                # drop the target database
                cur.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{settings.DBNAME}';")
                cur.execute(f"DROP DATABASE IF EXISTS {settings.DBNAME}")
                # close the cursor
                cur.close()
                con.commit()
                logger.info("Database dropped")
        except (Exception, psycopg2.DatabaseError) as error:
            error = "Error can't clean_Base, postgres says: " + str(error)
            logger.error(error)
            sys.exit()
        return None

    def create_database(self):
        try:
            con = psycopg2.connect(dbname="postgres", user=settings.DBUSER, password=settings.DBPASSWD, host=settings.DBHOST)
            sql = f"CREATE DATABASE {settings.DBNAME}"
            with con.cursor() as cur:
                con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cur.execute(sql)
            con.commit()
            con.close()
            logger.info("Database created")
        except (Exception, psycopg2.DatabaseError) as error:
            error = "Error can't clean_Base, postgres says: " + str(error)
            logger.error(error)
            sys.exit()
        return None

    def install_ohlcv(self):
        try:
            con = psycopg2.connect(dbname="postgres", user=settings.DBUSER, password=settings.DBPASSWD, host=settings.DBHOST)
            with con.cursor() as cur:
                # set connection to autocommit
                con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                # drop the target database
                cur.execute(f"CREATE DATABASE {settings.DBNAME_OHLCV}")
                # close the cursor
                cur.close()
                con.commit()
                logger.info("Database %s created", settings.DBNAME)
        except (Exception, psycopg2.DatabaseError) as error:
            if "already exists" in str(error):
                error = "Error can't create, postgres says: " + str(error).strip()
                logger.info(error)
                logger.info("You need to delete this one manually if you are sure.")
            else:
                sys.exit()
        return None

    def install_base_sql(self) -> None:
        """
        Installs the base SQL schema required for Fullon to work.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the installation of the schema.

        Returns:
            None
        """
        try:
            with open(settings.SQL_INSTALL_FILE) as file:
                content = file.read()
        except FileNotFoundError:
            with open("fullon/"+settings.SQL_INSTALL_FILE) as f:
                content = file.read()
        split_index = content.index("-- ddl-end --", content.index("CREATE DATABASE")) + len("-- ddl-end --")
        lines = content[split_index:]
        try:
            self.create_database()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("Error creating database: %s", str(error))
            raise
        try:
            con = psycopg2.connect(dbname=settings.DBNAME,
                                   user=settings.DBUSER,
                                   password=settings.DBPASSWD,
                                   host=settings.DBHOST)
            sql = "".join(lines) + 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
            with con.cursor() as cur:
                cur.execute(sql)
            con.commit()
            logger.info("Base sql schema installed")
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("Error installing database file: %s", str(error))
            raise
        return None
