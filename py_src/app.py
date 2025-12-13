# py_src/app.py

from flask import Flask, render_template, request, redirect, session, url_for
from functools import wraps
from datetime import datetime, timedelta
import sys
import re
import os
import hashlib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from CmsLib import *

app = Flask(__name__,
            template_folder='../html_src/',
            static_folder='../html_src/')
app.secret_key = "supersecretkey" #for session
# =========================
# Global Database Connection
# =========================
yaml_path = os.path.join(os.path.dirname(__file__), "../CmsLib/db.yaml")
pysql = PySql(app, yaml_path)

# Global variable for invoices
invoice_id_global = ""
# =========================
# Login Configuration
# =========================

# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        if not username or not password:
            error = "Please enter both username and password"
            return render_template("login/login.html", error=error)
        # Hash the entered password
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Query the database for this username
        sql = "SELECT PasswordHash FROM Users WHERE Username=%s"
        pysql.run(sql, (username,))
        db_hash = pysql.scalar_result

        if db_hash and db_hash == password_hash:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password"

    return render_template("login/login.html", error=error)
        

# Decorator to protect routes
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# =========================
# Register Page
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    success = None

    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        confirm = request.form.get("confirm").strip()

        # Validate fields
        if not username or not password or not confirm:
            error = "Please fill all fields"
            return render_template("login/register.html", error=error)

        if password != confirm:
            error = "Passwords do not match"
            return render_template("login/register.html", error=error)
        
        errors = [] #collect all errors
        if len(password) <8 or len(password) > 16:
            errors.append("Password length must be 8-16 characters.")
        
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")
        
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit.")

        if not re.search(r"[^A-Za-z0-9]", password):
            errors.append("Password must contain at least one special character.")

        if re.search(r"\s", password):
            errors.append("Password must not contain spaces.")

        if errors:
            return render_template("login/register.html", errors = errors)


        # Check existing username
        sql = "SELECT COUNT(*) FROM Users WHERE Username=%s"
        pysql.run(sql, (username,))
        exists = pysql.scalar_result

        if exists > 0:
            error = "Username already taken"
            return render_template("login/register.html", error=error)

        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Insert new user
        sql = "INSERT INTO Users (Username, PasswordHash) VALUES (%s, %s)"
        pysql.run(sql, (username, password_hash))
        pysql.commit()
        return render_template("login/register_success.html", message="Registration successful! You can now Login.")

    return render_template("login/register.html")


# =========================
# Index Page
# =========================
@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
@login_required
def index():
    username = session.get("username")  # get from session
    #notifications
    
    low_stock_notifications = InventoryManager.get_low_stock_notifications(pysql)
    low_stock_count = len(low_stock_notifications)
    
    sql= "SELECT COUNT(DISTINCT TokenID) FROM TokensSelectProducts"
    pysql.run(sql)
    token_assigned_products = pysql.scalar_result
    
    sql= """
           SELECT COUNT(*) 
          FROM Tokens t
          LEFT JOIN TokensSelectProducts tsp ON t.TokenID = tsp.TokenID
          WHERE t.Assigned = TRUE AND tsp.TokenID IS NULL
          """
    pysql.run(sql)
    empty_tokens=pysql.scalar_result
    
    #analytic card
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    last_7_days = today - timedelta(days=7)
    last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    #count invoices
    sql_today = "SELECT COUNT(*) FROM Invoices WHERE DATE(InvoiceDate) = %s"
    pysql.run(sql_today, (today,))
    sales_today=pysql.scalar_result
     
    sql_yesterday = "SELECT COUNT(*) FROM Invoices WHERE DATE(InvoiceDate) = %s"
    pysql.run(sql_yesterday, (yesterday,))
    sales_yesterday=pysql.scalar_result
    
    sql_last_7_days = "SELECT COUNT(*) FROM Invoices WHERE DATE(InvoiceDate) >= %s"
    pysql.run(sql_last_7_days, (last_7_days,))
    sales_last_7_days=pysql.scalar_result
    
    sql_last_month = "SELECT COUNT(*) FROM Invoices WHERE DATE(InvoiceDate) >= %s AND DATE(InvoiceDate) <= %s"
    pysql.run(sql_last_month, (last_month, today))
    sales_last_month=pysql.scalar_result
    
    sales_data = [sales_today, sales_yesterday, sales_last_7_days, sales_last_month]
    print(sales_data)
    
    #Card Values
    sql= "SELECT COUNT(*) FROM Products"
    pysql.run(sql)
    total_products = pysql.scalar_result
    
    sql="SELECT COUNT(*) FROM Invoices"
    pysql.run(sql)
    total_invoices = pysql.scalar_result
    
    sql= "SELECT COUNT(*) FROM Orders WHERE Delivered = FALSE AND Cancelled = FALSE"
    pysql.run(sql)
    total_placed = pysql.scalar_result
    
    sql= "SELECT COUNT(*) FROM Orders WHERE Delivered = TRUE"
    pysql.run(sql)
    total_received = pysql.scalar_result
    
    sql= "SELECT COUNT(*) FROM Orders WHERE Cancelled = TRUE"
    pysql.run(sql)
    total_cancelled = pysql.scalar_result
    
    sql= "SELECT COUNT(*) FROM TokensSelectProducts"
    pysql.run(sql)
    total_assigned_products = pysql.scalar_result
    
    
    
    
    return render_template("index.html", 
                           username=username,
                           low_stock_count=low_stock_count,
                           token_assigned_products=token_assigned_products,
                           empty_tokens=empty_tokens,
                           total_products=total_products,
                           total_invoices=total_invoices,
                           total_placed=total_placed,
                           total_received=total_received,
                           total_cancelled=total_cancelled,
                           total_assigned_products=total_assigned_products,
                           sales_data=sales_data
                           )

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))




# =========================
# Inventory Manager
# =========================
@app.route('/InventoryManager', methods=['GET', 'POST'])
@login_required
def inventory_manager():
    options = ["AddProduct", "PlaceOrder", "ReceiveOrder", "CancelOrder",
               "ViewInventory", "ViewProducts", "OrderDetails",
               "OrdersBetweenDates", "TransactionLog", "ProductDateTransactionLog","EditProduct"]
    if request.method == 'POST':
        for option in options:
            if option in request.form:
                return redirect("/InventoryManager/" + option)
    return render_template('/InventoryManager/inventory_manager.html')


# Add Product
@app.route('/InventoryManager/AddProduct', methods=['GET', 'POST'])
def inventory_manager_add_product():
    parent_url = request.args.get('parent', '/InventoryManager')
    if request.method == 'POST':
        product_id = request.form['ProductID'].strip()
        name = request.form['Name'].strip()
        size = request.form['Size'].strip()
        color = request.form['Color'].strip()
        description = request.form['Description'].strip()
        unit_type = "pcs"
        try:
            unit_price = float(request.form['UnitPrice'].strip())
            current_discount = float(request.form['Discount'].strip())
        except:
            return render_template('InventoryManager/inventory_manager_alert.html', result="Invalid price or discount", next_url=parent_url)

        # Validate Product ID format
        if not re.match("^[A-Z]{3}-[0-9]{3}$", product_id):
            return render_template('InventoryManager/inventory_manager_alert.html', result="Invalid Product ID format", next_url=parent_url)

        retval = ProductManager.add_product(
            pysql, product_id, name, description, unit_price, size, color, current_discount
        )

        if retval == 0:
            return render_template('InventoryManager/inventory_manager_success.html', result="Product added successfully", next_url=parent_url)
        elif retval == 4:
            return render_template('InventoryManager/inventory_manager_failure.html', reason="Product not allowed", next_url=parent_url)
        elif retval == 1:
            return render_template('InventoryManager/inventory_manager_failure.html', reason="Product ID or Name/Size/Color duplicate", next_url=parent_url)
        elif retval == 2:
            return render_template('InventoryManager/inventory_manager_failure.html', reason="Invalid UnitPrice", next_url=parent_url)
        elif retval == 3:
            return render_template('InventoryManager/inventory_manager_failure.html', reason="Invalid discount", next_url=parent_url)
    else:
        return render_template('/InventoryManager/inventory_manager_add_product.html', next_url=parent_url )


# View Products
@app.route('/InventoryManager/ViewProducts', methods=['GET', 'POST'])
def inventory_manager_view_products():
    parent_url = request.args.get('parent', '/InventoryManager')
    products = ProductManager.get_all_products(pysql)
    if not products:
        return render_template('/InventoryManager/inventory_manager_alert.html', result="No products found", next_url=parent_url)
    return render_template('/InventoryManager/inventory_manager_view_products.html', products=products, next_url=parent_url)


# View Inventory
@app.route('/InventoryManager/ViewInventory', methods=['GET', 'POST'])
def inventory_manager_view_inventory():
    next_url = request.args.get('parent', '/InventoryManager')
    inventory = InventoryManager.get_inventory_details(pysql)
    if not inventory:
        return render_template('/InventoryManager/inventory_manager_alert.html', result="Inventory empty", next_url=next_url)
    return render_template('/InventoryManager/inventory_manager_view_inventory.html', inventory=inventory, Title="Inventory Details", next_url=next_url)


@app.route('/InventoryManager/PlaceOrder', methods=['GET', 'POST'])
@login_required
def place_order():
    if request.method == 'POST':
        # Example: expecting products and quantities from form
        # Replace this with your actual form fields
        total_rows = int(request.form.get("TotalRows", 0))
        products_quantities = []

        for i in range(total_rows):
            pid = request.form.get(f"ProductID_{i}".strip())
            size = request.form.get(f"Size_{i}".strip())
            color = request.form.get(f"Color_{i}".strip())
            qty = request.form.get(f"Quantity_{i}".strip())

            if qty and qty.isdigit() and int(qty) > 0:
                products_quantities.append((pid, size, color, qty))

        # Call OrderManager
        order_id = OrderManager.place_order(pysql, products_quantities)
        if order_id == 1:
            return render_template('/InventoryManager/inventory_manager_failure.html', reason="One or more products not found" )
        elif order_id == 2:
            return render_template('/InventoryManager/inventory_manager_failure.html', reason="Invalid Quantity" )
        else:
            return render_template('/InventoryManager/inventory_manager_success.html', result =f"Order ID: {order_id} placed successfully!")
    pysql.run("SELECT ProductID, Name, Size, Color FROM Products")
    products = pysql.result
    print(products)

    # Render Place Order form
    return render_template('/InventoryManager/inventory_manager_place_order.html', products = products)
    



@app.route('/InventoryManager/ReceiveOrder', methods=['GET', 'POST'])
@login_required
def receive_order():
    if request.method == 'POST':
        order_id = request.form.get("OrderID", "").strip()

        if not order_id:
            return render_template(
                '/InventoryManager/inventory_manager_failure.html',
                reason="Order ID is required"
            )

        result = OrderManager.receive_order(pysql, order_id)

        if result == 0:
            return render_template(
                '/InventoryManager/inventory_manager_success.html',
                result=f"Order ID: {order_id} received successfully and inventory updated!"
            )
        elif result == 2:
            return render_template(
                '/InventoryManager/inventory_manager_failure.html',
                reason=f"Order ID: {order_id} has already been delivered!"
            )
        elif result == 3:
            return render_template(
                '/InventoryManager/inventory_manager_failure.html',
                reason=f"Order ID: {order_id} has been cancelled!"
            )
        elif result == 4:
            return render_template(
                '/InventoryManager/inventory_manager_failure.html',
                reason=f"Order ID: {order_id} does not exist"
            )
        else:
            return render_template(
                '/InventoryManager/inventory_manager_failure.html',
                reason=f"Unknown error while receiving order {order_id}"
            )

    # GET method – show a form to enter OrderID
    return render_template('/InventoryManager/inventory_manager_receive_order.html')

@app.route('/InventoryManager/OrderDetails', methods=['GET', 'POST'])
@login_required
def order_details():
    if request.method == 'POST':
        order_id = request.form.get("OrderID", "").strip()

        if not order_id:
            return render_template(
                '/InventoryManager/inventory_manager_failure.html',
                reason="Order ID is required"
            )

        result = OrderManager.get_order_details(pysql, order_id)

        if not result or result[0] is None:
            return render_template(
                '/InventoryManager/inventory_manager_failure.html',
                reason=f"Order ID: {order_id} does not exist"
            )

        header, items = result
        return render_template(
            '/InventoryManager/inventory_manager_order_details_result.html',
            order_header=header,
            order_items=items
        )
    return render_template('/InventoryManager/inventory_manager_order_details.html')

#cancel order
@app.route('/InventoryManager/CancelOrder', methods=['GET', 'POST'])
@login_required
def cancel_order_route():
    if request.method == 'POST':
        order_id = request.form.get("OrderID", "").strip()

        if not order_id:
            return render_template(
                '/InventoryManager/inventory_manager_failure.html',
                reason="Order ID is required"
            )

        result = OrderManager.cancel_order(pysql, order_id)

        # Interpret the return codes
        if result == 0:
            message = f"Order ID: {order_id} cancelled successfully!"
            return render_template(
                '/InventoryManager/inventory_manager_success.html',
                result=message
            )
        elif result == 2:
            reason = "Order has already been delivered and cannot be cancelled."
        elif result == 3:
            reason = "Order is already cancelled."
        elif result == 4:
            reason = "Order ID not found."
        else:
            reason = "Unknown error occurred."

        return render_template(
            '/InventoryManager/inventory_manager_failure.html',
            reason=reason
        )

    # GET request → show a form to input OrderID
    return render_template('/InventoryManager/inventory_manager_cancel_order.html')

@app.route("/InventoryManager/EditProduct/<product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    next_url = request.args.get('parent', '/InventoryManager/ViewProducts')
    if request.method == "GET":
        sql = "SELECT * FROM Products WHERE ProductID=%s"
        pysql.run(sql, (product_id,))
        product = pysql.result[0]  # single row
        print(product)
        return render_template("InventoryManager/edit_product.html", product=product, next_url=next_url)

    # POST -> save updates
    name = request.form["name"].strip()
    description = request.form["description"].strip()
    price = float(request.form["price"])
    size = request.form["size"]
    color = request.form["color"]
    discount = float(request.form["discount"])

    sql = """
        UPDATE Products
        SET Name=%s, Description=%s, UnitPrice=%s, CurrentDiscount=%s
        WHERE ProductID=%s AND Size=%s AND Color=%s
    """
    pysql.run(sql, (name, description, price, discount, product_id, size, color))
    pysql.commit()

    return render_template('/InventoryManager/inventory_manager_success.html', result =f"Changes updated successfully!",  next_url=next_url)


#notifications
@app.route('/InventoryManager/LowStock', methods=['GET'])
@login_required
def inventory_manager_low_stock():
    next_url = request.args.get('parent', '/InventoryManager')
    # Get all inventory details
    inventory = InventoryManager.get_inventory_details(pysql)

    if not inventory:
        return render_template('/InventoryManager/inventory_manager_alert.html', result="Inventory empty", next_url=next_url)

    # Filter low stock products: stored quantity <= minimum threshold
    low_stock_inventory = [row for row in inventory if row[4] <= row[6]]  # row[4] = Stored Quantity, row[6] = Minimum Threshold

    if not low_stock_inventory:
        return render_template('/InventoryManager/inventory_manager_alert.html', result="No low stock products", next_url=next_url)

    return render_template('/InventoryManager/inventory_manager_view_inventory.html', inventory=low_stock_inventory,  Title="Low Stock Products", next_url=next_url)

@app.route("/TokenManager/PendingTokens", methods=["GET"])
@login_required
def pending_tokens_dashboard():
    sql_stmt = "SELECT DISTINCT `TokenID` FROM `TokensSelectProducts`"
    pysql.run(sql_stmt)
    pending_tokens = [row[0] for row in pysql.result]
    print("Pending Tokens:", pending_tokens)
    return render_template(
        "TokenManager/pending_tokens.html",
        pending_tokens=pending_tokens,
        Title="Pending Tokens"
    )
    
@app.route("/TokenManager/Empty", methods=["GET"])
@login_required
def empty_tokens_dashboard():
    sql_stmt = """
        SELECT t.TokenID
        FROM Tokens t
        LEFT JOIN TokensSelectProducts tsp ON t.TokenID = tsp.TokenID
        WHERE t.Assigned = TRUE AND tsp.TokenID IS NULL
    """
    pysql.run(sql_stmt)
    empty_tokens = [row[0] for row in pysql.result]
    print("Empty Tokens:", empty_tokens)
    return render_template(
        "TokenManager/pending_tokens.html",
        pending_tokens=empty_tokens,
        Title="Empty Tokens"
    )
    
#Stat-cards

@app.route("/BillDesk/InvoicesDetails")
@login_required
def invoices_details():

    # ---------------------------
    # 1. Get ALL rows
    # ---------------------------
    sql = """
        SELECT p.InvoiceID, p.ProductID, p.Name, p.Size, p.Color,
               p.Quantity, p.UnitPrice, i.InvoiceTotal
        FROM ProductsInInvoices p
        JOIN Invoices i on i.InvoiceID = p.InvoiceID
        ORDER BY p.InvoiceID DESC
        
    """
    pysql.run(sql)
    invoice_products = pysql.result 
    # list of rows
    return render_template(
        "BillDesk/invoice_details.html",
        invoice_products=invoice_products
    )

# Orders Placed
@app.route('/Inventory/OrderedPlaced')
@login_required
def inventory_orders_placed():
    sql_stmt = """
        SELECT op.OrderID, op.ProductID, op.Size, op.Color, op.Quantity
        FROM OrdersOfProducts op
        JOIN Orders o ON TRIM(op.OrderID) = TRIM(o.OrderID)
        WHERE o.Delivered = FALSE AND o.Cancelled = FALSE
        ORDER BY op.OrderID DESC
    """
    pysql.run(sql_stmt)
    items = pysql.result

    return render_template('InventoryManager/orders_of_products.html', items=items, Title="Pending Orders")


# Orders Received
@app.route('/Inventory/OrderedReceived')
@login_required
def inventory_orders_received():
    sql = """
        SELECT op.OrderID, op.ProductID, op.Size, op.Color, op.Quantity
        FROM OrdersOfProducts op
        JOIN Orders o ON TRIM(op.OrderID) = TRIM(o.OrderID)
        WHERE o.Delivered = TRUE
        ORDER BY op.OrderID DESC
    """
    pysql.run(sql)
    items = pysql.result
    return render_template('InventoryManager/orders_of_products.html', items=items, Title="Received Orders")


# Cancelled Orders
@app.route('/Inventory/OrderedCancel')
@login_required
def inventory_orders_cancel():
    sql = """
        SELECT op.OrderID, op.ProductID, op.Size, op.Color, op.Quantity
        FROM OrdersOfProducts op
        JOIN Orders o ON TRIM(op.OrderID) = TRIM(o.OrderID)
        WHERE o.Cancelled = TRUE
        ORDER BY op.OrderID DESC
    """
    pysql.run(sql)
    items = pysql.result
    return render_template('InventoryManager/orders_of_products.html', items=items, Title="Cancelled Orders")


@app.route("/TokenManager/AssignedProducts", methods=["GET"])
@login_required
def assigned_products_dashboard():
    sql_stmt = """
        SELECT TokenID, ProductID, Size, Color, Quantity
        FROM TokensSelectProducts
        ORDER BY TokenID
    """
    pysql.run(sql_stmt)
    assigned_products = pysql.result  # list of tuples
    print("Assigned Products:", assigned_products)

    return render_template(
        "TokenManager/token_assigned_products.html",
        assigned_products=assigned_products
    )



# =========================
# Token Manager
# =========================
@app.route('/TokenManager', methods=['GET', 'POST'])
@login_required
def token_manager():
    options = ["GetTokenStatuses", "GetToken", "ReturnToken", "GetTokenDetails", "AddToken", "RemoveToken"]
    if request.method == 'POST':
        for option in options:
            if option in request.form:
                return redirect("/TokenManager/" + option)
    return render_template('/TokenManager/token_manager.html')


@app.route('/TokenManager/GetTokenStatuses', methods=['GET'])
def token_manager_statuses():
    statuses = TokenManager.get_all_tokens_status(pysql)
    if not statuses:
        return render_template('/TokenManager/token_manager_alert.html', result="No tokens found")
    return render_template('/TokenManager/token_manager_token_statuses.html', statuses=statuses)


@app.route('/TokenManager/GetToken', methods=['GET'])
def token_manager_get_token():
    next_url = request.args.get('parent', '/TokenManager')
    token_id = TokenManager.get_token(pysql)
    if not token_id:
        return render_template('/TokenManager/token_manager_failure.html', reason="Token not available", next_url=next_url)
    return render_template('/TokenManager/token_manager_success.html', result=f"Token {token_id} assigned", next_url=next_url)


@app.route('/TokenManager/ReturnToken', methods=['GET', 'POST'])
def token_manager_return_token():
    if request.method == 'POST':
        token_id = request.form['TokenID']
        retval = TokenManager.return_token(pysql, token_id)
        if retval == 0:
            return render_template('/TokenManager/token_manager_success.html', result="Token returned successfully")
        elif retval == 1:
            return render_template('/TokenManager/token_manager_failure.html', reason="Token has product")
        elif retval == 2:
            return render_template('/TokenManager/token_manager_failure.html', reason="Token not assigned")
        elif retval == 3:
            return render_template('/TokenManager/token_manager_failure.html', reason="Token does not exist")
        
        return render_template('/TokenManager/token_manager_failure.html', reason="Cannot return token")
    return render_template('/TokenManager/token_manager_token_id_input.html')


@app.route('/TokenManager/GetTokenDetails', methods=['GET', 'POST'])
def token_manager_details():
    if request.method == 'POST':
        token_id = request.form['TokenID']
        details = TokenManager.get_token_details(pysql, token_id)
        if not details:  
                return render_template('/TokenManager/token_manager_alert.html', result="No token details found")
        return render_template('/TokenManager/token_manager_get_token_details.html', details=details, token_id=token_id, Title="Token Details")
    return render_template('TokenManager/token_manager_token_id_input.html')


@app.route('/TokenManager/AddToken', methods=['GET'])
def token_manager_add_token():
    token_id = TokenManager.add_token(pysql)
    if token_id == 1:
        return render_template('/TokenManager/token_manager_failure.html', reason="Cannot add token")
    return render_template('/TokenManager/token_manager_success.html', result=f"Token {token_id} added successfully")


@app.route('/TokenManager/RemoveToken', methods=['GET', 'POST'])
def token_manager_remove_token():
    if request.method == 'POST':
        token_id = request.form['TokenID']
        retval = TokenManager.remove_token(pysql, token_id)
        if retval == 0:
            return render_template('/TokenManager/token_manager_success.html', result="Token removed successfully!")
        elif retval == 1:
            return render_template('/TokenManager/token_manager_failure.html', reason="Token has product!")
        elif retval == 2:
            return render_template('/TokenManager/token_manager_failure.html', reason="Token is assigned!")
        elif retval == 3:
            return render_template('/TokenManager/token_manager_failure.html', reason="Token does not exist!")
        
        return render_template('/TokenManager/token_manager_failure.html', reason="Cannot remove token!")
    return render_template('/TokenManager/token_manager_token_id_input.html')


# =========================
# Counter Operator
# =========================
@app.route('/CounterOperator', methods=['GET', 'POST'])
@login_required
def counter_operator():
    options = ["AddProductsToToken", "AddInventoryToCounter", "AddTokenToCounter"]
    if request.method == 'POST':
        for option in options:
            if option in request.form:
                return redirect("/CounterOperator/" + option)
    return render_template('/CounterOperator/counter_operator.html')


# Add products from counter to token (with size/color)
@app.route('/CounterOperator/AddProductsToToken', methods=['GET', 'POST'])
def counter_add_products_to_token():
    if request.method == 'POST':
        token_id = request.form['TokenID'].strip()
        product_id = request.form['ProductID'].strip()
        size = request.form['Size'].strip()
        color = request.form['Color'].strip()
        try:
            quantity = float(request.form['Quantity'].strip())
        except:
            return render_template('/CounterOperator/counter_operator_alert.html', result="Invalid quantity")
        retval = CounterManager.add_counter_to_token(pysql, token_id, product_id, quantity, size, color)
        if retval == 0:
            return render_template('/CounterOperator/counter_operator_success.html', result="Products added successfully")
        elif retval == 1:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Token not aasigned")
        elif retval == 2:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Invalid Quantity")
        elif retval == 3:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Product not found")
        elif retval == 4:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Insufficient Quantity")
        elif retval == 5:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Product not allowed")
        
        return render_template('/CounterOperator/counter_operator_failure.html', reason="Error adding products")
    return render_template('/CounterOperator/counter_operator_add_products_to_token.html')


# Add products from inventory to counter (with size/color)
@app.route('/CounterOperator/AddInventoryToCounter', methods=['GET', 'POST'])
def counter_add_inventory_to_counter():
    if request.method == 'POST':
        product_id = request.form['ProductID'].strip()
        size = request.form['Size'].strip()
        color = request.form['Color'].strip()
        try:
            quantity = float(request.form['Quantity'].strip())
        except:
            return render_template('/CounterOperator/counter_operator_alert.html', result="Invalid quantity")
        
        retval = CounterManager.add_inventory_to_counter(pysql, product_id, quantity, size, color)
        if retval == 0:
            return render_template('/CounterOperator/counter_operator_success.html', result="Products transferred successfully")
        elif retval == 2:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Invalid quantity")
        elif retval == 3:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Product not found")
        elif retval == 4:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Insufficient Quantity")
        
        return render_template('/CounterOperator/counter_operator_failure.html', reason="Error transferring products")
    return render_template('/CounterOperator/counter_operator_add_inventory_to_counter.html')


# Add products from token to counter (return from customer)
@app.route('/CounterOperator/AddTokenToCounter', methods=['GET', 'POST'])
def counter_add_token_to_counter():
    if request.method == 'POST':
        token_id = request.form['TokenID'].strip()
        product_id = request.form['ProductID'].strip()
        size = request.form['Size'].strip()
        color = request.form['Color'].strip()
        retval = CounterManager.add_token_to_counter(pysql, token_id, product_id, size, color)
        if retval == 0:
            return render_template('/CounterOperator/counter_operator_success.html', result="Product returned successfully")
        elif retval == 3:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Product not found")
        elif retval == 5:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Product not allowed")
        elif retval == 6:
            return render_template('/CounterOperator/counter_operator_failure.html', reason="Product not found in token")
    
        return render_template('/CounterOperator/counter_operator_failure.html', reason="Error returning product")
    return render_template('/CounterOperator/counter_operator_add_token_to_counter.html')


# =========================
# Bill Desk
# =========================
@app.route('/BillDesk', methods=['GET', 'POST'])
@login_required
def bill_desk():
    options = ["GenerateInvoice", "AdditionalDiscount", "ViewInvoice", "DateWiseInvoice"]
    if request.method == 'POST':
        for option in options:
            if option in request.form:
                return redirect("/BillDesk/" + option)
    return render_template('/BillDesk/bill_desk.html')


# Generate Invoice (handles size/color)
@app.route('/BillDesk/GenerateInvoice', methods=['GET', 'POST'])
def generate_invoice():
    next_url = request.args.get('parent', '/BillDesk')
    tokens = TokenManager.get_all_tokens_status(pysql)
    tokens = [t[0] for t in tokens] if tokens else []
    if request.method == 'POST':
        token_ids = request.form.getlist("Select[]")
        payment_mode = request.form['PaymentMode']
        if not token_ids or not payment_mode:
            return render_template('/BillDesk/bill_desk_failure.html', reason="Select tokens and payment mode", next_url=next_url)
        retval = InvoiceManager.generate_invoice(pysql, token_ids, payment_mode)
        if retval not in [1, 2, 3]:
            return render_template('/BillDesk/bill_desk_success.html', result=f"Invoice {retval} generated successfully", next_url=next_url)
        return render_template('/BillDesk/bill_desk_failure.html', reason="Error generating invoice", next_url=next_url)
    return render_template('/BillDesk/bill_desk_generate_invoice.html', tokens=tokens, next_url=next_url)

# View Invoice Details
@app.route('/BillDesk/ViewInvoice', methods=['GET', 'POST'])
@login_required
def view_invoice():
    if request.method == 'POST':
        invoice_id = request.form['InvoiceID'].strip()

        # Get invoice header and product details from InvoiceManager
        invoice_header, invoice_products = InvoiceManager.get_invoice_details(pysql, invoice_id)

        if not invoice_header:
            return render_template('/BillDesk/bill_desk_failure.html', reason=f"Invoice {invoice_id} not found")

        return render_template(
            '/BillDesk/bill_desk_view_invoice_details_result.html',
            invoice_products = invoice_products,
            invoice_header = invoice_header
        )

    # GET request: show input form
    return render_template('/BillDesk/bill_desk_view_invoice_details.html')

@app.route('/BillDesk/PrintInvoiceCopy', methods=['GET'])
@login_required
def print_invoice_copy():
    # Get invoice ID from query string
    invoice_id = request.args.get('InvoiceID')
    if not invoice_id:
        return render_template('/BillDesk/bill_desk_failure.html', reason=f"InvoiceID required")

    # Fetch invoice header and products
    invoice_header, invoice_products = InvoiceManager.get_invoice_details(pysql, invoice_id)

    if not invoice_header or not invoice_products:
        return render_template('/BillDesk/bill_desk_failure.html', reason=f"Invoice {invoice_id} not found")

    # Render the printable invoice template
    return render_template(
        '/BillDesk/bill_desk_print_invoice.html',
        invoice_header=invoice_header,
        invoice_products=invoice_products
    )



if __name__ == "__main__":
    app.run(debug=True)
