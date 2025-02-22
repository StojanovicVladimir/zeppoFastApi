import os
from dotenv import load_dotenv
import json
import re
import requests
from routes.db_query_manager import execute_query
load_dotenv()

base_url = "http://127.0.0.1:8000"
APINAME = os.getenv("APINAME")
APIPASSWORD = os.getenv("APIPASSWORD")
auth = (APINAME, APIPASSWORD)




def send_csv(message, api_key):
    # Fetch the old_values from the database
    pattern = r'(?<==)\s+|\s+(?==)'
    message = re.sub(pattern, '', message)
    pairs = message.split()
    values2 = {}
    for pair in pairs:
        # Find the first occurrence of '=' in the pair
        equal_index = pair.find('=')
        if equal_index != -1:
            key = pair[:equal_index].strip()
            value = pair[equal_index+1:].strip()
            if key:
                values2[key] = value

    print(values2)
    query = "SELECT csv_data FROM csv_alerts WHERE api_key_id = (SELECT id FROM api_keys WHERE api_key = :api_key);"
    values = {"api_key": api_key}

    results = execute_query(query, values)

    old_values = results[0][0]

    if old_values is None or len(old_values) == 0:
        # Update the csv_data in the database
        serialized_values = json.dumps(values)

        query = "UPDATE csv_alerts SET csv_data = :csv_data WHERE api_key_id = (SELECT id FROM api_keys WHERE api_key = :api_key);"
        values = {"csv_data": serialized_values, "api_key": api_key}

        results = execute_query(query, values)
    else:
        # Parse the original JSON string
        if old_values:
            original_data = json.loads(old_values.replace("'", '"'))
        else:
            original_data = {}

        # Update the old_values in original_data using the values dictionary
        for key, value in values2.items():
            if key in original_data:
                original_data[key] = original_data[key] + ', ' + value
            else:
                original_data[key] = value

        # Convert the modified data back to a JSON string
        updated_old_values = json.dumps(original_data)

        # Update the csv_data in the database
        query = "UPDATE csv_alerts SET csv_data = :csv_data WHERE api_key_id = (SELECT id FROM api_keys WHERE api_key = :api_key);"
        values = {"csv_data": updated_old_values, "api_key": api_key}

        results = execute_query(query, values)

