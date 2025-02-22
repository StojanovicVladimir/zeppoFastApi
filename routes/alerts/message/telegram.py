import os
from dotenv import load_dotenv
import requests
import urllib.parse
import re
import time

from routes.db_query_manager import execute_query
load_dotenv()



telegram_bot_key = os.getenv("TELEGRAM_BOT")

base_url = "http://127.0.0.1:8000"
APINAME = os.getenv("APINAME")
APIPASSWORD = os.getenv("APIPASSWORD")
auth = (APINAME, APIPASSWORD)


api_url = f"https://api.telegram.org/bot{telegram_bot_key}"
url = f"{api_url}/sendMessage"


def send_telegram(message, api_key):
    print("tg executed")
    query = "SELECT verified, chat_id FROM telegram_alerts WHERE api_key_id = (SELECT id FROM api_keys WHERE api_key = :api_key);"
    values = {"api_key": api_key}

    results = execute_query(query, values)
  
    is_verified = results[0][0]
    chat_id = results[0][1]
    print(chat_id)
    print(message)
    print(is_verified)
    if('wait=' in message.lower()):
        pattern = r'(?<==)\s+|\s+(?==)'
        message2 = re.sub(pattern, '', message.lower())
        pairs = message2.split()
        lowercasedata = {}
        for pair in pairs:
            equal_index = pair.find('=')
            if equal_index != -1:
                key = pair[:equal_index].strip()
                value = pair[equal_index+1:].strip()
                if key:
                    lowercasedata[key] = value

        #time.sleep(float(lowercasedata["wait"]))
        time_to_sleep = float(lowercasedata["wait"])
        #await asyncio.sleep(time_to_sleep)
        time.sleep(time_to_sleep)
        message = message.replace("wait=" + lowercasedata["wait"], "")
        message = message.replace("Wait=" + lowercasedata["wait"], "")
        message = message.replace("WAIT=" + lowercasedata["wait"], "")

    message = urllib.parse.quote(message)

    

    try:
        if is_verified == 1:
            response = requests.get(f"https://api.telegram.org/bot{telegram_bot_key}/sendMessage?chat_id={chat_id}&text={message}")
            response.raise_for_status()
            print("Message sent successfully")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the message: {e}")


