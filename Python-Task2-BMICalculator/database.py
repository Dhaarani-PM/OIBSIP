import sqlite3
from datetime import datetime
from pathlib import Path


DATABASE_FILE = Path(__file__).with_name("bmi_tracker.db")


def _connection():
    return sqlite3.connect(DATABASE_FILE)


def initialize_database():
    with _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bmi_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                height REAL NOT NULL,
                weight REAL NOT NULL,
                bmi REAL NOT NULL,
                category TEXT NOT NULL
            )
            """
        )


def save_bmi_record(name, age, gender, height, weight, bmi, category):
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO bmi_history
            (date, name, age, gender, height, weight, bmi, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp, name, age, gender, height, weight, bmi, category),
        )


def fetch_bmi_records(search_name=""):
    query = """
        SELECT id, date, name, age, gender, height, weight, bmi, category
        FROM bmi_history
    """
    parameters = ()
    if search_name.strip():
        query += " WHERE name LIKE ? COLLATE NOCASE"
        parameters = (f"%{search_name.strip()}%",)
    query += " ORDER BY id DESC"
    with _connection() as connection:
        return connection.execute(query, parameters).fetchall()


def delete_bmi_record(record_id):
    with _connection() as connection:
        connection.execute("DELETE FROM bmi_history WHERE id = ?", (record_id,))


def get_bmi_analytics():
    """Return summary metrics, category counts, and chronological trend data."""
    with _connection() as connection:
        records = connection.execute(
            "SELECT id, date, bmi, category FROM bmi_history ORDER BY id ASC"
        ).fetchall()

    category_counts = {
        "Underweight": 0,
        "Normal Weight": 0,
        "Overweight": 0,
        "Obese": 0,
    }
    bmi_values = []
    for _, _, bmi, category in records:
        bmi_values.append(float(bmi))
        if category in category_counts:
            category_counts[category] += 1

    total = len(records)
    return {
        "total_records": total,
        "average_bmi": round(sum(bmi_values) / total, 2) if total else 0,
        "lowest_bmi": min(bmi_values) if bmi_values else 0,
        "highest_bmi": max(bmi_values) if bmi_values else 0,
        "underweight": category_counts["Underweight"],
        "normal": category_counts["Normal Weight"],
        "overweight": category_counts["Overweight"],
        "obese": category_counts["Obese"],
        "category_counts": category_counts,
        "trend_records": records,
    }
