
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
import bcrypt
import getpass

app = FastAPI(title="Expenzo API")


# =========================
# MYSQL CONNECTION
# =========================

MYSQL_PASSWORD = getpass.getpass("Enter MySQL password: ")


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=MYSQL_PASSWORD,
        database="expense_analytics"
    )


# =========================
# REQUEST MODELS
# =========================

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ExpenseRequest(BaseModel):
    user_id: int
    category_id: int
    payment_method_id: int
    amount: float
    expense_date: str
    description: str | None = None


# =========================
# HOME
# =========================

@app.get("/")
def home():
    return {
        "message": "Expenzo API is running!"
    }


# =========================
# REGISTER
# =========================

@app.post("/register")
def register(user: RegisterRequest):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE email = %s
            """,
            (user.email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        password_hash = bcrypt.hashpw(
            user.password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO users
            (full_name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (
                user.full_name,
                user.email,
                password_hash
            )
        )

        connection.commit()

        return {
            "message": "Account created successfully"
        }

    finally:
        cursor.close()
        connection.close()


# =========================
# LOGIN
# =========================

@app.post("/login")
def login(user: LoginRequest):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                user_id,
                full_name,
                email,
                password_hash
            FROM users
            WHERE email = %s
            """,
            (user.email,)
        )

        existing_user = cursor.fetchone()

        if not existing_user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        password_correct = bcrypt.checkpw(
            user.password.encode("utf-8"),
            existing_user["password_hash"].encode("utf-8")
        )

        if not password_correct:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        return {
            "message": "Login successful",
            "user_id": existing_user["user_id"],
            "full_name": existing_user["full_name"],
            "email": existing_user["email"]
        }

    finally:
        cursor.close()
        connection.close()


# =========================
# ADD EXPENSE
# =========================

@app.post("/expenses")
def add_expense(expense: ExpenseRequest):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO expenses
            (
                user_id,
                category_id,
                payment_method_id,
                amount,
                expense_date,
                description
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                expense.user_id,
                expense.category_id,
                expense.payment_method_id,
                expense.amount,
                expense.expense_date,
                expense.description
            )
        )

        connection.commit()

        return {
            "message": "Expense added successfully",
            "expense_id": cursor.lastrowid
        }

    except mysql.connector.Error as error:

        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {error}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# GET USER EXPENSES
# =========================

@app.get("/expenses/{user_id}")
def get_expenses(user_id: int):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                expense_id,
                user_id,
                category_id,
                payment_method_id,
                amount,
                expense_date,
                description,
                created_at
            FROM expenses
            WHERE user_id = %s
            ORDER BY expense_date DESC
            """,
            (user_id,)
        )

        expenses = cursor.fetchall()

        return {
            "expenses": expenses
        }

    finally:
        cursor.close()
        connection.close()


# =========================
# TOTAL EXPENSES
# =========================

@app.get("/expenses/{user_id}/total")
def get_total_expenses(user_id: int):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS total_expenses
            FROM expenses
            WHERE user_id = %s
            """,
            (user_id,)
        )

        result = cursor.fetchone()

        return {
            "user_id": user_id,
            "total_expenses": float(result["total_expenses"])
        }

    finally:
        cursor.close()
        connection.close()


# =========================
# UPDATE / EDIT EXPENSE
# =========================

@app.put("/expenses/{expense_id}")
def update_expense(
    expense_id: int,
    expense: ExpenseRequest
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            UPDATE expenses
            SET
                category_id = %s,
                payment_method_id = %s,
                amount = %s,
                expense_date = %s,
                description = %s
            WHERE expense_id = %s
              AND user_id = %s
            """,
            (
                expense.category_id,
                expense.payment_method_id,
                expense.amount,
                expense.expense_date,
                expense.description,
                expense_id,
                expense.user_id
            )
        )

        if cursor.rowcount == 0:

            raise HTTPException(
                status_code=404,
                detail="Expense not found"
            )

        connection.commit()

        return {
            "message": "Expense updated successfully",
            "expense_id": expense_id
        }

    except mysql.connector.Error as error:

        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {error}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# DELETE EXPENSE
# =========================

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            DELETE FROM expenses
            WHERE expense_id = %s
            """,
            (expense_id,)
        )

        if cursor.rowcount == 0:

            raise HTTPException(
                status_code=404,
                detail="Expense not found"
            )

        connection.commit()

        return {
            "message": "Expense deleted successfully",
            "expense_id": expense_id
        }

    except mysql.connector.Error as error:

        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {error}"
        )

    finally:
        cursor.close()
        connection.close()

