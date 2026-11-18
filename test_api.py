import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
results = []


def call(method, path, body=None):
    """Отправляет запрос и возвращает (код ответа, JSON или None)."""
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as e:  # 4xx и 5xx тоже нормальный ответ для проверки
        status, raw = e.code, e.read()
    return status, (json.loads(raw) if raw else None)


def check(name, condition, info=""):
    results.append(bool(condition))
    line = ("OK   " if condition else "FAIL ") + name
    if not condition and info != "":
        line += f"   -> получено: {info}"
    print(line)


def finish():
    print(f"\nПройдено {sum(results)} из {len(results)}")
    sys.exit(0 if all(results) else 1)


try:
    status, all_emp = call("GET", "/api/employees")
except urllib.error.URLError:
    print("Сервер не отвечает. Запустите его в другом терминале: .venv\\Scripts\\python app.py")
    sys.exit(1)

print("--- Чтение ---")
check("GET /api/employees -> 200 и список", status == 200 and isinstance(all_emp, list), status)
start_count = len(all_emp)
salaries = [e["salary"] for e in all_emp]
check("сортировка по зарплате по убыванию", salaries == sorted(salaries, reverse=True))
check(
    "у сотрудника только id, full_name, department_id, salary (названия отдела нет)",
    all(set(e) == {"id", "full_name", "department_id", "salary"} for e in all_emp),
)

status, dep4 = call("GET", "/api/employees?department_id=4")
check("?department_id=4 -> только сотрудники отдела 4",
      status == 200 and len(dep4) > 0 and all(e["department_id"] == 4 for e in dep4), status)
sal4 = [e["salary"] for e in dep4] if isinstance(dep4, list) else []
check("... и тоже по убыванию зарплаты", sal4 == sorted(sal4, reverse=True))

status, _ = call("GET", "/api/employees?department_id=abc")
check("?department_id=abc -> 400", status == 400, status)

status, deps = call("GET", "/api/departments")
check("GET /api/departments -> 200 и список", status == 200 and isinstance(deps, list), status)

print("--- Создание и ошибки ---")
good = {"full_name": "Тестов Тест", "department_id": 2, "salary": 100000}

status, body = call("POST", "/api/employees", {**good, "salary": -100})
check("POST salary=-100 -> 400 и {'error': ...}", status == 400 and body and "error" in body, f"{status} {body}")

status, body = call("POST", "/api/employees", {**good, "department_id": 999})
check("POST несуществующий department_id -> 400", status == 400, f"{status} {body}")

status, body = call("POST", "/api/employees", {**good, "full_name": "   "})
check("POST пустое full_name -> 400", status == 400, f"{status} {body}")

status, body = call("POST", "/api/employees", {"full_name": "Без остальных полей"})
check("POST без обязательных полей -> 400", status == 400, f"{status} {body}")

status, created = call("POST", "/api/employees", good)
check("POST корректные данные -> 201 и запись с id",
      status == 201 and created and "id" in created and created["salary"] == 100000, f"{status} {created}")
if not created or "id" not in created:
    print("Дальше проверять нечего: сотрудник не создан.")
    finish()
new_id = created["id"]

print("--- Обновление и удаление ---")
status, body = call("GET", f"/api/employees/{new_id}")
check("GET /api/employees/{id} -> 200", status == 200 and body["full_name"] == "Тестов Тест", f"{status} {body}")

upd = {"full_name": "Тестов Т.", "department_id": 3, "salary": 123456.5}
status, body = call("PUT", f"/api/employees/{new_id}", upd)
check("PUT -> 200 и данные обновились",
      status == 200 and body and body["full_name"] == "Тестов Т." and body["department_id"] == 3
      and body["salary"] == 123456.5, f"{status} {body}")

status, body = call("PUT", f"/api/employees/{new_id}", {**upd, "salary": -1})
check("PUT salary=-1 -> 400", status == 400, f"{status} {body}")

status, body = call("PUT", "/api/employees/999999", upd)
check("PUT несуществующий id -> 404", status == 404, f"{status} {body}")

status, _ = call("DELETE", f"/api/employees/{new_id}")
check("DELETE -> 204", status == 204, status)

status, _ = call("DELETE", f"/api/employees/{new_id}")
check("повторный DELETE -> 404", status == 404, status)

status, _ = call("GET", f"/api/employees/{new_id}")
check("GET удалённого -> 404", status == 404, status)

status, after = call("GET", "/api/employees")
check("после всех проверок в базе столько же записей, сколько было",
      status == 200 and len(after) == start_count, f"{len(after) if after else after} вместо {start_count}")

finish()