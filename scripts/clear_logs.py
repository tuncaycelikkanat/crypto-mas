from sqlalchemy import text

from crypto_mas.infrastructure.db.session import SessionLocal

db = SessionLocal()
db.execute(text("DELETE FROM execution_logs"))
db.commit()
db.close()
print("All execution logs cleared.")
