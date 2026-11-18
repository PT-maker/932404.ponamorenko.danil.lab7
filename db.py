import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "employees.db")


@contextmanager
def get_connection():
    """Открывает соединение с БД, сохраняет изменения и всегда закрывает его."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row            # строки как словари: row["salary"]
    conn.execute("PRAGMA foreign_keys = ON")  # в SQLite внешние ключи включаются вручную
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Создаёт таблицы и заполняет их тестовыми данными, если БД пустая."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        # Название отдела хранится только здесь. В employees лежит лишь department_id.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name     TEXT NOT NULL,
                department_id INTEGER NOT NULL,
                salary        REAL NOT NULL CHECK (salary >= 0),
                FOREIGN KEY (department_id) REFERENCES departments(id)
            )
            """
        )
        if conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO departments (id, name) VALUES (?, ?)",
                [(1, "Разработка"), (2, "Тестирование"), (3, "Аналитика"),
                 (4, "Бухгалтерия"), (5, "Кадры")],
            )
            conn.executemany(
                "INSERT INTO employees (full_name, department_id, salary) VALUES (?, ?, ?)",
                [
                    ("Иванов Иван", 1, 150000),
                    ("Петрова Анна", 1, 175000),
                    ("Сидоров Павел", 2, 95000),
                    ("Кузнецова Мария", 2, 105000),
                    ("Смирнов Алексей", 3, 120000),
                    ("Орлова Елена", 4, 90000),
                    ("Волков Дмитрий", 4, 110000),
                    ("Морозова Ольга", 4, 85000),
                    ("Соколов Андрей", 5, 70000),
                    ("Лебедева Наталья", 5, 78000),
                ],
            )


# ---------- Отделы ----------

def get_departments():
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name FROM departments ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def department_exists(department_id):
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM departments WHERE id = ?", (department_id,)).fetchone()
        return row is not None


# ---------- Сотрудники: CRUD ----------

def get_employees(department_id=None):
    """READ (список). Фильтр по отделу и сортировка по зарплате по убыванию."""
    sql = "SELECT id, full_name, department_id, salary FROM employees"
    params = []
    if department_id is not None:
        sql += " WHERE department_id = ?"
        params.append(department_id)
    sql += " ORDER BY salary DESC, id"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_employee(employee_id):
    """READ (одна запись). Возвращает словарь или None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, full_name, department_id, salary FROM employees WHERE id = ?",
            (employee_id,),
        ).fetchone()
        return dict(row) if row else None


def create_employee(full_name, department_id, salary):
    """CREATE. Возвращает созданную запись."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO employees (full_name, department_id, salary) VALUES (?, ?, ?)",
            (full_name, department_id, salary),
        )
        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT id, full_name, department_id, salary FROM employees WHERE id = ?",
            (new_id,),
        ).fetchone()
        return dict(row)


def update_employee(employee_id, full_name, department_id, salary):
    """UPDATE. Возвращает обновлённую запись или None, если такого id нет."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE employees SET full_name = ?, department_id = ?, salary = ? WHERE id = ?",
            (full_name, department_id, salary, employee_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            "SELECT id, full_name, department_id, salary FROM employees WHERE id = ?",
            (employee_id,),
        ).fetchone()
        return dict(row)


def delete_employee(employee_id):
    """DELETE. Возвращает True, если запись была удалена."""
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        return cur.rowcount > 0