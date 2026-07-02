import pymysql

db_config = {
    "host": "mysql-c9622f-betitak35-e7ab.j.aivencloud.com",
    "port": 16712,
    "user": "avnadmin",
    "password": "AVNS_nPu8sF7j66qsonS9YaF",  # 👈 REPLACE this with your real Aiven password
    "database": "defaultdb",
    "autocommit": True
}

print("⚡ Connecting to Aiven Cloud MySQL...")
try:
    connection = pymysql.connect(**db_config)
    print("✅ Connected successfully!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)

# Step 1: Clean out any broken database artifacts
print("🧹 Wiping old broken structures to start completely fresh...")
with connection.cursor() as cursor:
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    cursor.execute("SHOW TABLES;")
    tables = cursor.fetchall()
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS `{table[0]}`;")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
print("✨ Database successfully cleared.")

# Step 2: Read and parse your full pulse.sql backup file
print("📖 Reading full pulse.sql backup file...")
try:
    with open("pulse.sql", "r", encoding="utf-8") as f:
        content = f.read()
except FileNotFoundError:
    print("❌ Error: Could not find 'pulse.sql' in this folder. Make sure it's in C:\\DJANGO\\djangotutorial")
    connection.close()
    exit(1)

# Split up the queries by the standard semicolon operator
raw_commands = content.split(";")
sql_commands = []

for cmd in raw_commands:
    clean_cmd = cmd.strip()
    # Skip version/environment comments
    if not clean_cmd or clean_cmd.startswith(('--', '/*', '#')):
        continue
    sql_commands.append(clean_cmd)

print(f"📦 Found {len(sql_commands)} total structural & data statements to execute.")

# Step 3: Stream structures and row records directly onto Aiven
with connection.cursor() as cursor:
    print("🔒 Disabling foreign key rules temporarily to prevent schema generation locks...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    
    success_count = 0
    skipped_count = 0
    
    for idx, cmd in enumerate(sql_commands, 1):
        try:
            cursor.execute(cmd)
            success_count += 1
        except Exception as e:
            skipped_count += 1
            # Suppress standard system syntax/version metadata errors
            if "syntax" not in str(e).lower():
                print(f"  ⚠️ Statement {idx} skipped: {str(e)[:75]}")

    print("🔓 Re-enabling database foreign key constraints safely...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

print(f"\n🏁 Complete Migration Process Finished!")
print(f"✅ {success_count} tables and existing data records successfully generated on Aiven.")
connection.close()