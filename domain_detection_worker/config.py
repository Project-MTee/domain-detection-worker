import yaml
from yaml.loader import SafeLoader
from typing import List, Dict

from pydantic import BaseSettings, BaseModel


class MQConfig(BaseSettings):
    """
    Imports MQ configuration from environment variables
    """
    host: str = 'localhost'
    port: int = 5672
    username: str = 'guest'
    password: str = 'guest'
    exchange: str = 'domain-detection'
    heartbeat: int = 30
    connection_name: str = 'Domain detection worker'

    class Config:
        env_prefix = 'mq_'


class ModelConfig(BaseModel):
    languages: List[str]
    labels: Dict[int, str]
    checkpoint_dir: str = "models/"


def read_model_config(file_path: str) -> ModelConfig:
    with open(file_path, 'r', encoding='utf-8') as f:
        model_config = ModelConfig(**yaml.load(f, Loader=SafeLoader))

    return model_config
