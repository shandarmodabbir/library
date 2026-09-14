from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    phone_number = Column(String)
    role = Column(String, nullable=False, server_default="reader")

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    author = Column(String, nullable=False)
    category = Column(String, nullable=False)
    provider_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    description = Column(Text, nullable=False, server_default="")
    isbn = Column(String, nullable=False, server_default="")
    publication_year = Column(Integer, nullable=True)
    cover_url = Column(String, nullable=False, server_default="")
    title_id = Column(Integer, ForeignKey("book_titles.id"), nullable=True, index=True)
    loans = relationship("Borrow", lazy="selectin", passive_deletes=True)

    reservations = relationship("Reservation", lazy="selectin", passive_deletes=True)

    @property
    def available(self):
        return not self.loans and not self.reservations


class Borrow(Base):
    __tablename__ = "borrow"
    __table_args__ = (UniqueConstraint("book_id", name="uq_borrow_book"),)

    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    borrowed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    renewals = Column(Integer, nullable=False, server_default="0")
    due_date = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc) + timedelta(days=14))

class ReadingStatus(Base):
    __tablename__ = "reading_status"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String, nullable=False)


class BookTitle(Base):
    __tablename__ = "book_titles"
    id = Column(Integer, primary_key=True)
    identity = Column(String, nullable=False, unique=True)

class LoanHistory(Base):
    __tablename__ = "loan_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    book_name = Column(String, nullable=False)
    book_author = Column(String, nullable=False)
    borrowed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    due_date = Column(TIMESTAMP(timezone=True), nullable=False)
    returned_at = Column(TIMESTAMP(timezone=True), nullable=False)
    renewals = Column(Integer, nullable=False, default=0)

class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (UniqueConstraint("book_id", "user_id"),)
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    ready_until = Column(TIMESTAMP(timezone=True), nullable=True)

class ChatRequestRecord(Base):
    __tablename__ = "chat_requests"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    request_id = Column(String, primary_key=True)
    fingerprint = Column(String, nullable=False)
    session_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="running")
    response = Column(Text, nullable=True)

class AgentAction(Base):
    __tablename__ = "agent_actions"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    request_id = Column(String, primary_key=True)
    action_key = Column(String, primary_key=True)
    result = Column(Text, nullable=False)
