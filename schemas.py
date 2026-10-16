from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ---------- Book ----------
class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    total_copies: int = 1


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    total_copies: Optional[int] = None


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    total_copies: int
    available_copies: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Member ----------
class MemberCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class MemberOut(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Issue ----------
class IssueCreate(BaseModel):
    book_id: int
    member_id: int
    days: int = 14  # kitne din ke liye book milegi


class IssueOut(BaseModel):
    id: int
    book_id: int
    member_id: int
    issue_date: date
    due_date: date
    return_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str