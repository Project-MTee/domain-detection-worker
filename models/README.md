# Domain detection models

Models can be attached to the main [domain-detection-worker](https://github.com/project-mtee/domain-detection-worker)
container by mounting a volume at `/app/models/`. Official models can be downloaded from the
[releases](https://github.com/project-mtee/domain-detection-worker/releases) section of this repository. Due to GitHub's
file size limitations, these may be uploaded as multipart zip files which have to unpacked first.

Alternatively, models are built into the [`domain-detection-model`](https://ghcr.io/project-mtee/domain-detection-model)
images published alongside this repository. These are `busybox` images that simply contain all model files in the
`/models/` directory. They can be used as init containers to populate the `/app/models/` volume of the
[`domain-detection-worker`](https://ghcr.io/project-mtee/domain-detection-worker) instance.

Each model is published as a separate image and corresponds to a specific release. Compatibility between
[`domain-detection-worker`](https://ghcr.io/project-mtee/domain-detection-worker) and
[`domain-detection-model`](https://ghcr.io/project-mtee/domain-detection-model) versions will be specified in the
release notes.

## Model configuration

By default, the `domain-detection-worker` looks for a `config.yaml` file on the `/app/models` volume (the `models/`
directory of the repository). This file should contain the following keys:

- `languages` - a list of supported languages
- `checkpoint_dir` - path of the directory that contains all model files (described below)
- `labels` - a mapping of label indexes to domain names

All file and directory paths must relative to the root directory of this repository. For more info check out
the [model training workflow](https://github.com/Project-MTee/domain-detection-scripts).

The included Dockerfile can be used to publish new model versions. The build-time argument `MODEL_DIR` can be used to
specify a subdirectory to be copied to `/models/` instead of the current directory.

### Configuration samples

Sample configuration for a model trained on 4 languages and 4 domain labels:

```
languages:
  - et
  - en
  - ru
  - de
checkpoint_dir: models/domain_detection_model/
labels:
  0: general
  1: crisis
  2: legal
  3: military
```

This corresponds to the following file structure:

```
models/
├── config.yaml
└── domain_detection_model/
    ├── config.json
    ├── optimizer.pt
    ├── pytorch_model.bin
    ├── rng_state.pth
    ├── scheduler.pt
    ├── special_tokens_map.json
    ├── tokenizer.json
    ├── tokenizer_config.json
    ├── trainer_state.json
    └── training_args.bin
```