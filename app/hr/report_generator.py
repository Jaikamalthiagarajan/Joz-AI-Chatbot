import io
import csv
from datetime import datetime, date
from typing import List, Dict, Optional
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
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


def generate_leave_type_pie_chart(stats: List[Dict]) -> io.BytesIO:
    total_casual = sum([emp["casual_taken"] for emp in stats])
    total_sick = sum([emp["sick_taken"] for emp in stats])
    total_earned = sum([emp["earned_taken"] for emp in stats])
    
    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor('#f8f9fa')
    ax.set_facecolor('#f8f9fa')
    
    leaves = [total_casual, total_sick, total_earned]
    labels = ['Casual Leave', 'Sick Leave', 'Earned Leave']
    colors_pie = ['#1f77b4', '#d62728', '#2ca02c']
    explode = (0.05, 0.05, 0.05)
    
    if sum(leaves) > 0:
        wedges, texts, autotexts = ax.pie(leaves, labels=labels, autopct='%1.1f%%', 
                                           colors=colors_pie, startangle=90, explode=explode,
                                           textprops={'fontsize': 11, 'weight': 'bold'})
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
        ax.set_title('Leave Distribution By Type', fontsize=14, fontweight='bold', 
                    pad=20, color='#1a1a1a')
    else:
        ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', fontsize=12)
    
    chart_image = io.BytesIO()
    plt.savefig(chart_image, format='png', dpi=100, bbox_inches='tight', facecolor='#f8f9fa')
    chart_image.seek(0)
    plt.close(fig)
    return chart_image


def generate_top_employees_chart(stats: List[Dict], limit: int = 5) -> io.BytesIO:
    top_stats = stats[:limit]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('#f8f9fa')
    ax.set_facecolor('#f8f9fa')
    
    names = [emp["username"].upper() for emp in top_stats]
    total_days = [emp["total_days_taken"] for emp in top_stats]
    casual = [emp["casual_taken"] for emp in top_stats]
    sick = [emp["sick_taken"] for emp in top_stats]
    earned = [emp["earned_taken"] for emp in top_stats]
    
    x = range(len(names))
    width = 0.25
    
    bars1 = ax.bar([i - width for i in x], casual, width, label='Casual', color='#1f77b4', edgecolor='#0d3b66', linewidth=1.2)
    bars2 = ax.bar(x, sick, width, label='Sick', color='#d62728', edgecolor='#a01d1d', linewidth=1.2)
    bars3 = ax.bar([i + width for i in x], earned, width, label='Earned', color='#2ca02c', edgecolor='#1a6b1a', linewidth=1.2)
    
    ax.set_ylabel('Days', fontsize=12, fontweight='bold', color='#1a1a1a')
    ax.set_xlabel('Employee', fontsize=12, fontweight='bold', color='#1a1a1a')
    ax.set_title('Top 5 Employees by Leave Consumption', fontsize=14, fontweight='bold', pad=20, color='#1a1a1a')
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha='right', fontsize=10)
    ax.legend(loc='upper left', fontsize=10, framealpha=0.95)
    ax.grid(axis='y', alpha=0.4, linestyle='--', color='gray')
    ax.set_axisbelow(True)
    
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    chart_image = io.BytesIO()
    plt.savefig(chart_image, format='png', dpi=100, bbox_inches='tight', facecolor='#f8f9fa')
    chart_image.seek(0)
    plt.close(fig)
    return chart_image


def generate_leave_type_bar_chart(stats: List[Dict]) -> io.BytesIO:
    total_casual = sum([emp["casual_taken"] for emp in stats])
    total_sick = sum([emp["sick_taken"] for emp in stats])
    total_earned = sum([emp["earned_taken"] for emp in stats])
    total = total_casual + total_sick + total_earned
    
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor('#f8f9fa')
    ax.set_facecolor('#f8f9fa')
    
    leave_types = ['Casual Leave', 'Sick Leave', 'Earned Leave']
    totals = [total_casual, total_sick, total_earned]
    colors_bar = ['#1f77b4', '#d62728', '#2ca02c']
    
    bars = ax.bar(leave_types, totals, color=colors_bar, edgecolor='#0d3b66', linewidth=2, width=0.6)
    
    for bar, total_val in zip(bars, totals):
        height = bar.get_height()
        percentage = (total_val / total * 100) if total > 0 else 0
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)} days\n({percentage:.1f}%)',
                ha='center', va='bottom', fontsize=11, fontweight='bold', color='#1a1a1a')
    
    ax.set_ylabel('Total Days', fontsize=12, fontweight='bold', color='#1a1a1a')
    ax.set_title('Organization-wide Leave Type Consumption', fontsize=14, fontweight='bold', pad=20, color='#1a1a1a')
    ax.set_ylim(0, max(totals) * 1.15)
    ax.grid(axis='y', alpha=0.4, linestyle='--', color='gray')
    ax.set_axisbelow(True)
    ax.tick_params(colors='#1a1a1a')
    
    chart_image = io.BytesIO()
    plt.savefig(chart_image, format='png', dpi=100, bbox_inches='tight', facecolor='#f8f9fa')
    chart_image.seek(0)
    plt.close(fig)
    return chart_image


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
        fontSize=18,
        textColor=colors.HexColor('#0d3b66'),
        spaceAfter=12,
        alignment=1,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    elements = []
    
    elements.append(Paragraph(f"Leave Analytics Report - {current_year}", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    if stats:
        elements.append(Paragraph("DASHBOARD - LEAVE OVERVIEW", heading_style))
        elements.append(Spacer(1, 0.1*inch))
        
        total_employees = len(stats)
        total_casual = sum([emp["casual_taken"] for emp in stats])
        total_sick = sum([emp["sick_taken"] for emp in stats])
        total_earned = sum([emp["earned_taken"] for emp in stats])
        total_leaves_taken = sum([emp["total_days_taken"] for emp in stats])
        avg_leaves = round(total_leaves_taken / total_employees, 1) if total_employees > 0 else 0
        
        highest = stats[0]
        lowest = stats[-1]
        
        dashboard_data = [
            ["METRIC", "VALUE"],
            ["Total Employees", str(total_employees)],
            ["Total Organization Leave Days", str(total_leaves_taken) + " days"],
            ["Average per Employee", str(avg_leaves) + " days"],
            ["", ""],
            ["LEAVE TYPE BREAKDOWN (Organization-wide)", ""],
            ["Casual Leave Used", str(total_casual) + " days"],
            ["Sick Leave Used", str(total_sick) + " days"],
            ["Earned Leave Used", str(total_earned) + " days"],
            ["", ""],
            ["HIGHLIGHTS", ""],
            ["Highest Consumer", highest["username"].upper() + f" ({highest['total_days_taken']} days)"],
            ["Lowest Consumer", lowest["username"].upper() + f" ({lowest['total_days_taken']} days)"],
        ]
        
        dashboard_table = Table(dashboard_data, colWidths=[3*inch, 2.5*inch])
        dashboard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d3b66')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 14),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8f1f8')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#e8f1f8')),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#e8f1f8')),
            ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 5), (-1, 5), colors.white),
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 5), (-1, 5), 11),
            ('BACKGROUND', (0, 10), (-1, 10), colors.HexColor('#d62728')),
            ('TEXTCOLOR', (0, 10), (-1, 10), colors.white),
            ('FONTNAME', (0, 10), (-1, 10), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 10), (-1, 10), 11),
            ('BACKGROUND', (0, 11), (-1, 12), colors.HexColor('#ffe8e8')),
            ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#0d3b66')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(dashboard_table)
        elements.append(Spacer(1, 0.3*inch))
        
        elements.append(Paragraph("DASHBOARD CHARTS", heading_style))
        elements.append(Spacer(1, 0.15*inch))
        
        try:
            pie_chart = generate_leave_type_pie_chart(stats)
            pie_image = Image(pie_chart, width=3.5*inch, height=3*inch)
            elements.append(pie_image)
            elements.append(Spacer(1, 0.1*inch))
        except Exception as e:
            elements.append(Paragraph(f"<i>Chart generation error: {str(e)}</i>", styles['Normal']))
        
        elements.append(Spacer(1, 0.2*inch))
        
        try:
            bar_chart = generate_leave_type_bar_chart(stats)
            bar_image = Image(bar_chart, width=3.5*inch, height=3*inch)
            elements.append(bar_image)
            elements.append(Spacer(1, 0.1*inch))
        except Exception as e:
            elements.append(Paragraph(f"<i>Chart generation error: {str(e)}</i>", styles['Normal']))
        
        elements.append(PageBreak())
        
        try:
            top_chart = generate_top_employees_chart(stats, limit=5)
            top_image = Image(top_chart, width=5.5*inch, height=3.5*inch)
            elements.append(top_image)
            elements.append(Spacer(1, 0.2*inch))
        except Exception as e:
            elements.append(Paragraph(f"<i>Chart generation error: {str(e)}</i>", styles['Normal']))
        
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("SECTION 1: CURRENT YEAR LEAVE CONSUMPTION", heading_style))
        
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
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#0d3b66')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (0, 3), colors.HexColor('#e8f1f8')),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#fff8e8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1f77b4')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
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
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#0d3b66')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (0, 3), colors.HexColor('#e8f1f8')),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#e8f8e8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2ca02c')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
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
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f4f8')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#e8f1f8')]),
            ('GRID', (0, 0), (-1, -1), 1.2, colors.HexColor('#1f77b4')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
    
    doc.build(elements)
    output.seek(0)
    return output
