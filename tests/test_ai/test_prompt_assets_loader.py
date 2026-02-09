"""Testes do loader de assets YAML de prompt/contexto."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai.config import prompt_assets_loader as loader


@pytest.fixture
def patched_asset_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    contexts_dir = tmp_path / "contexts"
    prompts_dir = tmp_path / "prompts_yaml"
    contexts_dir.mkdir()
    prompts_dir.mkdir()
    monkeypatch.setattr(loader, "_CONTEXTS_DIR", contexts_dir)
    monkeypatch.setattr(loader, "_PROMPTS_YAML_DIR", prompts_dir)
    loader.clear_prompt_assets_cache()
    return contexts_dir, prompts_dir


def test_resolve_relative_path_rejects_invalid_inputs() -> None:
    base_dir = Path("base")
    with pytest.raises(loader.PromptAssetError, match="relative_path vazio"):
        loader._resolve_relative_path(base_dir, "")
    with pytest.raises(loader.PromptAssetError, match="deve ser relativo"):
        loader._resolve_relative_path(base_dir, "/abs.yaml")
    with pytest.raises(loader.PromptAssetError, match="\\(\\.\\.\\) não permitido"):
        loader._resolve_relative_path(base_dir, "../segredo.yaml")


def test_load_context_for_prompt_uses_injection_then_summary_then_raw(
    patched_asset_dirs: tuple[Path, Path],
) -> None:
    contexts_dir, _ = patched_asset_dirs
    (contexts_dir / "inj.yaml").write_text("prompt_injection: Injetado", encoding="utf-8")
    (contexts_dir / "sum.yaml").write_text("prompt_summary: Resumido", encoding="utf-8")
    (contexts_dir / "raw.yaml").write_text("foo: bar\n", encoding="utf-8")

    assert loader.load_context_for_prompt("inj.yaml") == "Injetado"
    assert loader.load_context_for_prompt("sum.yaml") == "Resumido"
    assert loader.load_context_for_prompt("raw.yaml") == "foo: bar"


def test_load_context_for_prompt_cache_is_cleared_explicitly(
    patched_asset_dirs: tuple[Path, Path],
) -> None:
    contexts_dir, _ = patched_asset_dirs
    path = contexts_dir / "cache.yaml"
    path.write_text("prompt_injection: v1", encoding="utf-8")

    assert loader.load_context_for_prompt("cache.yaml") == "v1"
    path.write_text("prompt_injection: v2", encoding="utf-8")
    assert loader.load_context_for_prompt("cache.yaml") == "v1"

    loader.clear_prompt_assets_cache()
    assert loader.load_context_for_prompt("cache.yaml") == "v2"


def test_load_context_text_raises_for_missing_or_non_file(
    patched_asset_dirs: tuple[Path, Path],
) -> None:
    contexts_dir, _ = patched_asset_dirs
    with pytest.raises(loader.PromptAssetError, match="nao encontrado"):
        loader.load_context_text("inexistente.yaml")

    (contexts_dir / "pasta").mkdir()
    with pytest.raises(loader.PromptAssetError, match="Caminho de contexto invalido"):
        loader.load_context_text("pasta")


def test_load_prompt_yaml_raises_for_missing_non_file_and_non_dict(
    patched_asset_dirs: tuple[Path, Path],
) -> None:
    _, prompts_dir = patched_asset_dirs
    with pytest.raises(loader.PromptAssetError, match="nao encontrado"):
        loader.load_prompt_yaml("inexistente.yaml")

    (prompts_dir / "pasta").mkdir()
    with pytest.raises(loader.PromptAssetError, match="Caminho de prompt YAML invalido"):
        loader.load_prompt_yaml("pasta")

    (prompts_dir / "lista.yaml").write_text("- item\n", encoding="utf-8")
    with pytest.raises(loader.PromptAssetError, match="deve ser dict"):
        loader.load_prompt_yaml("lista.yaml")


def test_prompt_template_and_system_prompt_validation(
    patched_asset_dirs: tuple[Path, Path],
) -> None:
    _, prompts_dir = patched_asset_dirs
    (prompts_dir / "ok.yaml").write_text(
        "template: Ola {{ nome }}\nsystem_prompt: Seja util\n",
        encoding="utf-8",
    )
    assert loader.load_prompt_template("ok.yaml") == "Ola {{ nome }}"
    assert loader.load_system_prompt("ok.yaml") == "Seja util"

    (prompts_dir / "sem_template.yaml").write_text("system_prompt: ok\n", encoding="utf-8")
    with pytest.raises(loader.PromptAssetError, match="template"):
        loader.load_prompt_template("sem_template.yaml")

    (prompts_dir / "sem_system.yaml").write_text("template: ok\n", encoding="utf-8")
    with pytest.raises(loader.PromptAssetError, match="system_prompt"):
        loader.load_system_prompt("sem_system.yaml")
