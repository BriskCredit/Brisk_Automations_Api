import pandas as pd
from sqlalchemy.engine import Engine
from utils.logger import get_logger

logger = get_logger("app.common.brisk_data")


class BriskDataService:
    """
    Shared data access service for Brisk databases.
    Provides reusable methods for fetching common data from briskc_defined and briskc_core.
    Uses lazy loading and caching for efficiency.
    """
    
    def __init__(self, main_engine: Engine, core_engine: Engine):
        """
        Initialize with database engines.
        
        Args:
            main_engine: SQLAlchemy engine for main database (briskc_defined)
            core_engine: SQLAlchemy engine for core database (briskc_core)
        """
        self._main_engine = main_engine
        self._core_engine = core_engine
        
        # Cache for lazy-loaded data
        self._clients_cache = None
        self._branches_cache = None
        self._staff_cache = None
    
    # ==================== Cached Properties ====================
    
    @property
    def clients(self) -> pd.DataFrame:
        """Lazy load and cache clients data."""
        if self._clients_cache is None:
            query = "SELECT id, idno FROM org1_clients;"
            self._clients_cache = pd.read_sql(query, self._main_engine)
            logger.debug(f"Loaded {len(self._clients_cache)} clients")
        return self._clients_cache
    
    @property
    def branches(self) -> pd.DataFrame:
        """Lazy load and cache branches data."""
        if self._branches_cache is None:
            query = "SELECT branch, id FROM branches WHERE client = 1;"
            self._branches_cache = pd.read_sql(query, self._core_engine)
            logger.debug(f"Loaded {len(self._branches_cache)} branches")
        return self._branches_cache
    
    @property
    def staff(self) -> pd.DataFrame:
        """Lazy load and cache staff data."""
        if self._staff_cache is None:
            query = "SELECT id, name FROM org1_staff;"
            self._staff_cache = pd.read_sql(query, self._main_engine)
            logger.debug(f"Loaded {len(self._staff_cache)} staff members")
        return self._staff_cache
    
    # ==================== Loan Methods ====================
    
    def get_loans_by_days_ago(self, days: int) -> pd.DataFrame:
        """
        Fetch loans disbursed exactly X days ago.
        
        Args:
            days: Number of days ago (e.g., 7, 14, 21)
            
        Returns:
            DataFrame with loan data
        """
        query = f"""
        SELECT 
            id as loan_id,
            client,
            client_idno,
            branch,
            loan_officer,
            amount,
            balance,
            disbursement
        FROM org1_loans
        WHERE disbursement >= UNIX_TIMESTAMP(CURDATE() - INTERVAL {days} DAY)
        AND disbursement < UNIX_TIMESTAMP(CURDATE() - INTERVAL {days - 1} DAY);
        """
        result = pd.read_sql(query, self._main_engine)
        logger.debug(f"Fetched {len(result)} loans from {days} days ago")
        return result
    
    def get_active_loans(self) -> pd.DataFrame:
        """Fetch all active loans (balance > 0)."""
        query = """
        SELECT 
            id as loan_id,
            client,
            client_idno,
            branch,
            loan_officer,
            amount,
            balance,
            disbursement
        FROM org1_loans
        WHERE balance > 0;
        """
        return pd.read_sql(query, self._main_engine)
    
    # ==================== Interaction Methods ====================
    
    def get_todays_interactions(self, interaction_type: str) -> pd.DataFrame:
        """
        Fetch all today's interactions of a specific type.
        
        Args:
            interaction_type: The type of interaction (e.g., 'Customer visit, D7')
            
        Returns:
            DataFrame with interaction data
        """
        query = f"""
        SELECT client, type
        FROM interactions1
        WHERE type='{interaction_type}' AND DATE(FROM_UNIXTIME(time)) = CURDATE();
        """
        result = pd.read_sql(query, self._main_engine)
        logger.debug(f"Fetched {len(result)} '{interaction_type}' interactions for today")
        return result
    
    def get_call_dialer_interactions_by_days(self, days: int) -> pd.DataFrame:
        """
        Fetch most recent call dialer interactions starting from day after disbursement.
        For loans disbursed X days ago, fetch interactions from (X-1) days ago onwards.
        
        Args:
            days: Number of days ago the loan was disbursed
            
        Returns:
            DataFrame with client, type, and time columns
        """
        interaction_start = days - 1  # Day after disbursement
        query = f"""
        SELECT i.client, i.type, i.time
        FROM interactions1 i
        INNER JOIN (
            SELECT client, MAX(time) as max_time
            FROM interactions1
            WHERE type='call dialer'
              AND time >= UNIX_TIMESTAMP(CURDATE() - INTERVAL {interaction_start} DAY)
            GROUP BY client
        ) latest ON i.client = latest.client AND i.time = latest.max_time
        WHERE i.type='call dialer';
        """
        result = pd.read_sql(query, self._main_engine)
        logger.debug(f"Fetched {len(result)} call dialer interactions (from {interaction_start} days ago)")
        return result
    
    def get_interactions_by_date_range(
        self, 
        interaction_type: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        Fetch interactions within a date range.
        
        Args:
            interaction_type: Type of interaction
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            
        Returns:
            DataFrame with interaction data
        """
        query = f"""
        SELECT client, type, time
        FROM interactions1
        WHERE type='{interaction_type}' 
        AND DATE(FROM_UNIXTIME(time)) BETWEEN '{start_date}' AND '{end_date}';
        """
        return pd.read_sql(query, self._main_engine)
    
    # ==================== Client Methods ====================
    
    def get_client_by_idno(self, idno: str) -> pd.DataFrame:
        """Fetch client by ID number."""
        query = f"SELECT * FROM org1_clients WHERE idno = '{idno}';"
        return pd.read_sql(query, self._main_engine)
    
    def get_clients_by_branch(self, branch_id: int) -> pd.DataFrame:
        """Fetch all clients in a branch."""
        query = f"SELECT * FROM org1_clients WHERE branch = {branch_id};"
        return pd.read_sql(query, self._main_engine)
    
    # ==================== Utility Methods ====================
    
    def clear_cache(self):
        """Clear all cached data. Useful for long-running processes."""
        self._clients_cache = None
        self._branches_cache = None
        self._staff_cache = None
        logger.debug("Cache cleared")
    
    def execute_query(self, query: str, use_core: bool = False) -> pd.DataFrame:
        """
        Execute a custom SQL query.
        
        Args:
            query: SQL query string
            use_core: If True, use core engine; otherwise use main engine
            
        Returns:
            DataFrame with query results
        """
        engine = self._core_engine if use_core else self._main_engine
        return pd.read_sql(query, engine)
