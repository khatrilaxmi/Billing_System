# CmsLib/InvoiceManager.py
from CmsLib.TokenManager import *
from decimal import Decimal, ROUND_HALF_UP
# Global invoice counters
next_invoice_id = None
next_invoice_id_read = 0

class InvoiceManager:

    # ------------------- GENERATE INVOICE -------------------
    @staticmethod
    def __generate_invoice(pysql, token_ids, payment_mode):
        global next_invoice_id, next_invoice_id_read

        # Initialize next_invoice_id
        if not next_invoice_id_read:
            sql_stmt = "SELECT COUNT(*) FROM Invoices"
            pysql.run(sql_stmt)
            next_invoice_id = pysql.scalar_result
            next_invoice_id_read = 1

        invoice_has_products = False
        invoice_total_with_vat= Decimal('0.00')
        total_discount_all_products = Decimal('0.00')

        # Validate tokens and calculate invoice total
        for token in token_ids:
            if not TokenManager._TokenManager__is_token_assigned(pysql, token):
                return 1  # Token not assigned

            token_has_products = TokenManager._TokenManager__token_has_products(pysql, token)

            invoice_has_products = invoice_has_products or token_has_products

        if not invoice_has_products:
            return 2  # No products to bill

        if payment_mode not in ["cash", "card", "wallet"]:
            return 3  # Invalid payment mode

        # Generate invoice ID
        invoice_id = "INV-" + format(next_invoice_id, "010d")

        # Fetch product details (with Size & Color)
        sql_stmt = """
            SELECT p.ProductID, p.Name, p.Size, p.Color,
                   SUM(tsp.Quantity) AS Quantity, p.UnitPrice, p.CurrentDiscount
            FROM TokensSelectProducts tsp
            JOIN Products p ON p.ProductID = tsp.ProductID
              AND p.Size = tsp.Size
              AND p.Color = tsp.Color
            WHERE tsp.TokenID IN %s
            GROUP BY p.ProductID, p.Name, p.Size, p.Color, p.UnitPrice, p.CurrentDiscount
        """
        pysql.run(sql_stmt, (tuple(token_ids),))
        invoice_details = pysql.result

        invoice_details_with_tax = []
        for row in invoice_details:
            product_id, name, size, color, quantity, unit_price, discount = row
           
            # Ensure all are Decimal
            quantity = Decimal(quantity)
            unit_price = Decimal(unit_price)
            discount = Decimal(discount)

            # Discount amount
            discount_amount = (quantity * unit_price * (discount / Decimal('100'))).quantize(Decimal('0.01'), rounding= ROUND_HALF_UP)

            # Price after discount
            price_after_discount = (quantity * unit_price - discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Calculate VAT 13%
            tax_amount = (price_after_discount * Decimal('0.13')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Add VAT to invoice total
            invoice_total_with_vat += price_after_discount + tax_amount

            total_discount_all_products += discount_amount
        
            # Append data with tax_amount
            invoice_details_with_tax.append((product_id, name, size, color, quantity, unit_price, tax_amount, discount
        ))
        
        # Create invoice record with VAT-inclusive total
        sql_stmt = """
            INSERT INTO Invoices(InvoiceID, InvoiceDate, InvoiceTotal, DiscountGiven, PaymentMode)
            VALUES (%s, CURRENT_TIMESTAMP, %s, %s, %s)
        """
        pysql.run(sql_stmt, (invoice_id, invoice_total_with_vat, total_discount_all_products, payment_mode))

        # Link tokens to invoice
        token_tuples = [(token,) for token in token_ids]
        sql_stmt = "UPDATE Tokens SET InvoiceID = %s, Assigned = FALSE WHERE TokenID = %s"
        pysql.run_many(sql_stmt, [(invoice_id, t[0]) for t in token_tuples])


        # Insert into ProductsInInvoices
        sql_stmt = """
            INSERT INTO ProductsInInvoices
            (InvoiceID, ProductID, Name, Size, Color,
             Quantity, UnitPrice, TaxAmount, Discount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        pysql.run_many(sql_stmt, [(invoice_id, *row) for row in invoice_details_with_tax])

        # Clear TokensSelectProducts
        sql_stmt = "DELETE FROM TokensSelectProducts WHERE TokenID = %s"
        pysql.run_many(sql_stmt, token_tuples)

        next_invoice_id += 1
        return invoice_id

    # ------------------- ADDITIONAL DISCOUNT -------------------
    @staticmethod
    def __give_additional_discount(pysql, invoice_id, discount):
        sql_stmt = "SELECT COUNT(*) FROM Invoices WHERE InvoiceID = %s"
        pysql.run(sql_stmt, (invoice_id,))
        if not pysql.scalar_result:
            return 1  # Invoice not found
        if discount < 0:
            return 2  # Invalid discount
        sql_stmt = "UPDATE Invoices SET DiscountGiven = %s WHERE InvoiceID = %s"
        pysql.run(sql_stmt, (discount, invoice_id))
        return 0

    # ------------------- GET INVOICE DETAILS -------------------
    @staticmethod
    def __get_invoice_details(pysql, invoice_id):
        sql_stmt = "SELECT * FROM Invoices WHERE InvoiceID = %s"
        pysql.run(sql_stmt, (invoice_id,))
        invoice_parameters = pysql.first_result

        sql_stmt = """
            SELECT ProductID, Name, Size, Color,
                   Quantity, UnitPrice, TaxAmount, Discount
            FROM ProductsInInvoices
            WHERE InvoiceID = %s
        """
        pysql.run(sql_stmt, (invoice_id,))
        invoice_details = pysql.result

        return invoice_parameters, invoice_details

    # ------------------- GET INVOICES BY DATE -------------------
    @staticmethod
    def __get_invoices_by_date(pysql, date):
        sql_stmt = """
            SELECT InvoiceID, TIME(InvoiceDate), InvoiceTotal, DiscountGiven, PaymentMode
            FROM Invoices
            WHERE DATE(InvoiceDate) = %s
        """
        pysql.run(sql_stmt, (date,))
        return pysql.result

    # ------------------- PUBLIC WRAPPERS -------------------
    @staticmethod
    def generate_invoice(pysql, token_ids, payment_mode):
        return pysql.run_transaction(InvoiceManager.__generate_invoice, token_ids, payment_mode)

    @staticmethod
    def give_additional_discount(pysql, invoice_id, discount):
        return pysql.run_transaction(InvoiceManager.__give_additional_discount, invoice_id, discount)

    @staticmethod
    def get_invoice_details(pysql, invoice_id):
        return pysql.run_transaction(InvoiceManager.__get_invoice_details, invoice_id, commit=False)

    @staticmethod
    def get_invoices_by_date(pysql, date):
        return pysql.run_transaction(InvoiceManager.__get_invoices_by_date, date, commit=False)
