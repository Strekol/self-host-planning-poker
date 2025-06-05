#!/usr/bin/env python3
"""
Database configuration checker for Planning Poker.
This script helps validate database configuration and connectivity.
"""

import sys
import os
import logging

# Add the flask directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'flask'))

def main():
    """Main function to check database configuration"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        from database_config import get_database, validate_database_connection, get_database_info
        from gamestate.models import database_proxy, StoredGame
        
        logger.info("=== Planning Poker Database Configuration Check ===")
        
        # Show current configuration
        logger.info(f"Database configuration: {get_database_info()}")
        
        # Get database instance
        database = get_database()
        logger.info(f"Database type: {type(database).__name__}")
        
        # Initialize the database proxy
        database_proxy.initialize(database)
        
        # Test connection
        logger.info("Testing database connection...")
        if validate_database_connection(database):
            logger.info("✅ Database connection successful!")
        else:
            logger.error("❌ Database connection failed!")
            return 1
        
        # Test table creation
        logger.info("Testing table creation...")
        try:
            StoredGame.create_table(safe=True)
            logger.info("✅ Tables created/verified successfully!")
        except Exception as e:
            logger.error(f"❌ Table creation failed: {e}")
            return 1
        
        # Test basic operations
        logger.info("Testing basic database operations...")
        try:
            # Try to count existing games
            count = StoredGame.select().count()
            logger.info(f"✅ Current number of stored games: {count}")
        except Exception as e:
            logger.error(f"❌ Database query failed: {e}")
            return 1
        
        logger.info("🎉 All database checks passed successfully!")
        
        # Show environment variables being used
        logger.info("\n=== Environment Variables ===")
        env_vars = [
            'DATABASE_URL', 'DATABASE_TYPE', 'DATABASE_HOST', 'DATABASE_PORT',
            'DATABASE_NAME', 'DATABASE_USER', 'DATABASE_SSL_MODE', 'DATABASE_CHARSET',
            'DATABASE_PATH', 'FLASK_DEBUG'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                # Mask password in URL
                if var == 'DATABASE_URL' and '://' in value:
                    # Hide password in URL
                    parts = value.split('://')
                    if '@' in parts[1]:
                        auth_part, host_part = parts[1].split('@', 1)
                        if ':' in auth_part:
                            user, _ = auth_part.split(':', 1)
                            masked_value = f"{parts[0]}://{user}:***@{host_part}"
                        else:
                            masked_value = value
                    else:
                        masked_value = value
                    logger.info(f"  {var}={masked_value}")
                else:
                    logger.info(f"  {var}={value}")
        
        return 0
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure you're running this script from the project root directory")
        logger.error("and that all dependencies are installed (pip install -r flask/requirements.txt)")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
