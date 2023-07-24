from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
initialized = False


db_conn_str = "mssql+pymssql://sa:hthpass12!@localhost/hthdb?charset=utf8"
db_engine = None

def execute_sql(query):
    init_schema()
    with db_engine.connect() as con:
        return con.execute(query)



def init_db():
    global initialized
    global db_engine

    if initialized:
        return

    if not db_engine:
        db_engine = create_engine(db_conn_str)

    init_schema()

    initialized = True


def init_schema():
    # if not os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
    # Base.metadata.drop_all(engine)
    try:
        Base.metadata.create_all(db_engine)
    except Exception as exp:
        print(exp)


@contextmanager
def session_scope():
    init_db()
    """Provide a transactional scope around a series of operations."""
    session = scoped_session(sessionmaker(bind=db_engine))
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        db_engine.dispose()
        raise
    finally:
        session.close()
