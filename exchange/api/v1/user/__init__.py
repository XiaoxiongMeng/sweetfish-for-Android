from flask import Blueprint

user_page = Blueprint("userpage", __name__)
seller_operation = Blueprint("seller_operation", __name__)
buyer_operation = Blueprint("buyer_operation", __name__)
from . import users, seller_functions, buyer_functions
import pymysql

pymysql.install_as_MySQLdb()
