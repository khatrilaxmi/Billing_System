# InventoryManager.py
# -------------------------------------------------
# Fully updated for Shree Laxmi Collection
# Handles color & size variants of female clothing
# -------------------------------------------------

next_transaction_id = None
next_transaction_id_read = 0

class InventoryManager:
    """
    Handles all inventory-related operations:
    - Tracks displayed (counter) & stored (inventory) quantities
    - Supports product variants (Color, Size)
    - Logs every transaction with unique TransactionID
    - Includes UnitType
    """

    # ---------- PRIVATE METHODS ----------

    @staticmethod
    def __get_displayed_quantity(pysql, product_id, size, color):
        sql_stmt = """
            SELECT `DisplayedQuantity`, `UnitType`
            FROM `Inventory`
            JOIN `Products` USING (`ProductID`)
            WHERE `ProductID` = %s AND `Size` = %s AND `Color` = %s
        """
        pysql.run(sql_stmt, (product_id, size, color))
        result = pysql.first_result
        return result if result else (0, 'pcs')

    @staticmethod
    def __get_stored_quantity(pysql, product_id, size, color):
        sql_stmt = """
            SELECT `StoredQuantity`, `UnitType`
            FROM `Inventory`
            JOIN `Products` USING (`ProductID`)
            WHERE `ProductID` = %s AND `Size` = %s AND `Color` = %s
        """
        pysql.run(sql_stmt, (product_id, size, color))
        result = pysql.first_result
        return result if result else (0, 'pcs')

    @staticmethod
    def __is_below_threshold(pysql, product_id, size, color):
        sql_stmt = """
            SELECT `StoredQuantity` <= `StoreThreshold`
            FROM `Inventory`
            WHERE `ProductID` = %s AND `Size` = %s AND `Color` = %s
        """
        pysql.run(sql_stmt, (product_id, size, color))
        return pysql.scalar_result

    @staticmethod
    def __inventory_has_product(pysql, product_id, size, color):
        sql_stmt = """
            SELECT COUNT(*)
            FROM `Inventory`
            WHERE `ProductID` = %s AND `Size` = %s AND `Color` = %s
        """
        pysql.run(sql_stmt, (product_id, size, color))
        return pysql.scalar_result

    @staticmethod
    def __update_threshold(pysql, product_id, size, color, threshold):
        has_product = InventoryManager._InventoryManager__inventory_has_product(pysql, product_id, size, color)
        if threshold < 0:
            return 1
        if not has_product:
            return 2
        sql_stmt = """
            UPDATE `Inventory`
            SET `StoreThreshold` = %s
            WHERE `ProductID` = %s AND `Size` = %s AND `Color` = %s
        """
        pysql.run(sql_stmt, (threshold, product_id, size, color))
        return 0

    @staticmethod
    def __sub_product_from_inventory(pysql, product_id, size, color, quantity):
        has_product = InventoryManager._InventoryManager__inventory_has_product(pysql, product_id, size, color)
        if quantity < 0:
            return 1
        if not has_product:
            return 2
        sql_stmt = """
            UPDATE `Inventory`
            SET `StoredQuantity` = `StoredQuantity` - %s
            WHERE `ProductID` = %s AND `Size` = %s AND `Color` = %s
        """
        pysql.run(sql_stmt, (quantity, product_id, size, color))
        InventoryManager.__log_transaction(pysql, "INVENTORY_SUB", product_id, size, color, quantity)
        return 0

    @staticmethod
    def __log_transaction(pysql, transaction_type, product_id, size, color, quantity):
        global next_transaction_id, next_transaction_id_read

        if not next_transaction_id_read:
            sql_stmt = "SELECT COUNT(*) FROM `InventoryTransactions`"
            pysql.run(sql_stmt)
            next_transaction_id = pysql.scalar_result
            next_transaction_id_read = 1

        if transaction_type not in ["COUNTER_ADD", "COUNTER_SUB", "INVENTORY_TO_COUNTER", "INVENTORY_ADD", "INVENTORY_SUB"]:
            return 1

        has_product = InventoryManager._InventoryManager__inventory_has_product(pysql, product_id, size, color)
        if not has_product:
            return 2
        if quantity <= 0:
            return 3

        transaction_id = "TRC-" + format(next_transaction_id, "010d")
        sql_stmt = """
            INSERT INTO `InventoryTransactions`
            (`TransactionID`, `TransactionType`, `ProductID`, `Size`, `Color`, `Quantity`, `Timestamp`)
            VALUES (%s, %s, %s, %s, %s, %s, (SELECT CURRENT_TIMESTAMP))
        """
        pysql.run(sql_stmt, (transaction_id, transaction_type, product_id, size, color, quantity))
        next_transaction_id += 1
        return 0

    @staticmethod
    def __get_inventory_details(pysql):
        sql_stmt = """
            SELECT 
              Inventory.ProductID,
              Products.Name AS ProductName,
              Inventory.Size,
              Inventory.Color,
              Inventory.StoredQuantity,
              Inventory.DisplayedQuantity,
              Inventory.StoreThreshold
        FROM Inventory
        JOIN Products ON Inventory.ProductID = Products.ProductID
        """
        pysql.run(sql_stmt)
        return pysql.result

    @staticmethod
    def __get_transactions(pysql):
        sql_stmt = """
            SELECT `TransactionID`, `ProductID`, `Name`, `Size`, `Color`, 
                   `TransactionType`, `Quantity`, `UnitType`, `Timestamp`
            FROM `InventoryTransactions`
            JOIN `Products` USING (`ProductID`)
        """
        pysql.run(sql_stmt)
        return pysql.result

    @staticmethod
    def __get_transactions_by_date(pysql, date):
        sql_stmt = """
            SELECT `TransactionID`, `ProductID`, `Name`, `Size`, `Color`, 
                   `TransactionType`, `Quantity`, `UnitType`, TIME(`Timestamp`)
            FROM `InventoryTransactions`
            JOIN `Products` USING (`ProductID`)
            WHERE DATE(`Timestamp`) = %s
        """
        pysql.run(sql_stmt, (date,))
        return pysql.result

    @staticmethod
    def __get_transactions_of_product_by_date(pysql, product_id, size, color, date):
        sql_stmt = """
            SELECT `TransactionID`, `TransactionType`, `Quantity`, `UnitType`, TIME(`Timestamp`)
            FROM `InventoryTransactions`
            JOIN `Products` USING (`ProductID`)
            WHERE `ProductID` = %s AND `Size` = %s AND `Color` = %s AND DATE(`Timestamp`) = %s
        """
        pysql.run(sql_stmt, (product_id, size, color, date))
        return pysql.result

    # ---------- PUBLIC WRAPPERS ----------
    @staticmethod
    def get_displayed_quantity(pysql, product_id, size, color):
        return pysql.run_transaction(InventoryManager.__get_displayed_quantity, product_id, size, color, commit=False)

    @staticmethod
    def get_stored_quantity(pysql, product_id, size, color):
        return pysql.run_transaction(InventoryManager.__get_stored_quantity, product_id, size, color, commit=False)

    @staticmethod
    def is_below_threshold(pysql, product_id, size, color):
        return pysql.run_transaction(InventoryManager.__is_below_threshold, product_id, size, color, commit=False)

    @staticmethod
    def inventory_has_product(pysql, product_id, size, color):
        return pysql.run_transaction(InventoryManager.__inventory_has_product, product_id, size, color, commit=False)

    @staticmethod
    def update_threshold(pysql, product_id, size, color, threshold):
        return pysql.run_transaction(InventoryManager.__update_threshold, product_id, size, color, threshold)

    @staticmethod
    def sub_product_from_inventory(pysql, product_id, size, color, quantity):
        return pysql.run_transaction(InventoryManager.__sub_product_from_inventory, product_id, size, color, quantity)

    @staticmethod
    def log_transaction(pysql, transaction_type, product_id, size, color, quantity):
        return pysql.run_transaction(InventoryManager.__log_transaction, transaction_type, product_id, size, color, quantity, commit=False)

    @staticmethod
    def get_inventory_details(pysql):
        return pysql.run_transaction(InventoryManager.__get_inventory_details, commit=False)

    @staticmethod
    def get_transactions(pysql):
        return pysql.run_transaction(InventoryManager.__get_transactions, commit=False)

    @staticmethod
    def get_transactions_by_date(pysql, date):
        return pysql.run_transaction(InventoryManager.__get_transactions_by_date, date, commit=False)

    @staticmethod
    def get_transactions_of_product_by_date(pysql, product_id, size, color, date):
        return pysql.run_transaction(InventoryManager.__get_transactions_of_product_by_date, product_id, size, color, date, commit=False)
