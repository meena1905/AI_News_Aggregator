import psycopg

conn = psycopg.connect('postgresql://postgres.ksyjoltnijdrwejhwsal:Meena%4012322@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()

MY_EMAIL = 'meenakshis3019@gmail.com'

cur.execute(
    "DELETE FROM digests WHERE user_id IN (SELECT user_id FROM users WHERE email != %s)",
    (MY_EMAIL,)
)
print(f"Deleted {cur.rowcount} digest(s)")

cur.execute("DELETE FROM users WHERE email != %s", (MY_EMAIL,))
print(f"Deleted {cur.rowcount} user(s)")

conn.commit()
print("Done — your account was kept, everyone else removed.")