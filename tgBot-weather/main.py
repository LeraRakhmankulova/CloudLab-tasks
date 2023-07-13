import os
import json
import requests
import datetime

FUNC_RESPONSE = {
    'statusCode': 200,
    'body': ''
}
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

OWM_API_KEY = os.environ.get("OWM_API_KEY")

STT_API_KEY = os.environ.get("STT_API_KEY")
AUTH_HEADER = f"Api-Key {STT_API_KEY}"


def get_formatted_time(unix):
    date_time = datetime.datetime.fromtimestamp(unix)
    return date_time.strftime('%H:%M')


def get_file(file_id):
    res = requests.post(url=f'{TELEGRAM_API_URL}/getFile', json={'file_id': file_id})
    return res.json()['result']


def speech_recognition(message_in):
    voice = message_in['voice']
    file_id = voice['file_id']
    tg_file = get_file(file_id)
    file_path = tg_file['file_path']

    file_res = requests.get(url=f'https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}')
    audio = file_res.content
    
    stt_res = requests.post(url='https://stt.api.cloud.yandex.net/speech/v1/stt:recognize',
                            headers = {'Authorization': AUTH_HEADER},
                            data = audio)
    
    if stt_res.ok:
        res = stt_res.json()['result']
    else:
        res = f"Ошибка {stt_res.text}"
    
    return res


def send_message(text, message):
    message_id = message['message_id']
    chat_id = message['chat']['id']
    reply_message = {'chat_id': chat_id,
                     'text': text,
                     'reply_to_message_id': message_id}

    requests.post(url=f'{TELEGRAM_API_URL}/sendMessage', json=reply_message)


def send_voice(voice, message):
    voice_path = f"https://storage.yandexcloud.net/itiscl-spr23-32-public/{voice}"
    message_id = message['message_id']
    chat_id = message['chat']['id']
    reply_message = {'chat_id': chat_id,
                     'voice': voice_path,
                     'reply_to_message_id': message_id}

    requests.post(url=f'{TELEGRAM_API_URL}/sendVoice', json=reply_message)


def find_wind_direction(degree):
    if degree in range(348, 361) or degree in range(0, 12):
        return 'С'
    elif degree in range(12, 78):
        return 'СВ'
    elif degree in range(78, 101):
        return 'З'
    elif degree in range(101, 168):
        return 'ЮВ'
    elif degree in range(168, 191): 
        return 'Ю'
    elif degree in range(191, 258):
        return 'ЮЗ'
    elif degree in range(258, 281):
        return 'З'
    elif degree in range(281, 348):
        return 'СЗ'
    else:
        return 'В'


def get_weather_by_name(place):
    try:
        res = requests.get("http://api.openweathermap.org/data/2.5/weather",
                        params={'q': place, 'units': 'metric', 'lang': 'ru', 'APPID': OWM_API_KEY})
        data = res.json()

        sunrise_time = get_formatted_time(data['sys']['sunrise'])
        sunset_time = get_formatted_time(data['sys']['sunset'])
        wind_direction = data['wind']['deg']
        
        message_info = f"{data['weather'][0]['description'].title()} \n" \
                    f"Температура {data['main']['temp']} ℃, ощущается как {data['main']['feels_like']} ℃. \n" \
                    f"Атмосферное давление {data['main']['pressure']} мм рт. ст. \n" \
                    f"Влажность {data['main']['humidity']} %. \n" \
                    f"Видимость {data['visibility']} метров. \n" \
                    f"Ветер {data['wind']['speed']} м/с, направление ветра- {find_wind_direction(wind_direction)}. \n" \
                    f"Восход солнца {sunrise_time} МСК. Закат {sunset_time} МСК. \n"
    except Exception as e:
        message_info = f"Я не нашел населенный пункт {place}"
        
    return message_info
    

def get_weather_by_location(location):
    lat = location['latitude']
    lon = location['longitude']
    try:
        res = requests.get("http://api.openweathermap.org/data/2.5/weather",
                        params={'lat': lat, 'lon': lon, 'units': 'metric', 'lang': 'ru', 'APPID': OWM_API_KEY})
        data = res.json()

        sunrise_time = get_formatted_time(data['sys']['sunrise'])
        sunset_time = get_formatted_time(data['sys']['sunset'])
        wind_direction = data['wind']['deg']

        message_info = f"{data['weather'][0]['description'].title()} \n" \
                    f"Температура {data['main']['temp']} ℃, ощущается как {data['main']['feels_like']} ℃. \n" \
                    f"Атмосферное давление {data['main']['pressure']} мм рт. ст. \n" \
                    f"Влажность {data['main']['humidity']} %. \n" \
                    f"Видимость {data['visibility']} метров. \n" \
                    f"Ветер {data['wind']['speed']} м/с, направление ветра- {find_wind_direction(wind_direction)}. \n" \
                    f"Восход солнца {sunrise_time} МСК. Закат {sunset_time} МСК. \n"
    except Exception as e:
        message_info = f"Я не нашел населенный пункт {place}"
        
    return message_info


def handler(event, context):
    if TELEGRAM_BOT_TOKEN is None:
        return FUNC_RESPONSE

    update = json.loads(event['body'])

    if 'message' not in update:
        return FUNC_RESPONSE

    message_in = update['message']

    if 'text' in message_in:
        text = message_in['text']

        if text == '/start' or text == '/help':
            message_info = f'Я сообщу вам о погоде в том месте, которое сообщите мне.\n' \
            f'Я могу ответить на:\n' \
            f'- Текстовое сообщение с названием населенного пункта.\n' \
            f'- Голосовое сообщение с названием населенного пункта.\n' \
            f'- Сообщение с точкой на карте.'
            send_message(message_info, message_in)
            return FUNC_RESPONSE

        send_message(get_weather_by_name(text), message_in)
        return FUNC_RESPONSE

    if 'voice' in message_in:
        voice = message_in['voice']
        duration = voice['duration']

        if duration > 30:
            send_message("Я не могу понять голосовое сообщение длительность более 30 секунд.", message_in)
            return FUNC_RESPONSE

        data_name = speech_recognition(message_in)
        if data_name is None:
            send_message("Ошибка распознавания", message_in)
            return FUNC_RESPONSE

        weather_data = get_weather_by_name(data_name)
        send_message(weather_data, message_in)
        
        return FUNC_RESPONSE

    if 'location' in message_in:
        location = message_in['location']
        send_message(get_weather_by_location(location), message_in)
        return FUNC_RESPONSE

    error_message = f"Я не могу ответить на такой тип сообщения.\n" \
                    f"Но могу ответить на: \n" \
                    f"- Текстовое сообщение с названием населенного пункта. \n" \
                    f"- Голосовое сообщение с названием населенного пункта. \n" \
                    f"- Сообщение с точкой на карте. \n"
    send_message(error_message, message_in)     

    return FUNC_RESPONSE