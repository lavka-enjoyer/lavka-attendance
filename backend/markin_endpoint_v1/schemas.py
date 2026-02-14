from typing import List

from pydantic import BaseModel, HttpUrl


class SendApprove(BaseModel):
    initData: str
    url: HttpUrl


class MassApproveData(BaseModel):
    selectedUsers: List[int]
    url: str
    initData: str


class ContinueMarkingData(BaseModel):
    session_id: str
    url: str
    initData: str
