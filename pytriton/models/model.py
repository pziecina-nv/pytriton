# Copyright (c) 2022, NVIDIA CORPORATION. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Model base class."""
import copy
import enum
import logging
import pathlib
import shutil
import threading
import typing
from typing import Callable, Optional, Sequence, Union

import zmq

from pytriton.decorators import TritonContext
from pytriton.exceptions import PyTritonValidationError
from pytriton.model_config.generator import ModelConfigGenerator
from pytriton.model_config.model_config import ModelConfig
from pytriton.model_config.tensor import Tensor
from pytriton.model_config.triton_model_config import DeviceKind, ResponseCache, TensorSpec, TritonModelConfig
from pytriton.proxy.inference_handler import InferenceHandler, InferenceHandlerEvent
from pytriton.utils.workspace import Workspace

LOGGER = logging.getLogger(__name__)


class ModelEvent(enum.Enum):
    """Represents model event."""

    RUNTIME_TERMINATING = "runtime-terminating"
    RUNTIME_TERMINATED = "runtime-terminated"


ModelEventsHandler = typing.Callable[["Model", ModelEvent, typing.Optional[typing.Any]], None]


def _inject_triton_context(triton_context: TritonContext, model_callable: Callable) -> Callable:
    """Inject triton context into callable.

    Args:
        triton_context: Triton context
        model_callable: Callable to inject triton context

    Returns:
        Callable with injected triton context
    """
    if hasattr(model_callable, "__self__"):
        model_callable.__self__.__triton_context__ = triton_context
    else:
        model_callable.__triton_context__ = triton_context
    return model_callable


class Model:
    """Model definition."""

    def __init__(
        self,
        model_name: str,
        model_version: int,
        inference_fn: Union[Callable, Sequence[Callable]],
        inputs: Sequence[Tensor],
        outputs: Sequence[Tensor],
        config: ModelConfig,
        workspace: Workspace,
        triton_context: TritonContext,
    ):
        """Create Python model with required data.

        Args:
            model_name: Model name
            model_version: Model version
            inference_fn: Inference handler (function or lambda)
            inputs: Model inputs definition
            outputs: Model outputs definition
            config: model configuration parameters
            workspace: workspace for storing artifacts

        Raises:
            PyTritonValidationError if one or more of provided values are incorrect.
        """
        self.triton_context = triton_context
        self.model_name = model_name
        self.model_version = model_version
        self._inference_handlers = []
        self.zmq_context = zmq.Context()
        self._observers_lock = threading.Lock()
        self._inference_handlers_lock = threading.Lock()

        self.infer_functions = [inference_fn] if isinstance(inference_fn, Callable) else inference_fn
        if not isinstance(self.infer_functions, (Sequence, Callable)):
            raise PyTritonValidationError("inference_fn has to be either callable or sequence of callables")

        self.inputs = inputs
        self.outputs = outputs

        if any(output.optional for output in self.outputs):
            raise PyTritonValidationError("Output tensors cannot be optional.")

        self.config = config
        self._workspace = workspace
        ipc_socket_path = self._workspace.path / f"ipc_proxy_backend_{model_name}"
        self._shared_memory_socket = f"ipc://{ipc_socket_path.as_posix()}"
        self._triton_model_config: Optional[TritonModelConfig] = None
        self._model_events_observers: typing.List[ModelEventsHandler] = []

    def generate_model(self, model_repository: pathlib.Path) -> None:
        """Generate model and its config in the model repository.

        Args:
            model_repository: Path to Triton model repository

        Raises:
            OSError: when model repository not exists
        """
        LOGGER.debug(
            f"Generating model and config for {self.model_name} and {self.model_version} to {model_repository}"
        )

        model_catalog = model_repository / self.model_name

        config_file_path = model_catalog / "config.pbtxt"
        if config_file_path.exists():
            LOGGER.warning(f"The config file {config_file_path} is going to be overridden.")

        triton_model_config = self._get_triton_model_config()
        generator = ModelConfigGenerator(config=triton_model_config)
        generator.to_file(config_file_path)

        model_version_catalog = model_catalog / str(self.model_version)
        model_version_catalog.mkdir(exist_ok=True, parents=True)

        proxy_path = pathlib.Path(__file__).parent.parent / "proxy"

        files_to_copy = ["model.py", "communication.py", "types.py"]
        for file in files_to_copy:
            src_file_path = proxy_path / file
            dst_file_path = model_version_catalog / file
            shutil.copy(src_file_path, dst_file_path)

    def setup(self) -> None:
        """Create deployments and bindings to Triton Inference Server."""
        with self._inference_handlers_lock:
            if not self._inference_handlers:
                triton_model_config = self._get_triton_model_config()
                for i, infer_function in enumerate(self.infer_functions):
                    self.triton_context.model_configs[infer_function] = copy.deepcopy(triton_model_config)
                    _inject_triton_context(self.triton_context, infer_function)
                    inference_handler = InferenceHandler(
                        model_callable=infer_function,
                        model_config=triton_model_config,
                        shared_memory_socket=f"{self._shared_memory_socket}_{i}",
                        zmq_context=self.zmq_context,
                    )
                    inference_handler.on_proxy_backend_event(self._on_proxy_backend_event)
                    inference_handler.start()
                    self._inference_handlers.append(inference_handler)
                handshake_th = threading.Thread(target=self._model_proxy_handshake, daemon=True)
                handshake_th.start()

    def clean(self) -> None:
        """Post unload actions to perform on model."""
        with self._observers_lock:
            LOGGER.debug("Clearing model events observers")
            self._model_events_observers.clear()
        LOGGER.debug("Closing socket if needed")
        if self.zmq_context is not None:
            self.zmq_context.term()
        LOGGER.debug("Socket closed. Waiting for proxy backend to shut down")
        with self._inference_handlers_lock:
            for inference_handler in self._inference_handlers:
                inference_handler.stop()
            LOGGER.debug("All backends ")
            self._inference_handlers.clear()

    def is_alive(self) -> bool:
        """Validate if model is working on Triton.

        If model is fully loaded by Triton, return True. Otherwise, perform a custom verification.

        Returns:
            True if model is working, False otherwise
        """
        with self._inference_handlers_lock:
            if not self._inference_handlers:
                return False

            for inference_handler in self._inference_handlers:
                if not inference_handler.is_alive():
                    return False

        return True

    def _get_triton_model_config(self) -> TritonModelConfig:
        """Generate ModelConfig from descriptor and custom arguments for Python model.

        Returns:
            ModelConfig object with configuration for Python model deployment
        """
        if not self._triton_model_config:
            triton_model_config = TritonModelConfig(
                model_name=self.model_name,
                model_version=self.model_version,
                batching=self.config.batching,
                batcher=self.config.batcher,
                max_batch_size=self.config.max_batch_size,
                backend_parameters={"shared-memory-socket": self._shared_memory_socket},
                instance_group={DeviceKind.KIND_CPU: len(self.infer_functions)},
            )
            inputs = []
            for idx, input_spec in enumerate(self.inputs, start=1):
                input_name = input_spec.name if input_spec.name else f"INPUT_{idx}"
                tensor = TensorSpec(
                    name=input_name, dtype=input_spec.dtype, shape=input_spec.shape, optional=input_spec.optional
                )
                inputs.append(tensor)

            outputs = []
            for idx, output_spec in enumerate(self.outputs, start=1):
                output_name = output_spec.name if output_spec.name else f"OUTPUT_{idx}"
                tensor = TensorSpec(name=output_name, dtype=output_spec.dtype, shape=output_spec.shape)
                outputs.append(tensor)

            triton_model_config.inputs = inputs
            triton_model_config.outputs = outputs

            if self.config.response_cache:
                triton_model_config.response_cache = ResponseCache(enable=True)

            self._triton_model_config = triton_model_config

        return self._triton_model_config

    def _model_proxy_handshake(self) -> None:
        socket = self.zmq_context.socket(zmq.REP)
        socket.bind(self._shared_memory_socket)

        try:
            for i in range(len(self.infer_functions)):
                socket.recv()
                socket.send_string(f"{self._shared_memory_socket}_{i}")
        except Exception as exception:
            LOGGER.error("Internal proxy backend error. It will be closed.")
            LOGGER.exception(exception)
        finally:
            LOGGER.info("Closing socket")
            socket_close_timeout_s = 0
            socket.close(linger=socket_close_timeout_s)

    def on_model_event(self, model_event_handle_fn: ModelEventsHandler):
        """Register ModelEventsHandler callable.

        Args:
            model_event_handle_fn: function to be called when model events arises
        """
        with self._observers_lock:
            self._model_events_observers.append(model_event_handle_fn)

    def _notify_model_events_observers(self, event: ModelEvent, context: typing.Any):
        with self._observers_lock:
            for model_event_handle_fn in self._model_events_observers:
                model_event_handle_fn(self, event, context)

    def _on_proxy_backend_event(
        self, proxy_backend: InferenceHandler, event: InferenceHandlerEvent, context: typing.Optional[typing.Any] = None
    ):
        if event == InferenceHandlerEvent.UNRECOVERABLE_ERROR:
            self._notify_model_events_observers(ModelEvent.RUNTIME_TERMINATING, context)
        elif event == InferenceHandlerEvent.FINISHED:
            self._notify_model_events_observers(ModelEvent.RUNTIME_TERMINATED, context)
