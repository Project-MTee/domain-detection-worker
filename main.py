import logging.config
from argparse import ArgumentParser, FileType

from domain_detection_worker import MQConsumer, DomainDetector, MQConfig, read_model_config


def parse_args():
    parser = ArgumentParser(
        description="A multilingual neural language model that detects the topic of incoming translation requests."
    )
    parser.add_argument('--model-config', type=FileType('r'), default='models/config.yaml',
                        help="The model config YAML file to load.")
    parser.add_argument('--log-config', type=FileType('r'), default='logging/logging.ini',
                        help="Path to log config file.")

    return parser.parse_args()


def main():
    args = parse_args()
    logging.config.fileConfig(args.log_config.name)
    model_config = read_model_config(args.model_config.name)
    mq_config = MQConfig()

    domain_detector = DomainDetector(model_config)
    consumer = MQConsumer(
        domain_detector=domain_detector,
        mq_config=mq_config
    )
    consumer.start()


if __name__ == "__main__":
    main()
