from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import os

from app.core.database import get_db
from app.core.deps import get_current_user
from app.hr.services import process_policy
from app.hr.report_generator import generate_csv_report, generate_excel_report, generate_pdf_report
from app.models.user import User
from app.models.employee import Employee
from app.models.leave_request import LeaveRequest

router = APIRouter(prefix="/hr", tags=["HR"])


class EmployeeCreate(BaseModel):
    username: str
    password: str
    role: str
    department: str
    casual_total: int
    sick_total: int
    earned_total: int



@router.post("/add-employee")
def add_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] != "HR":
        raise HTTPException(status_code=403, detail="HR access only")

    if data.role.upper() not in ["HR", "EMPLOYEE"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    existing_user = db.query(User).filter(
        User.username == data.username
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username=data.username,
        password=data.password,
        role=data.role.upper()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_employee = Employee(
        user_id=new_user.id,
        department=data.department,

        casual_total=data.casual_total,
        casual_taken=0,

        sick_total=data.sick_total,
        sick_taken=0,

        earned_total=data.earned_total,
        earned_taken=0
    )

    db.add(new_employee)
    db.commit()

    return {
        "message": "Employee created successfully",
        "leave_structure": {
            "casual": data.casual_total,
            "sick": data.sick_total,
            "earned": data.earned_total
        }
    }


@router.get("/leave-requests")
def get_leave_requests(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    if user["role"] != "HR":
        raise HTTPException(status_code=403, detail="HR access only")

    requests = db.query(LeaveRequest).all()

    if not requests:
        return {"message": "No leave requests found"}

    result = []

    for req in requests:
        result.append({
            "request_id": req.id,
            "employee_id": req.employee_id,
            "leave_type": req.leave_type,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "reason": req.reason,
            "status": req.status
        })

    return result


@router.get("/pending-leaves")
def get_pending_leaves(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    if user["role"] != "HR":
        raise HTTPException(status_code=403, detail="HR access only")

    requests = db.query(LeaveRequest).filter(
        LeaveRequest.status == "PENDING"
    ).all()

    if not requests:
        return {"message": "No pending leave requests"}

    result = []

    for req in requests:
        result.append({
            "request_id": req.id,
            "employee_id": req.employee_id,
            "leave_type": req.leave_type,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "reason": req.reason
        })

    return result


@router.put("/approve-leave/{request_id}")
def approve_leave(
    request_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    if user["role"] != "HR":
        raise HTTPException(status_code=403, detail="HR access only")

    leave = db.query(LeaveRequest).filter(
        LeaveRequest.id == request_id
    ).first()

    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    if leave.status != "PENDING":
        raise HTTPException(status_code=400, detail="Leave already processed")

    employee = db.query(Employee).filter(
        Employee.id == leave.employee_id
    ).first()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    leave_type = leave.leave_type.upper()

    leave_days = (leave.end_date - leave.start_date).days + 1

    if leave_type == "CASUAL":

        remaining = employee.casual_total - employee.casual_taken

        if leave_days > remaining:
            raise HTTPException(status_code=400, detail="Not enough casual leaves")

        employee.casual_taken += leave_days

    elif leave_type == "SICK":

        remaining = employee.sick_total - employee.sick_taken

        if leave_days > remaining:
            raise HTTPException(status_code=400, detail="Not enough sick leaves")

        employee.sick_taken += leave_days

    elif leave_type == "EARNED":

        remaining = employee.earned_total - employee.earned_taken

        if leave_days > remaining:
            raise HTTPException(status_code=400, detail="Not enough earned leaves")

        employee.earned_taken += leave_days

    else:
        raise HTTPException(status_code=400, detail="Invalid leave type")

    leave.status = "APPROVED"
    db.add(leave)
    db.add(employee)
    db.commit()
    db.refresh(leave)
    db.refresh(employee)

    return {
        "message": "Leave approved successfully",
        "leave_balance": {
            "casual_remaining": employee.casual_total - employee.casual_taken,
            "sick_remaining": employee.sick_total - employee.sick_taken,
            "earned_remaining": employee.earned_total - employee.earned_taken
        }
    }


@router.put("/reject-leave/{request_id}")
def reject_leave(
    request_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    if user["role"] != "HR":
        raise HTTPException(status_code=403, detail="HR access only")

    leave = db.query(LeaveRequest).filter(
        LeaveRequest.id == request_id
    ).first()

    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    if leave.status != "PENDING":
        raise HTTPException(status_code=400, detail="Leave already processed")

    leave.status = "REJECTED"
    db.add(leave)
    db.commit()
    db.refresh(leave)

    return {
        "message": "Leave request rejected",
        "request_id": leave.id,
        "status": leave.status
    }


@router.post("/upload-policy")
async def upload_policy(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):

    if user["role"] != "HR":
        raise HTTPException(status_code=403, detail="HR access only")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    upload_dir = "uploaded_policies"
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    process_policy(file_path, file.filename)

    return {
        "message": "Policy uploaded and processed successfully"
    }


@router.get("/download-report/csv")
def download_report_csv(
    year: int = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] != "HR":
        raise HTTPException(status_code=403, detail="HR access only")
    
    current_year = year or datetime.today().year
    csv_file = generate_csv_report(db, current_year)
    
    filename = f"leave_analytics_{current_year}.csv"
    return StreamingResponse(
        iter([csv_file.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/download-report/excel")
def download_report_excel(
    year: int = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] != "HR":
        raise HTTPException(status_code=403, detail="HR access only")
    
    current_year = year or datetime.today().year
    excel_file = generate_excel_report(db, current_year)
    
    filename = f"leave_analytics_{current_year}.xlsx"
    return StreamingResponse(
        iter([excel_file.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/download-report/pdf")
def download_report_pdf(
    year: int = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] != "HR":
        raise HTTPException(status_code=403, detail="HR access only")
    
    current_year = year or datetime.today().year
    pdf_file = generate_pdf_report(db, current_year)
    
    filename = f"leave_analytics_{current_year}.pdf"
    return StreamingResponse(
        iter([pdf_file.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )