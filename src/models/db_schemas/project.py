from pydantic import BaseModel, Field, field_validator
from typing import Optional
from bson.objectid import ObjectId


class Project(BaseModel):
    _id: Optional[ObjectId]
    project_id: str = Field(..., min_length=1)

    # Custom validator to ensure project_id is alphanumeric
    @field_validator("project_id")
    def validate_project_id(cls, value: str) -> str:
        if not value.isalnum():
            raise ValueError("project_id must be alphanumeric")
        return value
    
    class Config:
        arbitrary_types_allowed = True
  
    @classmethod
    def get_indexes(cls):
        return [
            {
               "key": [
                   ("project_id", 1)
                   ],
               "name": "project_id_index_1",
               "unique": True
            }
        ]