import os
from dotenv import load_dotenv
import requests
import time
import re
from routes.db_query_manager import execute_query



load_dotenv()


base_url = "http://127.0.0.1:8000"
APINAME = os.getenv("APINAME")
APIPASSWORD = os.getenv("APIPASSWORD")
auth = (APINAME, APIPASSWORD)





def send_discord(message, api_key):
    query = "SELECT webhook_url FROM discord_alerts WHERE api_key_id = (SELECT id FROM api_keys WHERE api_key = :api_key);"
    values = {"api_key": api_key}

    results = execute_query(query, values)
    
    webhook = results[0][0]
    print(webhook)

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

        time_to_sleep = float(lowercasedata["wait"])
        #await asyncio.sleep(time_to_sleep)
        time.sleep(time_to_sleep)
        message = message.replace("wait=" + lowercasedata["wait"], "")
        message = message.replace("Wait=" + lowercasedata["wait"], "")
        message = message.replace("WAIT=" + lowercasedata["wait"], "")

    response = requests.post(webhook, json={"content": message})

    if response.ok:
        print("Message sent successfully.")
    else:
        print("Failed to send message. Status code:", response.status_code)
        


        

