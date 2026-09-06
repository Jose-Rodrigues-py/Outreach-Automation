from datetime import date
from app.database.db import AsyncSessionLocal
from app.database.models import Client, Message
from sqlalchemy import select
from tools.auth import get_service # still need to get this from google
import os
from email.mime.text import MIMEText
from base64 import urlsafe_b64encode

async def build_message(sender, destination, obj, body):
    message = MIMEText(body)
    message['to'] = destination
    message['from'] = sender
    message['subject'] = obj
    return {'raw': urlsafe_b64encode(message.as_bytes()).decode()}

async def send_message(sender, destination, obj, body, service):
    message_body = await build_message(sender, destination, obj, body)

    try:
        result = service.users().messages().send(userId="me", body=message_body).execute()
    except Exception as e:
        print(f"Failed to send to {destination}: {e}")
        return None

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Client.id).where(Client.email.any(destination)))
        client_id = res.scalar_one_or_none()
        if not client_id:
            print(f"Sent, but could not find client with email: {destination}")
            return result

        res2 = await db.execute(select(Message).where(Message.client_id == client_id))
        message = res2.scalar_one_or_none()
        if not message:
            print("Sent, but draft hasn't been created in DB.")
            return result

        message.content_sent = body
        message.sent_at = date.today()
        await db.commit()

    return result