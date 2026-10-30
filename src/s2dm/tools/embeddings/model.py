"""The embedding model format: the files a model publishes, and opening them once to run the model.

A model is usable when its files hold everything needed to run it: an ONNX file, ``tokenizer.json``,
and a way to turn token outputs into one vector (a ``sentence_embedding`` output, or a pooling module listed in
``modules.json``). Query and document prompts are read from ``config_sentence_transformers.json`` when present.
"""

from dataclasses import dataclass
from pathlib import Path

import onnxruntime
from onnxruntime.capi import onnxruntime_pybind11_state as onnxruntime_errors
from tokenizers import Tokenizer

from s2dm.tools.embeddings.errors import ModelResolutionError
from s2dm.tools.embeddings.model_spec import ModelSettings, ModelSourceReference, ModelSpec, Pooling
from s2dm.tools.embeddings.sentence_transformers.pooling import MODULES_FILE, find_pooling_config_file, read_pooling
from s2dm.tools.embeddings.sentence_transformers.prompts import PROMPTS_FILE, read_prompts
from s2dm.tools.embeddings.sources.source import ModelFiles, ModelSource

MODEL_CACHE_ROOT = Path.home() / ".s2dm" / "models"

QUANTIZED_ONNX_FILE = "onnx/model_quantized.onnx"
FULL_SIZE_ONNX_FILE = "onnx/model.onnx"
TOKENIZER_FILE = "tokenizer.json"
MAX_TOKENS = 256

# ONNX Runtime's errors all derive directly from Exception, not from OSError or RuntimeError.
_ONNX_RUNTIME_ERRORS = (
    onnxruntime_errors.EPFail,
    onnxruntime_errors.EngineError,
    onnxruntime_errors.Fail,
    onnxruntime_errors.InvalidArgument,
    onnxruntime_errors.InvalidGraph,
    onnxruntime_errors.InvalidProtobuf,
    onnxruntime_errors.ModelLoaded,
    onnxruntime_errors.NoModel,
    onnxruntime_errors.NoSuchFile,
    onnxruntime_errors.NotImplemented,
    onnxruntime_errors.RuntimeException,
)


@dataclass(frozen=True)
class LoadedModel:
    """A model ready to run: its spec, with its ONNX session and tokenizer opened once."""

    spec: ModelSpec
    session: onnxruntime.InferenceSession
    tokenizer: Tokenizer


def _open_session(model_path: Path) -> onnxruntime.InferenceSession:
    model_file = str(model_path)
    try:
        return onnxruntime.InferenceSession(model_file)
    except _ONNX_RUNTIME_ERRORS as error:
        raise ModelResolutionError(f"Cannot load ONNX model {model_path.name}: {error}") from error


def _open_tokenizer(tokenizer_path: Path) -> Tokenizer:
    """Open the model's tokenizer, set to truncate to ``MAX_TOKENS`` and pad each batch.

    ``tokenizers`` reports every failure, a missing file included, as a plain ``Exception``, so that is what is
    caught, around this one call only.

    Args:
        tokenizer_path: The model's ``tokenizer.json``.

    Returns:
        The tokenizer, ready to encode batches.

    Raises:
        ModelResolutionError: When the tokenizer file is missing or cannot be loaded.
    """
    tokenizer_file = str(tokenizer_path)
    try:
        tokenizer = Tokenizer.from_file(tokenizer_file)
    except Exception as error:
        raise ModelResolutionError(f"Cannot load tokenizer {tokenizer_path.name}: {error}") from error

    tokenizer.enable_truncation(MAX_TOKENS)
    tokenizer.enable_padding()
    return tokenizer


def _output_dim(output: onnxruntime.NodeArg) -> int:
    last_dimension = output.shape[-1]
    if not isinstance(last_dimension, int):
        raise ModelResolutionError(f"Output '{output.name}' has no fixed vector size")

    return last_dimension


def _pooling_and_dim(session: onnxruntime.InferenceSession, directory: Path) -> tuple[Pooling, int]:
    model_outputs = session.get_outputs()
    outputs = {output.name: output for output in model_outputs}
    if "sentence_embedding" in outputs:
        sentence_embedding_dim = _output_dim(outputs["sentence_embedding"])
        return "sentence_embedding", sentence_embedding_dim

    if "last_hidden_state" not in outputs:
        raise ModelResolutionError("Model has neither a 'sentence_embedding' nor a 'last_hidden_state' output")

    try:
        pooling = read_pooling(directory)
    except ModelResolutionError as error:
        message = f"Model has no 'sentence_embedding' output and no usable pooling: {error}"
        raise ModelResolutionError(message) from error

    hidden_state_dim = _output_dim(outputs["last_hidden_state"])
    return pooling, hidden_state_dim


def model_files(onnx_file: str) -> ModelFiles:
    """List the files a model is made of.

    Args:
        onnx_file: Model-relative path of the ONNX file to use.

    Returns:
        The ONNX file and tokenizer as required files; external weights, module list and prompts as optional
        ones. The pooling module's config is not listed; its path is read from the module list once that is
        available.
    """
    required_files = [onnx_file, TOKENIZER_FILE]
    optional_files = [f"{onnx_file}_data", MODULES_FILE, PROMPTS_FILE]
    return ModelFiles(required=required_files, optional=optional_files)


def open_model(directory: Path, onnx_file: str, source: ModelSourceReference) -> LoadedModel:
    """Open a model from a local copy of its files and read its settings.

    Args:
        directory: Folder holding the model's files.
        onnx_file: Model-relative path of the ONNX file to use.
        source: Where the model's files come from, recorded in its spec.

    Returns:
        The model's spec, with its session and tokenizer.

    Raises:
        ModelResolutionError: When the ONNX file or the tokenizer cannot be loaded, or the pooling information is
            missing.
    """
    session = _open_session(directory / onnx_file)
    tokenizer = _open_tokenizer(directory / TOKENIZER_FILE)
    pooling, dim = _pooling_and_dim(session, directory)
    prompts = read_prompts(directory)

    settings = ModelSettings(
        onnx_file=onnx_file,
        pooling=pooling,
        query_prompt=prompts.query_prompt,
        document_prompt=prompts.document_prompt,
        dim=dim,
    )
    spec = ModelSpec(source=source, settings=settings)
    return LoadedModel(spec=spec, session=session, tokenizer=tokenizer)


def load_model(source: ModelSource, full_size: bool) -> LoadedModel:
    """Download a model's files from its source and open the model.

    The pooling module's config is downloaded in a second step, from the path that ``modules.json`` gives.

    Args:
        source: Where the model's files come from.
        full_size: Use the full-precision ONNX file instead of the 8-bit one.

    Returns:
        The model's spec, with its session and tokenizer.

    Raises:
        ModelResolutionError: When the download fails or the files do not hold what is needed to run the model.
    """
    onnx_file = QUANTIZED_ONNX_FILE
    if full_size:
        onnx_file = FULL_SIZE_ONNX_FILE

    files = model_files(onnx_file)
    directory = source.download(files)

    pooling_config_file = find_pooling_config_file(directory)
    if pooling_config_file is not None:
        pooling_files = ModelFiles(required=[pooling_config_file])
        directory = source.download(pooling_files)

    return open_model(directory, onnx_file, source.reference)
