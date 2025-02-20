from celery import Celery
import time

# Configure the Celery app
app = Celery(
    "tasks",
    broker="redis://redis:6379/0",  # Use the service name defined in docker-compose
    backend="redis://redis:6379/0",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

@app.task
def long_task():
    """A long-running task simulation."""
    items = range(1, 6)  # Simulating work with 5 items
    results = []

    for item in items:
        # Simulate doing some work with each item
        time.sleep(1)  # Simulate a time-consuming operation
        results.append({"item": item, "status": "processed"})
        print(f"Processed item: {item}")

    return {"message": "Task completed", "results": results}
