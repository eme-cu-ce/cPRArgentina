import sqlite3
import os
from datetime import date

DB_NAME = "cpra_demo.db"

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE donors (
    donor_id TEXT PRIMARY KEY,
    sexo TEXT,
    edad TEXT,
    fecha_operativo TEXT,
    A1 TEXT,
    A2 TEXT,
    B1 TEXT,
    B2 TEXT,
    DRB1_1 TEXT,
    DRB1_2 TEXT,
    DQB1_1 TEXT,
    DQB1_2 TEXT,
    abo TEXT,
    rh TEXT
)
""")

donors_data = [
    ("1","M","45","2025-01-01","A1","A2","B8","B44","DR4","DR7","DQ2","DQ5","A","+"),
    ("2","F","38","2025-01-02","A3","A11","B35","B44","DR1","DR15","DQ5","DQ6","O","+"),
    ("3","M","52","2025-01-03","A2","A24","B7","B60","DR4","DR13","DQ7","DQ6","B","-"),
    ("4","F","29","2025-01-04","A1","A3","B8","B51","DR17","DR7","DQ2","DQ9","AB","+"),
    ("5","M","61","2025-01-05","A2","A30","B44","B62","DR11","DR4","DQ7","DQ7","A","+"),
    ("6","F","47","2025-01-06","A1","A26","B18","B35","DR7","DR15","DQ2","DQ6","O","-"),
    ("7","M","34","2025-01-07","A24","A29","B7","B8","DR4","DR13","DQ9","DQ6","B","+"),
    ("8","F","41","2025-01-08","A2","A68","B44","B57","DR18","DR4","DQ5","DQ8","A","+"),
    ("9","M","55","2025-01-09","A1","A2","B35","B44","DR7","DR11","DQ2","DQ7","O","+"),
    ("10","F","36","2025-01-10","A3","A23","B7","B8","DR4","DR3","DQ8","DQ2","AB","-"),
    ("11","M","49","2025-01-11","A11","A24","B60","B62","DR13","DR15","DQ6","DQ5","A","+"),
    ("12","F","43","2025-01-12","A2","A26","B18","B51","DR7","DR4","DQ2","DQ2","O","+"),
    ("13","M","58","2025-01-13","A1","A30","B8","B44","DR17","DR11","DQ2","DQ7","B","+"),
    ("14","F","40","2025-01-14","A24","A29","B7","B35","DR13","DR15","DQ6","DQ5","A","-"),
    ("15","M","33","2025-01-15","A2","A3","B44","B57","DR4","DR7","DQ8","DQ2","O","+"),
    ("16","F","50","2025-01-16","A1","A68","B8","B60","DR17","DR4","DQ2","DQ8","AB","+"),
    ("17","M","44","2025-01-17","A11","A23","B35","B62","DR1","DR15","DQ5","DQ6","A","+"),
    ("18","F","37","2025-01-18","A2","A24","B7","B18","DR4","DR13","DQ8","DQ6","O","+"),
    ("19","M","53","2025-01-19","A1","A26","B8","B44","DR7","DR11","DQ2","DQ7","B","+"),
    ("20","F","42","2025-01-20","A3","A29","B35","B51","DR13","DR15","DQ6","DQ5","A","+"),
    ("21","M","39","2025-01-21","A2","A11","B7","B44","DR4","DR15","DQ8","DQ6","O","+"),
    ("22","F","46","2025-01-22","A1","A24","B8","B62","DR17","DR7","DQ2","DQ9","A","+"),
    ("23","M","48","2025-01-23","A3","A30","B35","B60","DR11","DR13","DQ7","DQ6","B","+"),
    ("24","F","35","2025-01-24","A2","A68","B44","B57","DR4","DR11","DQ8","DQ7","O","+"),
    ("25","M","60","2025-01-25","A1","A23","B8","B51","DR17","DR15","DQ2","DQ6","AB","+"),
]

cursor.executemany("""
INSERT INTO donors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", donors_data)

conn.commit()
conn.close()

# Keep this ASCII-only to avoid Windows cp1252 console encoding issues.
print("cpra_demo.db created successfully with 25 synthetic donors.")
