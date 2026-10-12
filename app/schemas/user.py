from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    department_id: int | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
