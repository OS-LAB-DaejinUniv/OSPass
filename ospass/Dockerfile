# python3.10-slim : 불필요 패키지 제거 -> 이미지 크기 최적화
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONPATH=/app:${PYTHONPATH}

COPY ./ospass/requirements.txt .
COPY ./common ./common
COPY ./custom_log.py ./
COPY ./ospass/ .
COPY ospass/.env ./

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info" ]