from hth_model import Course, Category, User, Role, CoursesUsers, TimeTable, SysLog
import pg_conn
from flask import url_for, request
from flask_admin import Admin, consts, expose, BaseView
from flask_admin.contrib import sqla
from flask_admin import helpers as admin_helpers
import flask_login as login
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    RegisterForm,
    current_user
)
from flask_sqlalchemy import SQLAlchemy
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

SECONDS_TO_KEEP_COURSE = 60 * 10

DAY_SLOT_REPR = {"1": "ראשונה", "2": "שניה",
                "3": "שלישית", "4": "רביעית",
                "5": "חמישית", "6": "שישית",
                "7": "שביעית", "8": "שמינית",
                "9": "תשיעית", "10": "עשירית",
                "11": "אחת עשרה"
                }

TEACHERS = ["yaeln@hadash-holon.org.il", "moscovig@gmail.com"]
STUDENTS = ["moscovig@gmail.com"]
db = None

pg_conn.init_db()

def init_admin(app):
    global db

    admin = Admin(app, name='HTH Courses',
                  base_template="hth_template.html", template_mode='bootstrap4')

    db = SQLAlchemy(app)

    pg_conn.init_schema()

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=delete_expired, trigger="interval", seconds=5)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    class UserCls(db.Model, User):
        pass

    class RoleCls(db.Model, Role):
        pass

    user_datastore = SQLAlchemyUserDatastore(db, UserCls, RoleCls)

    security = Security(app, user_datastore, register_form=RegisterForm)

    @security.context_processor
    def security_context_processor():
        return dict(
            admin_base_template=admin.base_template,
            admin_view=admin.index_view,
            h=admin_helpers,
            get_url=url_for,
        )

    admin.add_view(
        CourseViewTeachers(
            Course,
            db.session,
            category="ניהול",
            name="קורסים",
            endpoint="courses_te",
            menu_icon_type=consts.ICON_TYPE_FONT_AWESOME,
            menu_icon_value="fa fa-edit",
        )
    )
    admin.add_view(
        CourseViewStudents(
            Course,
            db.session,
            name="רשימת קורסים",
            endpoint="courses_st",
            menu_icon_type=consts.ICON_TYPE_FONT_AWESOME,
        )
    )

    admin.add_view(
        MyCourseViewStudents(
            Course,
            db.session,
            name="הקורסים שלי",
            endpoint="my_courses_st",
            menu_icon_type=consts.ICON_TYPE_FONT_AWESOME,
        )
    )

    admin.add_view(
        CategoryView(
            Category,
            db.session,
            name="קטגוריות",
            category="ניהול",
            endpoint="category",
            menu_icon_type=consts.ICON_TYPE_FONT_AWESOME,
            menu_icon_value="fa fa-edit",
        )
    )

    admin.add_view(
        UserView(
            User,
            db.session,
            name="משתמשים",
            category="ניהול",
            endpoint="users"
        )
    )

    admin.add_view(
        CourseRegistrationView(
            Course,
            db.session,
            name="רישום",
            endpoint="c_reg"
        )
    )

    admin.add_view(TimeTableView(
        TimeTable,
        db.session,
        name="מערכות",
        category="ניהול",
        endpoint="ttable"
    ))



class AdminView(sqla.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated and is_teacher(
            login.current_user.email
        )

class CourseView(sqla.ModelView):
    column_labels = dict(
        teacher="מורה",
        name="שם",
        category="קטגוריה",
        week_day="יום בשבוע",
        capacity="מכסת משתתפים",
        left="מקומות פנויים",
        day_slot="שעה"
    )
    column_formatters = {
        # "last_active": _last_active,
        "day_slot": lambda v, c, m, p: get_day_slot_repr(m.day_slot)
    }

class StudentView(sqla.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated and is_teacher(
            login.current_user.email
        )
    can_create = False
    can_edit = False
    can_delete = False

class UserView(AdminView):
    column_labels = dict(
        teachers="Courses as a teacher",
        courses="Courses as a student"
    )

class CourseViewTeachers(AdminView):
    column_list = ["name", "teacher", "category", "capacity"]

class CourseViewStudents(StudentView, CourseView):
    column_list = ["name", "category", "teacher", "week_day", "day_slot", "capacity", "remain_capacity"]
    list_template = "courses_students_list.html"



    def _remain_capacity(self, context, model, name):
        left = get_course_left_places(self.session, model.capacity, model.id)
        return left


    column_formatters = {
        # "last_active": _last_active,
        "remain_capacity": _remain_capacity,
        "day_slot": lambda v, c, m, p: get_day_slot_repr(m.day_slot)
    }

    # def total_enrolled(self, course_id):
    #     # this should take into account any filters/search inplace
    #     return self.session.query(CoursesUsers).filter(CoursesUsers.course_id == course_id).count()
    #
    def render(self, template, **kwargs):
        kwargs["user_ttables"] = get_time_table(self.session)
        return super(CourseViewStudents, self).render(template, **kwargs)

    def get_query(self):
        user_courses_q = self.session.query(CoursesUsers.course_id).filter(CoursesUsers.user_id == current_user.id)

        return (
            self.session.query(Course).filter(Course.id.not_in(user_courses_q))
        )

class MyCourseViewStudents(StudentView, CourseView):
    column_list = ["name", "category", "teacher", "week_day", "day_slot"]

    def get_query(self):
        return (
            self.session.query(Course)
                .filter(Course.id == CoursesUsers.course_id and CoursesUsers.user_id == current_user.id)
        )

    column_formatters = {
        "day_slot": lambda v, c, m, p: get_day_slot_repr(m.day_slot),
    }

    list_template = "my_courses_students_list.html"

    def render(self, template, **kwargs):
        kwargs["user_courses"] = get_user_courses(self.session)
        return super(MyCourseViewStudents, self).render(template, **kwargs)

class CategoryView(AdminView):
    column_list = ["name"]


class CourseRegistrationView(AdminView):
    def is_visible(self):
        return False

    @expose("/")
    def index(self, **kwargs):
        err_msg = ""
        course_id = request.args.get("course_id")
        if not course_id:
            err_msg = "Course Id is missing"
            return err_msg

        course_obj = self.session.query(Course).filter(Course.id == course_id).first()
        course_dict = {"id": course_id, "name": course_obj.name, "description": course_obj.description,
                       "grade": course_obj.grade, "week_day": course_obj.week_day, "capacity": course_obj.capacity,
                       "hours": course_obj.hours, "school_year": course_obj.school_year, "category": course_obj.category.name,
                       "teacher": course_obj.teacher.first_name + " " + course_obj.teacher.last_name,
                       "day_slot": get_day_slot_repr(course_obj.day_slot)}

        places_left = get_course_left_places(self.session, course_obj.capacity, course_id)
        course_dict["current_occ"] = course_obj.capacity - places_left
        course_dict["places_left"] = places_left
        kwargs["email"] = current_user.email
        kwargs["first_name"] = current_user.first_name
        kwargs["last_name"] = current_user.last_name
        kwargs["user_id"] = current_user.id
        kwargs['dir'] = "ltr"
        kwargs["course"] = course_dict

        return self.render("course_registration.html", **kwargs)

class TimeTableView(AdminView):
    pass

def is_teacher(login):
    return login in TEACHERS

def is_student(login):
    return login in STUDENTS

def get_course_left_places(session, capacity, course_id):
    return (capacity or 100) - session.query(CoursesUsers).filter(CoursesUsers.course_id == course_id).count()

def get_time_table(session):
    tt_dicts = []
    tt_records = session.query(TimeTable).filter(TimeTable.user_id == current_user.id).all()
    for tt_rec in tt_records:
        tt_dicts.append({"class_name": tt_rec.class_name,
                         "day_slot": get_day_slot_repr(tt_rec.day_slot),
                         "week_day": tt_rec.week_day})
    return tt_dicts

def get_day_slot_repr(day_slot):
    return DAY_SLOT_REPR.get(str(day_slot), str(day_slot)) if day_slot else ""

def get_user_courses(session):
    user_courses = {}
    user_courses_recs = session.query(CoursesUsers).filter(CoursesUsers.user_id == current_user.id).all()
    for u_c_rec in user_courses_recs:
        seconds_diff = (datetime.datetime.utcnow() - u_c_rec.created_at).total_seconds()
        seconds_left = SECONDS_TO_KEEP_COURSE - seconds_diff
        if seconds_left < 0:
            seconds_left = 0
        user_courses[str(u_c_rec.course_id)] = {"created_at": u_c_rec.created_at,
                                           "time_left": "%s דקות ו%s שניות" % (int(seconds_left/60), int(seconds_left % 60))}
    return user_courses

def delete_expired():
    limit = datetime.datetime.utcnow() - datetime.timedelta(seconds=SECONDS_TO_KEEP_COURSE + 10)
    with pg_conn.session_scope() as session:
        resp = session.query(CoursesUsers).filter(CoursesUsers.status == "open").filter(CoursesUsers.created_at < limit).delete
        if resp > 0:
            log = SysLog(msg="delete expire task response: %s" % resp)
            session.add(log)

