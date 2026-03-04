from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
import os
from dotenv import load_dotenv
from utils.logger import get_logger
from urllib.parse import quote_plus

load_dotenv()

logger = get_logger("app.database.brisk_engines")


def get_mysql_connection_string(db_name: str, user: str, password: str) -> str:
    """
    Build MySQL connection string using shared host/port.
    
    Args:
        db_name: Database name
        user: Database user
        password: Database password
        
    Returns:
        MySQL connection URL
    """
    host = os.getenv("BRISK_DB_HOST")
    port = os.getenv("MYSQL_PORT", "3306")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"


class BriskEngines:
    """
    Manages dual SQLAlchemy engines for Core and Main Brisk databases.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_engines()
        return cls._instance
    
    def _initialize_engines(self):
        """Initialize both database engines."""
        # Core database engine
        core_db = os.getenv("BRISK_CORE_DB")
        core_user = os.getenv("BRISK_CORE_DB_USER")
        core_password = quote_plus(os.getenv("BRISK_CORE_DB_PASSWORD"))
        
        self._core_url = get_mysql_connection_string(core_db, core_user, core_password)
        self._core_engine = create_engine(
            self._core_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=os.getenv("ENVIRONMENT") == "development"
        )
        self._CoreSession = sessionmaker(autocommit=False, autoflush=False, bind=self._core_engine)
        logger.info(f"Core database engine initialized: {core_db}")
        
        # Main database engine
        main_db = os.getenv("BRISK_MAIN_DB")
        main_user = os.getenv("BRISK_MAIN_DB_USER")
        main_password = quote_plus(os.getenv("BRISK_MAIN_DB_PASSWORD"))
        
        self._main_url = get_mysql_connection_string(main_db, main_user, main_password)
        self._main_engine = create_engine(
            self._main_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=os.getenv("ENVIRONMENT") == "development"
        )
        self._MainSession = sessionmaker(autocommit=False, autoflush=False, bind=self._main_engine)
        logger.info(f"Main database engine initialized: {main_db}")

    @property
    def core_engine(self) -> Engine:
        """Get the Core database engine."""
        return self._core_engine

    @property
    def main_engine(self) -> Engine:
        """Get the Main database engine."""
        return self._main_engine

    def get_core_session(self) -> Session:
        """Create a new Core database session."""
        return self._CoreSession()

    def get_main_session(self) -> Session:
        """Create a new Main database session."""
        return self._MainSession()

    def dispose(self):
        """Dispose both engines and release connections."""
        self._core_engine.dispose()
        self._main_engine.dispose()
        logger.info("Both database engines disposed")


# Singleton instance
brisk_engines = BriskEngines()
