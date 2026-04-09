from sqlalchemy import Column, Integer, String, ForeignKey
from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    department = Column(String)

    casual_total = Column(Integer)
    casual_taken = Column(Integer, default=0)

    sick_total = Column(Integer)
    sick_taken = Column(Integer, default=0)

    earned_total = Column(Integer)
    earned_taken = Column(Integer, default=0)