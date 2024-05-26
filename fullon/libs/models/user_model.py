import sys
import psycopg2
#import urllib, json
from libs import log
from libs.models import symbol_model as database
from typing import Dict, Any, Optional, List


logger = log.fullon_logger(__name__)


class Database(database.Database):

    def get_user_id(self, mail: str) -> Optional[int]:
        """
        Retrieve the user ID for a given email address.

        Args:
            mail (str): The email address of the user.

        Returns:
            Optional[int]: The user ID if found, otherwise None.
        """
        sql = f"SELECT uid FROM users WHERE mail='{mail}'"

        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
            return row[0] if row else None
        except (Exception, psycopg2.DatabaseError) as error:
            if 'relation' in str(error):
                return None
            logger.warning(self.error_print(error=error, method="get_user_id", query=sql))
            raise

    def remove_user(self, user_id: Optional[str] = None, email: Optional[str] = None) -> bool:
        """
        Remove a user from the database based on their user_id or email address.

        Args:
            user_id (Optional[str], default=None): The user ID of the user to remove.
            email (Optional[str], default=None): The email address of the user to remove.
        """
        if not user_id and not email:
            raise ValueError("Either user_id or email must be provided.")

        sql = "DELETE FROM users WHERE "
        if user_id:
            sql += f"uid = '{user_id}'"
        elif email:
            sql += f"mail = '{email}'"

        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                self.con.commit()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(self.error_print(error=error, method="remove_user", query=sql))
        return False

    def add_user(self, user: Dict[str, Any]) -> None:
        """
        Add a new user to the database securely using parameterized queries.

        Args:
            user (Dict[str, Any]): A dictionary containing user information.
        """
        sql = """INSERT INTO users (mail, password, f2a, role, name, lastname, phone, id_num, note, manager, active)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        values = (
            user.get('mail'), user.get('password'), user.get('f2a'), user.get('role'),
            user.get('name'), user.get('lastname'), user.get('phone'), user.get('id_num'), user.get('note'),
            user.get('manager'), user.get('active', True)
        )
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, values)
                self.con.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(self.error_print(error=error, method="add_user", query=sql))

    def get_user_list(self, page: int = 1, page_size: int = 10, all: bool = False) -> List[Dict]:
        """
        Gets a list of users.

        Parameters:
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.
            all (bool): Whether to retrieve all users without pagination. Defaults to False.

        Returns:
            List[Dict]: A list of users for the current page.
        """

        sql = "select * from users ORDER BY mail"

        # Apply pagination if 'all' is False
        if not all:
            offset = (page - 1) * page_size
            sql += f" LIMIT {page_size} OFFSET {offset}"

        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()

            # Convert each row to a dictionary
            formatted_rows = [dict(row) for row in rows]
            return formatted_rows
        except (Exception, psycopg2.DatabaseError) as error:
            error_message = "Error can't database query; PostgreSQL says: " + str(error) + "\n" + sql
            logger.info(error_message)
            return []
