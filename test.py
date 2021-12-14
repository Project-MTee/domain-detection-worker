import unittest

from domain_detection_worker import DomainDetector, read_model_config
from domain_detection_worker.schemas import Response, Request

model_config = read_model_config('models/config.yaml')
domain_detector = DomainDetector(model_config)


class DomainDetectionTests(unittest.TestCase):
    def test_prediction(self):
        """
        Check that prediction a list of sentences returns a valid prediction label.
        """
        text = ["Eesti on iseseisev ja sõltumatu demokraatlik vabariik, kus kõrgeima riigivõimu kandja on rahvas.",
                "Eesti iseseisvus ja sõltumatus on aegumatu ning võõrandamatu."]
        prediction = domain_detector.predict(text)
        self.assertIn(prediction, domain_detector.model_config.labels.values())

    def test_request_response(self):
        """
        Check that a response object is returned upon request.
        """
        request = Request(text=["Eesti on iseseisev ja sõltumatu demokraatlik vabariik, kus kõrgeima riigivõimu "
                                "kandja on rahvas. Eesti iseseisvus ja sõltumatus on aegumatu ning võõrandamatu."],
                          src="et")
        response = domain_detector.process_request(request)
        self.assertIsInstance(response, Response)


if __name__ == '__main__':
    unittest.main()
