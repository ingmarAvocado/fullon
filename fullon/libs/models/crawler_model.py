import sys
from libs import log
from libs.models import symbol_model as database
from libs.structs.crawler_struct import CrawlerStruct
from libs.structs.crawler_post_struct import CrawlerPostStruct
from libs.structs.crawler_analyzer_struct import CrawlerAnalyzerStruct
from typing import Optional, List, Dict, Tuple
import psycopg2
import arrow
from decimal import Decimal


logger = log.fullon_logger(__name__)


class Database(database.Database):

    def upsert_profile(self, profile: CrawlerStruct) -> Optional[int]:
        """
        Adds or updates a crawler profile in the database.

        Args:
            profile (CrawlerStruct): The crawler profile to be upserted.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the upsert operation.

        Returns:
            Optional[int]: The fid of the upserted profile, or None if the operation fails.
        """
        sql = """
        INSERT INTO sites_follows (uid, site, account, ranking, contra, expertise)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (uid, account, site) DO UPDATE
        SET  ranking = EXCLUDED.ranking, contra = EXCLUDED.contra,
        expertise = EXCLUDED.contra  RETURNING fid;
        """
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (profile.uid, profile.site, profile.account, profile.ranking, profile.contra, profile.expertise))
                fid = cur.fetchone()[0]
                self.con.commit()
                return fid
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            if 'not-null' in str(error):
                error = "Some of the parameters of the profile are wrong,.\n" + str(error)
            logger.warning(self.error_print(error=error, method="upsert_profile", query=sql,))
            return None

    def get_profiles(self,
                     site: Optional[str] = None,
                     page: int = 1,
                     page_size: int = 10,
                     all: bool = False) -> List[CrawlerStruct]:
        """
        Get a list of site follows profiles from the database.

        Args:
            site (str): The name of the site to filter profiles by.
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.
            all (bool): If True, retrieves all records without pagination. Defaults to False.

        Returns:
            List[CrawlerStruct]: A list of CrawlerStruct instances representing the symbols.
        """
        sql = """
              SELECT * FROM public.sites_follows
        """
        params = []
        if site:
            sql += " WHERE site=%s"
            params.append(site)

        sql += " ORDER BY account"

        if not all:
            offset = (page - 1) * page_size
            sql += " LIMIT %s OFFSET %s"
            params.extend([page_size, offset])

        with self.con.cursor() as cur:
            try:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                profiles = [CrawlerStruct(*row) for row in rows]
                cur.close()
                return profiles
            except (Exception, psycopg2.DatabaseError) as error:
                logger.error(self.error_print(
                    error=error, method="get_profiles", query=sql))
                cur.close()
        return []

    def get_crawling_list(self, site: str) -> List[tuple]:
        """
        Get a list of site follows profiles from the database.

        Args:
            site (str): The name of the site to filter profiles by.
        Returns:
            List[str]: A list of accounts
        """
        sql = """
               SELECT DISTINCT account FROM public.sites_follows
                WHERE site=%s ORDER BY account
               """  # Use %s placeholder for parameters safely
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, (site,))  # Pass 'site' as a tuple
                rows = cur.fetchall()
                return [row[0] for row in rows]  # Assuming you want to return a list of strings

            except (Exception, psycopg2.DatabaseError) as error:
                logger.error(self.error_print(
                    error=error, method="get_profiles_crawl", query=sql))
                cur.close()
        return []

    def del_profile(self, fid: int) -> bool:
        """
        Deletes a crawler profile from the database.

        Args:
            fid (int): The follow ID to be deleted.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the removal.

        Returns:
            bool: True if the profile was deleted, False otherwise.
        """
        sql = "DELETE FROM sites_follows WHERE fid = %s"
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (fid,))  # Note the comma to make it a tuple
                self.con.commit()
                if cur.rowcount == 0:  # No rows deleted
                    return False
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(self.error_print(error=error, method="del_profile", query=sql))
        return False

    def add_crawler_site(self, site: str) -> bool:
        """
        Adds a crawler site to the database.

        Args:
            site (str): The site to be added.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the addition.

        Returns:
            bool: True if the site was added successfully, False otherwise.
        """
        sql = "INSERT INTO cat_sites (sites) VALUES (%s)"
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (site,))  # Note the comma to make it a tuple
                self.con.commit()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(self.error_print(error=error, method="add_crawler_site", query=sql))
            return False

    def del_crawler_site(self, site: str) -> bool:
        """
        Deletes a crawler site from the database.

        Args:
            site (str): The site to be deleted.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the deletion.

        Returns:
            bool: True if the site was deleted successfully, False otherwise.
        """
        sql = "DELETE FROM cat_sites WHERE sites = %s"
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (site,))  # Note the comma to make it a tuple
                self.con.commit()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(self.error_print(error=error, method="del_crawler_site", query=sql))
            return False

    def get_crawler_sites(self, page: int = 1, page_size: int = 10, all: bool = False, active=False) -> List[str]:
        """
        Get a list of crawler site profiles from the database.

        Args:
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.
            all (bool): If True, retrieves all records without pagination. Defaults to False.

        Returns:
            List[str]: A list of sites that can be crawled.
        """
        if active:
            sql = "SELECT DISTINCT(site) FROM public.sites_follows"  # Adjusted to specifically select the 'sites' column
        else:
            sql = "SELECT * FROM public.cat_sites"
        params = []
        if not all:
            offset = (page - 1) * page_size
            sql += " LIMIT %s OFFSET %s"
            params.extend([page_size, offset])

        with self.con.cursor() as cur:
            try:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                # Extract site names from the tuples
                sites = [row[0] for row in rows]  # Assuming site names are in the first column
                return sites
            except (Exception, psycopg2.DatabaseError) as error:
                logger.error(self.error_print(error=error, method="get_crawler_sites", query=sql))
        return []

    def add_posts(self, posts: List[CrawlerPostStruct]) -> bool:
        """
        Adds multiple posts to the table sites_posts or updates the scores if a post with the same unique constraint already exists.

        Args:
            posts (List[CrawlerPostStruct]): A list of CrawlerPostStruct objects representing the posts to add or update.

        Returns:
            bool: True if all posts were added or updated successfully, False otherwise.
        """
        sql = ("INSERT INTO sites_posts (account, account_id, remote_id, site, content, media, media_ocr, urls, "
               "timestamp, is_reply, reply_to, self_reply, views, likes, reposts, replies, followers, pre_score, score) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
               "ON CONFLICT ON CONSTRAINT remote_id_site_unique "
               "DO UPDATE SET pre_score = EXCLUDED.pre_score, score = EXCLUDED.score")

        # Prepare data for all posts, adjusted for new columns
        data = [(post.account, post.account_id, post.remote_id, post.site, post.content, post.media, post.media_ocr, post.urls,
                 post.timestamp, post.is_reply, post.reply_to, post.self_reply, post.views, post.likes,
                 post.reposts, post.replies, post.followers, post.pre_score, post.score) for post in posts]
        try:
            with self.con.cursor() as cur:
                cur.executemany(sql, data)
                self.con.commit()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning("Error adding or updating posts: {}".format(error))
            return False

    def get_posts(self, account: str, site: str, replies: bool = False, self_reply: bool = False) -> List[CrawlerPostStruct]:
        """
        Retrieve posts from the database by account and site.

        Args:
            account (str): The account name of the posts to retrieve.
            site (str): The site name of the posts to retrieve.
            replies (bool): If true it should return replies, if false no replies
            self_replies (bool): if true it should return replies to self using table attribute self_reply

        Returns:
            List[CrawlerPostStruct]: A list of retrieved posts as CrawlerPostStruct objects, empty if none found.
        """
        # Initialize the base SQL query
        sql = "SELECT * FROM sites_posts WHERE account = %s AND site = %s"     
        # Add conditions based on `replies` and `self_reply` parameters
        conditions = []
        if not replies:
            # Exclude replies
            conditions.append("is_reply = False")
        if self_reply:
            # Include only self-replies
            conditions.append("self_reply = True")      
        # Combine the conditions with AND operator if any
        if conditions:
            sql += " AND " + " AND ".join(conditions)

        posts = []
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (account, site))
                rows = cur.fetchall()
                for row in rows:
                    # Convert each psycopg2 DictRow to a standard dict
                    post_dict = dict(row)
                    # Use the from_dict class method to convert the dict to a CrawlerPostStruct object
                    post = CrawlerPostStruct.from_dict(post_dict)
                    posts.append(post)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error fetching posts for account '{account}' and site '{site}': {error}")
        return posts

    def get_post(self, post_id: int) -> Optional[CrawlerPostStruct]:
        """
        Retrieve a post from the database by its post_id.

        Args:
            post_id (int): The ID of the post to retrieve.

        Returns:
            Optional[CrawlerPostStruct]: The retrieved post as a CrawlerPostStruct object if found, None otherwise.
        """
        sql = "SELECT * FROM sites_posts WHERE post_id = %s"
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (post_id,))
                row = cur.fetchone()
                if row:
                    # Convert the psycopg2 DictRow to a standard dict
                    post_dict = dict(row)
                    # Use the from_dict class method to convert the dict to a CrawlerPostStruct object
                    return CrawlerPostStruct.from_dict(post_dict)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error fetching post with post_id {post_id}: {error}")
        return None

    def update_post_media(self, posts: List[CrawlerPostStruct]) -> bool:
        """
        Edits media and media_ocr fields in a list of posts in the database.

        Args:
            posts (List[CrawlerPostStruct]): A list of CrawlerPostStruct objects representing the posts to update.

        Returns:
            bool: True if the updates were successful, False otherwise.
        """
        # Filter and prepare parameters for posts that need updating and have valid post_id

        params = []
        for post in posts:
            # Only include posts that have both a media value and a valid post_id
            if post.media is not None and post.post_id is not None:
                params.append((post.media, post.media_ocr, post.post_id))
                if not params:
                    logger.info("No updates to perform.")
                    return True  # No updates needed due to filter criteria

        sql = "UPDATE sites_posts SET media = %s, media_ocr = %s WHERE post_id = %s;"

        try:
            with self.con.cursor() as cur:
                cur.executemany(sql, params)
                self.con.commit()
                updated_count = cur.rowcount  # Fetch the count of updated rows
                logger.info(f"Successfully updated {updated_count} posts.")
                return True
        except Exception as error:
            self.con.rollback()
            logger.error(f"Error updating posts: {error}")
            return False

    def get_last_post_dates(self, site: str) -> Optional[Dict[str, arrow.Arrow]]:
        """
        Get the last date of the latest post by site for each account.

        Args:
            site (str): The name of the site to filter posts by.

        Returns:
            Dict[str, arrow.Arrow]: A dictionary mapping accounts to their last post date.
        """
        sql = """
              SELECT account, MAX(timestamp) AS last_timestamp
              FROM public.sites_posts
              WHERE site = %s
              GROUP BY account
              ORDER BY last_timestamp DESC;
        """
        results_dict = {}
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, (site,))
                rows = cur.fetchall()
                if rows:
                    for row in rows:
                        account, last_timestamp = row
                        results_dict[account] = arrow.get(last_timestamp)
                return results_dict
            except (Exception, psycopg2.DatabaseError) as error:
                logger.error(self.error_print(
                    error=error, method="get_last_post_dates", query=sql))
        return None

    def get_pre_scores(self, num: int = 25000) -> list[tuple[float]]:
        """
        Get last 15000 pre_scores.

        Returns:
            list a list of scores
        """
        sql = """
              SELECT pre_score
              FROM public.sites_posts
              ORDER BY timestamp DESC
              limit %s;
        """
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, (num,))
                rows = cur.fetchall()
                return [float(row[0]) for row in rows]
            except (Exception, psycopg2.DatabaseError) as error:
                logger.error(self.error_print(
                    error=error, method="get_pre_scores", query=sql))
        return []

    def add_llm_engine(self, engine: str) -> bool:
        """
        Adds a new engine to the llm_catalog.

        Args:
            engine (str): The name of the engine.

        Returns:
            bool: True if the engine was added, False otherwise.
        """
        sql = "INSERT INTO llm_engines(engine) VALUES(%s)"
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, (engine,))
                self.con.commit()  # Commit changes
                return True
            except (Exception, psycopg2.DatabaseError) as error:
                self.con.rollback()
                logger.error(f"Error adding llm_engine: {error}")
                return False

    def del_llm_engine(self, engine: str) -> bool:
        """
        Deletes an engine from the llm_catalog.

        Args:
            engine (str): The name of the engine.

        Returns:
            bool: True if the engine was deleted, False otherwise.
        """
        sql = "DELETE FROM llm_engines WHERE engine = %s"
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, (engine,))
                self.con.commit()  # Commit changes
                return True
            except (Exception, psycopg2.DatabaseError) as error:
                self.con.rollback()
                logger.error(f"Error deleting llm_engine: {error}")
                return False

    def get_llm_engines(self, page: int = 1, page_size: int = 10, all: bool = False) -> List[str]:
        """
        Get a list of llm_engines from the database.

        Args:
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.
            all (bool): If True, retrieves all records without pagination. Defaults to False.

        Returns:
            List[str]: A list of engine names.
        """
        sql = "SELECT engine FROM public.llm_engines"
        params = []
        if not all:
            offset = (page - 1) * page_size
            sql += " LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                engines = [row[0] for row in rows]  # Assuming engine names are in the first column
                return engines
            except (Exception, psycopg2.DatabaseError) as error:
                logger.error(f"Error in get_llm_engines: {error}, Query: {sql}")
                return []

    def add_engine_score(self, post_id: int, aid:int, engine: str, score: Decimal) -> bool:
        """
        Adds a new llm_score to database

        Args:
            post_id (int): The analyzed post
            aid (int): The analzyer id
            engine (str): The engine used (openai)
            score (float): The scored gotten

        Returns:
            Bool: True if score was added
        """
        sql = """
        INSERT INTO engine_scores (post_id, aid, engine, score)
        VALUES (%s, %s, %s, %s)
        """
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, (post_id, aid, engine, score),)
                logger.debug("Score added for post_id %s", (post_id))
                self.con.commit()
                return True
            except (Exception, psycopg2.DatabaseError) as error:
                print("shit")
                self.con.rollback()
                logger.error("Error adding engine score: {}".format(error))
        return False

    def get_engine_scores(self, post_id: int, engine: str) -> List[Tuple[int, str, Decimal]]:
        """
        Retrieves scores for a given post and engine from the database.

        Args:
            post_id (int): The ID of the analyzed post.
            engine (str): The name of the engine used (e.g., "openai").

        Returns:
            List[Tuple[int, str, Decimal]]: A list of tuples, each containing the post_id, 
                                            analyzer ID (aid), and the score as a Decimal. 
                                            Returns an empty list if no scores are found.
        """
        sql = """
        SELECT post_id, aid, score
        FROM engine_scores
        WHERE post_id = %s AND engine = %s
        """
        scores = []
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (post_id, engine))
                rows = cur.fetchall()
                for row in rows:
                    # Assuming 'aid' can be directly used and recognized as the analyzer ID.
                    scores.append((row[0], row[1], Decimal(row[2])))
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.error(f"Error retrieving engine scores for post_id {post_id} and engine '{engine}': {error}")
        return scores

    def add_analyzer(self, analyzer: CrawlerAnalyzerStruct) -> Optional[int]:
        """
        Adds a new analyzer to the database.

        Args:
            analyzer (CrawlerAnalyzerStruct): The analyzer details to add.

        Returns:
            Optional[int]: The aid of the added analyzer, or None if the operation fails.
        """
        sql = """
        INSERT INTO post_analyzers (title, prompt)
        VALUES (%s, %s)
        RETURNING aid;
        """
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, (analyzer.title, analyzer.prompt))
                aid = cur.fetchone()[0]
                self.con.commit()
                return aid
            except (Exception, psycopg2.DatabaseError) as error:
                self.con.rollback()
                logger.warning("Error adding analyzer: {}".format(error))
                return None

    def edit_analyzer(self, analyzer: CrawlerAnalyzerStruct) -> bool:
        """
        Edits an existing analyzer in the database.

        Args:
            analyzer (CrawlerAnalyzerStruct): The analyzer details to update.

        Returns:
            bool: True if the analyzer was successfully updated, False otherwise.
        """
        if analyzer.aid is None:
            logger.warning("Analyzer ID is required for editing.")
            return False

        sql = """
        UPDATE post_analyzers
        SET title = %s, prompt = %s
        WHERE aid = %s;
        """
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, (analyzer.title, analyzer.prompt, analyzer.aid))
                self.con.commit()
                return cur.rowcount > 0
            except (Exception, psycopg2.DatabaseError) as error:
                self.con.rollback()
                logger.warning("Error editing analyzer: {}".format(error))
                return False

    def del_analyzer(self, aid: int) -> bool:
        """
        Deletes an analyzer from the database.

        Args:
            aid (int): The ID of the analyzer to delete.

        Returns:
            bool: True if the analyzer was successfully deleted, False otherwise.
        """
        sql = "DELETE FROM post_analyzers WHERE aid = %s"
        with self.con.cursor() as cur:
            try:
                cur.execute(sql, (aid,))
                self.con.commit()
                return cur.rowcount > 0
            except (Exception, psycopg2.DatabaseError) as error:
                self.con.rollback()
                logger.warning("Error deleting analyzer: {}".format(error))
                return False

    def get_analyzers(self) -> list[CrawlerAnalyzerStruct]:
        """
        gets all analyzers from the database

        Returns:
            list: a list of CrawlerAnalyzerStruct
        """
        sql = "SELECT aid, title, prompt FROM post_analyzers;"
        analyzers = []
        with self.con.cursor() as cur:
            try:
                cur.execute(sql)
                rows = cur.fetchall()
                for row in rows:
                    analyzers.append(CrawlerAnalyzerStruct(aid=row[0], title=row[1], prompt=row[2]))
                return analyzers
            except (Exception, psycopg2.DatabaseError) as error:
                logger.warning("Error fetching analyzers: {}".format(error))
                return []

    def get_account_analyzers(self) -> list[CrawlerAnalyzerStruct]:
        """
        Gets all unique analyzers from the database that are associated with accounts.

        Returns:
            list[CrawlerAnalyzerStruct]: A list of unique CrawlerAnalyzerStruct instances for each account.
        """
        sql = """
        SELECT DISTINCT pa.aid, pa.title, pa.prompt
        FROM post_analyzers pa
        INNER JOIN follows_analyzers fe ON pa.aid = fe.aid
        ORDER BY pa.aid;
        """
        analyzers = []
        with self.con.cursor() as cur:
            try:
                cur.execute(sql)
                rows = cur.fetchall()
                for row in rows:
                    analyzers.append(CrawlerAnalyzerStruct(aid=row[0], title=row[1], prompt=row[2]))
                return analyzers
            except (Exception, psycopg2.DatabaseError) as error:
                logger.warning(f"Error fetching unique account analyzers: {error}")
                return []

    def add_follows_analyzer(self, uid: int, aid: int, fid: int, account: str) -> bool:
        """
        Inserts a new record into the follows_analyzers table.

        Args:
            uid (int): User ID associated with the record.
            aid (int): Analyzer ID associated with the record.
            fid (int): Follows ID associated with the record.
            account (str): Account text associated with the record.

        Returns:
            bool: True if the record was successfully inserted, False otherwise.
        """
        sql = """
        INSERT INTO follows_analyzers (uid, aid, fid, account)
        VALUES (%s, %s, %s, %s);
        """
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (uid, aid, fid, account))
                self.con.commit()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error inserting into follows_engines: {error}")
            self.con.rollback()
            return False

    def delete_follows_analyzer(self, uid: int, aid: int, fid: int) -> bool:
        """
        Deletes a record from the follows_analyzers table.

        Args:
            uid (int): User ID associated with the record to delete.
            aid (int): Analyzer ID associated with the record to delete.
            fid (int): Follows ID associated with the record to delete.
            account (str): Account text associated with the record to delete.

        Returns:
            bool: True if the record was successfully deleted, False otherwise.
        """
        sql = """
        DELETE FROM follows_analyzers
        WHERE uid = %s AND aid = %s AND fid = %s;
        """
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (uid, aid, fid))
                self.con.commit()
                # Verify that the record was indeed deleted
                if cur.rowcount > 0:
                    return True
                else:
                    logger.warning(f"No record found to delete with uid={uid}, aid={aid}, fid={fid}, account='{account}'.")
                    return False
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(self.error_print(
                error=error, method="delete_follows_analyzer", query=sql))
        return False

    def get_unscored_posts(self, aid: int, engine: str, no_is_reply: bool = False) -> List[CrawlerPostStruct]:
        """
        Retrieves posts that have not been scored by a given analyzer and engine, ordered by account and sorted by date.

        Args:
            aid (int): The analyzer ID.
            engine (str): The name of the engine.
            no_is_reply (bool): If True, exclude posts that are replies, unless they are self-replies.

        Returns:
            List[CrawlerPostStruct]: A list of unscored posts.
        """
        sql = """
        SELECT sp.post_id, sp.timestamp, sp.remote_id, sp.account, sp.account_id, sp.site, sp.content,
               sp.media, sp.media_ocr, sp.urls, sp.is_reply, sp.reply_to, sp.self_reply, sp.views,
               sp.likes, sp.reposts, sp.replies, sp.followers, sp.pre_score
        FROM sites_posts sp
        LEFT JOIN engine_scores es ON sp.post_id = es.post_id AND es.aid = %s AND es.engine = %s
        WHERE es.score IS NULL
        """
        # Modify the condition to exclude is_reply posts if no_is_reply is True, but include if self_reply is True
        if no_is_reply:
            sql += " AND (sp.is_reply = False OR sp.self_reply = True)"
        else:
            # If no_is_reply is False, no need to modify the query to filter out replies
            pass
        sql += " ORDER BY sp.account ASC, sp.timestamp ASC"
        posts = []
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (aid, engine))
                for row in cur.fetchall():
                    post = CrawlerPostStruct(
                        post_id=row[0], timestamp=row[1], remote_id=row[2], account=row[3],
                        account_id=row[4], site=row[5], content=row[6], media=row[7],
                        media_ocr=row[8], urls=row[9], is_reply=row[10], reply_to=row[11],
                        self_reply=row[12], views=row[13], likes=row[14], reposts=row[15],
                        replies=row[16], followers=row[17], pre_score=row[18]
                    )
                    posts.append(post)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(self.error_print(
                error=error, method="get_unscored_posts", query=sql))
        return posts
