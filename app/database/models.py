"""
what the database looks like: tables, their columns, and how they relate to each other (foreign keys, relationships).
"""
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Enum as SqlEnum, ARRAY, String
from datetime import date
from app.database.db import Base
from enum import Enum
import uuid

class Results(str, Enum): 
    rejected = "rejected"
    ignored = "ignored"
    accepted = "accepted"

class Client(Base): 
    __tablename__ = "clients"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default = uuid.uuid4)
    google_places_api: Mapped[str] = mapped_column(unique = True)
    # business information
    business_name: Mapped[str]
    owner_name: Mapped[str | None] = mapped_column(nullable= True)
    category: Mapped[str]
    location: Mapped[str]
    # contact information
    phone: Mapped[str | None] = mapped_column(nullable = True)
    email: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable = True)
    # outreach status and result (does it make sense for this to be another db? with just 3 rows)
    messaged_at: Mapped[date] = mapped_column(nullable = True)
    contacted: Mapped[bool] = mapped_column(default = False)
    contact_result: Mapped[str | None] = mapped_column(SqlEnum(Results), name = "results", nullable= True)
    # relationships
    notes: Mapped[list["Note"]] = relationship(back_populates="client")
    project: Mapped[list["Project"]] = relationship(back_populates="client")

class ProjectStatus(str, Enum): 
    done = "done"
    pending = "pending"
    to_start = "to_start"

class Project(Base): 
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(primary_key= True, default = uuid.uuid4)
    # project information
    description: Mapped[str]
    due_date: Mapped[date]
    # status
    status: Mapped[str] = mapped_column(SqlEnum(ProjectStatus), name = "project_status")
    # relationships
    client: Mapped["Client"] = relationship(back_populates="projects")
    notes: Mapped[list["Note"]] = relationship(back_populates="project")

class Type(str, Enum):
    project = "project"
    client = "client"

class Note(Base):
    __tablename__ = "notes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key= True, default = uuid.uuid4)
    information: Mapped[str]
    type: Mapped[str] = mapped_column(SqlEnum(Type), name = "Type")
    created_at: Mapped[date] = mapped_column(default = date.today)
    # relationships
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clients.id"), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True) # actual relationships
    client: Mapped["Client | None"] = relationship(back_populates="notes") # ensures it's in sync
    project: Mapped["Project | None"] = relationship(back_populates="notes")