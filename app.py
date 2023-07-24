import admin
import pg_conn
from flask import Flask


app = Flask(__name__)
app.config.from_pyfile("config.py")
app.config['SQLALCHEMY_DATABASE_URI'] = pg_conn.db_conn_str
# Create dummy secrey key so we can use sessions

if __name__ == '__main__':
    admin.init_admin(app)
    app.run(debug=True)

# See PyCharm help at https://www.jetbrains.com/help/pycharm