#!/usr/bin/env python3
"""
Script to fix all PostgreSQL sequence values to match their table data.
This prevents "duplicate key value" errors.
"""

import sys
import subprocess
import os
from typing import List, Tuple

def get_db_config():
    """Get database configuration from environment or use defaults."""
    return {
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'database': os.getenv('POSTGRES_DB', 'alem'),
        'container': 'tabys_postgres_1'
    }

def run_psql_command(container: str, user: str, database: str, sql: str) -> Tuple[bool, str]:
    """Execute a PostgreSQL command via docker exec."""
    cmd = [
        'docker', 'exec', '-i', container,
        'psql', '-U', user, '-d', database, '-c', sql
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def get_all_sequences(container: str, user: str, database: str) -> List[str]:
    """Get all sequence names from the database."""
    sql = """
    SELECT sequence_name 
    FROM information_schema.sequences 
    WHERE sequence_schema = 'public';
    """
    
    success, output = run_psql_command(container, user, database, sql)
    if not success:
        print(f"Error getting sequences: {output}")
        return []
    
    # Parse sequence names from output
    sequences = []
    lines = output.strip().split('\n')
    for line in lines[2:-2]:  # Skip header and footer
        seq_name = line.strip()
        if seq_name and not seq_name.startswith('-'):
            sequences.append(seq_name)
    
    return sequences

def fix_sequence(container: str, user: str, database: str, sequence_name: str) -> bool:
    """Fix a single sequence by resetting it to MAX(id) of its table."""
    # Extract table name from sequence name (usually tablename_id_seq)
    table_name = sequence_name.replace('_id_seq', '')
    
    sql = f"""
    SELECT setval('{sequence_name}', 
                  COALESCE((SELECT MAX(id) FROM {table_name}), 1), 
                  true);
    """
    
    success, output = run_psql_command(container, user, database, sql)
    if success:
        print(f"✓ Fixed {sequence_name}: {output.strip()}")
        return True
    else:
        print(f"✗ Failed to fix {sequence_name}: {output}")
        return False

def main():
    print("=" * 60)
    print("PostgreSQL Sequence Repair Tool")
    print("=" * 60)
    
    config = get_db_config()
    print(f"\nDatabase: {config['database']}")
    print(f"Container: {config['container']}")
    print(f"User: {config['user']}\n")
    
    # Get all sequences
    print("Finding all sequences...")
    sequences = get_all_sequences(config['container'], config['user'], config['database'])
    
    if not sequences:
        print("No sequences found or error occurred.")
        sys.exit(1)
    
    print(f"Found {len(sequences)} sequences\n")
    
    # Fix each sequence
    fixed = 0
    failed = 0
    
    for seq in sequences:
        if fix_sequence(config['container'], config['user'], config['database'], seq):
            fixed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {fixed} fixed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
