FROM python:3.10-slim

WORKDIR /app

ENV PYTHONPATH=/app:${PYTHONPATH}

COPY ./ostools/requirements.txt .
COPY ./common ./common
COPY ./custom_log.py ./
COPY ./ostools/ .
COPY ostools/.env ./

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002", "--log-level", "info" ]