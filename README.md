# Domain Detection Worker

A component that automatically detects the domain of a given text which can be used to route translation request to the
correct domain-specific machine translation model. The worker processes domain detection requests via RabbitMQ.

The model is a fine-tuned version of XLM-RoBERTa which is a large multi-lingual language model created by Facebook AI.
We use model version available in [HuggingFace](https://huggingface.co/transformers/model_doc/xlmroberta.html).

Instructions to train a new domain detection model can be
found [here](https://github.com/Project-MTee/domain-detection-scripts).

## Setup

The worker can be used by running the prebuilt docker images published alongside this repository. The container is
designed to run in a CPU environment.

The worker can be set up using the
[`domain-detection-worker`](https://ghcr.io/project-mtee/domain-detection-worker) image. This image contains only the
environment setup and code to run the models, and is designed to be used in a CPU environment. The container should be
configured using the following parameters:

- Volumes:
    - `/app/models/` - the image does not contain the model files and these must be attached as described in
      [`models/README.md`](https://github.com/project-mtee/domain-detection-worker/tree/main/models).

- Environment variables:
    - Variables that configure the connection to a [RabbitMQ message broker](https://www.rabbitmq.com/):
        - `MQ_USERNAME` - RabbitMQ username
        - `MQ_PASSWORD` - RabbitMQ user password
        - `MQ_HOST` - RabbitMQ host
        - `MQ_PORT` (optional) - RabbitMQ port (`5672` by default)
        - `MQ_EXCHANGE` (optional) - RabbitMQ exchange name (`translation` by default)
        - `MQ_CONNECTION_NAME` (optional) - friendly connection name (`Translation worker` by default)
        - `MQ_HEARTBEAT` (optional) - heartbeat interval (`30` seconds by default)
    - PyTorch-related variables:
        - `MKL_NUM_THREADS` (optional) - number of threads used for intra-op parallelism by PyTorch. This defaults to
          the number of CPU cores which may cause computational overhead when deployed on larger nodes. Alternatively,
          the `docker run` flag `--cpuset-cpus` can be used to control this. For more details, refer to
          the [performance and hardware requirements](#performance-and-hardware-requirements) section below.

By default, the container entrypoint is `main.py` without additional arguments, but these can be defined with the
`COMMAND` option. For example by using `["--log-config", "logging/debug.ini"]` to enable debug level logging.

## Manual setup

For a manual setup, please refer to the included Dockerfile and the environment specification described in
`requirements/requirements.txt`. Alternatively, the included `requirements/environment.yml` can be used to install the
requirements using Conda. Additionally,
[`models/README.md`](https://github.com/project-mtee/domain-detection-worker/models) describes how models should be set
up correctly.

To initialize the sentence splitting functionality, the following command should be run before starting the application:

```python -c "import nltk; nltk.download(\"punkt\")"```

RabbitMQ and PyTorch parameters should be configured with environment variables as described above. The worker can be
started with:

```python main.py [--model-config models/config.yaml] [--log-config logging/logging.ini]```

## Performance and hardware requirements

The worker loads the XLM-R model into memory. A conservative estimate is to have **6 GB of memory** available.

The performance depends on the available CPU resources, however, this should be finetuned for the deployment
infrastructure. By default, PyTorch will try to utilize all CPU cores to 100% and run as many threads as there are
cores. This can cause major computational overhead if the worker is deployed on large nodes. The **number of threads
used should be limited** using the `MKL_NUM_THREADS` environment variable or the `docker run` flag `--cpuset-cpus`.

Limiting CPU usage by docker configuration which only limits CPU shares is not sufficient (e.g. `docker run` flag
`--cpus` or the CPU limit in K8s, unless the non-default
[static CPU Manager policy](https://kubernetes.io/docs/tasks/administer-cluster/cpu-management-policies/) is used). For
example, on a node with 128 cores, setting the CPU limit at `16.0` results in 128 parallel threads running with each one
utilizing only 1/8 of each core's computational potential. This amplifies the effect of multithreading overhead and can
result in inference speeds up to 20x slower than expected.

Although the optimal number of threads depends on the exact model and infrastructure used, a good starting point is
around `16`. With optimal configuration and modern hardware, the worker should be able to process ~7 sentences per
second. For more information, please refer to
[PyTorch documentation](https://pytorch.org/docs/stable/notes/cpu_threading_torchscript_inference.html).

### Request Format

The worker consumes domain detection requests from a RabbitMQ message broker and responds with the detected domain name.
The following format is compatible with the [text translation API](https://ghcr.io/project-mtee/text-translation-api).

Requests should be published with the following parameters:

- Exchange name: `domain-detection` (exchange type is `direct`)
- Routing key: `domain-detection.<src>` where `<src>` refers to 2-letter ISO language code of the given text. For
  example `domain-detection.et`
- Message properties:
    - Correlation ID - a UID for each request that can be used to correlate requests and responses.
    - Reply To - name of the callback queue where the response should be posted.
    - Content Type - `application/json`
    - Headers:
        - `RequestId`
        - `ReturnMessageType`
- JSON-formatted message content with the following keys:
    - `text` – input text, either a string or a list of strings which are allowed to contain multiple sentences or
      paragraphs.
    - `src` – 2-letter ISO language code

The worker will return a response with the following parameters:

- Exchange name: (empty string)
- Routing key: the Reply To property value from the request
- Message properties:
    - Correlation ID - the Correlation ID value of the request
    - Content Type - `application/json`
    - Headers:
        - `RequestId` - the `RequestId` value of the request
        - `MT-MessageType` - the `ReturnMessageType` value of the request
- JSON-formatted message content with the following keys:
    - `domain` – name of the detected domain (`general`, `legal`, `crisis` or `military`). In case of any exceptions,
      the worker will default to `general`.
