from unittest import result
from .BaseDataModel import BaseDataModel
from .db_schemas import DataChunk
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from pymongo import InsertOne


class ChunkModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_CHUNK_NAME.value]

    @classmethod
    async def create_instance(cls, db_client: object):
        # 1. ask class to call init function
        instance = cls(db_client)
        # 2. ask class to call initialize_collection function
        await instance.initialize_collection()
        # 3. return instance object with combined functions
        return instance

    async def initialize_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.COLLECTION_CHUNK_NAME.value not in all_collections:
            self.collection = self.db_client[DataBaseEnum.COLLECTION_CHUNK_NAME.value]
            indexes = DataChunk.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"], name=index["name"], unique=index["unique"]
                )

    # Create a new chunk
    async def create_chunk(self, chunk: DataChunk) -> DataChunk:

        result = await self.collection.insert_one(
            chunk.model_dump(by_alias=True, exclude_unset=True)
        )
        return result.inserted_id

    # Get Chunks by file_id
    async def get_chunk(self, chunk_id: str):
        result = await self.collection.find_one({"_id": ObjectId(chunk_id)})

        if result is None:
            return None

        return DataChunk(**result)

    # Bulk insert many chunks
    async def insert_many_chunks(self, chunks: list, batch_size: int = 100):

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            operations = [
                InsertOne(chunk.model_dump(by_alias=True, exclude_unset=True))
                for chunk in batch
            ]
            await self.collection.bulk_write(operations)
        return len(chunks)

    # Delete chunks by project_id
    async def delete_chunks_by_project_id(self, project_id: str):
        result = await self.collection.delete_many({"chunk_project_id": project_id})
        return result.deleted_count

    # Get Project Chunks by project_id
    async def get_chunks_by_project_id(
        self, project_id: str, page_no: int = 1, page_size: int = 50
    ):
        records = (
            await self.collection.find({"chunk_project_id": project_id})
            .skip((page_no - 1) * page_size)
            .limit(page_size)
            .to_list(length=None)
        )
        return [DataChunk(**record) for record in records]
