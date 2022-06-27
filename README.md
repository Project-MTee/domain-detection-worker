# Domain Detection Worker

A component that automatically detects the domain of a given text which can be used to route translation request to the
correct domain-specific machine translation model. The worker processes domain detection requests via RabbitMQ.

The model is a fine-tuned version of [XLM-RoBERTa](https://huggingface.co/transformers/model_doc/xlmroberta.html) which
is a large multilingual language model created by Facebook AI.

Instructions to train a new domain detection model can be
found [here](https://github.com/Project-MTee/domain-detection-scripts).

## Setup

The worker can be used by running the
prebuilt [`domain-detection-worker`](https://ghcr.io/project-mtee/domain-detection-worker) docker image published
alongside this repository. This image contains both the code and models (starting from version 1.2.0), and is designed
to be used in a CPU environment. Additional details about configuring the models can be found
in [`models/README.md`](https://github.com/project-mtee/domain-detection-worker/tree/main/models).

When building the image, the following arguments are used:

- `HF_MODEL` (optional) - a HuggingFace model
  identifyer ([`tartuNLP/mtee-domain-detection`](https://huggingface.co/tartuNLP/mtee-domain-detection) by
  default). The model is automatically downloaded from HuggingFace during the build phase.

The container should be configured using the following parameters:

- Environment variables:
    - Variables that configure the connection to a [RabbitMQ message broker](https://www.rabbitmq.com/):
        - `MQ_USERNAME` - RabbitMQ username
        - `MQ_PASSWORD` - RabbitMQ user password
        - `MQ_HOST` - RabbitMQ host
        - `MQ_PORT` (optional) - RabbitMQ port (`5672` by default)
        - `MQ_EXCHANGE` (optional) - RabbitMQ exchange name (`domain-detection` by default)
        - `MQ_CONNECTION_NAME` (optional) - friendly connection name (`Domain detection worker` by default)
        - `MQ_HEARTBEAT` (optional) - heartbeat interval (`60` seconds by default)
    - PyTorch-related variables:
        - `MKL_NUM_THREADS` (optional) - number of threads used for intra-op parallelism by PyTorch. This defaults
          to
          the number of CPU cores which may cause computational overhead when deployed on larger nodes.
          Alternatively,
          the `docker run` flag `--cpuset-cpus` can be used to control this. For more details, refer to
          the [performance and hardware requirements](#performance-and-hardware-requirements) section below.
    - Other variables:
        - `WORKER_MAX_INPUT_LENGTH` (optional) - the number of characters allowed per request (`2000` by default).
          Longer requests will be processed but only the first characters will be considered. By increasing this limit,
          more memory needs to be allocated to the container.

- Optional runtime flags (`COMMAND` options):
    - `--model-config` - path to the model config file (`models/config.yaml` by default), the default file is already
      included and the format described
      in [`models/README.md`](https://github.com/project-mtee/domain-detection-worker/tree/main/models).
    - `--log-config` - path to logging config files (`logging/logging.ini` by default), `logging/debug.ini` can be used
      for debug-level logging
    - `--port` - port of the healthcheck probes (`8000` by default):

- Endpoints for healthcheck probes:
    - `/health/startup`
    - `/health/readiness`
    - `/health/liveness`

### Building new images

When building the image, the model can be built with different targets. BuildKit should be enabled to skip any unused
stages of the build.

- `worker-base` - the worker code without any models.
- `worker-model` - a worker with an included model. Requires **one** of the following build-time arguments:
    - `MODEL_IMAGE` - the image name where the model is copied from. For example any of
      the [`domain-detection-model`](https://ghcr.io/project-mtee/domain-detection-model) images.
    - `MODEL_CONFIG_FILE` - path to the model configuration file, for example `models/general.yaml`. The file must
      contain the otherwise optional key `huggingface` to download the model or the build will fail.

- `env` - an intermediate build stage with all packages installed, but no code.
- `model-dl` - images that only contain model files and configuration. The separate stage is used to cache this step and
  speed up builds because HuggingFace downloads can be very slow compared to copying model files from a build stage.
  Published at [`domain-detection-model`](https://ghcr.io/project-mtee/domain-detection-model). Alternatively, these can
  be used as init containers to copy models over during startup, but this is quite slow and not recommended.
- `model` - an alias for the model image, the value of `MODEL_IMAGE` or `model-dl` by default.

### Performance and hardware requirements

The worker loads the XLM-R model into memory. An estimate is to have **6 GB of memory** available. More memory is
required if the `WORKER_MAX_INPUT_LENGTH` variable is increased.

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

### Manual / development setup

For a manual setup, please refer to the included Dockerfile and the environment specification described in
`requirements/requirements.txt`.
Additionally, [`models/README.md`](https://github.com/project-mtee/domain-detection-worker/tree/main/models) describes
how models should be set up correctly.

To initialize the sentence splitting functionality, the following command should be run before starting the application:

```python -c "import nltk; nltk.download(\"punkt\")"```

RabbitMQ and PyTorch parameters should be configured with environment variables as described above. The worker can be
started with:

```python main.py [--model-config models/config.yaml --log-config logging/logging.ini --port 8000]```

## Request Format

The worker consumes domain detection requests from a RabbitMQ message broker and responds with the detected domain name.
The following format is compatible with
the [text translation service](https://ghcr.io/project-mtee/translation-api-service).

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
