from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
CORS(app)  # permite chamadas de qualquer origem (útil para testar no navegador ou apps externos)

# Inicializa cliente da Groq
client = Groq(api_key='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')

@app.route('/tina', methods=['POST'])
def tina():
    data = request.get_json()
    pergunta = data.get("pergunta", "")

    if not pergunta:
        return jsonify({"erro": "Pergunta vazia"}), 400

    try:
        completion = client.chat.completions.create(
            model="llama-3-70b-8192",
            messages=[
                {
                    "role": "assistant",
                    "content": "Olá! Eu sou a Tina, a inteligencia artificial desenvolvida pela empresa Eliobros Tech e estou aqui pra te ajudar."
                },
                {
                    "role": "user",
                    "content": pergunta
                }
            ],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=True
        )

        resposta = ""
        for chunk in completion:
            if chunk.choices[0].delta.content is not None:
                resposta += chunk.choices[0].delta.content

        return jsonify({"resposta": resposta})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
