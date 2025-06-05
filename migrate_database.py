#!/usr/bin/env python3
"""
Database migration utility for Planning Poker.
This script helps migrate data from SQLite to external databases.
"""

import sys
import os
import logging
import json
from datetime import datetime

# Add the flask directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'flask'))

def export_sqlite_data(sqlite_path):
    """Export data from SQLite database to JSON format"""
    from peewee import SqliteDatabase
    from gamestate.models import StoredGame, database_proxy
    
    logger = logging.getLogger(__name__)
    
    # Connect to SQLite database
    sqlite_db = SqliteDatabase(sqlite_path)
    database_proxy.initialize(sqlite_db)
    
    if database_proxy.is_closed():
        database_proxy.connect()
    
    # Export data
    games = []
    try:
        for game in StoredGame.select():
            games.append({
                'uuid': str(game.uuid),
                'name': game.name,
                'deck': game.deck
            })
        logger.info(f"Exported {len(games)} games from SQLite")
        return games
    except Exception as e:
        logger.error(f"Failed to export from SQLite: {e}")
        return None

def import_data_to_target(games_data):
    """Import data to the target database configured via environment variables"""
    from database_config import get_database, validate_database_connection
    from gamestate.models import StoredGame, database_proxy
    import uuid
    
    logger = logging.getLogger(__name__)
    
    # Get target database
    target_db = get_database()
    database_proxy.initialize(target_db)
    
    if not validate_database_connection(target_db):
        logger.error("Cannot connect to target database")
        return False
    
    # Create tables
    StoredGame.create_table(safe=True)
    
    # Import data
    success_count = 0
    for game_data in games_data:
        try:
            StoredGame.create(
                uuid=uuid.UUID(game_data['uuid']),
                name=game_data['name'],
                deck=game_data['deck']
            )
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to import game {game_data['uuid']}: {e}")
    
    logger.info(f"Successfully imported {success_count}/{len(games_data)} games")
    return success_count == len(games_data)

def backup_to_file(games_data, filename=None):
    """Backup games data to JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"planning_poker_backup_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(games_data, f, indent=2)
    
    logging.getLogger(__name__).info(f"Backup saved to {filename}")
    return filename

def restore_from_file(filename):
    """Restore games data from JSON file"""
    try:
        with open(filename, 'r') as f:
            games_data = json.load(f)
        logging.getLogger(__name__).info(f"Loaded {len(games_data)} games from {filename}")
        return games_data
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to load backup file: {e}")
        return None

def main():
    """Main migration function"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Export from SQLite to JSON:")
        print("    python migrate_database.py export <sqlite_file> [output.json]")
        print("  Import from JSON to target database:")
        print("    python migrate_database.py import <backup.json>")
        print("  Migrate directly from SQLite to target:")
        print("    python migrate_database.py migrate <sqlite_file>")
        print("  Backup current database to JSON:")
        print("    python migrate_database.py backup [output.json]")
        return 1
    
    command = sys.argv[1].lower()
    
    try:
        if command == "export":
            if len(sys.argv) < 3:
                logger.error("SQLite file path required")
                return 1
            
            sqlite_path = sys.argv[2]
            output_file = sys.argv[3] if len(sys.argv) > 3 else None
            
            games_data = export_sqlite_data(sqlite_path)
            if games_data is not None:
                backup_to_file(games_data, output_file)
                logger.info("Export completed successfully")
                return 0
            else:
                return 1
        
        elif command == "import":
            if len(sys.argv) < 3:
                logger.error("Backup JSON file path required")
                return 1
            
            backup_file = sys.argv[2]
            games_data = restore_from_file(backup_file)
            if games_data and import_data_to_target(games_data):
                logger.info("Import completed successfully")
                return 0
            else:
                return 1
        
        elif command == "migrate":
            if len(sys.argv) < 3:
                logger.error("SQLite file path required")
                return 1
            
            sqlite_path = sys.argv[2]
            
            # Export from SQLite
            logger.info("Exporting from SQLite...")
            games_data = export_sqlite_data(sqlite_path)
            if games_data is None:
                return 1
            
            # Create backup first
            backup_file = backup_to_file(games_data)
            logger.info(f"Backup created: {backup_file}")
            
            # Import to target
            logger.info("Importing to target database...")
            if import_data_to_target(games_data):
                logger.info("Migration completed successfully")
                return 0
            else:
                logger.error("Migration failed")
                return 1
        
        elif command == "backup":
            from database_config import get_database, validate_database_connection
            from gamestate.models import StoredGame, database_proxy
            
            output_file = sys.argv[2] if len(sys.argv) > 2 else None
            
            # Connect to current database
            current_db = get_database()
            database_proxy.initialize(current_db)
            
            if not validate_database_connection(current_db):
                logger.error("Cannot connect to current database")
                return 1
            
            # Export data
            games = []
            for game in StoredGame.select():
                games.append({
                    'uuid': str(game.uuid),
                    'name': game.name,
                    'deck': game.deck
                })
            
            backup_file = backup_to_file(games, output_file)
            logger.info(f"Backup completed: {len(games)} games saved to {backup_file}")
            return 0
        
        else:
            logger.error(f"Unknown command: {command}")
            return 1
            
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure all dependencies are installed")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
