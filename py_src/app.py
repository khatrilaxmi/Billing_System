# py_src/app.py

from flask import Flask, render_template, request, redirect, session, url_for
from functools import wraps
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
# Index Page
# =========================
@app.route("/")
@login_required
def index():
    return render_template("index.html")

# @app.route('/', methods=['GET', 'POST'])
#def index():
 #   return render_template('index.html')
 # Logout
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
               "OrdersBetweenDates", "TransactionLog", "ProductDateTransactionLog"]
    if request.method == 'POST':
        for option in options:
            if option in request.form:
                return redirect("/InventoryManager/" + option)
    return render_template('/InventoryManager/inventory_manager.html')


# Add Product
@app.route('/InventoryManager/AddProduct', methods=['GET', 'POST'])
def inventory_manager_add_product():
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
            return render_template('InventoryManager/inventory_manager_alert.html', result="Invalid price or discount")

        # Validate Product ID format
        if not re.match("^[A-Z]{3}-[0-9]{3}$", product_id):
            return render_template('InventoryManager/inventory_manager_alert.html', result="Invalid Product ID format")

        retval = ProductManager.add_product(
            pysql, product_id, name, description, unit_price, size, color, current_discount
        )

        if retval == 0:
            return render_template('InventoryManager/inventory_manager_success.html', result="Product added successfully")
        else:
            return render_template('InventoryManager/inventory_manager_failure.html', reason="Product ID or Name/Size/Color duplicate")
    else:
        return render_template('/InventoryManager/inventory_manager_add_product.html')


# View Products
@app.route('/InventoryManager/ViewProducts', methods=['GET', 'POST'])
def inventory_manager_view_products():
    products = ProductManager.get_all_products(pysql)
    if not products:
        return render_template('/InventoryManager/inventory_manager_alert.html', result="No products found")
    return render_template('/InventoryManager/inventory_manager_view_products.html', products=products)


# View Inventory
@app.route('/InventoryManager/ViewInventory', methods=['GET', 'POST'])
def inventory_manager_view_inventory():
    inventory = InventoryManager.get_inventory_details(pysql)
    if not inventory:
        return render_template('/InventoryManager/inventory_manager_alert.html', result="Inventory empty")
    return render_template('/InventoryManager/inventory_manager_view_inventory.html', inventory=inventory)


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
    token_id = TokenManager.get_token(pysql)
    if not token_id:
        return render_template('/TokenManager/token_manager_failure.html', reason="Token not available")
    return render_template('/TokenManager/token_manager_success.html', result=f"Token {token_id} assigned")


@app.route('/TokenManager/ReturnToken', methods=['GET', 'POST'])
def token_manager_return_token():
    if request.method == 'POST':
        token_id = request.form['TokenID']
        retval = TokenManager.return_token(pysql, token_id)
        if retval == 0:
            return render_template('/TokenManager/token_manager_success.html', result="Token returned successfully")
        return render_template('/TokenManager/token_manager_failure.html', reason="Cannot return token")
    return render_template('/TokenManager/token_manager_token_id_input.html')


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
            return render_template('/TokenManager/token_manager_success.html', result="Token removed successfully")
        return render_template('/TokenManager/token_manager_failure.html', reason="Cannot remove token")
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
    tokens = TokenManager.get_all_tokens_status(pysql)
    tokens = [t[0] for t in tokens] if tokens else []
    if request.method == 'POST':
        token_ids = request.form.getlist("Select[]")
        payment_mode = request.form['PaymentMode']
        retval = InvoiceManager.generate_invoice(pysql, token_ids, payment_mode)
        if retval not in [1, 2, 3]:
            return render_template('/BillDesk/bill_desk_success.html', result=f"Invoice {retval} generated successfully")
        return render_template('/BillDesk/bill_desk_failure.html', reason="Error generating invoice")
    return render_template('/BillDesk/bill_desk_generate_invoice.html', tokens=tokens)

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
