# py_src/main.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from py_src.app import app        # Import your Flask app
from CmsLib import *              # Import all CMS modules
import hashlib

# ============================================================
# Shree Laxmi Collection Initialization Script
# ============================================================

# Make sure MySQL schema is ready:
# > mysql -u root -p
# > source ./sql_src/cms_ddl.sql
# ============================================================

with app.app_context():

    # -----------------------------
    # Initialize PySql
    # -----------------------------
    yaml_path = os.path.join(os.path.dirname(__file__), "../CmsLib/db.yaml")
    pysql = PySql(app, yaml_path)
    # -----------------------------
    # 1. Add admin user
    # -----------------------------
    username = "laxmi"
    password = "laxmi123"
    
    # Hash the password
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    # Check if user already exists
    sql_check = "SELECT COUNT(*) FROM Users WHERE Username=%s"
    pysql.run(sql_check, (username,))
    exists = pysql.scalar_result

    if not exists:
         sql_insert = "INSERT INTO Users (Username, PasswordHash) VALUES (%s, %s)"
         pysql.run(sql_insert, (username, password_hash))
         print(f"User '{username}' added successfully.")    
    else:
        print(f"User '{username}' already exists.")
     

    # -----------------------------
    # 2. Add sample women's clothing products
    # -----------------------------
    products = [
        # ProductID, Name, Description, UnitPrice, Size, Color, CurrentDiscount
        ("KUR-001", "Women’s Designer Kurti", "Cotton blend with embroidery", 1800.00, "S", "Red", 0),
        ("KUR-002", "Women’s Designer Kurti", "Cotton blend with embroidery", 1800.00, "M", "Red", 0),
        ("SAR-003", "Silk Saree", "Pure Banarasi silk saree with golden border", 5200.00, "L", "Golden", 0),
        ("TOP-004", "Ladies Formal Top", "Office wear formal top (navy blue)", 1450.00, "M", "Blue", 0),
        ("SKT-005", "Long Skirt", "Printed chiffon long skirt", 1650.00, "L", "Pink", 0),
        ("DRS-006", "Party Dress", "Elegant evening gown", 3500.00, "S", "Black", 0),
    ]

    for pid, name, desc, price, size, color, discount in products:
        pid = pid.strip()
        ProductManager.add_product(pysql, pid, name, desc, price, size, color, discount=discount)

    # -----------------------------
    # 3. Initialize inventory
    # -----------------------------

    inventory_data = [
        ("KUR-001", "S", "Red", 50, 20, 10),
        ("KUR-002", "M", "Red", 40, 15, 10),
        ("SAR-003", "L", "Golden", 30, 10, 5),
        ("TOP-004", "M", "Blue", 60, 25, 10),
        ("SKT-005", "L", "Pink", 40, 20, 5),
        ("DRS-006", "S", "Black", 20, 10, 5),
    ]

    for pid, size, color, stored, displayed, threshold in inventory_data:
        # 1️⃣ Check if product exists
        sql_product_check = "SELECT COUNT(*) FROM Products WHERE ProductID=%s"
        pysql.run(sql_product_check, (pid,))
        product_exists = pysql.scalar_result

        if not product_exists:
           print(f"⚠️ Product {pid} does not exist in Products table. Skipping inventory insert.")
           continue  # Skip this inventory entry
        
        # Check if inventory row exists
        sql_check = "SELECT COUNT(*) FROM Inventory WHERE ProductID=%s AND Size=%s AND Color=%s"
        pysql.run(sql_check, (pid, size, color))
        exists = pysql.scalar_result
        if exists:
             # Update existing inventory
             sql_update = """
                UPDATE Inventory
                SET StoredQuantity = %s,
                  DisplayedQuantity = %s,
                  StoreThreshold = %s
             WHERE ProductID=%s AND Size=%s AND Color=%s
             """
             pysql.run(sql_update, (stored, displayed, threshold, pid, size, color))
        else:
            # Insert new inventory
            sql_insert = """
              INSERT INTO Inventory
             (ProductID, Size, Color, StoredQuantity, DisplayedQuantity, StoreThreshold)
             VALUES (%s,%s,%s,%s,%s,%s)
             """
            pysql.run(sql_insert, (pid, size, color, stored, displayed, threshold))


    # -----------------------------
    # 4. Generate tokens
    # -----------------------------
    # Remove old tokens
    pysql.run("DELETE FROM Tokens")
    
    token_ids = [("TOK-" + format(i, "02d"),) for i in range(20)]
    pysql.run_many("INSERT INTO Tokens (TokenID) VALUES (%s)", token_ids)

    tok1 = TokenManager.get_token(pysql)
    tok2 = TokenManager.get_token(pysql)
    print("Allocated Tokens:", tok1, tok2)

    # -----------------------------
    # 5. Add items to customer tokens
    # -----------------------------
    CounterManager.add_counter_to_token(pysql, tok1, "KUR-001", 1, "S", "Red")
    CounterManager.add_counter_to_token(pysql, tok1, "TOP-004", 2, "M", "Blue")
    CounterManager.add_counter_to_token(pysql, tok2, "SAR-003", 1, "L", "Golden")
    CounterManager.add_counter_to_token(pysql, tok2, "DRS-006", 1, "S", "Black")

    # -----------------------------
    # 6. Move inventory to counter
    # -----------------------------
    CounterManager.add_inventory_to_counter(pysql, "KUR-001", 20, "S", "Red")
    CounterManager.add_inventory_to_counter(pysql, "TOP-004", 30, "M", "Blue")

    # -----------------------------
    # 7. Place supplier orders
    # -----------------------------
    ord_id = OrderManager.place_order(pysql, [
        ("SAR-003", "L", "Golden", 40),
        ("DRS-006", "S", "Black", 30)
    ])
    print("Placed Supplier Order ID:", ord_id)

    # -----------------------------
    # 8. Generate combined invoice
    # -----------------------------
    inv_id = InvoiceManager.generate_invoice(pysql, [tok1, tok2], "cash")
    InvoiceManager.give_additional_discount(pysql, inv_id, 200)  # Rs. 200 discount
    print("Generated Invoice ID:", inv_id)

    # -----------------------------
    # 9. Return tokens to pool
    # -----------------------------
    TokenManager.return_token(pysql, tok1)
    TokenManager.return_token(pysql, tok2)

    # -----------------------------
    # 10. Receive supplier order
    # -----------------------------
    OrderManager.receive_order(pysql, ord_id)
    print("Supplier order received successfully and stock updated.")
    pysql.close()
    print("\n✅ Shree Laxmi Collection setup completed successfully!")

