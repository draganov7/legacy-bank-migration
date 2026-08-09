import os
import duckdb
from dotenv import load_dotenv

load_dotenv()

con = duckdb.connect(os.environ['DUCKDB_PATH'])
con.execute('CALL start_ui()')
input('Press Enter to stop...')