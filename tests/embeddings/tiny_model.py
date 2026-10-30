"""Writes a tiny real model folder (ONNX graph, tokenizer, sentence-transformers configs) for model tests."""

import json
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing

from s2dm.tools.embeddings.model import QUANTIZED_ONNX_FILE, TOKENIZER_FILE
from s2dm.tools.embeddings.model_spec import ModelSourceReference, TokenPooling
from s2dm.tools.embeddings.sentence_transformers.pooling import MODULE_CONFIG_FILE, MODULES_FILE, POOLING_MODULE_TYPE
from s2dm.tools.embeddings.sentence_transformers.prompts import PROMPTS_FILE

HIDDEN_SIZE = 4
SENTENCE_EMBEDDING_SIZE = 6
VOCABULARY = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "door", "open", "tire", "pressure", "q", ":", "x", "a", "b", "c"]
PROMPT = "q: "
HIDDEN_STATE_OUTPUT = "last_hidden_state"

LOCAL_MODEL_REFERENCE = ModelSourceReference(kind="folder")


def _write_tokenizer(path: Path) -> None:
    vocabulary = {token: index for index, token in enumerate(VOCABULARY)}
    word_level_model = WordLevel(vocabulary, unk_token="[UNK]")
    tokenizer = Tokenizer(word_level_model)
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer.post_processor = TemplateProcessing(
        single="[CLS] $A [SEP]",
        special_tokens=[("[CLS]", vocabulary["[CLS]"]), ("[SEP]", vocabulary["[SEP]"])],
    )
    tokenizer_path = str(path)
    tokenizer.save(tokenizer_path)


def _write_onnx_model(path: Path, with_sentence_embedding: bool, hidden_state_output: str) -> None:
    random_generator = np.random.default_rng(seed=7)
    vocabulary_size = len(VOCABULARY)
    embedding_table = random_generator.normal(size=(vocabulary_size, HIDDEN_SIZE)).astype(np.float32)
    inputs = [
        helper.make_tensor_value_info(name, TensorProto.INT64, ["batch", "sequence"])
        for name in ("input_ids", "attention_mask", "token_type_ids")
    ]
    hidden_state_shape: list[str | int] = ["batch", "sequence", HIDDEN_SIZE]
    outputs = [helper.make_tensor_value_info(hidden_state_output, TensorProto.FLOAT, hidden_state_shape)]
    nodes = [helper.make_node("Gather", ["embedding_table", "input_ids"], [hidden_state_output])]
    initializers = [numpy_helper.from_array(embedding_table, name="embedding_table")]

    if with_sentence_embedding:
        projection = random_generator.normal(size=(HIDDEN_SIZE, SENTENCE_EMBEDDING_SIZE)).astype(np.float32)
        projection_initializer = numpy_helper.from_array(projection, name="projection")
        pooling_node = helper.make_node("ReduceMean", [hidden_state_output], ["pooled"], axes=[1], keepdims=0)
        projection_node = helper.make_node("MatMul", ["pooled", "projection"], ["sentence_embedding"])
        sentence_embedding_shape: list[str | int] = ["batch", SENTENCE_EMBEDDING_SIZE]
        sentence_embedding_output = helper.make_tensor_value_info(
            "sentence_embedding", TensorProto.FLOAT, sentence_embedding_shape
        )
        initializers.append(projection_initializer)
        nodes.extend([pooling_node, projection_node])
        outputs.append(sentence_embedding_output)

    graph = helper.make_graph(nodes, "tiny_encoder", inputs, outputs, initializers)
    opset = helper.make_opsetid("", 17)
    model = helper.make_model(graph, opset_imports=[opset])
    model.ir_version = 10
    path.parent.mkdir(parents=True, exist_ok=True)
    model_path = str(path)
    onnx.save(model, model_path)


def _write_pooling_config(directory: Path, pooling_mode: TokenPooling, pooling_path: str) -> None:
    modules = [
        {"idx": 0, "name": "0", "path": "", "type": "sentence_transformers.models.Transformer"},
        {"idx": 1, "name": "1", "path": pooling_path, "type": POOLING_MODULE_TYPE},
    ]
    pooling_config = {
        "word_embedding_dimension": HIDDEN_SIZE,
        "pooling_mode_cls_token": pooling_mode == "cls",
        "pooling_mode_mean_tokens": pooling_mode == "mean",
    }
    modules_json = json.dumps(modules)
    pooling_config_json = json.dumps(pooling_config)
    (directory / MODULES_FILE).write_text(modules_json)
    (directory / pooling_path).mkdir()
    (directory / pooling_path / MODULE_CONFIG_FILE).write_text(pooling_config_json)


def write_model_dir(
    directory: Path,
    *,
    onnx_file: str = QUANTIZED_ONNX_FILE,
    with_sentence_embedding: bool = True,
    hidden_state_output: str = HIDDEN_STATE_OUTPUT,
    pooling_mode: TokenPooling | None = None,
    pooling_path: str = "1_Pooling",
    query_prompt: str = "",
    document_prompt: str = "",
    with_tokenizer: bool = True,
) -> None:
    """Write a tiny model folder shaped like a Hugging Face sentence-transformers repo.

    The prompts config is written only when a prompt is set.

    Args:
        directory: The folder to write into; created when missing.
        onnx_file: The ONNX model's path inside the folder.
        with_sentence_embedding: Whether the model has a pooled ``sentence_embedding`` output.
        hidden_state_output: The name of the model's per-token output.
        pooling_mode: The pooling that the module list and pooling config declare; ``None`` writes neither.
        pooling_path: The pooling module's folder, relative to ``directory``.
        query_prompt: The query prompt in the prompts config.
        document_prompt: The document prompt in the prompts config.
        with_tokenizer: Whether to write the tokenizer file.
    """
    directory.mkdir(parents=True, exist_ok=True)
    _write_onnx_model(directory / onnx_file, with_sentence_embedding, hidden_state_output)
    if with_tokenizer:
        _write_tokenizer(directory / TOKENIZER_FILE)
    if pooling_mode is not None:
        _write_pooling_config(directory, pooling_mode, pooling_path)
    if query_prompt or document_prompt:
        prompts_config = {"prompts": {"query": query_prompt, "document": document_prompt}}
        prompts_json = json.dumps(prompts_config)
        (directory / PROMPTS_FILE).write_text(prompts_json)
