import logging
from transformers import XLMRobertaForSequenceClassification, AutoTokenizer
import torch
import numpy as np
from nltk import sent_tokenize

from .config import ModelConfig
from .schemas import Response, Request

logger = logging.getLogger(__name__)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class DomainDetector:

    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config

        self.model = XLMRobertaForSequenceClassification.from_pretrained(self.model_config.checkpoint_dir)
        self.model.to(DEVICE)
        self.model.eval()

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_config.checkpoint_dir)

    @staticmethod
    def _sentence_tokenize(text: str) -> list:
        """
        Split text into sentences.
        """
        sentences = [sent.strip() for sent in sent_tokenize(text)]
        if len(sentences) == 0:
            return ['']

        return sentences

    def predict(self, sentences: list) -> str:
        tokenized_sents = self.tokenizer(sentences,
                                         return_tensors="pt",
                                         truncation=True,
                                         padding='max_length',
                                         max_length=256)
        tokenized_sents.to(DEVICE)
        
        predictions = self.model(**tokenized_sents)
        predictions = predictions[0].cpu().data.numpy().argmax(axis=1)

        counts = np.bincount(predictions)

        return self.model_config.labels[np.argmax(counts)]

    def process_request(self, request: Request) -> Response:
        if type(request.text) == str:
            sentences = [self._sentence_tokenize(request.text)]
        else:
            sentences = [sentence for text in request.text for sentence in self._sentence_tokenize(text)]
        domain = self.predict(sentences)

        return Response(domain=domain)
