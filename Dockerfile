# Base Image 
FROM python:3.10

# Work Directory
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir log

COPY .env ./

COPY . .

CMD [ "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000" , "--log-level", "info"]
