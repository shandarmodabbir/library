from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, Annotated
from pydantic.types import conint

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    role: str

    model_config = ConfigDict(from_attributes=True)

class BookBase(BaseModel):
    name: str
    author: str
    category: str
    description: str = Field(default="", max_length=5000)
    isbn: str = Field(default="", max_length=32)
    publication_year: int | None = Field(default=None, ge=1, le=9999)
    cover_url: str = Field(default="", max_length=2000)

    @field_validator("name", "author", "category")
    @classmethod
    def not_blank(cls, value):
        value = value.strip()
        if not value or len(value) > 300:
            raise ValueError("Must contain between 1 and 300 characters")
        return value

    @field_validator("cover_url")
    @classmethod
    def safe_cover(cls, value):
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Cover URL must use http or https")
        return value


class BookCreate(BookBase):
    pass

class BookOut(BookBase):
    id: int
    provider_user_id: int | None
    available: bool = True
    title_id: int | None = None


    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[int] = None


class Borrow(BaseModel):
    book_id: int
    dir: Annotated[int, Field(ge=0, le= 1)]
