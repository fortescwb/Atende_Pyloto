"""Configuração do pytest para o projeto Atende_Pyloto."""

import sys
from pathlib import Path

# Adiciona src/ ao PYTHONPATH para permitir imports absolutos
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
