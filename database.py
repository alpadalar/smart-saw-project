import sqlite3
import os


def create_table(db_path, columns):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_table_query = "CREATE TABLE IF NOT EXISTS imas_testere ({})".format(
        ", ".join(["{} {}".format(col, dtype) for col, dtype in columns.items()])
    )
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()


def insert_to_database(db_path, data, columns):
    create_table(db_path, columns)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    columns_str = ", ".join(columns.keys())
    placeholders = ", ".join(["?" for _ in columns])
    cursor.execute(f'INSERT INTO imas_testere ({columns_str}) VALUES ({placeholders})', data)
    conn.commit()
    conn.close()
