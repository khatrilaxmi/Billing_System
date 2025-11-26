# ProductManager.py
# -------------------------------------------------
# Fully updated for Shree Laxmi Collection
# UnitType is always 'pcs'
# Includes Size and Color
# -------------------------------------------------

class ProductManager:

    # ---------- PRIVATE METHODS ----------

    @staticmethod
    def __add_product(pysql, product_id, name, description, unit_price, size, color, discount=None):
        """
        Adds a new product with size and color.
        unit_price: price per piece
        discount: optional discount in percentage
        """
        # Check if product exists
        if ProductManager._ProductManager__product_exists(pysql, product_id):
            return 1

        # Check if price is positive
        if unit_price <= 0:
            return 2

        # Check discount
        if discount is not None and discount < 0:
            return 3

        # Insert product into Products table
        sql_stmt = """
            INSERT INTO `Products`
            (`ProductID`, `Name`, `Description`, `UnitPrice`, `UnitType`, `Size`, `Color`, `CurrentDiscount`)
            VALUES (%s, %s, %s, %s, 'pcs', %s, %s, %s)
        """
        pysql.run(sql_stmt, (product_id, name, description, unit_price, size, color, discount or 0))

        sql_stmt = """
            INSERT INTO Inventory
            (ProductID, Size, Color, StoredQuantity, DisplayedQuantity, StoreThreshold)
            VALUES (%s, %s, %s, %s, %s,%s)
        """
        pysql.run(sql_stmt, (product_id, size, color, 0, 0, 5))
        return 0

    @staticmethod
    def __update_product_discount(pysql, product_id, discount):
        if not ProductManager._ProductManager__product_exists(pysql, product_id):
            return 1
        if discount < 0:
            return 2

        sql_stmt = "UPDATE `Products` SET `CurrentDiscount` = %s WHERE `ProductID` = %s"
        pysql.run(sql_stmt, (discount, product_id))
        return 0

    @staticmethod
    def __update_product_price(pysql, product_id, price):
        if not ProductManager._ProductManager__product_exists(pysql, product_id):
            return 1
        if price <= 0:
            return 2

        sql_stmt = "UPDATE `Products` SET `UnitPrice` = %s WHERE `ProductID` = %s"
        pysql.run(sql_stmt, (price, product_id))
        return 0

    @staticmethod
    def __update_product_description(pysql, product_id, description):
        if not ProductManager._ProductManager__product_exists(pysql, product_id):
            return 1

        sql_stmt = "UPDATE `Products` SET `Description` = %s WHERE `ProductID` = %s"
        pysql.run(sql_stmt, (description, product_id))
        return 0

    @staticmethod
    def __product_exists(pysql, product_id):
        sql_stmt = "SELECT COUNT(*) FROM `Products` WHERE `ProductID` = %s"
        pysql.run(sql_stmt, (product_id,))
        return pysql.scalar_result

    @staticmethod
    def __get_all_products(pysql):
        sql_stmt = "SELECT * FROM `Products`"
        pysql.run(sql_stmt)
        return pysql.result

    @staticmethod
    def __get_product_id_from_name(pysql, name):
        sql_stmt = "SELECT `ProductID` FROM `Products` WHERE `Name` = %s"
        pysql.run(sql_stmt, (name,))
        return [row[0] for row in pysql.result] if pysql.result else []

    # ---------- PUBLIC WRAPPERS ----------

    @staticmethod
    def add_product(pysql, product_id, name, description, unit_price, size, color, discount=None):
        return pysql.run_transaction(
            ProductManager.__add_product, product_id, name, description, unit_price, size, color, discount
        )

    @staticmethod
    def update_product_discount(pysql, product_id, discount):
        return pysql.run_transaction(ProductManager.__update_product_discount, product_id, discount)

    @staticmethod
    def update_product_price(pysql, product_id, price):
        return pysql.run_transaction(ProductManager.__update_product_price, product_id, price)

    @staticmethod
    def update_product_description(pysql, product_id, description):
        return pysql.run_transaction(ProductManager.__update_product_description, product_id, description)

    @staticmethod
    def product_exists(pysql, product_id):
        return pysql.run_transaction(ProductManager.__product_exists, product_id, commit=False)

    @staticmethod
    def get_all_products(pysql):
        return pysql.run_transaction(ProductManager.__get_all_products, commit=False)

    @staticmethod
    def get_product_id_from_name(pysql, name):
        return pysql.run_transaction(ProductManager.__get_product_id_from_name, name, commit=False)
