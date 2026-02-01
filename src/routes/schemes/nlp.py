from pydantic import BaseModel
from typing import Optional


class PushRequest(BaseModel):
    # he still didn't use those fields
    # file_id: str = None
    # text: str = None
    # chunk_size: Optional[int] = 100
    # overlap_size: Optional[int] = 20
    do_reset: Optional[int] = 0
    
class SearchRequest(BaseModel):
    text: str
    limit: Optional[int] = 5
    # query: str
    # top_k: Optional[int] = 5    