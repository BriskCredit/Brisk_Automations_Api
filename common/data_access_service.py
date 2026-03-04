from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import TypeVar, Generic, Type, Optional, Any
from utils.logger import get_logger

logger = get_logger("app.common.data_access")

T = TypeVar("T")


class DataAccessService(Generic[T]):
    """
    Common Data Access Service providing shared database operations.
    Can be consumed by other services for generic data access patterns.
    """
    
    def __init__(self, db: Session):
        """
        Initialize with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.logger = logger

    def get_by_id(self, model: Type[T], record_id: int) -> Optional[T]:
        """
        Generic get by ID for any model.
        
        Args:
            model: SQLAlchemy model class
            record_id: The ID to look up
            
        Returns:
            The record if found, None otherwise
        """
        return self.db.query(model).filter(model.id == record_id).first()

    def get_all(
        self, 
        model: Type[T], 
        skip: int = 0, 
        limit: int = 100,
        order_by: Optional[Any] = None
    ) -> list[T]:
        """
        Generic get all with pagination.
        
        Args:
            model: SQLAlchemy model class
            skip: Number of records to skip
            limit: Maximum number of records
            order_by: Optional column to order by
            
        Returns:
            List of records
        """
        query = self.db.query(model)
        if order_by is not None:
            query = query.order_by(order_by)
        return query.offset(skip).limit(limit).all()

    def count(self, model: Type[T]) -> int:
        """
        Get total count of records for a model.
        
        Args:
            model: SQLAlchemy model class
            
        Returns:
            Total count
        """
        return self.db.query(model).count()

    def exists(self, model: Type[T], record_id: int) -> bool:
        """
        Check if a record exists.
        
        Args:
            model: SQLAlchemy model class
            record_id: The ID to check
            
        Returns:
            True if exists, False otherwise
        """
        return self.db.query(model).filter(model.id == record_id).first() is not None

    def create(self, record: T) -> T:
        """
        Generic create operation.
        
        Args:
            record: The model instance to create
            
        Returns:
            The created record with ID
        """
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update(self, record: T) -> T:
        """
        Generic update operation (assumes record is already in session).
        
        Args:
            record: The model instance to update
            
        Returns:
            The updated record
        """
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete(self, record: T) -> bool:
        """
        Generic delete operation.
        
        Args:
            record: The model instance to delete
            
        Returns:
            True if deleted
        """
        self.db.delete(record)
        self.db.commit()
        return True

    def delete_by_id(self, model: Type[T], record_id: int) -> bool:
        """
        Delete a record by ID.
        
        Args:
            model: SQLAlchemy model class
            record_id: The ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        record = self.get_by_id(model, record_id)
        if not record:
            return False
        return self.delete(record)

    def filter_by(self, model: Type[T], **filters) -> list[T]:
        """
        Filter records by column values.
        
        Args:
            model: SQLAlchemy model class
            **filters: Column=value pairs to filter by
            
        Returns:
            List of matching records
        """
        query = self.db.query(model)
        for column, value in filters.items():
            if hasattr(model, column):
                query = query.filter(getattr(model, column) == value)
        return query.all()

    def first_by(self, model: Type[T], **filters) -> Optional[T]:
        """
        Get first record matching filters.
        
        Args:
            model: SQLAlchemy model class
            **filters: Column=value pairs to filter by
            
        Returns:
            First matching record or None
        """
        results = self.filter_by(model, **filters)
        return results[0] if results else None

    def bulk_create(self, records: list[T]) -> list[T]:
        """
        Create multiple records in one transaction.
        
        Args:
            records: List of model instances to create
            
        Returns:
            List of created records
        """
        self.db.add_all(records)
        self.db.commit()
        for record in records:
            self.db.refresh(record)
        return records

    def execute_raw(self, query: str, params: Optional[dict] = None) -> Any:
        """
        Execute raw SQL query.
        
        Args:
            query: Raw SQL string
            params: Optional parameters for the query
            
        Returns:
            Query result
        """
        result = self.db.execute(query, params or {})
        self.db.commit()
        return result
