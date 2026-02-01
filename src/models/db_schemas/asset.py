from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, Annotated
from datetime import datetime, timezone

# 1. Create a reusable type that converts ObjectId to string automatically
PyObjectId = Annotated[str, BeforeValidator(str)]


class Asset(BaseModel):
    # 2. Use the new type here. It will handle the conversion for you.
    id: Optional[PyObjectId] = Field(None, alias="_id")
    asset_project_id: str
    asset_type: str
    asset_name: str
    asset_size: int
    asset_config: Optional[dict] = None
    asset_pushed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [("asset_project_id", 1)],
                "name": "asset_project_id_index_1",
                "unique": False,
            },
            {
                "key": [("asset_project_id", 1), ("asset_name", 1)],
                "name": "asset_project_id_name_index_1",
                "unique": True,
            },
        ]
