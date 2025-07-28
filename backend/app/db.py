import os
from flask import Flask
from dotenv import load_dotenv
import pymysql
from google.cloud.sql.connector import Connector

# load enviornment vars from .env file
load_dotenv()

app = Flask(__name__)

# Load database connection details from enviornment vars
instance_connection_name = os.environ[
        "INSTANCE_CONNECTION_NAME"
    ]  # e.g. 'project:region:instance'
db_user = os.environ["DB_USER"]  # e.g. 'my-db-user'
db_pass = os.environ["DB_PASS"]  # e.g. 'my-db-password'
db_name = os.environ["DB_NAME"]  # e.g. 'my-database'

# Initialize the Cloud SQL Connector
connector = Connector()

# Connect to the database 
def getconn() -> pymysql.connections.Connection:
    conn: pymysql.connections.Connection = connector.connect(
        instance_connection_name,
        "pymysql",
        user=db_user,
        password=db_pass,
        db=db_name,
    )
    return conn