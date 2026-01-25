"""
Force migration by temporarily using a copy
This works even if the backend is running
"""
import sqlite3
import shutil
import os

def force_migrate():
    db_path = 'trading_bot.db'
    backup_path = 'trading_bot.db.backup'
    
    # Check if DB is locked
    try:
        conn = sqlite3.connect(db_path, timeout=1.0)
        conn.close()
        print("DB is accessible. Proceeding with migration...")
    except sqlite3.OperationalError:
        print("ERROR: Database is locked!")
        print("\nPlease stop the backend server first:")
        print("  1. Press Ctrl+C in the terminal running uvicorn")
        print("  2. Run this script again")
        print("  3. Restart the backend")
        return False
    
    # Create backup
    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    # Migrate
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    columns_to_add = [
        ("roi", "FLOAT NULL"),
        ("entry_time", "DATETIME NULL"),
        ("exit_time", "DATETIME NULL"),
        ("status", "VARCHAR DEFAULT 'CLOSED'")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added '{col_name}' column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"○ '{col_name}' already exists")
            else:
                print(f"✗ Failed to add '{col_name}': {e}")
    
    conn.commit()
    
    # Verify
    cursor.execute('PRAGMA table_info(trades)')
    columns = [row[1] for row in cursor.fetchall()]
    
    print("\n" + "="*60)
    print("MIGRATION COMPLETE!")
    print("="*60)
    print("\nTrades table columns:")
    for i, col in enumerate(columns, 1):
        marker = "🆕" if col in ['roi', 'entry_time', 'exit_time', 'status'] else "  "
        print(f"{marker} {i:2d}. {col}")
    
    new_cols = ['roi', 'entry_time', 'exit_time', 'status']
    missing = [col for col in new_cols if col not in columns]
    
    if missing:
        print(f"\n⚠️  WARNING: Missing columns: {missing}")
        print(f"✓ Backup saved at: {backup_path}")
        conn.close()
        return False
    else:
        print("\n✅ SUCCESS! All new columns added!")
        print(f"✓ Backup saved at: {backup_path}")
        print("\n📋 Next steps:")
        print("  1. The database is ready")
        print("  2. Restart the backend server (Ctrl+C, then restart)")
        print("  3. Test: GET http://localhost:8000/api/history/trades?limit=5")
        conn.close()
        return True

if __name__ == "__main__":
    print("="*60)
    print("TRADES TABLE MIGRATION TOOL")
    print("="*60)
    print()
    success = force_migrate()
    print("\n" + "="*60)
    if success:
        print("✅ MIGRATION SUCCESSFUL!")
    else:
        print("⚠️  MIGRATION INCOMPLETE - Check errors above")
    print("="*60)
