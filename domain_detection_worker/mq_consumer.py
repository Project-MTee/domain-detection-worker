import json
import logging
import hashlib
from sys import getsizeof
from time import time, sleep

import pika
import pika.exceptions
from pika import credentials, BlockingConnection, ConnectionParameters

from domain_detection_worker.schemas import Response, Request
from domain_detection_worker.domain_detector import DomainDetector
from domain_detection_worker.config import MQConfig

logger = logging.getLogger(__name__)


class MQConsumer:
    def __init__(self, domain_detector: DomainDetector, mq_config: MQConfig):
        """
        Initializes a RabbitMQ consumer class that listens for requests for a specific worker and responds to
        them.
        """
        self.mq_config = mq_config
        self.domain_detector = domain_detector
        self.routing_keys = []
        self.queue_name = None
        self.channel = None

        self._generate_queue_config()

    def _generate_queue_config(self):
        routing_keys = []
        for language in self.domain_detector.model_config.languages:
            routing_keys.append(f'{self.mq_config.exchange}.{language}')
        self.routing_keys = sorted(routing_keys)
        hashed = hashlib.sha256(str(self.routing_keys).encode('utf-8')).hexdigest()[:8]
        self.queue_name = f'{self.mq_config.exchange}_{hashed}'

    def start(self):
        """
        Connect to RabbitMQ and start listening for requests. Automatically tries to reconnect if the connection
        is lost.
        """
        while True:
            try:
                self._connect()
                logger.info('Ready to process requests.')
                self.channel.start_consuming()
            except pika.exceptions.AMQPConnectionError as e:
                logger.error(e)
                logger.info('Trying to reconnect in 5 seconds.')
                sleep(5)
            except KeyboardInterrupt:
                logger.info('Interrupted by user. Exiting...')
                self.channel.close()
                break

    def _connect(self):
        """
        Connects to RabbitMQ, (re)declares the exchange for the service and a queue for the worker binding
        any alternative routing keys as needed.
        """
        logger.info(f'Connecting to RabbitMQ server: {{host: {self.mq_config.host}, port: {self.mq_config.port}}}')
        connection = BlockingConnection(ConnectionParameters(
            host=self.mq_config.host,
            port=self.mq_config.port,
            credentials=credentials.PlainCredentials(
                username=self.mq_config.username,
                password=self.mq_config.password
            ),
            heartbeat=self.mq_config.heartbeat,
            client_properties={
                'connection_name': self.mq_config.connection_name
            }
        ))
        self.channel = connection.channel()
        self.channel.queue_declare(queue=self.queue_name)
        self.channel.exchange_declare(exchange=self.mq_config.exchange, exchange_type='direct')

        for route in self.routing_keys:
            self.channel.queue_bind(exchange=self.mq_config.exchange, queue=self.queue_name,
                                    routing_key=route)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self._on_request)

    @staticmethod
    def _respond(channel: pika.adapters.blocking_connection.BlockingChannel, method: pika.spec.Basic.Deliver,
                 properties: pika.BasicProperties, body: bytes):
        """
        Publish the response to the callback queue and acknowledge the original queue item.
        """
        channel.basic_publish(exchange='',
                              routing_key=properties.reply_to,
                              properties=pika.BasicProperties(
                                  correlation_id=properties.correlation_id,
                                  content_type='application/json',
                                  headers={
                                      'RequestId': properties.headers["RequestId"],
                                      'MT-MessageType': properties.headers["ReturnMessageType"]
                                  }),
                              body=body)
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def _on_request(self, channel: pika.adapters.blocking_connection.BlockingChannel, method: pika.spec.Basic.Deliver,
                    properties: pika.BasicProperties, body: bytes):
        """
        Pass the request to the worker and return its response.
        """
        t1 = time()
        logger.info(f"Received request: {{id: {properties.correlation_id}, size: {getsizeof(body)} bytes}}")
        try:
            request = json.loads(body)
            request = Request(**request)
            response = self.domain_detector.process_request(request)
        except Exception as e:
            logger.exception(e)
            response = Response()

        response = response.encode()
        response_size = getsizeof(response)

        self._respond(channel, method, properties, response)
        t2 = time()

        logger.info(f"Request processed: {{id: {properties.correlation_id}, duration: {round(t2 - t1, 3)} s, "
                    f"size: {response_size} bytes}}")
