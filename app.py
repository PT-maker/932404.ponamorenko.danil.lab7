import math

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import db

app = FastAPI(title="Сотрудники и отделы", description="Лабораторная №7, вариант 15")
db.init_db()  # создаёт таблицы и тестовые данные при запуске


# ---------- Модели ----------

class EmployeeIn(BaseModel):
    full_name: str
    department_id: int
    salary: float


class Employee(EmployeeIn):
    id: int


class Department(BaseModel):
    id: int
    name: str


class Error(BaseModel):
    error: str


# ---------- Ошибки: всегда JSON {"error": "..."} ----------

class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # неверный тип или отсутствующее поле: отвечаем 400, а не стандартным 422
    fields = ", ".join(str(err["loc"][-1]) for err in exc.errors())
    return JSONResponse(status_code=400, content={"error": f"Некорректные данные: {fields}"})


def validate_employee(data: EmployeeIn):
    if not math.isfinite(data.salary) or data.salary < 0:
        raise ApiError(400, "salary должна быть числом не меньше 0")
    if data.full_name.strip() == "":
        raise ApiError(400, "full_name не должно быть пустым")
    if not db.department_exists(data.department_id):
        raise ApiError(400, "Отдела с таким department_id не существует")


ERRORS = {
    400: {"model": Error, "description": "Некорректные данные"},
    404: {"model": Error, "description": "Сотрудник не найден"},
}


# ---------- Маршруты ----------

@app.get("/api/departments", response_model=list[Department])
def list_departments():
    return db.get_departments()


@app.get("/api/employees", response_model=list[Employee], responses={400: ERRORS[400]})
def list_employees(department_id: int | None = None):
    """Все сотрудники по убыванию зарплаты. ?department_id=4 оставляет только этот отдел."""
    return db.get_employees(department_id)


@app.get("/api/employees/{employee_id}", response_model=Employee, responses=ERRORS)
def get_employee(employee_id: int):
    employee = db.get_employee(employee_id)
    if employee is None:
        raise ApiError(404, "Сотрудник не найден")
    return employee


@app.post("/api/employees", response_model=Employee, status_code=201, responses={400: ERRORS[400]})
def create_employee(data: EmployeeIn):
    validate_employee(data)
    return db.create_employee(data.full_name.strip(), data.department_id, data.salary)


@app.put("/api/employees/{employee_id}", response_model=Employee, responses=ERRORS)
def update_employee(employee_id: int, data: EmployeeIn):
    validate_employee(data)
    employee = db.update_employee(employee_id, data.full_name.strip(), data.department_id, data.salary)
    if employee is None:
        raise ApiError(404, "Сотрудник не найден")
    return employee


@app.delete("/api/employees/{employee_id}", status_code=204, responses={404: ERRORS[404]})
def delete_employee(employee_id: int):
    if not db.delete_employee(employee_id):
        raise ApiError(404, "Сотрудник не найден")
    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)