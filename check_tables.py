import psycopg

conn = psycopg.connect('postgresql://postgres.ksyjoltnijdrwejhwsal:Meena%4012322@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
print(cur.fetchall())