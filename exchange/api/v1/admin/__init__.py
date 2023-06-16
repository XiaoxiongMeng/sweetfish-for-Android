from flask import Blueprint

admin_operation = Blueprint("admin_operation", __name__)
from . import admin_functions
import pymysql

pymysql.install_as_MySQLdb()
