from datetime import datetime, timezone
from typing import Any
import uuid
import inflect
from pydantic import ConfigDict
from sqlmodel import SQLModel
import re
from sqlalchemy.orm.attributes import InstrumentedAttribute


# Initialize the inflect engine for pluralization
p = inflect.engine()

def to_snake_case(name: str) -> str:
    """Convert CamelCase or PascalCase to snake_case."""
    # Insert underscores before uppercase letters and convert to lowercase
    s1 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return s1.replace(" ", "_").lower()
# Create a custom base class that automatically pluralizes the table name
class MySQLModel(SQLModel):
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Convert the class name to snake_case and pluralize it
        table_name = to_snake_case(cls.__name__)
        cls.__tablename__ = p.plural(table_name)  # type: ignore
    
    def to_json(self, exclude: list[str] | None = ['password'], only: list[str] | set[str] | None = None) -> dict:
        """Custom JSON serialization with recursive processing."""
        exclude = exclude or []
        only = only or list(self.__fields__.keys())

        def process_value(value: Any) -> Any:
            """Recursively process values for serialization."""
            if isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, uuid.UUID):
                return str(value)
            elif isinstance(value, list):
                return [process_value(item) for item in value]
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif isinstance(value, InstrumentedAttribute):
                return None  # Skip non-serializable relationships
            elif isinstance(value, MySQLModel):
                return value.to_json()  # Serialize nested SQLModel instances
            return value

        # Process instance dictionary
        data = {k: process_value(v) for k, v in self.__dict__.items() if k not in exclude and k in only}

        # Remove SQLAlchemy's internal state
        data.pop('_sa_instance_state', None)
        return data
    
    # Custom configuration for automatic serialization
    model_config = ConfigDict(  # type: ignore
        json_encoders={
            # Automatically convert datetime to ISO format (UTC by default)
            datetime: lambda v: v.astimezone(timezone.utc).isoformat() if v else None,
            uuid.UUID: lambda v: str(v),  # Convert UUID to string
        },
        extra='ignore',
        arbitrary_types_allowed=True
    )