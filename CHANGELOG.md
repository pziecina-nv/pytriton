<!--
Copyright (c) 2022, NVIDIA CORPORATION. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Changelog

## Unreleased

- Fixed handling `TritonConfig.cache_directory` option - the directory was always overwritten with the default value.
- Fixed tritonclient dependency - PyTriton need tritonclient supporting http headers and parameters

[//]: <> (put here on external component update with short summary what change or link to changelog)

- Version of [Triton Inference Server](https://github.com/triton-inference-server/) embedded in wheel: [2.33.0](https://github.com/triton-inference-server/server/releases/tag/v2.33.0)

## 0.2.0 (2023-05-30)

- Added support for using custom HTTP/gRPC request headers and parameters.

  This change breaks backward compatibility of the inference function signature.
  The undecorated inference function now accepts a list of `Request` instances instead
  of a list of dictionaries. The `Request` class contains data for inputs and parameters
  for combined parameters and headers.

  See [docs/custom_params.md](docs/custom_params.md) for further information

- Added `FuturesModelClient` which enables sending inference requests in a parallel manner.
- Added displaying documentation link after models are loaded.

[//]: <> (put here on external component update with short summary what change or link to changelog)

- Version of [Triton Inference Server](https://github.com/triton-inference-server/) embedded in wheel: [2.33.0](https://github.com/triton-inference-server/server/releases/tag/v2.33.0)

## 0.1.5 (2023-05-12)

- Improved `pytriton.decorators.group_by_values` function
  - Modified the function to avoid calling the inference callable on each individual sample when grouping by string/bytes input
  - Added `pad_fn` argument for easy padding and combining of the inference results
- Fixed Triton binaries search
- Improved Workspace management (remove workspace on shutdown)

[//]: <> (put here on external component update with short summary what change or link to changelog)

- Version of external components used during testing:
  - [Triton Inference Server](https://github.com/triton-inference-server/): 2.29.0
  - Other component versions depend on the used framework and Triton Inference Server containers versions.
    Refer to its [support matrix](https://docs.nvidia.com/deeplearning/frameworks/support-matrix/index.html)
    for a detailed summary.

## 0.1.4 (2023-03-16)

- Add validation of the model name passed to Triton bind method.
- Add monkey patching of `InferenceServerClient.__del__` method to prevent unhandled exceptions.

[//]: <> (put here on external component update with short summary what change or link to changelog)

- Version of external components used during testing:
  - [Triton Inference Server](https://github.com/triton-inference-server/): 2.29.0
  - Other component versions depend on the used framework and Triton Inference Server containers versions.
    Refer to its [support matrix](https://docs.nvidia.com/deeplearning/frameworks/support-matrix/index.html)
    for a detailed summary.

## 0.1.3 (2023-02-20)

- Fixed getting model config in `fill_optionals` decorator.

[//]: <> (put here on external component update with short summary what change or link to changelog)

- Version of external components used during testing:
  - [Triton Inference Server](https://github.com/triton-inference-server/): 2.29.0
  - Other component versions depend on the used framework and Triton Inference Server containers versions.
    Refer to its [support matrix](https://docs.nvidia.com/deeplearning/frameworks/support-matrix/index.html)
    for a detailed summary.

## 0.1.2 (2023-02-14)

- Fixed wheel build to support installations on operating systems with glibc version 2.31 or higher.
- Updated the documentation on custom builds of the package.
- Change: TritonContext instance is shared across bound models and contains model_configs dictionary.
- Fixed support of binding multiple models that uses methods of the same class.

[//]: <> (put here on external component update with short summary what change or link to changelog)

- Version of external components used during testing:
  - [Triton Inference Server](https://github.com/triton-inference-server/): 2.29.0
  - Other component versions depend on the used framework and Triton Inference Server containers versions.
    Refer to its [support matrix](https://docs.nvidia.com/deeplearning/frameworks/support-matrix/index.html)
    for a detailed summary.

## 0.1.1 (2023-01-31)

- Change: The `@first_value` decorator has been updated with new features:
  - Renamed from `@first_values` to `@first_value`
  - Added a `strict` flag to toggle the checking of equality of values on a single selected input of the request. Default is True
  - Added a `squeeze_single_values` flag to toggle the squeezing of single value ND arrays to scalars. Default is True
- Fix: `@fill_optionals` now supports non-batching models
- Fix: `@first_value` fixed to work with optional inputs
- Fix: `@group_by_values` fixed to work with string inputs
- Fix: `@group_by_values` fixed to work per sample-wise

[//]: <> (put here on external component update with short summary what change or link to changelog)

- Version of external components used during testing:
  - [Triton Inference Server](https://github.com/triton-inference-server/): 2.29.0
  - Other component versions depend on the used framework and Triton Inference Server containers versions.
    Refer to its [support matrix](https://docs.nvidia.com/deeplearning/frameworks/support-matrix/index.html)
    for a detailed summary.

## 0.1.0 (2023-01-12)

- Initial release of PyTriton

[//]: <> (put here on external component update with short summary what change or link to changelog)

- Version of external components used during testing:
  - [Triton Inference Server](https://github.com/triton-inference-server/): 2.29.0
  - Other component versions depend on the used framework and Triton Inference Server containers versions.
    Refer to its [support matrix](https://docs.nvidia.com/deeplearning/frameworks/support-matrix/index.html)
    for a detailed summary.
