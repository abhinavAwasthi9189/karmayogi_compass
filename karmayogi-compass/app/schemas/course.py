from typing import List
from pydantic import BaseModel


class CourseOut(BaseModel):
    id: str
    title: str
    domain: str
    source: str
    launch_url: str
    description: str = ""


class RecommendationResponse(BaseModel):
    user_id: int
    based_on_gaps: List[str]
    courses: List[CourseOut]


class CourseModuleOut(BaseModel):
    module_no: int
    module_title: str
    study_material: str
    module_learning_outcome: str


class CourseModulesResponse(BaseModel):
    course_id: str
    course_title: str
    modules: List[CourseModuleOut]
