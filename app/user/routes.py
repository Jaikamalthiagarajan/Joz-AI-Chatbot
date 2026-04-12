from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.employee import Employee
from app.models.leave_request import LeaveRequest
from app.models.user import User

router = APIRouter(prefix="/user", tags=["User"])


class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    employee_id: int = None  


@router.post("/request-leave")
def request_leave(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] not in ["EMPLOYEE", "HR"]:
        raise HTTPException(status_code=403, detail="Employee or HR access only")

    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="End date cannot be before start date")

    if user["role"] == "EMPLOYEE":
        employee = db.query(Employee).join(User).filter(
            User.username == user["username"]
        ).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee profile not found")
    else:
        if data.employee_id:
            employee = db.query(Employee).filter(
                Employee.id == data.employee_id
            ).first()
            if not employee:
                raise HTTPException(status_code=404, detail="Employee not found")
        else:
            employee = db.query(Employee).join(User).filter(
                User.username == user["username"]
            ).first()
            if not employee:
                raise HTTPException(status_code=404, detail="HR employee profile not found")

    days_requested = (data.end_date - data.start_date).days + 1
    
    if data.leave_type == "CASUAL":
        remaining = employee.casual_total - employee.casual_taken
        leave_type_name = "Casual"
    elif data.leave_type == "SICK":
        remaining = employee.sick_total - employee.sick_taken
        leave_type_name = "Sick"
    elif data.leave_type == "EARNED":
        remaining = employee.earned_total - employee.earned_taken
        leave_type_name = "Earned"
    else:
        raise HTTPException(status_code=400, detail="Invalid leave type")
    
    if remaining < days_requested:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient {leave_type_name} leave balance. Available: {remaining} days, Requested: {days_requested} days"
        )

    leave = LeaveRequest(
        employee_id=employee.id,
        leave_type=data.leave_type,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
        status="PENDING"
    )

    db.add(leave)
    db.commit()

    return {"message": "Leave request submitted successfully"}

@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    if user["role"] not in ["EMPLOYEE", "HR"]:
        raise HTTPException(status_code=403, detail="Access denied")

    employee = db.query(Employee).join(User).filter(
        User.username == user["username"]
    ).first()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    casual_remaining = employee.casual_total - employee.casual_taken
    sick_remaining = employee.sick_total - employee.sick_taken
    earned_remaining = employee.earned_total - employee.earned_taken

    return {
        "username": user["username"],
        "role": user["role"],
        "department": employee.department,
        "leave_balance": {
            "casual": {
                "total": employee.casual_total,
                "taken": employee.casual_taken,
                "remaining": casual_remaining
            },
            "sick": {
                "total": employee.sick_total,
                "taken": employee.sick_taken,
                "remaining": sick_remaining
            },
            "earned": {
                "total": employee.earned_total,
                "taken": employee.earned_taken,
                "remaining": earned_remaining
            }
        }
    }