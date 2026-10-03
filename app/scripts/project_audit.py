from __future__ import annotations

import ast
import hashlib
import platform
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AUDIT_DIR = PROJECT_ROOT / "docs" / "project_audit"
AUDIT_FILE = AUDIT_DIR / "PROJECT_AUDIT.md"

DATA_DIR = PROJECT_ROOT / "data"
SOURCE_DIR = DATA_DIR / "source"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"

REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}

FINGERPRINT_EXCLUDED_FILES = {
    AUDIT_FILE.resolve(),
}


# ============================================================
# COMMAND EXECUTION
# ============================================================


def run_command(command: list[str], timeout: int = 180) -> str:
    """Executa um comando na raiz do projeto."""
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        parts: list[str] = []

        if stdout:
            parts.append(stdout)
        if stderr:
            parts.append(stderr)

        return "\n".join(parts) if parts else "Sem saída."

    except subprocess.TimeoutExpired:
        return f"Erro: comando excedeu o tempo limite de {timeout} segundos."
    except Exception as exc:
        return f"Erro ao executar comando: {exc}"


# ============================================================
# PATH FILTERING
# ============================================================


def is_ignored(path: Path) -> bool:
    """Informa se um caminho deve ser ignorado pela auditoria."""
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return True

    return any(part in IGNORED_DIRS for part in relative.parts)


# ============================================================
# PROJECT STRUCTURE
# ============================================================


def get_project_tree() -> str:
    """Gera uma árvore simples do estado atual do repositório."""
    lines: list[str] = [f"{PROJECT_ROOT.name}/"]

    for path in sorted(PROJECT_ROOT.rglob("*")):
        if is_ignored(path):
            continue
        if path.resolve() == AUDIT_FILE.resolve():
            continue

        relative = path.relative_to(PROJECT_ROOT)
        depth = len(relative.parts)
        prefix = "    " * depth

        if path.is_dir():
            lines.append(f"{prefix}[DIR] {path.name}/")
        else:
            lines.append(f"{prefix}[FILE] {path.name}")

    return "\n".join(lines)


# ============================================================
# PYTHON ANALYSIS
# ============================================================


def get_python_files() -> list[Path]:
    """Retorna arquivos Python relevantes do projeto."""
    return sorted(
        path
        for path in PROJECT_ROOT.rglob("*.py")
        if path.is_file() and not is_ignored(path)
    )


def analyze_python_file(path: Path) -> dict[str, Any]:
    """Analisa estrutura básica de um arquivo Python usando AST."""
    relative = path.relative_to(PROJECT_ROOT).as_posix()

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "file": relative,
            "lines": 0,
            "effective_lines": 0,
            "functions": [],
            "classes": [],
            "imports": [],
            "todos": [],
            "syntax_error": "UnicodeDecodeError",
        }

    lines = content.splitlines()
    result: dict[str, Any] = {
        "file": relative,
        "lines": len(lines),
        "effective_lines": sum(
            1
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ),
        "functions": [],
        "classes": [],
        "imports": [],
        "todos": [],
        "syntax_error": "",
    }

    todo_pattern = re.compile(r"\b(TODO|FIXME)\b", re.IGNORECASE)

    for number, line in enumerate(lines, start=1):
        if todo_pattern.search(line):
            result["todos"].append({"line": number, "text": line.strip()})

    try:
        tree = ast.parse(content, filename=relative)
    except SyntaxError as exc:
        result["syntax_error"] = f"Line {exc.lineno}: {exc.msg}"
        return result

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"].append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "docstring": bool(ast.get_docstring(node)),
                }
            )
        elif isinstance(node, ast.ClassDef):
            result["classes"].append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "docstring": bool(ast.get_docstring(node)),
                }
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result["imports"].append(node.module)

    result["functions"].sort(key=lambda item: item["line"])
    result["classes"].sort(key=lambda item: item["line"])
    return result


def get_python_analysis() -> list[dict[str, Any]]:
    """Analisa todos os arquivos Python relevantes."""
    return [analyze_python_file(path) for path in get_python_files()]


def get_python_metrics(analyses: list[dict[str, Any]]) -> dict[str, int]:
    """Consolida métricas Python."""
    return {
        "python_files": len(analyses),
        "total_lines": sum(item["lines"] for item in analyses),
        "effective_lines": sum(item["effective_lines"] for item in analyses),
        "functions": sum(len(item["functions"]) for item in analyses),
        "classes": sum(len(item["classes"]) for item in analyses),
        "todos": sum(len(item["todos"]) for item in analyses),
        "syntax_errors": sum(1 for item in analyses if item["syntax_error"]),
    }


# ============================================================
# ENTERPRISE KNOWLEDGE CORPUS
# ============================================================


def get_files_under(directory: Path) -> list[Path]:
    """Retorna arquivos relevantes abaixo de um diretório."""
    if not directory.exists():
        return []

    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and not is_ignored(path)
    )


def get_corpus_inventory() -> dict[str, Any]:
    """Inventaria os documentos que formam o corpus empresarial."""
    files = get_files_under(SOURCE_DIR)
    extensions = Counter(path.suffix.lower() or "[no extension]" for path in files)
    categories = Counter()

    for path in files:
        relative = path.relative_to(SOURCE_DIR)
        categories[relative.parts[0] if len(relative.parts) > 1 else "root"] += 1

    return {
        "files": files,
        "extensions": extensions,
        "categories": categories,
    }


def get_ground_truth_inventory() -> dict[str, Any]:
    """Inventaria os artefatos de ground truth."""
    files = get_files_under(GROUND_TRUTH_DIR)
    expected = {
        "canonical_facts.yaml": GROUND_TRUTH_DIR / "canonical_facts.yaml",
        "document_registry.yaml": GROUND_TRUTH_DIR / "document_registry.yaml",
        "golden_questions.yaml": GROUND_TRUTH_DIR / "golden_questions.yaml",
    }
    return {"files": files, "expected": expected}


# ============================================================
# GIT
# ============================================================


def get_git_branch() -> str:
    """Retorna a branch Git atual."""
    return run_command(["git", "branch", "--show-current"])


def get_git_commit() -> str:
    """Retorna o hash curto do HEAD."""
    return run_command(["git", "rev-parse", "--short", "HEAD"])


def get_git_status() -> str:
    """Retorna o estado resumido do working tree."""
    status = run_command(["git", "status", "--short"])
    return "Working tree clean." if status == "Sem saída." else status


def get_recent_commits(limit: int = 10) -> str:
    """Lista os commits mais recentes."""
    return run_command(
        [
            "git",
            "log",
            f"-{limit}",
            "--date=iso",
            "--pretty=format:%h | %ad | %s",
        ]
    )


def get_working_tree_summary() -> str:
    """Resume arquivos modificados, staged e untracked."""
    status = run_command(["git", "status", "--short"])

    if status == "Sem saída.":
        return "State: CLEAN\n\nNo modified, staged, or untracked files."

    unstaged = run_command(["git", "diff", "--stat"])
    staged = run_command(["git", "diff", "--cached", "--stat"])
    parts = ["State: DIRTY", "", "Files:", status]

    if unstaged != "Sem saída.":
        parts.extend(["", "Unstaged diff:", unstaged])
    if staged != "Sem saída.":
        parts.extend(["", "Staged diff:", staged])

    return "\n".join(parts)


# ============================================================
# SNAPSHOT FINGERPRINT
# ============================================================


def get_fingerprint_files() -> list[Path]:
    """Retorna arquivos usados no fingerprint do projeto."""
    files: list[Path] = []

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or is_ignored(path):
            continue
        if path.resolve() in FINGERPRINT_EXCLUDED_FILES:
            continue
        files.append(path)

    return sorted(
        files,
        key=lambda item: item.relative_to(PROJECT_ROOT).as_posix(),
    )


def get_project_fingerprint() -> str:
    """Calcula SHA-256 determinístico do estado do projeto."""
    digest = hashlib.sha256()

    for path in get_fingerprint_files():
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")

        try:
            digest.update(path.read_bytes())
        except OSError as exc:
            digest.update(
                f"<READ_ERROR:{type(exc).__name__}:{exc}>".encode("utf-8")
            )

        digest.update(b"\0")

    return digest.hexdigest()


def get_snapshot_signature() -> dict[str, str]:
    """Captura assinatura observável do repositório."""
    return {
        "head": get_git_commit(),
        "status": get_git_status(),
        "fingerprint": get_project_fingerprint(),
    }


def evaluate_snapshot_integrity(
    before: dict[str, str],
    after: dict[str, str],
) -> str:
    """Verifica estabilidade do repositório durante a auditoria."""
    same_head = before["head"] == after["head"]
    same_status = before["status"] == after["status"]
    same_fingerprint = before["fingerprint"] == after["fingerprint"]

    if same_head and same_status and same_fingerprint:
        return (
            "PASS\n\n"
            f"- HEAD before: {before['head']}\n"
            f"- HEAD after: {after['head']}\n"
            f"- Fingerprint before: {before['fingerprint']}\n"
            f"- Fingerprint after: {after['fingerprint']}\n"
            "- Repository content remained stable during audit collection."
        )

    changes: list[str] = []
    if not same_head:
        changes.append("- HEAD changed during audit collection.")
    if not same_status:
        changes.append("- Git status changed during audit collection.")
    if not same_fingerprint:
        changes.append("- Repository fingerprint changed during audit collection.")

    return "WARNING\n\n" + "\n".join(changes)


# ============================================================
# TESTS
# ============================================================


def get_tests() -> str:
    """Executa a suíte de testes."""
    return run_command([sys.executable, "-m", "pytest", "-q"], timeout=180)


def get_collected_tests() -> str:
    """Lista testes descobertos pelo pytest."""
    return run_command(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        timeout=180,
    )


# ============================================================
# DEPENDENCIES
# ============================================================


def get_declared_dependencies() -> str:
    """Lê requirements.txt, quando existente."""
    if not REQUIREMENTS_FILE.exists():
        return "requirements.txt not found."

    content = REQUIREMENTS_FILE.read_text(encoding="utf-8").strip()
    return content or "requirements.txt is empty."


def get_installed_dependencies() -> str:
    """Lista dependências instaladas no ambiente."""
    return run_command([sys.executable, "-m", "pip", "freeze"])


# ============================================================
# REPORT SECTIONS
# ============================================================


def build_python_file_section(analyses: list[dict[str, Any]]) -> str:
    """Gera tabela dos arquivos Python."""
    lines = [
        "| File | Lines | Functions | Classes | TODOs | Syntax |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for item in analyses:
        syntax = "ERROR" if item["syntax_error"] else "OK"
        lines.append(
            f"| `{item['file']}` "
            f"| {item['lines']} "
            f"| {len(item['functions'])} "
            f"| {len(item['classes'])} "
            f"| {len(item['todos'])} "
            f"| {syntax} |"
        )

    if not analyses:
        lines.append("| — | 0 | 0 | 0 | 0 | No Python files |")

    return "\n".join(lines)


def build_corpus_section(inventory: dict[str, Any]) -> str:
    """Gera seção de inventário do corpus."""
    lines = [
        f"- Total source documents: **{len(inventory['files'])}**",
        "",
        "### Documents by extension",
        "",
    ]

    if inventory["extensions"]:
        for extension, count in sorted(inventory["extensions"].items()):
            lines.append(f"- `{extension}`: {count}")
    else:
        lines.append("- No source documents found.")

    lines.extend(["", "### Documents by source area", ""])

    if inventory["categories"]:
        for category, count in sorted(inventory["categories"].items()):
            lines.append(f"- `{category}`: {count}")
    else:
        lines.append("- No source areas found.")

    lines.extend(["", "### Source documents", ""])

    if inventory["files"]:
        for path in inventory["files"]:
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            lines.append(f"- `{relative}`")
    else:
        lines.append("- No source documents found.")

    return "\n".join(lines)


def build_ground_truth_section(inventory: dict[str, Any]) -> str:
    """Gera seção de ground truth."""
    lines = [
        "| Artifact | Status |",
        "|---|:---:|",
    ]

    for name, path in inventory["expected"].items():
        status = "PRESENT" if path.exists() else "MISSING"
        lines.append(f"| `{name}` | {status} |")

    lines.extend(["", "### Ground-truth files", ""])

    if inventory["files"]:
        for path in inventory["files"]:
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            lines.append(f"- `{relative}`")
    else:
        lines.append("- No ground-truth files found.")

    return "\n".join(lines)


# ============================================================
# AUDIT BUILD
# ============================================================


def build_audit() -> str:
    """Constrói o snapshot técnico do projeto."""
    started_at = datetime.now()
    snapshot_before = get_snapshot_signature()

    analyses = get_python_analysis()
    metrics = get_python_metrics(analyses)
    project_tree = get_project_tree()
    corpus = get_corpus_inventory()
    ground_truth = get_ground_truth_inventory()

    tests = get_tests()
    collected_tests = get_collected_tests()

    branch = get_git_branch()
    commit = get_git_commit()
    status = get_git_status()
    recent_commits = get_recent_commits()
    working_tree = get_working_tree_summary()

    declared_dependencies = get_declared_dependencies()
    installed_dependencies = get_installed_dependencies()

    python_files_section = build_python_file_section(analyses)
    corpus_section = build_corpus_section(corpus)
    ground_truth_section = build_ground_truth_section(ground_truth)

    snapshot_after = get_snapshot_signature()
    integrity = evaluate_snapshot_integrity(snapshot_before, snapshot_after)

    finished_at = datetime.now()
    duration = (finished_at - started_at).total_seconds()
    started_text = started_at.strftime("%Y-%m-%d %H:%M:%S")
    finished_text = finished_at.strftime("%Y-%m-%d %H:%M:%S")

    return f"""# PROJECT AUDIT — Enterprise Knowledge AI System

Version: 1.0
Generated: {finished_text}

> This file is generated automatically by `app/scripts/project_audit.py`.
> Do not edit it manually.

## 1. Snapshot Integrity

```text
{integrity}
```

- Audit started: {started_text}
- Audit finished: {finished_text}
- Duration: {duration:.2f} seconds

## 2. Environment

- Python: {platform.python_version()}
- Executable: `{sys.executable}`
- Platform: {platform.platform()}

## 3. Git State

- Branch: `{branch}`
- Commit: `{commit}`

### Status

```text
{status}
```

## 4. Code Metrics

- Python files: **{metrics["python_files"]}**
- Total Python lines: **{metrics["total_lines"]}**
- Effective Python lines: **{metrics["effective_lines"]}**
- Functions: **{metrics["functions"]}**
- Classes: **{metrics["classes"]}**
- TODO/FIXME occurrences: **{metrics["todos"]}**
- Files with syntax errors: **{metrics["syntax_errors"]}**

## 5. Project Structure

```text
{project_tree}
```

## 6. Python Files

{python_files_section}

## 7. Enterprise Knowledge Corpus

{corpus_section}

## 8. Ground Truth

{ground_truth_section}

## 9. Test Execution

```text
{tests}
```

## 10. Test Discovery / Behavioral Contracts

```text
{collected_tests}
```

## 11. Recent Commits

```text
{recent_commits}
```

## 12. Working Tree

```text
{working_tree}
```

## 13. Declared Dependencies

```text
{declared_dependencies}
```

## 14. Installed Dependencies

```text
{installed_dependencies}
```

---

## Audit Purpose

This artifact is an automated snapshot of the current technical
state of the Enterprise Knowledge AI System.

Its purpose is to support development continuity, architecture
review, debugging, handoffs, and context recovery between human
developers and AI coding agents.

The audit records observable repository facts. Architectural intent,
design decisions, business semantics, and planned capabilities remain
the responsibility of the human-maintained project documentation.
"""


# ============================================================
# ENTRY POINT
# ============================================================


def main() -> None:
    """Gera e sobrescreve o PROJECT_AUDIT.md."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    AUDIT_FILE.write_text(audit, encoding="utf-8")

    print()
    print("Project audit generated successfully:")
    print(AUDIT_FILE)
    print()


if __name__ == "__main__":
    main()
