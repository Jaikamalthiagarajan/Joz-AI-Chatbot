from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import re
from datetime import date, timedelta, datetime

from app.vectorstore import collection
from app.llm.embeddings import get_embedding
from app.llm.llm_services import generate_response
from app.core.deps import get_current_user
from app.core.database import get_db

from app.models.user import User
from app.models.employee import Employee
from app.models.leave_request import LeaveRequest


router = APIRouter(prefix="/chat", tags=["Policy QA"])


class ChatRequest(BaseModel):
    question: str


def detect_intent(question: str):
    q = question.lower()

    if re.search(r'(most|least|highest|lowest|maximum|minimum|more than|less than).*(leave|leaves|taken)', q):
        return "TRENDS"
    
    if re.search(r'(who|which).*(taken|used).*(most|least|maximum|minimum).*(leave|leaves)', q):
        return "TRENDS"
    
    if re.search(r'(comparison|compare|vs|versus|previous year|last year)', q):
        return "COMPARISON"
    
    if re.search(r'(statistics|stats|summary|report|analytics|trend)', q):
        return "TRENDS"

    if re.search(r'(apply|take|book|request).*(leave|leaves)', q):
        return "APPLY_LEAVE"

    if re.search(r'(my|how many|balance|remaining).*(leave|leaves)', q):
        return "PERSONAL_BALANCE"

    if re.search(r'(leave).*(of|for|does)\s+\w+', q):
        return "PERSONAL_BALANCE"

    return "POLICY"


def detect_leave_type(question: str):
    q = question.lower()

    if "casual" in q:
        return "CASUAL"
    if "sick" in q:
        return "SICK"
    if "earned" in q:
        return "EARNED"

    return None


def extract_days(question: str):

    q = question.lower()
    match = re.search(r'(\d+)\s*(day|days)', q)

    if match:
        return int(match.group(1))

    return 1

def extract_date(question: str):

    q = question.lower()

    month_map = {
        "january":1, "february":2, "march":3, "april":4,
        "may":5, "june":6, "july":7, "august":8,
        "september":9, "october":10, "november":11, "december":12
    }

    match1 = re.search(r'(\d{1,2})(st|nd|rd|th)?\s*(of)?\s*(january|february|march|april|may|june|july|august|september|october|november|december)', q)
    match2 = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{1,2})', q)
    match3 = re.search(r'(\d{1,2})[/-](\d{1,2})', q)

    try:
        year = datetime.today().year

        if match1:
            day = int(match1.group(1))
            month = month_map[match1.group(4)]
            return date(year, month, day)

        elif match2:
            month = month_map[match2.group(1)]
            day = int(match2.group(2))
            return date(year, month, day)

        elif match3:
            day = int(match3.group(1))
            month = int(match3.group(2))
            return date(year, month, day)

    except:
        return None

    return None


def extract_employee_name(question: str):
    match = re.search(r'(for|of|does)\s+(\w+)', question.lower())
    if match:
        candidate = match.group(2)
        if re.search(r'^\d+(st|nd|rd|th)?$', candidate):
            return None
        return candidate
    return None


def get_leave_statistics(db: Session, year: int = None):
    if year is None:
        year = datetime.today().year
    
    employees = db.query(Employee).join(User).all()
    stats = []
    
    for emp in employees:
        user = db.query(User).filter(User.id == emp.user_id).first()
        
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        
        leaves_taken = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.status == "APPROVED",
            LeaveRequest.start_date >= year_start,
            LeaveRequest.start_date <= year_end
        ).all()
        
        total_days_taken = sum([
            (leave.end_date - leave.start_date).days + 1 
            for leave in leaves_taken
        ])
        
        stats.append({
            "username": user.username,
            "employee_id": emp.id,
            "total_days_taken": total_days_taken,
            "casual_taken": emp.casual_taken,
            "sick_taken": emp.sick_taken,
            "earned_taken": emp.earned_taken,
            "casual_available": emp.casual_total - emp.casual_taken,
            "sick_available": emp.sick_total - emp.sick_taken,
            "earned_available": emp.earned_total - emp.earned_taken,
        })
    
    return sorted(stats, key=lambda x: x["total_days_taken"], reverse=True)


def get_leave_statistics_by_type(db: Session, year: int = None):
    if year is None:
        year = datetime.today().year
    
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    
    stats = {
        "CASUAL": {"employees": [], "total_days": 0},
        "SICK": {"employees": [], "total_days": 0},
        "EARNED": {"employees": [], "total_days": 0}
    }
    
    for leave_type in ["CASUAL", "SICK", "EARNED"]:
        leaves = db.query(LeaveRequest).filter(
            LeaveRequest.leave_type == leave_type,
            LeaveRequest.status == "APPROVED",
            LeaveRequest.start_date >= year_start,
            LeaveRequest.start_date <= year_end
        ).all()
        
        emp_dict = {}
        for leave in leaves:
            employee = db.query(Employee).filter(Employee.id == leave.employee_id).first()
            user = db.query(User).filter(User.id == employee.user_id).first()
            
            days = (leave.end_date - leave.start_date).days + 1
            stats[leave_type]["total_days"] += days
            
            if user.username not in emp_dict:
                emp_dict[user.username] = 0
            emp_dict[user.username] += days
        
        stats[leave_type]["employees"] = sorted(
            emp_dict.items(), key=lambda x: x[1], reverse=True
        )
    
    return stats


def get_employee_by_username(db: Session, username: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    return db.query(Employee).filter(Employee.user_id == user.id).first()

@router.post("/query")
def query_policy(
    data: ChatRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    question = data.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    intent = detect_intent(question)

    username = user["username"]
    role = user["role"]

    if intent == "TRENDS":
        if role.upper() != "HR":
            return {
                "answer": "Trends and analytics are available for HR users.",
                "sources": []
            }
        
        current_year = datetime.today().year
        current_year_stats = get_leave_statistics(db, current_year)
        previous_year_stats = get_leave_statistics(db, current_year - 1)
        
        if current_year_stats:
            most_leaves = current_year_stats[0]
            least_leaves = current_year_stats[-1]
            
            most_prev = next((s for s in previous_year_stats if s["username"] == most_leaves["username"]), None)
            least_prev = next((s for s in previous_year_stats if s["username"] == least_leaves["username"]), None)
            
            most_prev_days = most_prev['total_days_taken'] if most_prev else 0
            least_prev_days = least_prev['total_days_taken'] if least_prev else 0
            most_change = most_leaves['total_days_taken'] - most_prev_days
            least_change = least_leaves['total_days_taken'] - least_prev_days
            
            answer = f"""

         LEAVE TRENDS & ANALYTICS REPORT - {current_year}              

SECTION 1: CURRENT YEAR LEAVE CONSUMPTION ({current_year})


 HIGHEST LEAVE CONSUMER 
  Employee Name:        {most_leaves['username'].upper()}
  Total Days Taken:     {most_leaves['total_days_taken']} days

  Breakdown by Type:
    Casual Leave:    {most_leaves['casual_taken']} days
    Sick Leave:      {most_leaves['sick_taken']} days
    Earned Leave:    {most_leaves['earned_taken']} days



 LOWEST LEAVE CONSUMER 
  Employee Name:        {least_leaves['username'].upper()}
  Total Days Taken:     {least_leaves['total_days_taken']} days

  Breakdown by Type:
    Casual Leave:    {least_leaves['casual_taken']} days
    Sick Leave:      {least_leaves['sick_taken']} days
    Earned Leave:    {least_leaves['earned_taken']} days




SECTION 2: YEAR-OVER-YEAR COMPARISON ({current_year - 1} → {current_year})

 {most_leaves['username'].upper()} (Highest Consumer) 
  {current_year - 1}: {most_prev_days:2d} days     →     {current_year}: {most_leaves['total_days_taken']:2d} days
         Change: {"↑" if most_change > 0 else "→" if most_change == 0 else "↓"} {abs(most_change)} days ({("INCREASE" if most_change > 0 else "STABLE" if most_change == 0 else "DECREASE")}))


 {least_leaves['username'].upper()} (Lowest Consumer) 
  {current_year - 1}: {least_prev_days:2d} days     →     {current_year}: {least_leaves['total_days_taken']:2d} days
         Change: {"↑" if least_change > 0 else "→" if least_change == 0 else "↓"} {abs(least_change)} days ({("INCREASE" if least_change > 0 else "STABLE" if least_change == 0 else "DECREASE")}))

"""
            
            return {"answer": answer, "sources": [{"document": "Employee Analytics"}]}
    
    if intent == "COMPARISON":
        if role.upper() != "HR":
            return {
                "answer": "Comparison reports are available for HR users.",
                "sources": []
            }
        
        current_year = datetime.today().year
        previous_year = current_year - 1
        
        current_year_stats = get_leave_statistics_by_type(db, current_year)
        previous_year_stats = get_leave_statistics_by_type(db, previous_year)
        
        casual_change = current_year_stats['CASUAL']['total_days'] - previous_year_stats['CASUAL']['total_days']
        sick_change = current_year_stats['SICK']['total_days'] - previous_year_stats['SICK']['total_days']
        earned_change = current_year_stats['EARNED']['total_days'] - previous_year_stats['EARNED']['total_days']
        total_previous = previous_year_stats['CASUAL']['total_days'] + previous_year_stats['SICK']['total_days'] + previous_year_stats['EARNED']['total_days']
        total_current = current_year_stats['CASUAL']['total_days'] + current_year_stats['SICK']['total_days'] + current_year_stats['EARNED']['total_days']
        
        answer = f"""
    LEAVE USAGE COMPARISON REPORT {previous_year} vs {current_year}                       │

ANNUAL OVERVIEW

ORGANIZATION-WIDE LEAVE USAGE 
  Year {previous_year}:  {total_previous:3d} days total
  Year {current_year}:  {total_current:3d} days total
  Net Change: {"↑" if (total_current - total_previous) > 0 else "→" if (total_current - total_previous) == 0 else "↓"} {abs(total_current - total_previous):2d} days


LEAVE TYPE BREAKDOWN

 CASUAL LEAVE 
  {previous_year}:  {previous_year_stats['CASUAL']['total_days']:3d} days  →  {current_year}:  {current_year_stats['CASUAL']['total_days']:3d} days
  Change: {"↑" if casual_change > 0 else "→" if casual_change == 0 else "↓"} {abs(casual_change):2d} days {"(INCREASED)" if casual_change > 0 else "(STABLE)" if casual_change == 0 else "(DECREASED)"}


SICK LEAVE 
  {previous_year}:  {previous_year_stats['SICK']['total_days']:3d} days  →  {current_year}:  {current_year_stats['SICK']['total_days']:3d} days
  Change: {"↑" if sick_change > 0 else "→" if sick_change == 0 else "↓"} {abs(sick_change):2d} days {"(INCREASED)" if sick_change > 0 else "(STABLE)" if sick_change == 0 else "(DECREASED)"}


EARNED LEAVE

  {previous_year}:  {previous_year_stats['EARNED']['total_days']:3d} days  →  {current_year}:  {current_year_stats['EARNED']['total_days']:3d} days
  Change: {"↑" if earned_change > 0 else "→" if earned_change == 0 else "↓"} {abs(earned_change):2d} days {"(INCREASED)" if earned_change > 0 else "(STABLE)" if earned_change == 0 else "(DECREASED)"}


KEY INSIGHTS

  Most Utilized Type:  {max([('Casual', current_year_stats['CASUAL']['total_days']), ('Sick', current_year_stats['SICK']['total_days']), ('Earned', current_year_stats['EARNED']['total_days'])], key=lambda x: x[1])[0]} Leave ({max([current_year_stats['CASUAL']['total_days'], current_year_stats['SICK']['total_days'], current_year_stats['EARNED']['total_days']])} days)
  Total Org Usage:     {total_current} days in {current_year} ({total_previous} in {previous_year})



"""
        
        return {"answer": answer, "sources": [{"document": "Employee Analytics"}]}

    target_username = username
    requested_user = extract_employee_name(question)

    if role.upper() == "HR":
        if requested_user:
            target_username = requested_user
    else:
        if requested_user and requested_user.lower() != username.lower():
            return {
                "answer": "You do not have access to view other employees' details.",
                "sources": []
            }
        target_username = username  

    employee = get_employee_by_username(db, target_username)

    if not employee:
        return {
            "answer": f"No employee found with username '{target_username}'.",
            "sources": []
        }

    casual_remaining = employee.casual_total - employee.casual_taken
    sick_remaining = employee.sick_total - employee.sick_taken
    earned_remaining = employee.earned_total - employee.earned_taken

    leave_date = extract_date(question)

    if intent == "PERSONAL_BALANCE":
        if role.upper() != "HR" and target_username.lower() != username.lower():
            return {
                "answer": "You do not have access to view other employees' leave details.",
                "sources": []
            }

    if intent == "APPLY_LEAVE":

        if role.upper() != "HR" and target_username.lower() != username.lower():
            return {
                "answer": "You can only apply leave for yourself.",
                "sources": []
            }

        leave_type = detect_leave_type(question)
        days = extract_days(question)

        if "all" in question.lower():
            if leave_type == "CASUAL":
                days = casual_remaining
            elif leave_type == "SICK":
                days = sick_remaining
            elif leave_type == "EARNED":
                days = earned_remaining

        if not leave_type:
            return {
                "answer": f"""
INCOMPLETE REQUEST
{'=' * 60}

Please specify which type of leave you want to apply for:
  • CASUAL Leave
  • SICK Leave
  • EARNED Leave

For example: "I want to apply 2 days of casual leave from 15th April"

{'=' * 60}
""",
                "sources": []
            }

        if not leave_date:
            return {
                "answer": f"""
INCOMPLETE REQUEST
{'=' * 60}

Leave Type: {leave_type.upper()}

Please specify the date for your leave request.

Format examples:
  • "15th April" or "April 15"
  • "15/4" or "15-4"

For example: "I want to apply 2 days of {leave_type.lower()} leave starting 15th April"

{'=' * 60}
""",
                "sources": []
            }

        if leave_date < date.today():
            return {
                "answer": f"""
INVALID DATE - PAST DATE NOT ALLOWED
{'=' * 60}

You requested leave for: {leave_date.strftime('%d %B %Y')}
Today's date: {date.today().strftime('%d %B %Y')}

Leave can only be applied for current or future dates.
Please select a date from today onwards.

{'=' * 60}
""",
                "sources": []
            }

        if days <= 0:
            alternative_leaves = []
            if casual_remaining > 0:
                alternative_leaves.append(f"{casual_remaining} day(s) of Casual Leave")
            if sick_remaining > 0:
                alternative_leaves.append(f"{sick_remaining} day(s) of Sick Leave")
            if earned_remaining > 0:
                alternative_leaves.append(f"{earned_remaining} day(s) of Earned Leave")
            
            if alternative_leaves:
                suggestions = ", ".join(alternative_leaves)
                return {
                    "answer": f"""
INSUFFICIENT LEAVE BALANCE
{'=' * 60}

Leave Type: {leave_type.upper()}
Days Requested: {days}
Balance Available: 0 days

Unfortunately, you do not have any {leave_type.lower()} leave remaining.

ALTERNATIVE OPTIONS:
You currently have:
  • {alternative_leaves[0]}
  {"  • " + alternative_leaves[1] if len(alternative_leaves) > 1 else ""}
  {"  • " + alternative_leaves[2] if len(alternative_leaves) > 2 else ""}

Would you like to apply for a different type of leave?

{'=' * 60}
""",
                    "sources": [{"document": "Employee Database"}]
                }
            else:
                return {
                    "answer": f"""
NO LEAVE BALANCE AVAILABLE
{'=' * 60}

Leave Type: {leave_type.upper()}
Days Requested: {days}
Balance Available: 0 days

Unfortunately, you have no leave balance available across all leave types.
Please contact HR for assistance.

{'=' * 60}
""",
                    "sources": [{"document": "Employee Database"}]
                }

        if leave_type == "CASUAL" and days > casual_remaining:
            alternative_leaves = []
            if sick_remaining > 0:
                alternative_leaves.append(("Sick Leave", sick_remaining))
            if earned_remaining > 0:
                alternative_leaves.append(("Earned Leave", earned_remaining))
            
            if alternative_leaves:
                suggestions = ", ".join([f"{count} day(s) of {leave_type_name}" for leave_type_name, count in alternative_leaves])
                
                return {
                    "answer": f"""
INSUFFICIENT CASUAL LEAVE BALANCE
{'=' * 60}

Leave Type: CASUAL
Days Requested: {days} days
Balance Available: {casual_remaining} day(s)
Shortfall: {days - casual_remaining} day(s)

ALTERNATIVE OPTIONS:
You have:
  • {alternative_leaves[0][1]} day(s) of {alternative_leaves[0][0]}
  {"  • " + str(alternative_leaves[1][1]) + " day(s) of " + alternative_leaves[1][0] if len(alternative_leaves) > 1 else ""}

Would you like to apply for {alternative_leaves[0][0]} instead for {leave_date.strftime('%d %B %Y')}?

{'=' * 60}
""",
                    "sources": [{"document": "Employee Database"}]
                }
            else:
                return {
                    "answer": f"""
INSUFFICIENT CASUAL LEAVE BALANCE
{'=' * 60}

Leave Type: CASUAL
Days Requested: {days} days
Balance Available: {casual_remaining} day(s)
Shortfall: {days - casual_remaining} day(s)

Unfortunately, no alternative leave options are available.
Please contact HR for assistance.

{'=' * 60}
""",
                    "sources": [{"document": "Employee Database"}]
                }

        elif leave_type == "SICK" and days > sick_remaining:
            alternative_leaves = []
            if casual_remaining > 0:
                alternative_leaves.append(("Casual Leave", casual_remaining))
            if earned_remaining > 0:
                alternative_leaves.append(("Earned Leave", earned_remaining))
            
            if alternative_leaves:
                suggestions = ", ".join([f"{count} day(s) of {leave_type_name}" for leave_type_name, count in alternative_leaves])
                
                return {
                    "answer": f"""
INSUFFICIENT SICK LEAVE BALANCE
{'=' * 60}

Leave Type: SICK
Days Requested: {days} days
Balance Available: {sick_remaining} day(s)
Shortfall: {days - sick_remaining} day(s)

ALTERNATIVE OPTIONS:
You have:
  • {alternative_leaves[0][1]} day(s) of {alternative_leaves[0][0]}
  {"  • " + str(alternative_leaves[1][1]) + " day(s) of " + alternative_leaves[1][0] if len(alternative_leaves) > 1 else ""}

Would you like to apply for {alternative_leaves[0][0]} instead for {leave_date.strftime('%d %B %Y')}?

{'=' * 60}
""",
                    "sources": [{"document": "Employee Database"}]
                }
            else:
                return {
                    "answer": f"""
INSUFFICIENT SICK LEAVE BALANCE
{'=' * 60}

Leave Type: SICK
Days Requested: {days} days
Balance Available: {sick_remaining} day(s)
Shortfall: {days - sick_remaining} day(s)

Unfortunately, no alternative leave options are available.
Please contact HR for assistance.

{'=' * 60}
""",
                    "sources": [{"document": "Employee Database"}]
                }

        elif leave_type == "EARNED" and days > earned_remaining:
            alternative_leaves = []
            if casual_remaining > 0:
                alternative_leaves.append(("Casual Leave", casual_remaining))
            if sick_remaining > 0:
                alternative_leaves.append(("Sick Leave", sick_remaining))
            
            if alternative_leaves:
                suggestions = ", ".join([f"{count} day(s) of {leave_type_name}" for leave_type_name, count in alternative_leaves])
                
                return {
                    "answer": f"""
INSUFFICIENT EARNED LEAVE BALANCE
{'=' * 60}

Leave Type: EARNED
Days Requested: {days} days
Balance Available: {earned_remaining} day(s)
Shortfall: {days - earned_remaining} day(s)

ALTERNATIVE OPTIONS:
You have:
  • {alternative_leaves[0][1]} day(s) of {alternative_leaves[0][0]}
  {"  • " + str(alternative_leaves[1][1]) + " day(s) of " + alternative_leaves[1][0] if len(alternative_leaves) > 1 else ""}

Would you like to apply for {alternative_leaves[0][0]} instead for {leave_date.strftime('%d %B %Y')}?

{'=' * 60}
""",
                    "sources": [{"document": "Employee Database"}]
                }
            else:
                return {
                    "answer": f"""
INSUFFICIENT EARNED LEAVE BALANCE
{'=' * 60}

Leave Type: EARNED
Days Requested: {days} days
Balance Available: {earned_remaining} day(s)
Shortfall: {days - earned_remaining} day(s)

Unfortunately, no alternative leave options are available.
Please contact HR for assistance.

{'=' * 60}
""",
                    "sources": [{"document": "Employee Database"}]
                }

        start_date = leave_date
        end_date = leave_date + timedelta(days=days - 1)

        leave_request = LeaveRequest(
            employee_id=employee.id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason="Applied via chatbot",
            status="PENDING"
        )

        db.add(leave_request)
        db.commit()

        return {
            "answer": f"""
LEAVE REQUEST SUBMITTED SUCCESSFULLY
{'=' * 60}

Request Details:
  • Leave Type: {leave_type.upper()}
  • Duration: {days} day(s)
  • Start Date: {start_date.strftime('%d %B %Y')}
  • End Date: {end_date.strftime('%d %B %Y')}
  • Status: PENDING (Awaiting HR Approval)

Your request has been submitted to HR for review.
You will be notified once it is approved or requires modifications.

{'=' * 60}
""",
            "sources": [{"document": "Employee Database"}]
        }

    query_embedding = get_embedding(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=["documents", "metadatas", "distances"]
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    filtered_docs = []
    filtered_sources = []

    for doc, meta, dist in zip(docs, metas, dists):
        if dist <= 1.3:
            filtered_docs.append(doc)
            filtered_sources.append({
                "document": meta.get("source"),
                "page": meta.get("page")
            })

    unique_sources = {(s["document"], s["page"]): s for s in filtered_sources}
    final_sources = list(unique_sources.values())[:2]

    policy_context = "\n\n".join(filtered_docs)

    personal_info = f"""
EMPLOYEE LEAVE BALANCE SUMMARY
{'=' * 60}

Employee Name: {target_username.upper()}

LEAVE BALANCE STATUS:
  • Casual Leave Available: {casual_remaining} days
  • Sick Leave Available: {sick_remaining} days
  • Earned Leave Available: {earned_remaining} days

{'=' * 60}
"""

    if role.upper() != "HR" and target_username.lower() != username.lower():
        return {
            "answer": "You do not have permission to view this employee's data.",
            "sources": []
        }

    if filtered_docs:

        llm_answer = generate_response(
            question=question,
            personal_data=personal_info,
            policy_context=policy_context
        )

        clean_answer = re.sub(
            r"(the policy does not contain this information|no information found in policy|not mentioned in the policy)",
            "",
            llm_answer,
            flags=re.IGNORECASE
        ).strip()

        if clean_answer and clean_answer != ".":
            final_answer = clean_answer + "\n\n" + personal_info
        else:
            final_answer = personal_info
            final_sources = [{"document": "Employee Database"}]

    else:
        final_answer = personal_info
        final_sources = [{"document": "Employee Database"}]

    return {
        "answer": final_answer,
        "sources": final_sources
    }