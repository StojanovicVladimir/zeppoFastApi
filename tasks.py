from celery import Celery
import time
import re
import datetime as dt
from decimal import Decimal
from routes.db_query_manager import execute_query
from routes.alerts.message.discord import send_discord
from routes.alerts.message.telegram import send_telegram
from routes.alerts.message.csv import send_csv
from routes.alerts.exchange.binance_exchange import send_binance
from routes.alerts.exchange.bybit_exchange import send_bybit
import os
from dotenv import load_dotenv


load_dotenv()

# Retrieve the connection details from environment variables
host = os.getenv("HOST")
port = int(os.getenv("PORT"))
database = os.getenv("DATABASE")
username = os.getenv("DBUSERNAME")
password = os.getenv("PASSWORD")
telegram_bot_key = os.getenv("TELEGRAM_BOT")
MessageAlerts = os.getenv("MESSAGEALERTS")
APINAME = os.getenv("APINAME")
APIPASSWORD = os.getenv("APIPASSWORD")
auth = (APINAME, APIPASSWORD)




# Configure the Celery app
app = Celery(
    "tasks",
    broker="redis://redis:6379/0",  # Use the service name defined in docker-compose
    backend="redis://redis:6379/0",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)


def message_caculations(expression):
    pattern = r'[-+]?\d+(?:\.\d+)?\s*([+\-*/])\s*[-+]?\d+(?:\.\d+)?'
    while True:
        match = re.search(pattern, expression)
        if not match:
            break
        operator = match.group(1)
        operands = [Decimal(x) for x in match.group().split(operator)]
        if operator == '+':
            result = operands[0] + operands[1]
        elif operator == '-':
            result = operands[0] - operands[1]
        elif operator == '*':
            result = operands[0] * operands[1]
        elif operator == '/':
            result = operands[0] / operands[1]
        expression = expression.replace(match.group(), str(result), 1)
    return expression



@app.task(name='tasks.long_task')
def validate_in_background(message: str, name: str, to: str):
    if("api_" not in name):
        verification_code = re.search(r'\b(\d{6})\b', message)
        if verification_code:
            code = verification_code.group(1)
            print("Verification code:", code)
            current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            query = "INSERT INTO verification_logs (created_at, updated_at, email, verification_code) VALUES (:created_at, :updated_at, :email, :verification_code)"
            values = {"created_at": current_time, "updated_at": current_time, "email": to, "verification_code": code}

            execute_query(query, values)

                
                
    else:
        split_string = name.split(": ")
        api_id = split_string[1]
        print(api_id)  

        # Execute a SELECT query with a WHERE clause to check if the api_id exists in the api_keys table
        
        query = "SELECT service_type, user_id, status FROM api_keys WHERE api_key = :api_id"
        values = {"api_id": api_id}  # Named parameter for security
        results =  execute_query(query, values)
        print(results)

        # Check if an error occurred during the execution of the query
        if 1 == 2:
            print("Error executing the query.")
        else:
            # Fetch the results
    
            if len(results) == 0:
                print("API ID does not exist in the database.")
            else:
                
                service_type = results[0][0]
                user_id = results[0][1]
                status = results[0][2]
        
                query = "SELECT plan_expire_date, max_alerts, current_alerts, current_alert_date, plan_id FROM users WHERE id = :id"
                values = {"id": user_id}
                results =  execute_query(query, values)
                
                expire_date = results[0][0]
                max_alerts = results[0][1]
                current_alerts = results[0][2]
                current_date = results[0][3]

                plan_id  = results[0][4]


                query = "SELECT is_free FROM plans WHERE id = :id"
                values = {"id": plan_id}

                results =  execute_query(query, values)
                print(results)
                


                is_free = results[0][0]

                print("is free: " +  str(is_free) )
                today =dt.datetime.now().date()

           
                if today == current_date:
                    print("It is the same date.")
                else:
                    print(today)
                    print(current_date)
                    query = "UPDATE users SET current_alert_date = :current_alert_date, current_alerts = 0 WHERE id = :id"
                    values = {"current_alert_date": today, "id": user_id}
                    execute_query(query, values)
                    
                    current_date = today
                    current_alerts = 0




                if(current_alerts < max_alerts):
                    current_date = dt.date.today()

                    #expire_date = datetime.strptime(expire_date, "%Y-%m-%d").date()
                    if expire_date < current_date:
                        print(f"API ID exists in the database. Service type: {service_type}. Expire date: {expire_date}. (Expired)")
                    else:
                        print(f"API ID exists in the database. Service type: {service_type}. Expire date: {expire_date}. (Valid)")


                        if(status == 1):

                        
                            

                            #print("Alert is turned ON!")
                            print(user_id)

                            query = "UPDATE users SET current_alerts = current_alerts + 1 WHERE id = :id"
                            values = {"id": user_id}
                            execute_query(query, values)
                        
                            #do caculations in alert message
                            while True:
                                match = re.search(r'\([^()]+\)', message)
                                if match:
                                    expression_inside_parentheses = match.group()
                                    result_inside_parentheses = message_caculations(expression_inside_parentheses[1:-1])
                                    message = message.replace(expression_inside_parentheses, result_inside_parentheses)
                                else:
                                    message =message_caculations(message)
                                    break
                            try:
                                if 'round[' in message:
                                    message = re.sub(r'\bround\[ *(\d+\.?\d*), *(\d+)\]', r'round[\1, \2]', message)
                                    matches = re.findall(r'round\[([^\]]+),\s*(\d+)\]', message)
                                    for match in matches:
                                        value = Decimal(match[0])
                                        decimal_places = int(match[1])
                                        rounded_value = round(value, decimal_places)
                                        message = message.replace(f"round[{match[0]}, {match[1]}]", str(rounded_value))
                            except Exception as e:
                                print("rounding failed")


                            if(service_type in MessageAlerts):
                                #print("message alert")

                                if(service_type in MessageAlerts):
                                    function_name = "send_" + service_type
                                    if function_name in globals() and callable(globals()[function_name]):
                                        globals()[function_name](message, api_id)
                                                                        
                        

                            else:
                                
                                pattern = r'(?<==)\s+|\s+(?==)'
                                message = re.sub(pattern, '', message)
                                pairs = message.split()
                                values = {}
                                for pair in pairs:
                                    # Find the first occurrence of '=' in the pair
                                    equal_index = pair.find('=')
                                    if equal_index != -1:
                                        key = pair[:equal_index].strip()
                                        value = pair[equal_index+1:].strip()
                                        if key:
                                            values[key] = value

                                function_name = "send_" + service_type
                                if function_name in globals() and callable(globals()[function_name]):
                                    globals()[function_name](values, api_id, message)

                                
                                

                        
                    
                    
                        else:
                            1 == 1
                            #print("Alert is turned OFF!")
                        
                else:
                    print("alerts limit reached")

