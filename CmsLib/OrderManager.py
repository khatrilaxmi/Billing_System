# OrderManager.py
# -------------------------------------------------
# Shree Laxmi Collection – Final Production Version
# Handles Supplier Orders and Inventory Updates
# -------------------------------------------------

from decimal import Decimal
from CmsLib.InventoryManager import *
from CmsLib.ProductManager import *

# Auto-increment cache
next_order_id = None
next_order_id_read = False


class OrderManager:

    # ---------- PRIVATE METHODS ----------

    @staticmethod
    def __load_next_order_id(pysql):
        """Reads MAX OrderID and sets the next number."""
        global next_order_id, next_order_id_read

        pysql.run("SELECT OrderID FROM Orders ORDER BY OrderID DESC LIMIT 1")
        last_id = pysql.scalar_result

        if last_id:
            num = int(last_id.replace("ORD-", ""))
            next_order_id = num + 1
        else:
            next_order_id = 1  # First order

        next_order_id_read = True

    @staticmethod
    def __place_order(pysql, items):
        """
        items = [(ProductID, Size, Color, Quantity)]
        """

        global next_order_id, next_order_id_read

        # Load next order id if not read yet
        if not next_order_id_read:
            OrderManager.__load_next_order_id(pysql)

        # Merge duplicate items
        merged = {}
        for pid, size, color, qty in items:

            if not ProductManager._ProductManager__product_exists(pysql, pid, size, color):
                return 1 # Product does not exist

            qty = Decimal(qty)
            if qty <= 0:
                return 2 #Invalid quantity

            merged[(pid, size, color)] = merged.get((pid, size, color), Decimal(0)) + qty

        # Create final order id
        order_id = f"ORD-{next_order_id:010d}"

        # Insert into Orders
        pysql.run(
            "INSERT INTO Orders (OrderID, OrderDate, Delivered, Cancelled) "
            "VALUES (%s, CURRENT_TIMESTAMP, 0, 0)",
            (order_id,)
        )

        # Insert each product
        rows = [(order_id, pid, size, color, qty) for (pid, size, color), qty in merged.items()]
        pysql.run_many(
            "INSERT INTO OrdersOfProducts (OrderID, ProductID, Size, Color, Quantity) "
            "VALUES (%s, %s, %s, %s, %s)",
            rows
        )

        next_order_id += 1
        return (order_id)

    @staticmethod
    def __get_order_status(pysql, order_id):
        pysql.run("SELECT Delivered, Cancelled FROM Orders WHERE OrderID=%s", (order_id,))
        row = pysql.first_result
        if not row:
            return None
        d, c = row
        return (bool(d), bool(c))

    @staticmethod
    def __cancel_order(pysql, order_id):
        status = OrderManager.__get_order_status(pysql, order_id)
        if status is None:
            return 4
        delivered, cancelled = status
        if delivered:
            return 2
        if cancelled:
            return 3

        pysql.run("UPDATE Orders SET Cancelled=1 WHERE OrderID=%s", (order_id,))
        return 0

    @staticmethod
    def __receive_order(pysql, order_id):
        status = OrderManager.__get_order_status(pysql, order_id)
        if status is None:
            return 4
        delivered, cancelled = status
        
        if delivered:
            return 2
        if cancelled:
            return 3

        # Retrieve order products
        pysql.run(
            "SELECT ProductID, Size, Color, Quantity "
            "FROM OrdersOfProducts WHERE OrderID=%s",
            (order_id,)
        )
        rows = pysql.result or []

        for pid, size, color, qty in rows:

            qty = Decimal(qty)
            threshold = max(1, round(qty * Decimal("0.10")))

            pysql.run(
                "SELECT COUNT(*) FROM Inventory WHERE ProductID=%s AND Size=%s AND Color=%s",
                (pid, size, color)
            )
            exists = pysql.scalar_result

            if exists:
                pysql.run(
                    "UPDATE Inventory SET StoredQuantity = StoredQuantity + %s, "
                    "StoreThreshold = GREATEST(StoreThreshold, %s)"
                    "WHERE ProductID=%s AND Size=%s AND Color=%s",
                    (qty, threshold, pid, size, color)
                )
            else:
                pysql.run(
                    "INSERT INTO Inventory "
                    "(ProductID, Size, Color, StoredQuantity, DisplayedQuantity, StoreThreshold) "
                    "VALUES (%s, %s, %s, %s, 0, %s)",
                    (pid, size, color, qty, threshold)
                )

            InventoryManager._InventoryManager__log_transaction(
                pysql, "INVENTORY_ADD", pid, size, color, qty
            )

        pysql.run("UPDATE Orders SET Delivered=1 WHERE OrderID=%s", (order_id,))
        return 0

    @staticmethod
    def __get_orders(pysql):
        pysql.run("SELECT * FROM Orders ORDER BY OrderDate DESC")
        return pysql.result

    @staticmethod
    def __get_order_details(pysql, order_id):

        pysql.run("SELECT * FROM Orders WHERE OrderID=%s", (order_id,))
        header = pysql.first_result

        pysql.run(
            "SELECT O.ProductID, P.Name, O.Size, O.Color, O.Quantity, P.UnitType "
            "FROM OrdersOfProducts O "
            "JOIN Products P ON O.ProductID=P.ProductID "
            "AND O.Size=P.Size AND O.Color=P.Color "
            "WHERE O.OrderID=%s",
            (order_id,)
        )

        items = pysql.result
        return (header, items)

    # ---------- PUBLIC WRAPPERS ----------

    @staticmethod
    def place_order(pysql, items):
        return pysql.run_transaction(OrderManager.__place_order, items)

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
