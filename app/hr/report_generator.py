import io
import csv
from datetime import datetime, date
from typing import List, Dict, Optional
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.employee import Employee
from app.models.leave_request import LeaveRequest


def get_leave_statistics(db: Session, year: int = None) -> List[Dict]:
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
        
        casual_days = 0
        sick_days = 0
        earned_days = 0
        
        for leave in leaves_taken:
            days = (leave.end_date - leave.start_date).days + 1
            leave_type = leave.leave_type.upper()
            if leave_type == "CASUAL":
                casual_days += days
            elif leave_type == "SICK":
                sick_days += days
            elif leave_type == "EARNED":
                earned_days += days
        
        total_days_taken = casual_days + sick_days + earned_days
        
        stats.append({
            "username": user.username,
            "employee_id": emp.id,
            "total_days_taken": total_days_taken,
            "casual_taken": casual_days,
            "sick_taken": sick_days,
            "earned_taken": earned_days,
            "casual_available": emp.casual_total - casual_days,
            "sick_available": emp.sick_total - sick_days,
            "earned_available": emp.earned_total - earned_days,
        })
    
    return sorted(stats, key=lambda x: x["total_days_taken"], reverse=True)


def generate_csv_report(db: Session, year: int = None) -> io.BytesIO:
    stats = get_leave_statistics(db, year)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    current_year = year or datetime.today().year
    writer.writerow([f"Leave Analytics Report - {current_year}"])
    writer.writerow([f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([])
    
    writer.writerow(["Employee Name", "Total Days Taken", "Casual", "Sick", "Earned", 
                     "Casual Available", "Sick Available", "Earned Available"])
    
    for emp in stats:
        writer.writerow([
            emp["username"].upper(),
            emp["total_days_taken"],
            emp["casual_taken"],
            emp["sick_taken"],
            emp["earned_taken"],
            emp["casual_available"],
            emp["sick_available"],
            emp["earned_available"]
        ])
    
    csv_bytes = io.BytesIO(output.getvalue().encode('utf-8'))
    return csv_bytes


def generate_excel_report(db: Session, year: int = None) -> io.BytesIO:
    stats = get_leave_statistics(db, year)
    current_year = year or datetime.today().year
    
    data = {
        "Employee Name": [emp["username"].upper() for emp in stats],
        "Total Days Taken": [emp["total_days_taken"] for emp in stats],
        "Casual Taken": [emp["casual_taken"] for emp in stats],
        "Sick Taken": [emp["sick_taken"] for emp in stats],
        "Earned Taken": [emp["earned_taken"] for emp in stats],
        "Casual Available": [emp["casual_available"] for emp in stats],
        "Sick Available": [emp["sick_available"] for emp in stats],
        "Earned Available": [emp["earned_available"] for emp in stats]
    }
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Leave Analytics', index=False)
        
        summary_data = {
            "Metric": ["Report Year", "Generated Date", "Total Employees", "Overall Avg Days Taken"],
            "Value": [
                current_year,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                len(stats),
                round(sum([emp["total_days_taken"] for emp in stats]) / len(stats), 2) if stats else 0
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    output.seek(0)
    return output


def generate_pdf_report(db: Session, year: int = None) -> io.BytesIO:
    stats = get_leave_statistics(db, year)
    current_year = year or datetime.today().year
    previous_year = current_year - 1
    
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        alignment=1  
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=8,
        spaceBefore=8
    )
    
    elements = []
    
    elements.append(Paragraph(f"Leave Analytics Report - {current_year}", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    if stats:
        elements.append(Paragraph("SECTION 1: CURRENT YEAR LEAVE CONSUMPTION", heading_style))
        elements.append(Spacer(1, 0.1*inch))
        
        highest = stats[0]
        lowest = stats[-1]
        
        elements.append(Paragraph("<b>HIGHEST LEAVE CONSUMER</b>", styles['Heading3']))
        highest_data = [
            ["Employee Name:", highest["username"].upper()],
            ["Total Days Taken:", str(highest["total_days_taken"]) + " days"],
            ["", ""],
            ["Leave Breakdown:", ""],
            ["  Casual Leave:", str(highest["casual_taken"]) + " days"],
            ["  Sick Leave:", str(highest["sick_taken"]) + " days"],
            ["  Earned Leave:", str(highest["earned_taken"]) + " days"],
        ]
        highest_table = Table(highest_data, colWidths=[2*inch, 2.5*inch])
        highest_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
            ('BACKGROUND', (0, 0), (0, 3), colors.HexColor('#ecf0f1')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(highest_table)
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("<b>LOWEST LEAVE CONSUMER</b>", styles['Heading3']))
        lowest_data = [
            ["Employee Name:", lowest["username"].upper()],
            ["Total Days Taken:", str(lowest["total_days_taken"]) + " days"],
            ["", ""],
            ["Leave Breakdown:", ""],
            ["  Casual Leave:", str(lowest["casual_taken"]) + " days"],
            ["  Sick Leave:", str(lowest["sick_taken"]) + " days"],
            ["  Earned Leave:", str(lowest["earned_taken"]) + " days"],
        ]
        lowest_table = Table(lowest_data, colWidths=[2*inch, 2.5*inch])
        lowest_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
            ('BACKGROUND', (0, 0), (0, 3), colors.HexColor('#ecf0f1')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(lowest_table)
        elements.append(Spacer(1, 0.3*inch))
        
        elements.append(Paragraph("SECTION 2: ALL EMPLOYEES SUMMARY", heading_style))
        elements.append(Spacer(1, 0.1*inch))
        
        table_data = [["Employee", "Total Days", "Casual", "Sick", "Earned", "Casual Avail", "Sick Avail", "Earned Avail"]]
        for emp in stats:
            table_data.append([
                emp["username"].upper()[:15],
                str(emp["total_days_taken"]),
                str(emp["casual_taken"]),
                str(emp["sick_taken"]),
                str(emp["earned_taken"]),
                str(emp["casual_available"]),
                str(emp["sick_available"]),
                str(emp["earned_available"])
            ])
        
        summary_table = Table(table_data, colWidths=[1*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(summary_table)
    
    doc.build(elements)
    output.seek(0)
    return output
