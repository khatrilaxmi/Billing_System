# CmsLib/CounterManager.py
import re
from CmsLib.InventoryManager import *
from CmsLib.TokenManager import *

class CounterManager:

    # ------------------- ADD COUNTER TO TOKEN -------------------
    @staticmethod
    def __add_counter_to_token(pysql, token_id, product_id, quantity, size, color):

        # Fetch name from ProductID for validation
        sql = "SELECT Name FROM Products WHERE ProductID=%s AND Size=%s AND Color=%s"
        pysql.run(sql, (product_id, size, color))
        product_name = pysql.scalar_result

        if not product_name:
            return 3  # Product not found

        # Token assigned check
        token_assigned = TokenManager.is_token_assigned(pysql, token_id)
        if not token_assigned:
            return 1

        # Check displayed inventory
        displayed_quantity, _ = InventoryManager.get_displayed_quantity(pysql, product_id, size, color)
        # Ensure it is a number
        if isinstance(displayed_quantity, tuple):
            displayed_quantity = displayed_quantity[0]

        if quantity <= 0:
            return 2
        if displayed_quantity < quantity:
            return 4

        # Deduct from displayed inventory
        sql_stmt = """UPDATE Inventory 
                      SET DisplayedQuantity = DisplayedQuantity - %s
                      WHERE ProductID=%s AND Size=%s AND Color=%s"""
        pysql.run(sql_stmt, (quantity, product_id, size, color))

        # Add to TokensSelectProducts
        sql_stmt = """SELECT 1 FROM TokensSelectProducts 
                      WHERE TokenID=%s AND ProductID=%s AND Size=%s AND Color=%s"""
        pysql.run(sql_stmt, (token_id, product_id, size, color))
        product_present = pysql.scalar_result

        if product_present:
            sql_stmt = """UPDATE TokensSelectProducts
                          SET Quantity = Quantity + %s
                          WHERE TokenID=%s AND ProductID=%s AND Size=%s AND Color=%s"""
            pysql.run(sql_stmt, (quantity, token_id, product_id, size, color))
        else:
            sql_stmt = """INSERT INTO TokensSelectProducts
                          (TokenID, ProductID, Quantity, Size, Color)
                          VALUES (%s, %s, %s, %s, %s)"""
            pysql.run(sql_stmt, (token_id, product_id, quantity, size, color))

        InventoryManager._InventoryManager__log_transaction(pysql, "COUNTER_SUB", product_id, size, color, quantity)
        return 0

    # ------------------- ADD INVENTORY TO COUNTER -------------------
    @staticmethod
    def __add_inventory_to_counter(pysql, product_id, quantity, size, color):

         # Fetch name from ProductID for validation
        sql = "SELECT Name FROM Products WHERE ProductID=%s AND Size=%s AND Color=%s"
        pysql.run(sql, (product_id, size, color))
        product_name = pysql.scalar_result

        if not product_name:
            return 3 # Product not found

        stored_quantity = InventoryManager._InventoryManager__get_stored_quantity(pysql, product_id, size, color)
        # Ensure it is a number
        if isinstance(stored_quantity, tuple):
            stored_quantity = stored_quantity[0]

        if quantity <= 0:
            return 2
        if stored_quantity < quantity:
            return 4

        # Transfer from stored to displayed
        sql_stmt = """UPDATE Inventory
                      SET DisplayedQuantity = DisplayedQuantity + %s,
                          StoredQuantity = StoredQuantity - %s
                      WHERE ProductID=%s AND Size=%s AND Color=%s"""
        pysql.run(sql_stmt, (quantity, quantity, product_id, size, color))

        InventoryManager._InventoryManager__log_transaction(pysql, "INVENTORY_TO_COUNTER", product_id, size, color, quantity)
        return 0

    # ------------------- ADD TOKEN TO COUNTER -------------------
    @staticmethod
    def __add_token_to_counter(pysql, token_id, product_id, size, color):

        # Get ProductName
        sql = "SELECT Name FROM Products WHERE ProductID=%s AND Size=%s AND Color=%s"
        pysql.run(sql, (product_id, size, color))
        product_name = pysql.scalar_result

        if not product_name:
            return 3 # Product not found
    
      
        sql_stmt = """SELECT Quantity FROM TokensSelectProducts 
                      WHERE TokenID=%s AND ProductID=%s AND Size=%s AND Color=%s"""
        pysql.run(sql_stmt, (token_id, product_id, size, color))

        quantity = pysql.scalar_result

        if isinstance(quantity, tuple):
            quantity = quantity[0]

        if not quantity:
            return 5 #product not found in token

        # Remove from token
        sql_stmt = """DELETE FROM TokensSelectProducts
                      WHERE TokenID=%s AND ProductID=%s AND Size=%s AND Color=%s"""
        pysql.run(sql_stmt, (token_id, product_id, size, color))

        # Add back to displayed inventory
        sql_stmt = """UPDATE Inventory
                      SET DisplayedQuantity = DisplayedQuantity + %s
                      WHERE ProductID=%s AND Size=%s AND Color=%s"""
        pysql.run(sql_stmt, (quantity, product_id, size, color))

        InventoryManager._InventoryManager__log_transaction(pysql, "COUNTER_ADD", product_id, size, color, quantity)
        return 0

    # ------------------- PUBLIC METHODS -------------------
    @staticmethod
    def add_counter_to_token(pysql, token_id, product_id, quantity, size, color):
        return pysql.run_transaction(CounterManager.__add_counter_to_token,
                                     token_id, product_id, quantity, size, color)

    @staticmethod
    def add_inventory_to_counter(pysql, product_id, quantity, size, color):
        return pysql.run_transaction(CounterManager.__add_inventory_to_counter,
                                     product_id, quantity, size, color)

    @staticmethod
    def add_token_to_counter(pysql, token_id, product_id, size, color):
        return pysql.run_transaction(CounterManager.__add_token_to_counter,
                                     token_id, product_id, size, color)
