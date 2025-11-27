from settings import settings

# direct connection
conn = settings.connection
cursor = conn.cursor()

cursor.execute("SELECT NOW();")
print(cursor.fetchone())

cursor.close()
conn.close()
