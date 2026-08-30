from typing import Optional
from sqlmodel import SQLModel, Field


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)   # id on iGOT
    title: str
    domain: str                            # statistical | technical | digital_gov | managerial
    source: str = "iGOT Karmayogi"
    launch_url: str
    description: str = ""
