from datetime import date, timedelta
from pathlib import Path
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import models, schemas
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
)
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Library Management System")


@app.get("/")
def home():
    return {"message": "Library API chal rahi hai! /docs par jao."}


# =====================================================
#                       AUTH
# =====================================================

@app.post("/auth/register", response_model=schemas.UserOut, status_code=201, tags=["Auth"])
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already le liya gaya hai")

    # Demo ke liye: sabse pehla user admin banega, baaki normal user
    role = "admin" if db.query(models.User).count() == 0 else "user"

    user = models.User(
        username=data.username,
        hashed_password=hash_password(data.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token, tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Username ya password galat hai")

    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UserOut, tags=["Auth"])
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


# =====================================================
#                    BOOKS CRUD
# =====================================================

# CREATE (sirf admin)
@app.post("/books", response_model=schemas.BookOut, status_code=201,
          dependencies=[Depends(require_admin)], tags=["Books"])
def create_book(book: schemas.BookCreate, db: Session = Depends(get_db)):
    if db.query(models.Book).filter(models.Book.isbn == book.isbn).first():
        raise HTTPException(status_code=400, detail="Is ISBN ki book already hai")

    new_book = models.Book(
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        total_copies=book.total_copies,
        available_copies=book.total_copies,
    )
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book


# READ ALL (login hona chahiye)
@app.get("/books", response_model=List[schemas.BookOut],
         dependencies=[Depends(get_current_user)], tags=["Books"])
def get_books(search: str = None, skip: int = 0, limit: int = 10,
              db: Session = Depends(get_db)):
    query = db.query(models.Book)
    if search:
        query = query.filter(
            models.Book.title.ilike(f"%{search}%")
            | models.Book.author.ilike(f"%{search}%")
        )
    return query.offset(skip).limit(limit).all()


# READ ONE (login hona chahiye)
@app.get("/books/{book_id}", response_model=schemas.BookOut,
         dependencies=[Depends(get_current_user)], tags=["Books"])
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book nahi mili")
    return book


# UPDATE (sirf admin)
@app.put("/books/{book_id}", response_model=schemas.BookOut,
         dependencies=[Depends(require_admin)], tags=["Books"])
def update_book(book_id: int, data: schemas.BookUpdate, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book nahi mili")

    updates = data.model_dump(exclude_unset=True)

    if "total_copies" in updates:
        issued = book.total_copies - book.available_copies
        if updates["total_copies"] < issued:
            raise HTTPException(
                status_code=400,
                detail=f"{issued} copies issued hain, total isse kam nahi ho sakta",
            )
        book.available_copies = updates["total_copies"] - issued

    for key, value in updates.items():
        setattr(book, key, value)

    db.commit()
    db.refresh(book)
    return book


# DELETE (sirf admin)
@app.delete("/books/{book_id}", dependencies=[Depends(require_admin)], tags=["Books"])
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book nahi mili")

    active = (
        db.query(models.Issue)
        .filter(models.Issue.book_id == book_id, models.Issue.return_date == None)
        .first()
    )
    if active:
        raise HTTPException(status_code=400, detail="Book abhi issued hai, delete nahi hogi")

    db.delete(book)
    db.commit()
    return {"message": "Book delete ho gayi"}


# =====================================================
#                   MEMBERS CRUD
# =====================================================

@app.post("/members", response_model=schemas.MemberOut, status_code=201,
          dependencies=[Depends(require_admin)], tags=["Members"])
def create_member(member: schemas.MemberCreate, db: Session = Depends(get_db)):
    if db.query(models.Member).filter(models.Member.email == member.email).first():
        raise HTTPException(status_code=400, detail="Email already registered hai")

    new_member = models.Member(**member.model_dump())
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


@app.get("/members", response_model=List[schemas.MemberOut],
         dependencies=[Depends(get_current_user)], tags=["Members"])
def get_members(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(models.Member).offset(skip).limit(limit).all()


@app.get("/members/{member_id}", response_model=schemas.MemberOut,
         dependencies=[Depends(get_current_user)], tags=["Members"])
def get_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member nahi mila")
    return member


@app.put("/members/{member_id}", response_model=schemas.MemberOut,
         dependencies=[Depends(require_admin)], tags=["Members"])
def update_member(member_id: int, data: schemas.MemberUpdate, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member nahi mila")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(member, key, value)

    db.commit()
    db.refresh(member)
    return member


@app.delete("/members/{member_id}", dependencies=[Depends(require_admin)], tags=["Members"])
def delete_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member nahi mila")

    active = (
        db.query(models.Issue)
        .filter(models.Issue.member_id == member_id, models.Issue.return_date == None)
        .first()
    )
    if active:
        raise HTTPException(status_code=400, detail="Member ke paas book issued hai")

    db.delete(member)
    db.commit()
    return {"message": "Member delete ho gaya"}


# =====================================================
#                ISSUE / RETURN BOOKS
# =====================================================

@app.post("/issues", response_model=schemas.IssueOut, status_code=201,
          dependencies=[Depends(require_admin)], tags=["Issues"])
def issue_book(data: schemas.IssueCreate, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == data.book_id).first()
    member = db.query(models.Member).filter(models.Member.id == data.member_id).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book nahi mili")
    if not member:
        raise HTTPException(status_code=404, detail="Member nahi mila")
    if book.available_copies < 1:
        raise HTTPException(status_code=400, detail="Is book ki koi copy available nahi hai")

    issue = models.Issue(
        book_id=data.book_id,
        member_id=data.member_id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=data.days),
    )
    book.available_copies -= 1

    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@app.put("/issues/{issue_id}/return", response_model=schemas.IssueOut,
         dependencies=[Depends(require_admin)], tags=["Issues"])
def return_book(issue_id: int, db: Session = Depends(get_db)):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue record nahi mila")
    if issue.return_date:
        raise HTTPException(status_code=400, detail="Book pehle hi return ho chuki hai")

    issue.return_date = date.today()
    issue.book.available_copies += 1

    db.commit()
    db.refresh(issue)
    return issue


@app.get("/issues", response_model=List[schemas.IssueOut],
         dependencies=[Depends(get_current_user)], tags=["Issues"])
def get_issues(only_active: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.Issue)
    if only_active:
        query = query.filter(models.Issue.return_date == None)
    return query.all()

BASE_DIR = Path(__file__).resolve().parent
app.mount("/app", StaticFiles(directory=BASE_DIR / "static", html=True), name="frontend")