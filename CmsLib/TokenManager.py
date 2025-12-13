# TokenManager.py
# -------------------------------------------------
# Updated for Shree Laxmi Collection
# Handles color & size variants of female clothing
# -------------------------------------------------

class TokenManager:

    # ---------- PRIVATE METHODS ----------

    @staticmethod
    def __add_token(pysql):
        sql_stmt = "SELECT `TokenID` FROM `Tokens` ORDER BY `TokenID` ASC"
        pysql.run(sql_stmt)
        tokens = [int(token[0][4:]) for token in pysql.result]

        token_i = 0
        for token in tokens:
            if token_i != token:
                break
            token_i += 1

        if token_i >= 100:
            return 1

        token_id = "TOK-" + format(token_i, "02d")
        sql_stmt = "INSERT INTO `Tokens` (`TokenID`) VALUES (%s)"
        pysql.run(sql_stmt, (token_id,))
        return token_id

    @staticmethod
    def __remove_token(pysql, token_id):
        has_products = TokenManager._TokenManager__token_has_products(pysql, token_id)
        is_assigned = TokenManager._TokenManager__is_token_assigned(pysql, token_id)

        if has_products:
            return 1
        if is_assigned:
            return 2
        if is_assigned is None:
            return 3

        sql_stmt = "DELETE FROM `Tokens` WHERE `TokenID` = %s"
        pysql.run(sql_stmt, (token_id,))
        return 0

    @staticmethod
    def __get_token(pysql):
        sql_stmt = "SELECT `TokenID` FROM `Tokens` WHERE `Assigned` = 0 LIMIT 1"
        pysql.run(sql_stmt)
        token_id = pysql.scalar_result
        if not token_id:
            return None

        sql_stmt = "UPDATE `Tokens` SET `Assigned` = true WHERE `TokenID` = %s"
        pysql.run(sql_stmt, (token_id,))
        return token_id

    @staticmethod
    def __return_token(pysql, token_id):
        has_products = TokenManager._TokenManager__token_has_products(pysql, token_id)
        is_assigned = TokenManager._TokenManager__is_token_assigned(pysql, token_id)

        if has_products:
            return 1
        if is_assigned == 0:
            return 2
        if is_assigned is None:
            return 3

        sql_stmt = "UPDATE `Tokens` SET `Assigned` = false, `InvoiceID` = NULL WHERE `TokenID` = %s"
        pysql.run(sql_stmt, (token_id,))
        return 0

    @staticmethod
    def __is_token_assigned(pysql, token_id):
        sql_stmt = "SELECT `Assigned` FROM `Tokens` WHERE `TokenID` = %s"
        pysql.run(sql_stmt, (token_id,))
        return pysql.scalar_result

    @staticmethod
    def __token_has_products(pysql, token_id):
        sql_stmt = "SELECT COUNT(*) FROM `TokensSelectProducts` WHERE `TokenID` = %s"
        pysql.run(sql_stmt, (token_id,))
        return pysql.scalar_result

    @staticmethod
    def __get_token_details(pysql, token_id):
        sql_stmt = """
            SELECT `ProductID`, `Color`, `Size`, `Quantity`
            FROM `TokensSelectProducts`
            WHERE `TokenID` = %s
        """
        pysql.run(sql_stmt, (token_id,))
        return pysql.result

    @staticmethod
    def __get_all_tokens_status(pysql):
        sql_stmt = "SELECT `TokenID`, `Assigned` FROM `Tokens`"
        pysql.run(sql_stmt)
        return pysql.result
    
    @staticmethod
    def __get_pending_tokens(pysql):
        """
        Returns a list of TokenIDs that have products assigned (i.e., pending tokens)
        """
        sql_stmt = "SELECT DISTINCT `TokenID` FROM `TokensSelectProducts`"
        pysql.run(sql_stmt)
        
        pending_tokens = [row[0] for row in pysql.result]
        print("Pending Tokens okay:", pending_tokens)
        if not pysql.result:
            return []
        return [row[0] for row in pysql.result]


    # ---------- PUBLIC WRAPPERS ----------

    @staticmethod
    def add_token(pysql):
        return pysql.run_transaction(TokenManager.__add_token)

    @staticmethod
    def remove_token(pysql, token_id):
        return pysql.run_transaction(TokenManager.__remove_token, token_id)

    @staticmethod
    def get_token(pysql):
        return pysql.run_transaction(TokenManager.__get_token)

    @staticmethod
    def return_token(pysql, token_id):
        return pysql.run_transaction(TokenManager.__return_token, token_id)

    @staticmethod
    def is_token_assigned(pysql, token_id):
        return pysql.run_transaction(TokenManager.__is_token_assigned, token_id, commit=False)

    @staticmethod
    def token_has_products(pysql, token_id):
        return pysql.run_transaction(TokenManager.__token_has_products, token_id, commit=False)

    @staticmethod
    def get_all_tokens_status(pysql):
        return pysql.run_transaction(TokenManager.__get_all_tokens_status, commit=False)
    
    @staticmethod
    def get_pending_tokens(pysql):
        return pysql.run_transaction(TokenManager.__get_pending_tokens, commit=False)

    @staticmethod
    def get_token_details(pysql, token_id):
        return pysql.run_transaction(TokenManager.__get_token_details, token_id, commit=False)
