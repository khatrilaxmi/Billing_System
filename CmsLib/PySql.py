# CmsLib/PySql.py
from flask_mysqldb import MySQL 
import yaml
from MySQLdb import InterfaceError, OperationalError, ProgrammingError

# @brief This class connects Python to MySQL and provides
#        helper methods for queries and transactions
class PySql:
    def __init__(self, flask_app, path_to_yaml):
        # Load DB configuration from YAML
        db_details = yaml.load(open(path_to_yaml), Loader=yaml.FullLoader)
        flask_app.config['MYSQL_HOST'] = db_details['mysql_host']
        flask_app.config['MYSQL_USER'] = db_details['mysql_user']
        flask_app.config['MYSQL_PASSWORD'] = db_details['mysql_password']
        flask_app.config['MYSQL_DB'] = db_details['mysql_db']
        self.mysql = MySQL(flask_app)
        self.mysql_cursor = None
        self.__last_result = None

    # ----------------- Cursor Management -----------------
    def init(self):
        # Check if connection is alive
        try:
            if self.mysql.connection:
                self.mysql.connection.ping(reconnect=True) # Reconnect if needed
        except:
            # Recreate connection object if ping fails
            self.mysql_cursor = None

        # Create cursor if it's None
        if self.mysql_cursor is None:
            self.mysql_cursor = self.mysql.connection.cursor()


    def deinit(self):
       try:
         if self.mysql_cursor:
            self.mysql_cursor.close()
       finally:
         self.mysql_cursor = None


    # ----------------- Query Execution -----------------
    def run(self, sql_stmt, params=None):
        
        try:
            self.init() 
            self.mysql_cursor.execute(sql_stmt, params)
        except (InterfaceError, OperationalError) as e:
            # Retry once after re-init
            self.deinit()
            self.init()
            self.mysql_cursor.execute(sql_stmt, params)
        except ProgrammingError as e:
            raise RuntimeError(f"MySQL query failed: {e}")

    def run_many(self, sql_stmt, params):
        self.init() 
        try:
            self.mysql_cursor.executemany(sql_stmt, params)
        except (InterfaceError, OperationalError, ProgrammingError) as e:
            raise RuntimeError(f"MySQL bulk query failed: {e}")

    # ----------------- Fetch Results -----------------
    def __result(self):
        try:
            self.__last_result = self.mysql_cursor.fetchall()
            return self.__last_result
        except InterfaceError:
            # If result cannot be fetched, return previous result
            return self.__last_result

    @property
    def result(self):
        return self.__result()

    @property
    def scalar_result(self):
        try:
            return self.__result()[0][0]
        except (IndexError, TypeError):
            return None

    @property
    def first_result(self):
        try:
            return self.__result()[0]
        except (IndexError, TypeError):
            return None

    # ----------------- Transaction Management -----------------
    def commit(self):
        if self.mysql.connection:
            self.mysql.connection.commit()

    def rollback(self):
        if self.mysql.connection:
            self.mysql.connection.rollback()

    def run_transaction(self, function, *args, commit=True):
        """
        Runs a function within a transaction with safe commit/rollback
        :param function: function(self, *args) to run
        :param args: arguments for function
        :param commit: whether to commit after success
        :return: result of function
        """
        self.init()
        try:
            result = function(self, *args)
        except Exception as e:
            self.rollback()
            self.deinit()
            print(f"[PySql Transaction Error] {e}")
            raise RuntimeError(f"Transaction failed: {e}")
        else:
            if commit:
                self.commit()
            return result
        finally:
            self.deinit()
