import requests
import json

def send_whatsapp_message(phone, message):
    print(f"Сообщение (первые 50 символов): {message[:50]}...")

    url = "https://7103.api.greenapi.com/waInstance7103152373/sendMessage/31af42310e21457c9dbf002b9382a476549e54799cb84a5cad"

    headers = {
        'Content-Type': 'application/json',
    }

    # Презентационное сообщение (можно менять текст/оформление)
    presentation_text = "🔑 ВАШ КОД ВЕРИФИКАЦИИ\n🌟 SARYARQA JASTARY\n\n"

    payload = {
        "chatId": f"{phone}@c.us",
        "message": presentation_text + message
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            return True
        else:
            print(response.text)
            return False
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

# Пример вызова:
# send_whatsapp_message("77711745741", "Ваш код: 123456")
