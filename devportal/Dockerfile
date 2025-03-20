FROM python:3.10

WORKDIR /app

ENV PYTHONPATH=/app:${PYTHONPATH}

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY .env ./

COPY . .

CMD [ "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "info" ]

