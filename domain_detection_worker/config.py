import yaml
from yaml.loader import SafeLoader
from typing import List, Dict, Optional, Any

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
    heartbeat: int = 60
    connection_name: str = 'Domain detection worker'

    class Config:
        env_prefix = 'mq_'


class WorkerConfig(BaseSettings):
    """
    Imports general workr configuration from environment variables
    """
    max_input_length: int = 2000

    class Config:
        env_prefix = 'worker_'


class ModelConfig(BaseModel):
    languages: List[str]

    huggingface: Optional[str] = None
    model_root: Optional[str] = None
    checkpoint_dir: Optional[str] = None  # for backwards compatibility

    labels: Dict[int, str] = {}
    default_label_id: int = 0

    def __init__(self, **data: Any):
        super().__init__(**data)
        if self.checkpoint_dir is not None and self.model_root is None:
            self.model_root = self.checkpoint_dir


def read_model_config(file_path: str) -> ModelConfig:
    with open(file_path, 'r', encoding='utf-8') as f:
        model_config = ModelConfig(**yaml.load(f, Loader=SafeLoader))

    return model_config


mq_config = MQConfig()
worker_config = WorkerConfig()
