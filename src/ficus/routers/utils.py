
from fastapi import Request


from ficus.database.data_store import DataStore


def data_store(request: Request) -> DataStore:
    return request.app.state.data_store
