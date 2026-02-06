from celery import Celery
import os

celery_app = Celery(
    "worker",
    broker=os.environ["CELERY_BROKER_URL"],
    backend=os.environ.get("CELERY_RESULT_BACKEND"),
)

celery_app.conf.update(include=["agent.indexing_agent"])