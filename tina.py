from flask import Flask, request, render_template
import requests
from groq import Groq
import os
import tempfile
import urllib.request
import time
from collections import defaultdict, deque

app = Flask(__name__)

# Histórico dos usuários
user_history = {}

# Sistema de rate limiting - 5 perguntas por minuto
user_requests = defaultdict(deque)
MAX_REQUESTS_PER_MINUTE = 2
RATE_LIMIT_WINDOW = 60  # 60 segundos

# Config do cliente Groq
client = Groq(api_key='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')

PAGE_ACCESS_TOKEN = "EAAozvjZBGw5gBPPRKqB34HHpYz6SHuhEgGqccrIg0yppUUjigRHwYO0jvXgSeLZCZA02Fzd4sxGX60RuwFv2RRo1w95yyJjw5gUXcFOsqCdgD2yErojjWOo3yYDzTlVRKcJRKJZAQLZCVzGBficu9K5vbTisZANvs02S7FOuDdQLeEtBWTyr1KK9wRkpU5rnJxjaV5GEipVxuOyX9mGfj0nZAHHWVqHGQZCQznSQHA2ZCbNLN"
VERIFY_TOKEN = "tina_bot_eliobros_tech_verify"

SYSTEM_PROMPT = """
Seu nome é Tina IA, a inteligência artificial desenvolvida pela empresa Eliobros Tech que fou fundada a 15 de maio de 2024 pelo Habibo Salimo Julio mais conhecido por B0B40_D3V
"""

def check_rate_limit(sender_id):
    """
    Verifica se o usuário excedeu o limite de 5 perguntas por minuto
    Retorna True se o usuário pode fazer a pergunta, False caso contrário
    """
    current_time = time.time()
    user_queue = user_requests[sender_id]
    
    # Remove requests antigos (mais de 1 minuto)
    while user_queue and current_time - user_queue[0] > RATE_LIMIT_WINDOW:
        user_queue.popleft()
    
    # Verifica se o usuário excedeu o limite
    if len(user_queue) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    # Adiciona o request atual
    user_queue.append(current_time)
    return True

def get_rate_limit_message(sender_id):
    """
    Retorna mensagem personalizada com tempo restante para próxima pergunta
    """
    current_time = time.time()
    user_queue = user_requests[sender_id]
    
    if user_queue:
        oldest_request = user_queue[0]
        time_remaining = int(RATE_LIMIT_WINDOW - (current_time - oldest_request))
        
        return (
            f"⏱️ Limite atingido! Você pode fazer até {MAX_REQUESTS_PER_MINUTE} perguntas por minuto.\n"
            f"Próxima pergunta disponível em {time_remaining} segundos.\n\n"
            f"💡 Para perguntas ilimitadas e funcionalidades avançadas, "
            f"visite nosso site: https://www.assistentetina.com 🚀"
        )
    
    return (
        f"⏱️ Limite de {MAX_REQUESTS_PER_MINUTE} perguntas por minuto atingido!\n"
        f"Aguarde alguns==  segundos antes de fazer outra pergunta.\n\n"
        f"💡 Para perguntas ilimitadas, visite: https://www.assistentetina.com 🚀"
    )

def getAnswer(sender_id, question, image_url=None):
    try:
        history = user_history.get(sender_id, [])[-10:]
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if image_url:
            model = "meta-llama/llama-4-scout-17b-16e-instruct"
            messages += history
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            })
        else:
            model = "qwen/qwen3-32b"
            history.append({"role": "user", "content": question})
            messages += history

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=True
        )

        bot_response = ""
        found_think_end = False
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            if not found_think_end:
                idx = content.find("</think>")
                if idx != -1:
                    found_think_end = True
                    content = content[idx + len("</think>"):]
                else:
                    continue
            bot_response += content

        history.append({"role": "assistant", "content": bot_response})
        user_history[sender_id] = history
        return bot_response
    except Exception as e:
        print(f"Erro ao gerar resposta: {str(e)}")
        return (
            "Desculpe, ocorreu um erro. "
            "A minha equipe de programadores já foi notificada ou liga para 862840075. 😊 #EliobrosTech"
        )

@app.route("/politicas-privacidade.html")
def politica():
    return render_template("politicas.html")

@app.route("/termos_uso.html")
def termos():
    return render_template("termos.html")

@app.errorhandler(404)
def pagina_nao_encontrada(e):
    return render_template("404.html"), 404

@app.route("/", methods=["GET"])
def verify():
    token_sent = request.args.get("hub.verify_token")
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Token de verificação inválido"

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    messaging_events = data["entry"][0]["messaging"]

    for event in messaging_events:
        sender_id = event["sender"]["id"]

        if "message" in event:
            # Verifica rate limit antes de processar a mensagem
            if not check_rate_limit(sender_id):
                rate_limit_msg = get_rate_limit_message(sender_id)
                send_message(sender_id, rate_limit_msg)
                continue

            message = event["message"]

            if "text" in message:
                text = message["text"]
                response = getAnswer(sender_id, text)
                send_message(sender_id, response)

            elif "attachments" in message:
                for attachment in message["attachments"]:
                    if attachment["type"] == "image":
                        image_url = attachment["payload"]["url"]
                        response = getAnswer(sender_id, "Analisa esta imagem:", image_url=image_url)
                        send_message(sender_id, response)

                    elif attachment["type"] == "audio":
                        audio_url = attachment["payload"]["url"]
                        transcript = transcribe_audio(audio_url)
                        response = getAnswer(sender_id, transcript)
                        send_message(sender_id, response)

    return "ok"

def transcribe_audio(audio_url):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp_file:
            urllib.request.urlretrieve(audio_url, tmp_file.name)
            with open(tmp_file.name, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(tmp_file.name, file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json"
                )
        os.remove(tmp_file.name)
        return transcription.text
    except Exception as e:
        print(f"Erro na transcrição de áudio: {str(e)}")
        return "Não consegui entender o áudio. Por favor, tente novamente."

def send_message(recipient_id, message_text):
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    auth = {"access_token": PAGE_ACCESS_TOKEN}
    response = requests.post(
        "https://graph.facebook.com/v12.0/me/messages",
        params=auth,
        json=payload
    )
    return response.json()

if __name__ == "__main__":
    app.run(debug=True)

