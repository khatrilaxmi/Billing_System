# OrderManager.py
# -------------------------------------------------
# Fully updated for Shree Laxmi Collection
# Handles supplier orders, inventory updates, and order management
# Size comes before Color to match database schema
# -------------------------------------------------

from decimal import Decimal
from CmsLib.InventoryManager import *
from CmsLib.ProductManager import *

# Global variables for OrderID management
next_order_id = None
next_order_id_read = 0

class OrderManager:

    # ---------- PRIVATE METHODS ----------

    @staticmethod
    def __place_order(pysql, products_quantities):
        """
        Place a supplier order.
        products_quantities: list of tuples (ProductID, Size, Color, Quantity)
        """
        global next_order_id, next_order_id_read

        if not next_order_id_read:
            pysql.run("SELECT COUNT(*) FROM Orders")
            next_order_id = pysql.scalar_result
            next_order_id_read = 1

        # Validate products
        for product_id, size, color, quantity in products_quantities:
            if not ProductManager._ProductManager__product_exists(pysql, product_id):
                return 1  # Product not found
            if quantity <= 0:
                return 2  # Invalid quantity

        # Create order ID
        order_id = "ORD-" + format(next_order_id, "010d")

        # Insert order
        pysql.run(
            "INSERT INTO Orders (OrderID, OrderDate) VALUES (%s, (SELECT CURRENT_TIMESTAMP))",
            (order_id,)
        )

        # Insert order products
        pysql.run_many(
            "INSERT INTO OrdersOfProducts (OrderID, ProductID, Size, Color, Quantity) VALUES (%s,%s,%s,%s,%s)",
            [(order_id, pid, sz, col, qty) for pid, sz, col, qty in products_quantities]
        )

        next_order_id += 1
        return order_id

    @staticmethod
    def __get_order_status(pysql, order_id):
        pysql.run("SELECT Delivered, Cancelled FROM Orders WHERE OrderID = %s", (order_id,))
        status = pysql.first_result
        if not status:
            return (1, 1)  # Order not found
        return status

    @staticmethod
    def __cancel_order(pysql, order_id):
        delivered, cancelled = OrderManager._OrderManager__get_order_status(pysql, order_id)
        if delivered and cancelled:
            return 1  # Already delivered & cancelled (invalid)
        if delivered:
            return 2  # Already delivered
        if cancelled:
            return 3  # Already cancelled

        pysql.run("UPDATE Orders SET Delivered = 0, Cancelled = 1 WHERE OrderID = %s", (order_id,))
        return 0

    @staticmethod
    def __receive_order(pysql, order_id):
        delivered, cancelled = OrderManager._OrderManager__get_order_status(pysql, order_id)
        if delivered and cancelled:
            return 1
        if delivered:
            return 2
        if cancelled:
            return 3

        # Fetch products
        pysql.run(
            "SELECT ProductID, Size, Color, Quantity FROM OrdersOfProducts WHERE OrderID = %s",
            (order_id,)
        )
        products_list = pysql.result

        for product_id, size, color, quantity in products_list:
            # Check if inventory row exists
            pysql.run(
                "SELECT COUNT(*) FROM Inventory WHERE ProductID=%s AND Size=%s AND Color=%s",
                (product_id, size, color)
            )
            exists = pysql.scalar_result

            if exists:
                # Update stored quantity
                pysql.run(
                    "UPDATE Inventory SET StoredQuantity = StoredQuantity + %s WHERE ProductID=%s AND Size=%s AND Color=%s",
                    (quantity, product_id, size, color)
                )
            else:
                # Insert new inventory row
                pysql.run(
                    "INSERT INTO Inventory (ProductID, Size, Color, StoredQuantity, DisplayedQuantity, StoreThreshold) VALUES (%s,%s,%s,%s,%s,%s)",
                    (product_id, size, color, quantity, 0, quantity * Decimal("0.1"))
                )

            # Log transaction
            InventoryManager._InventoryManager__log_transaction(pysql, "INVENTORY_ADD", product_id, size, color, quantity)

        # Mark order as delivered
        pysql.run("UPDATE Orders SET Delivered = 1 WHERE OrderID = %s", (order_id,))
        return 0

    @staticmethod
    def __get_orders(pysql):
        pysql.run("SELECT * FROM Orders")
        return pysql.result

    @staticmethod
    def __get_order_details(pysql, order_id):
        pysql.run("SELECT * FROM Orders WHERE OrderID = %s", (order_id,))
        order_status = pysql.first_result

        pysql.run(
            "SELECT OrdersOfProducts.ProductID, Products.Name, OrdersOfProducts.Size, OrdersOfProducts.Color, OrdersOfProducts.Quantity, Products.UnitType "
            "FROM OrdersOfProducts JOIN Products USING (ProductID) "
            "WHERE OrderID = %s",
            (order_id,)
        )
        order_details = pysql.result
        return order_status, order_details

    @staticmethod
    def __get_orders_between_date(pysql, start_date, end_date):
        pysql.run(
            "SELECT * FROM Orders WHERE DATE(OrderDate) BETWEEN %s AND %s",
            (start_date, end_date)
        )
        return pysql.result

    # ---------- PUBLIC WRAPPERS ----------

    @staticmethod
    def place_order(pysql, products_quantities):
        return pysql.run_transaction(OrderManager.__place_order, products_quantities)

    @staticmethod
    def get_order_status(pysql, order_id):
        return pysql.run_transaction(OrderManager.__get_order_status, order_id, commit=False)

    @staticmethod
    def cancel_order(pysql, order_id):
        return pysql.run_transaction(OrderManager.__cancel_order, order_id)

    @staticmethod
    def receive_order(pysql, order_id):
        return pysql.run_transaction(OrderManager.__receive_order, order_id)

    @staticmethod
    def get_orders(pysql):
        return pysql.run_transaction(OrderManager.__get_orders, commit=False)

    @staticmethod
    def get_order_details(pysql, order_id):
        return pysql.run_transaction(OrderManager.__get_order_details, order_id, commit=False)

    @staticmethod
    def get_orders_between_date(pysql, start_date, end_date):
        return pysql.run_transaction(OrderManager.__get_orders_between_date, start_date, end_date, commit=False)
