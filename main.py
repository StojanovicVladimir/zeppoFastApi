from fastapi import FastAPI
from tasks import long_task

app = FastAPI()

@app.get("/send-task/")
async def send_task():
    """Endpoint to send a long task to Celery."""
    result = long_task.delay()  # Send the task to Celery
    return {"task_id": result.id, "status": "Task sent!"}

@app.get("/task-status/{task_id}")
async def task_status(task_id: str):
    """Check the status of a given task."""
    result = long_task.AsyncResult(task_id)
    return {"task_id": task_id, "status": result.status, "result": result.result}
