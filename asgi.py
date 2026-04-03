from main import app
import os
import sys

project_home = "/home/cprargentina/cPRArgentina"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ["CPRA_DB"] = "cpra.db"
