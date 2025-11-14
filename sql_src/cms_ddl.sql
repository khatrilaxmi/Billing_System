    -- ============================================================
    -- Drop database if exists
    -- ============================================================
    DROP DATABASE IF EXISTS CMS;
    CREATE DATABASE CMS;
    USE CMS;

    -- ============================================================
    -- Drop tables if they exist
    -- ============================================================
    DROP TABLE IF EXISTS TokensSelectProducts;
    DROP TABLE IF EXISTS ProductsInInvoices;
    DROP TABLE IF EXISTS Tokens;
    DROP TABLE IF EXISTS Products;
    DROP TABLE IF EXISTS Invoices;
    DROP TABLE IF EXISTS Inventory;
    DROP TABLE IF EXISTS InventoryTransactions;
    DROP TABLE IF EXISTS Orders;
    DROP TABLE IF EXISTS OrdersOfProducts;

    -- ============================================================
    -- Products Table
    -- ============================================================
    CREATE TABLE IF NOT EXISTS Products (
        ProductID CHAR(7) NOT NULL,
        Name VARCHAR(64) NOT NULL,
        Description VARCHAR(128),
        UnitPrice NUMERIC(9,3) UNSIGNED,
        UnitType ENUM('pcs') DEFAULT 'pcs',
        Size ENUM('S','M','L','XL','XXL') NOT NULL,
        Color VARCHAR(32) NOT NULL,
        CurrentDiscount NUMERIC(4,2) UNSIGNED DEFAULT 0,
        CONSTRAINT Products_PK_FMT CHECK (ProductID REGEXP '^[A-Z]{3}-[0-9]{3}$'),
        CONSTRAINT Products_NAME_FMT UNIQUE (Name, Size, Color),
        CONSTRAINT Products_PK PRIMARY KEY (ProductID)
    );

    -- ============================================================
    -- Inventory Table
    -- ============================================================
    CREATE TABLE IF NOT EXISTS Inventory (
        ProductID CHAR(7),
        Size ENUM('S','M','L','XL','XXL') NOT NULL,
        Color VARCHAR(32) NOT NULL,
        StoredQuantity NUMERIC(9,3) UNSIGNED,
        DisplayedQuantity NUMERIC(9,3) UNSIGNED,
        StoreThreshold NUMERIC(9,3) UNSIGNED,
        CONSTRAINT Inventory_PK PRIMARY KEY (ProductID, Size, Color),
        CONSTRAINT Inventory_FK FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    );

    -- ============================================================
    -- Invoices Table
    -- ============================================================
    CREATE TABLE IF NOT EXISTS Invoices (
        InvoiceID CHAR(14),
        InvoiceDate DATETIME,
        InvoiceTotal NUMERIC(9,3) UNSIGNED,
        DiscountGiven NUMERIC(9,3) UNSIGNED DEFAULT 0,
        PaymentMode ENUM('cash','card','wallet'),
        CONSTRAINT Invoices_PK_FMT CHECK (InvoiceID REGEXP '^INV-[0-9]{10}$'),
        CONSTRAINT Invoices_PK PRIMARY KEY (InvoiceID)
    );

    -- ============================================================
    -- Tokens Table
    -- ============================================================
    CREATE TABLE IF NOT EXISTS Tokens (
        TokenID CHAR(6),
        Assigned BOOLEAN DEFAULT FALSE,
        InvoiceID CHAR(14) DEFAULT NULL,
        CONSTRAINT Tokens_PK_FMT CHECK (TokenID REGEXP '^TOK-[0-9]{2}$'),
        CONSTRAINT Tokens_PK PRIMARY KEY (TokenID),
        CONSTRAINT Tokens_FK FOREIGN KEY (InvoiceID) REFERENCES Invoices(InvoiceID)
    );

    -- ============================================================
    -- InventoryTransactions Table
    -- ============================================================
    CREATE TABLE IF NOT EXISTS InventoryTransactions (
        TransactionID CHAR(14),
        TransactionType ENUM ('COUNTER_SUB','COUNTER_ADD','INVENTORY_SUB','INVENTORY_ADD','INVENTORY_TO_COUNTER'),
        ProductID CHAR(7),
        Size ENUM('S','M','L','XL','XXL') NOT NULL,
        Color VARCHAR(32) NOT NULL,
        Quantity NUMERIC(9,3) UNSIGNED,
        Timestamp DATETIME,
        CONSTRAINT InventoryTransactions_PK_FMT CHECK (TransactionID REGEXP '^TRC-[0-9]{10}$'),
        CONSTRAINT InventoryTransactions_PK PRIMARY KEY (TransactionID),
        CONSTRAINT InventoryTransactions_FK FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    );

    -- ============================================================
    -- Orders Table
    -- ============================================================
    CREATE TABLE IF NOT EXISTS Orders (
        OrderID CHAR(14),
        OrderDate DATETIME,
        Delivered BOOLEAN DEFAULT FALSE,
        Cancelled BOOLEAN DEFAULT FALSE,
        CONSTRAINT Orders_PK_FMT CHECK (OrderID REGEXP '^ORD-[0-9]{10}$'),
        CONSTRAINT Orders_PK PRIMARY KEY (OrderID)
    );

    -- ============================================================
    -- OrdersOfProducts Table
    -- ============================================================
    CREATE TABLE IF NOT EXISTS OrdersOfProducts (
        OrderID CHAR(14),
        ProductID CHAR(7),
        Size ENUM('S','M','L','XL','XXL') NOT NULL,
        Color VARCHAR(32) NOT NULL,
        Quantity NUMERIC(9,3) UNSIGNED,
        CONSTRAINT OrdersOfProducts_PK PRIMARY KEY (OrderID, ProductID, Size, Color),
        CONSTRAINT OrdersOfProducts_FK1 FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
        CONSTRAINT OrdersOfProducts_FK2 FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    );

    -- ============================================================
    -- TokensSelectProducts Table
    -- ============================================================
    CREATE TABLE IF NOT EXISTS TokensSelectProducts (
        TokenID CHAR(6),
        ProductID CHAR(7),
        Size ENUM('S','M','L','XL','XXL') NOT NULL,
        Color VARCHAR(32) NOT NULL,
        Quantity NUMERIC(9,3) UNSIGNED,
        CONSTRAINT TokensSelectProducts_PK PRIMARY KEY (TokenID, ProductID, Size, Color),
        CONSTRAINT TokensSelectProducts_FK1 FOREIGN KEY (TokenID) REFERENCES Tokens(TokenID),
        CONSTRAINT TokensSelectProducts_FK2 FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    );

    -- ============================================================
    -- ProductsInInvoices Table
    -- ============================================================
    CREATE TABLE IF NOT EXISTS ProductsInInvoices (
        InvoiceID CHAR(14),
        ProductID CHAR(7),
        Name VARCHAR(64),
        Size ENUM('S','M','L','XL','XXL') NOT NULL,
        Color VARCHAR(32) NOT NULL,
        Quantity NUMERIC(9,3) UNSIGNED,
        UnitPrice NUMERIC(9,3) UNSIGNED,
        Discount NUMERIC(4,2) UNSIGNED,
        CONSTRAINT ProductsInInvoices_PK PRIMARY KEY (InvoiceID, ProductID, Size, Color),
        CONSTRAINT ProductsInInvoices_FK1 FOREIGN KEY (InvoiceID) REFERENCES Invoices(InvoiceID),
        CONSTRAINT ProductsInInvoices_FK2 FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    );
