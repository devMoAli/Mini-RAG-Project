from .BaseDataModel import BaseDataModel
from .db_schemas import Asset
from .enums.DataBaseEnum import DataBaseEnum


class AssetModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_ASSET_NAME.value]

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
        # Use .value here to get the actual string "assets"
        collection_name = DataBaseEnum.COLLECTION_ASSET_NAME.value

        if collection_name not in all_collections:
            # This creates the collection implicitly
            self.collection = self.db_client[collection_name]
            indexes = Asset.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"], name=index["name"], unique=index["unique"]
                )

    # Create a new asset
    async def create_asset(self, asset: Asset):
        # 1. Convert to dict using the alias '_id'
        asset_dict = asset.model_dump(by_alias=True, exclude_unset=True)

        # 2. Safely remove '_id' if it's None so MongoDB generates a real one
        if asset_dict.get("_id") is None:
            asset_dict.pop("_id", None)  # The 'None' here prevents the KeyError

        result = await self.collection.insert_one(asset_dict)
        return result.inserted_id

    # Get Asset by Name
    async def get_asset_by_name(self, asset_name: str, project_project_id: str):
        record = await self.collection.find_one(
            {"asset_project_id": project_project_id, "asset_name": asset_name}
        )
        if record:
            return Asset(**record)
        return None

    # Get Asset Record
    async def get_asset_record(self, asset_project_id: str, asset_name: str):
        # 1. Clean query filter
        query = {"asset_project_id": asset_project_id, "asset_name": asset_name}

        # 2. Find the record
        record = await self.collection.find_one(query)

        # 3. Convert to Pydantic (our BeforeValidator handles the ObjectId -> str)
        if record:
            return Asset(**record)

        return None

    # Get All Project Assets
    async def get_all_project_assets(self, asset_project_id: str, asset_type: str):
        # instead of returning list of dictionary straight from mongodb, we return it as Asset Pydantic Model
        records = await self.collection.find(
            {"asset_project_id": asset_project_id, "asset_type": asset_type}
        ).to_list(length=None)
        return [Asset(**record) for record in records]
