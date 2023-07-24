import pg_conn
import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Enum,
    Index,
    Text,
    func
)
from sqlalchemy.orm import relationship, backref
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    UserMixin,
    RoleMixin,
    current_user,
    RegisterForm,
)

Base = pg_conn.Base

class Course(Base):
    __tablename__ = "course"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String(255), unique=True, nullable=False)

    week_day = Column(String(120), nullable=False)
    hours = Column(Integer)
    day_slot = Column(Integer)

    capacity = Column(Integer)
    min_capacity = Column(Integer)

    school_year = Column(String(120))
    is_semesterised = Column(Boolean, default=True)
    semester = Column(String(20))

    gender = Column(String(30))
    grade = Column(String(30))
    is_for_diploma = Column(Boolean, default=True)

    cat_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    category = relationship('Category', backref=backref('courses', lazy=True))

    teacher_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    teacher = relationship('User', backref=backref('teachers', lazy=True))


    def __repr__(self):
        return self.name

class Category(Base):
    __tablename__ = "category"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    is_mandatory = Column(Boolean, default=False)

    def __repr__(self):
        return self.name

class RoleUser(Base):
    __tablename__ = "roleuser"
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("role.id"), primary_key=True)

class Role(pg_conn.Base, RoleMixin):
    __tablename__ = "role"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    is_admin = Column(Boolean, default=False)

class User(pg_conn.Base, UserMixin):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    active = Column(Boolean)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)

    is_reg_completed = Column(Boolean)

    roles = relationship(
        "Role", secondary="roleuser", backref=backref("user", lazy="dynamic")
    )
    courses = relationship(
        "Course", secondary="courseuser", backref=backref("user", lazy="dynamic")
    )

    def __repr__(self):
        return self.first_name + " " + self.last_name

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.email

class CoursesUsers(Base):
    __tablename__ = "courseuser"
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    course_id = Column(Integer, ForeignKey("course.id"), primary_key=True)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class TimeTable(Base):
    __tablename__ = "timetable"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    user = relationship('User', backref=backref('users', lazy=True))
    class_name = Column(String, nullable=False)
    week_day = Column(String(120), nullable=False, index=True)
    day_slot = Column(Integer, index=True)
    is_mandatory = Column(Boolean)

class SysLog(Base):
    __tablename__ = "sys_log"
    id = Column(Integer, primary_key=True)
    msg = Column(String, nullable=False)
    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)
