import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from db.engine import Base

class EcommerceCustomer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "ecommerce"}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    location = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("EcommerceOrder", back_populates="customer")

class EcommerceCategory(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "ecommerce"}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    products = relationship("EcommerceProduct", back_populates="category")

class EcommerceProduct(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "ecommerce"}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey("ecommerce.categories.id"))
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    category = relationship("EcommerceCategory", back_populates="products")

class EcommerceOrder(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "ecommerce"}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("ecommerce.customers.id"))
    order_date = Column(Date, nullable=False, index=True)
    total_value = Column(Float, nullable=False)
    status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("EcommerceCustomer", back_populates="orders")

class SupportCustomer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "support"}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    contact_info = Column(String(512), nullable=True)
    account_status = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tickets = relationship("SupportTicket", back_populates="customer")

class SupportAgent(Base):
    __tablename__ = "agents"
    __table_args__ = {"schema": "support"}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)
    email = Column(String(255), unique=True)
    
    tickets = relationship("SupportTicket", back_populates="agent")
    notes = relationship("SupportTicketNote", back_populates="agent")

class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SupportTicket(Base):
    __tablename__ = "tickets"
    __table_args__ = {"schema": "support"}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("support.customers.id"))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="open", index=True)
    priority = Column(String(50), default="medium", index=True)
    assigned_agent_id = Column(Integer, ForeignKey("support.agents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    customer = relationship("SupportCustomer", back_populates="tickets")
    agent = relationship("SupportAgent", back_populates="tickets")
    notes = relationship("SupportTicketNote", back_populates="ticket")

class SupportTicketNote(Base):
    __tablename__ = "ticket_notes"
    __table_args__ = {"schema": "support"}
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support.tickets.id"))
    agent_id = Column(Integer, ForeignKey("support.agents.id"))
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    ticket = relationship("SupportTicket", back_populates="notes")
    agent = relationship("SupportAgent", back_populates="notes")


class UploadDataset(Base):
    """User-uploaded spreadsheet snapshot per conversation (Postgres uploads schema)."""

    __tablename__ = "datasets"
    __table_args__ = {"schema": "uploads"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(String(64), nullable=False, index=True)
    file_name = Column(String(512), nullable=False)
    row_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    rows = relationship(
        "UploadDatasetRow",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )


class UploadDatasetRow(Base):
    __tablename__ = "dataset_rows"
    __table_args__ = {"schema": "uploads"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_index = Column(Integer, nullable=False)
    data = Column(JSONB, nullable=False)

    dataset = relationship("UploadDataset", back_populates="rows")