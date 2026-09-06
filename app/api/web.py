from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.database.models import Client, Message, Project
from app.worker.llm import create_message
from app.worker.gmail import send_message
from app.tools.auth import get_gmail_service_for_account

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ACCOUNTS = {
    "conta1": {"email": "rodriguesjosepedro407@gmail.com"},
    "conta2": {"email": "zepedromartinsrodrigues@gmail.com"},
    "conta3": {"email": "josepmartrodrigues@gmail.com"},
}

SUBJECT = "Rápido feedback sobre o dia-a-dia do seu negócio?"

async def _get_clients(db: AsyncSession):
    res = await db.execute(
        select(Client).options(selectinload(Client.message)).order_by(Client.business_name)
    )
    return res.scalars().all()

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    clients = await _get_clients(db)
    return templates.TemplateResponse(
        request, "index.html", {"clients": clients, "accounts": ACCOUNTS}
    )

@router.post("/ui/clients/{client_id}/accept", response_class=HTMLResponse)
async def ui_accept_client(client_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if not client:
        return HTMLResponse("", status_code=404)

    await create_message(client_id)

    res = await db.execute(
        select(Client).options(selectinload(Client.message)).where(Client.id == client_id)
    )
    client = res.scalar_one_or_none()
    return templates.TemplateResponse("partials/_client_row.html", {"request": request, "c": client})


@router.delete("/ui/clients/{client_id}")
async def ui_delete_client(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if client:
        await db.delete(client)  # cascades to Message/Note/Project via ondelete=CASCADE
        await db.commit()
    return Response(status_code=200)


@router.patch("/ui/messages/{message_id}", response_class=HTMLResponse)
async def ui_update_message(message_id: str, draft: str = Form(...), db: AsyncSession = Depends(get_db)):
    message = await db.get(Message, message_id)
    if not message:
        return HTMLResponse("Não encontrado", status_code=404)
    message.draft = draft
    await db.commit()
    return HTMLResponse("Guardado")


@router.get("/ui/clients/{client_id}/projects", response_class=HTMLResponse)
async def ui_client_projects(client_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Project).where(Project.client_id == client_id))
    projects = res.scalars().all()
    return templates.TemplateResponse("partials/_projects.html", {"request": request, "projects": projects})


@router.post("/ui/messages/bulk-send", response_class=HTMLResponse)
async def ui_bulk_send(
    request: Request,
    message_ids: list[str] = Form(...),
    account_key: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    service = get_gmail_service_for_account(ACCOUNTS[account_key]["email"])
    sender = ACCOUNTS[account_key]["email"]

    for message_id in message_ids:
        message = await db.get(Message, message_id)
        if not message:
            continue
        await send_message(message_id, sender, SUBJECT, message.draft, service)

    clients = await _get_clients(db)
    return templates.TemplateResponse("partials/_table_body.html", {"request": request, "clients": clients})