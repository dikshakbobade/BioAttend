
import sys
import os
from sqlalchemy import create_mock_engine
from app.models.models import Base

def dump(sql, *multiparams, **params):
    print(sql.compile(dialect=engine.dialect))

engine = create_mock_engine("mysql+pymysql://", dump)

print("CREATE DATABASE IF NOT EXISTS biometric_attendance;")
print("USE biometric_attendance;")

Base.metadata.create_all(engine)
