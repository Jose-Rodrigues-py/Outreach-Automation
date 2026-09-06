import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.database.models import Client, Message, Project
from app.worker.gmail import send_message
from app.worker.llm import create_message
from app.tools.auth import get_gmail_service_for_account 

router = APIRouter()
# Schemas 
class MessageOut(BaseModel):
    id: str
    draft: str
    content_sent: str | None
    sent_at: date | None

    class Config:
        from_attributes = True

class MessageUpdate(BaseModel):
    draft: str

class ClientOut(BaseModel):
    id: str
    business_name: str
    category: str
    location: str
    phone: str | None
    email: list[str] | None
    contact_result: str | None
    message: MessageOut | None

    class Config:
        from_attributes = True

class ClientUpdate(BaseModel):
    business_name: str | None = None
    owner_name: str | None = None
    category: str | None = None
    location: str | None = None
    phone: str | None = None
    email: list[str] | None = None

class ProjectOut(BaseModel):
    id: str
    description: str
    due_date: date
    status: str

    class Config:
        from_attributes = True

# Clients

@router.get("/clients", response_model=list[ClientOut])
async def list_clients(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Client).options(selectinload(Client.message)))
    return res.scalars().all()

@router.get("/clients/{client_id}", response_model=ClientOut)
async def get_client(client_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Client).options(selectinload(Client.message)).where(Client.id == client_id))
    client = res.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.patch("/clients/{client_id}", response_model=ClientOut)
async def update_client(client_id: str, updates: ClientUpdate, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    await db.commit()
    await db.refresh(client)
    return client

@router.delete("/clients/{client_id}", status_code=204)
async def delete_client(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.delete(client) 
    await db.commit()

@router.post("/clients/{client_id}/accept", response_model=ClientOut)
async def accept_client(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    await create_message(client_id) 

    res = await db.execute(select(Client).options(selectinload(Client.message)).where(Client.id == client_id))
    return res.scalar_one_or_none()

# Messages 

@router.patch("/messages/{message_id}", response_model=MessageOut)
async def update_message(message_id: str, body: MessageUpdate, db: AsyncSession = Depends(get_db)):
    message = await db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    message.draft = body.draft
    await db.commit()
    await db.refresh(message)
    return message

# Projects 

@router.get("/clients/{client_id}/projects", response_model=list[ProjectOut])
async def list_client_projects(client_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Project).where(Project.client_id == client_id))
    return res.scalars().all()

# Email

class BulkSendRequest(BaseModel):
    message_ids: list[str]
    account_key: str  # "conta1", "conta2", or "conta3"

ACCOUNTS = {
    "conta1": {"email": "rodriguesjosepedro407@gmail.com", "token_file": "token_rodriguesjosepedro407@gmail.com.json"},
    "conta2": {"email": "zepedromartinsrodrigues@gmail.com", "token_file": "token_zepedromartinsrodrigues@gmail.com.json"},
    "conta3": {"email": "josepmartrodrigues@gmail.com", "token_file": "token_josepmartrodrigues@gmail.com.json"},
}

subject = "Rápido feedback sobre o dia-a-dia do seu negócio?"

@router.post("/messages/bulk-send")
async def bulk_send(body: BulkSendRequest, db: AsyncSession = Depends(get_db)):
    service = get_gmail_service_for_account(ACCOUNTS[body.account_key]["email"])
    sender = ACCOUNTS[body.account_key]["email"]
    results = {}

    for message_id in body.message_ids:
        message = await db.get(Message, message_id)
        if not message:
            results[message_id] = "not_found"
            continue
        result = await send_message(message_id, sender, subject, message.draft, service)
        results[message_id] = "sent" if result else "failed"

    return results