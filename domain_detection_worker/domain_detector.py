import logging
from typing import Dict

from transformers import XLMRobertaForSequenceClassification, AutoTokenizer, AutoConfig
import torch
import numpy as np
from nltk import sent_tokenize

from .config import ModelConfig, worker_config
from .schemas import Response, Request

logger = logging.getLogger(__name__)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class DomainDetector:
    labels: Dict[int, str]
    model_src: str

    def __init__(self, model_config: ModelConfig):

        if model_config.model_root:
            logger.info(f"Loading a model from \"{model_config.model_root}\"")
            self.model_src = model_config.model_root
        elif model_config.huggingface:
            logger.info(f"Downloading a model from \"{model_config.huggingface}\"")
            self.model_src = model_config.huggingface
        else:
            raise ValueError("No model path or repository specified.")

        self.model = XLMRobertaForSequenceClassification.from_pretrained(self.model_src)

        self.model.to(DEVICE)
        self.model.eval()

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_src)

        self.languages = model_config.languages

        if model_config.labels:
            self.labels = model_config.labels
        else:
            self.labels = AutoConfig.from_pretrained(self.model_src).id2label

        self.default_label = self.labels[model_config.default_label_id]

        logger.info(f"All models loaded for languages \"{self.languages}\" and domains {self.labels}.")
        logger.info(f"Default label: {self.default_label}.")

    @staticmethod
    def _sentence_tokenize(text: str) -> list:
        """
        Split text into sentences.
        """
        text = text[:worker_config.max_input_length]
        sentences = [sent.strip() for sent in sent_tokenize(text)]
        if len(sentences) == 0:
            return ['']

        if len(text) > len(text[:worker_config.max_input_length]):
            sentences = sentences[-1]

        return sentences

    def predict(self, sentences: list) -> str:
        logger.debug(f"Input sentences: {sentences}")
        tokenized_sents = self.tokenizer(sentences,
                                         return_tensors="pt",
                                         truncation=True,
                                         padding='max_length',
                                         max_length=256)
        tokenized_sents.to(DEVICE)

        predictions = self.model(**tokenized_sents)
        predictions = predictions[0].cpu().data.numpy().argmax(axis=1)

        counts = np.bincount(predictions)
        label = self.labels[np.argmax(counts)]

        logger.debug(f"Predicted domain: {label}")

        return self.labels[np.argmax(counts)]

    def process_request(self, request: Request) -> Response:
        if type(request.text) == str:
            sentences = self._sentence_tokenize(request.text)
        else:
            sentences = self._sentence_tokenize(' '.join(request.text))

        domain = self.predict(sentences)

        return Response(domain=domain)
