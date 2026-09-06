from datetime import date
from app.database.db import AsyncSessionLocal
from app.database.models import Client, Message
from sqlalchemy import select
import os
from email.mime.text import MIMEText
from base64 import urlsafe_b64encode

async def build_message(sender, destination, obj, body):
    message = MIMEText(body)
    message['to'] = destination
    message['from'] = sender
    message['subject'] = obj
    return {'raw': urlsafe_b64encode(message.as_bytes()).decode()}

async def send_message(message_id, sender, obj, body, service):
    async with AsyncSessionLocal() as db:
        message = await db.get(Message, message_id)
        client = await db.get(Client, message.client_id)
        destination = client.email[0] 

        message_body = await build_message(sender, destination, obj, body)

        try:
            result = service.users().messages().send(userId="me", body=message_body).execute()
        except Exception as e:
            print(f"Failed to send to {destination}: {e}")
            return None

        message.content_sent = body
        message.sent_at = date.today()
        await db.commit()

    return result