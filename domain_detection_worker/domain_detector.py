import logging
from transformers import XLMRobertaForSequenceClassification, AutoTokenizer
import torch
import numpy as np
from nltk import sent_tokenize

from .utils import Response, Request

logger = logging.getLogger("domain_detection")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

class DomainDetector:

    def __init__(self, labels: dict, checkpoint_path: str = "models/domain-detection-model"):
        self.labels = labels
        self.model = self._get_model(checkpoint_path)
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint_path)

    def _get_model(self, checkpoint_path: str):
        model = XLMRobertaForSequenceClassification.from_pretrained(checkpoint_path)
        model.to(DEVICE)
        model.eval()
        return model

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
        tokenized_sents = self.tokenizer(sentences, return_tensors="pt", truncation=True, padding=True, max_length=256)
        tokenized_sents.to(DEVICE)
        
        predictions = self.model(**tokenized_sents)
        predictions = predictions[0].cpu().data.numpy().argmax(axis=1)

        counts = np.bincount(predictions)

        return self.labels[np.argmax(counts)]

    def process_request(self, request: Request) -> Response:
        if type(request.text) == str:
            sentences = [request.text]
        else:
            sentences = [sentence for text in request.text for sentence in self._sentence_tokenize(text)]
        domain = self.predict(sentences)

        return Response(domain=domain)
