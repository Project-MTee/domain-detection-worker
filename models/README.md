# Domain detection models

Models are included in some [domain-detection-worker](https://github.com/project-mtee/domain-detection-worker)
images, or they can be attached to the base image by mounting a volume at `/app/models/`. If a model is not found, the
worker will try to download it from HuggingFace upon startup, and it will be cached
in `~/.cache/huggingface/transformers/`. The official model can be found
in [HuggingFace](https://huggingface.co/tartuNLP/mtee-domain-detection).

Some model parameters are loaded from `models/config.yaml` (or a different file set by the `--model-config` flag). The
file may contain the following parameters:

- `huggingface` (optional) - a HuggingFace model ID. This is used during model build to download the model or upon
  startup if a model does not exist.
- `model_root` - a path where the model is loaded from. This path should be absolute or relative to the root
  directory of this repository. During the build phase, the model is stored in this path, however, if a model is
  downloaded upon startup, it is cached in the default `~/.cache/huggingface/transformers/` directory instead.
- `checkpoint_dir` (optional) - alias to `model_root` for backwards compatibility.
- `languages` - a list of language codes that the model supports.
- `labels` (optional) - a mapping between model predictions and labels. By default, the `id2label` value of the
  model's `config.json` file is used instead.
- `default_label_id` (optional) - default model output ID. `0` by default.

The model must be an XLMRoberta sequence classification model and the directory should contain the following files:

```
config.json
pytorch_model.bin
special_tokens_map.json
tokenizer.json
tokenizer_config.json
```

# Configuration samples

Sample configuration for a locally saved model trained on 4 languages and 4 domain labels can be seen below. Only
the `languages` parameter is required, others are optional (label values will otherwise be imported from `config.json`
in the checkpoint directory).

```yaml
huggingface: tartuNLP/mtee-domain-detection
model_root: models/tartuNLP/mtee-domain-detection
languages:
  - et
  - en
  - ru
  - de
labels:
  0: general
  1: crisis
  2: legal
  3: military
default_label_id: 0
```

This corresponds to the following file structure:

```
models/
├── config.yaml
└── tartuNLP/
    └── mtee-domain-detection/
        ├── config.json
        ├── pytorch_model.bin
        ├── special_tokens_map.json
        ├── tokenizer.json
        └── tokenizer_config.json
```