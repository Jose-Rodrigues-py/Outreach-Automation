from app.database.models import Client, Message
from sqlalchemy import select
from ollama import AsyncClient
from app.database.db import AsyncSessionLocal
from ollama import web_fetch, web_search
import ollama
import os

client = AsyncClient(headers={"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"})

SYSTEM_PROMPT1 = """
    You are an assitant helping a business tailor his outreach message to each client. 
    Your task is to take the basic message and add subtle details that show the business has done some research on the client.
    You should keep the overall structure and tone of the original message.

    # IMPORTANT
    If you don't have enough information, don't make any changes.
""" # improve, possibly

SYSTEM_PROMPT2 = """
    You are a research assistant and your task is to find relevant information about local businesses. 
    # What you should look for:
    - what the business does
    - who they serve and why
    - relevant and recent projects or success stories

    Your work will be used to personalize messages that will be used to cold-email those businesses.
    You can consider your work complete when you have enough information to generate a succint paragraph with the main ideas.

    Return your answer in a short paragraph.
    If you don't find relevant information you should return "None".
"""

BOILERPLATE = """
Olá,
Sou o José, estudante de Engenharia Informática na Universidade do Porto. Com o intuitio de aplicar de uma forma útil aquilo que tenho vindo a aprender, ando a tentar perceber melhor o dia-a-dia de negócios como o seu, nomeadamente onde é que se perde mais tempo com tarefas repetitivas, comunicação com clientes ou agendamentos.

Não tenho nada pré-definido. A ideia é mesmo perceber primeiro onde está a maior dor de cabeça, e só depois avaliar se faz sentido construir alguma coisa ou não.

Tem 10-15 minutos esta semana para uma chamada rápida? Deixo o meu número: 932 927 296 — pode ligar ou mandar mensagem a qualquer altura.

Como estudante, não estou a vender nada — é um projeto para aprender e aplicar aquilo que tenho estudado de forma útil, sem qualquer compromisso.

Se leu até aqui, obrigado pelo tempo. E se andar com a agenda cheia esta semana, compreendo perfeitamente.

Cumprimentos,
José Rodrigues
"""

available_tools = {"web_search": web_search, "web_fetch": web_fetch}

async def find_information(conversation_history, max_iterations=10):
    for _ in range(max_iterations):
        response = ollama.chat(
            model = "qwen2.5:7b-instruct-q4_0",
            messages = conversation_history,
            tools = available_tools
        )
        message = response["message"]
        conversation_history.append(message)

        if not message.get("tool_calls"): # if the model does not call any tool, end the hob
            return message["content"]

        for tool_call in message.tool_calls:
            func = available_tools.get(tool_call.function.name)
            if func:
                result = func(**tool_call.function.arguments)
                conversation_history.append({
                    "role": "tool",
                    "content": str(result),
                    "tool_name": tool_call.function.name,
                })
    return None  # gave up after max_iterations without a final answer

async def create_message(client_id): # should be called in main, going one by one on db; by client_id (not google_api_id)
    async with AsyncSessionLocal() as db: 
        result = await db.execute(select(Client).where(Client.id == client_id))
        biz = result.scalar_one_or_none()
        if not biz:
            print(f"could not find a client with id {client_id}")
            return None
                                  
        conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT2},
            {"role": "user", "content": f"Research this business: {biz.business_name}, located in {biz.location}."},
        ]
        about = await find_information(conversation_history)

        user_message = f"Given this message as boilerplate: {BOILERPLATE}; tailor it to business in question. You should use this information: {about}"
        messages = [
                {"role": "system", "content": SYSTEM_PROMPT1},
                {"role": "user", "content": user_message}
            ]

        response = await client.chat(model="qwen2.5:7b-instruct-q4_0", messages = messages)

        # saving message on database is only done when message is actually sent (on main?) - possibly update models so I have a table Message with a row "draft", then I could updaye it now
        message = Message(
            client_id = client_id, 
            draft = response.message.content
        )
        db.add(message)
        await db.commit()
    print("message successfully created.")
    return response.message.content