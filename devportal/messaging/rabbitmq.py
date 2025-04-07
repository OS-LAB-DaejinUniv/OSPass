import pika
from pika.exceptions import AMQPConnectionError, AMQPError
import os
import time
from dotenv import load_dotenv

load_dotenv()

class RabbitMQ:
    def __init__(self, max_retries=3):
        self.url = os.getenv("RabbitMQ_SERVER")
        self.params = pika.URLParameters(self.url)
        self.connection = None
        self.channel = None
        self.max_retries = max_retries # 재시도 횟수
        
        try:
            self._connect()
        except pika.exceptions.AMQPConnectionError as e:
            print(f"[ERROR] RabbitMQ 연결 실패: {e}")
            raise
    
    def _connect(self):
        """
        RabbitMQ Connection Method
        """
        for attempt in range(self.max_retries):
            try:
                self.connection = pika.BlockingConnection(self.params)
                self.channel = self.connection.channel()
                print("RabbitMQ 연결 성공")
                return
            except pika.exceptions.AMQPError as e:
                if attempt == self.max_retries -1:
                    raise
                sleep_time = 2 ** attempt
                print(f"[WARN] 재연결 시도 {attempt+1}/{self.max_retries} ({sleep_time})초 후")
                time.sleep(sleep_time)
    
    def declare_queue(self,queue_name):
        """
        Queue Declare Method
        durable = True : 영속성 True
        """
        try:
            self.channel.queue_declare(queue=queue_name, durable=True)
        except pika.exceptions.AMQPError as e:
            print(f"[ERROR] 큐 선언 중 오류: {e}")
            raise
    
    def publish(self, queue_name, message):
        """
        Data Send to Broker(RMQ)
        """
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)  # 영속성
            )
            print(f"메시지 전송됨: {message}")
        except pika.exceptions.AMQPError as e:
            print(f"[ERROR] 메시지 전송 실패: {e}")
            raise
        
    def close(self):
        """
        RabbitMQ Connection Closed
        """
        if self.connection:
            self.connection.close()
            print("RabbitMQ 연결 종료")
            
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("RabbitMQ 연결 종료")