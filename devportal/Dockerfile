FROM python:3.10

WORKDIR /app

ENV PYTHONPATH=/app:${PYTHONPATH}

COPY ./devportal/requirements.txt .
COPY ./common ./common
COPY ./custom_log.py ./
COPY ./devportal/ .
COPY devportal/.env ./

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "info" ]

