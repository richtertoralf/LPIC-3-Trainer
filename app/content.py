"""Validation and import of learning content (JSON, schema version 1).

Four file kinds share the same envelope::

    {"schema_version": 1, "kind": "objectives" | "terms" | "questions" | "labs", ...}

Every file is validated completely before anything is written. Imported content is
treated as data only: it is never executed and always rendered with HTML escaping.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Choice,
    ImportBatch,
    Lab,
    Module,
    Objective,
    Question,
    QuestionTerm,
    Term,
    Topic,
    utcnow,
)

SCHEMA_VERSION = 1
KINDS = ("objectives", "terms", "questions", "labs")
QUESTION_TYPES = ("single", "multiple")
VISIBILITIES = ("public", "private")
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
CODE_PATTERN = re.compile(r"^\d{3}(\.\d)?$")
MAX_TEXT = 4000


class ContentError(ValueError):
    """Raised when a content file is invalid. ``errors`` lists all problems."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors[:5]) + (" ..." if len(errors) > 5 else ""))
        self.errors = errors


@dataclass
class ImportResult:
    kind: str
    created: int = 0
    updated: int = 0
    batch_id: int | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.created + self.updated


# ---------------------------------------------------------------------- helpers


def _is_str(value: Any, *, allow_empty: bool = False, max_len: int = MAX_TEXT) -> bool:
    if not isinstance(value, str):
        return False
    if not allow_empty and not value.strip():
        return False
    return len(value) <= max_len


def _check_str(errors: list[str], data: dict, key: str, where: str, *, required: bool = True,
               max_len: int = MAX_TEXT) -> None:
    if key not in data:
        if required:
            errors.append(f"{where}: field '{key}' is missing")
        return
    if not _is_str(data[key], allow_empty=not required, max_len=max_len):
        errors.append(f"{where}: field '{key}' must be a non-empty string (max {max_len} chars)")


def load_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ContentError([f"{path.name}: invalid JSON ({exc.msg} at line {exc.lineno})"]) from exc
    if not isinstance(data, dict):
        raise ContentError([f"{path.name}: top level must be an object"])
    return data


def parse_json_bytes(raw: bytes, filename: str = "upload") -> dict:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContentError([f"{filename}: invalid JSON or encoding ({exc})"]) from exc
    if not isinstance(data, dict):
        raise ContentError([f"{filename}: top level must be an object"])
    return data


# ------------------------------------------------------------------- validation


def validate_envelope(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if data.get("kind") not in KINDS:
        errors.append(f"kind must be one of {', '.join(KINDS)}")
    return errors


def validate_terms_list(errors: list[str], terms: Any, where: str) -> None:
    if not isinstance(terms, list):
        errors.append(f"{where}: 'terms' must be a list")
        return
    for i, term in enumerate(terms):
        w = f"{where} term {i + 1}"
        if not isinstance(term, dict):
            errors.append(f"{w}: must be an object")
            continue
        _check_str(errors, term, "term", w, max_len=128)
        _check_str(errors, term, "de", w, max_len=255)
        _check_str(errors, term, "explanation_de", w, required=False)


def validate_objectives(data: dict) -> list[str]:
    errors: list[str] = []
    module = data.get("module")
    if not isinstance(module, dict):
        return ["'module' must be an object"]
    _check_str(errors, module, "code", "module", max_len=8)
    if isinstance(module.get("code"), str) and not re.fullmatch(r"\d{3}", module["code"]):
        errors.append("module.code must be three digits")
    _check_str(errors, module, "title", "module", max_len=128)
    for key in ("title_de", "description_de", "version", "source_url"):
        _check_str(errors, module, key, "module", required=False)
    topics = data.get("topics")
    if not isinstance(topics, list) or not topics:
        return errors + ["'topics' must be a non-empty list"]
    seen: set[str] = set()
    for t in topics:
        if not isinstance(t, dict):
            errors.append("topic must be an object")
            continue
        code = t.get("code")
        w = f"topic {code}"
        if not isinstance(code, str) or not re.fullmatch(r"\d{3}", code):
            errors.append(f"{w}: code must be three digits")
        elif code in seen:
            errors.append(f"{w}: duplicate code")
        else:
            seen.add(code)
        _check_str(errors, t, "title", w, max_len=128)
        _check_str(errors, t, "title_de", w, required=False, max_len=128)
        objectives = t.get("objectives")
        if not isinstance(objectives, list) or not objectives:
            errors.append(f"{w}: 'objectives' must be a non-empty list")
            continue
        for o in objectives:
            if not isinstance(o, dict):
                errors.append(f"{w}: objective must be an object")
                continue
            ocode = o.get("code")
            ow = f"objective {ocode}"
            if not isinstance(ocode, str) or not re.fullmatch(r"\d{3}\.\d", ocode):
                errors.append(f"{ow}: code must look like 301.1")
            elif ocode in seen:
                errors.append(f"{ow}: duplicate code")
            else:
                seen.add(ocode)
            _check_str(errors, o, "title", ow, max_len=160)
            _check_str(errors, o, "title_de", ow, required=False, max_len=160)
            _check_str(errors, o, "summary_de", ow, required=False)
            _check_str(errors, o, "tools", ow, required=False)
            if not isinstance(o.get("weight", 1), int) or not 1 <= o.get("weight", 1) <= 20:
                errors.append(f"{ow}: weight must be an integer between 1 and 20")
    return errors


def validate_question(q: Any, index: int, seen_ids: set[str]) -> list[str]:
    errors: list[str] = []
    w = f"question {index + 1}"
    if not isinstance(q, dict):
        return [f"{w}: must be an object"]
    qid = q.get("id")
    if not isinstance(qid, str) or not ID_PATTERN.match(qid):
        errors.append(f"{w}: 'id' must match {ID_PATTERN.pattern}")
    elif qid in seen_ids:
        errors.append(f"{w}: duplicate id '{qid}'")
    else:
        seen_ids.add(qid)
        w = f"question {qid}"
    if "objective" in q and (
        not isinstance(q["objective"], str) or not CODE_PATTERN.match(q["objective"])
    ):
        errors.append(f"{w}: 'objective' must look like 301.1")
    qtype = q.get("type", "single")
    if qtype not in QUESTION_TYPES:
        errors.append(f"{w}: 'type' must be single or multiple")
    difficulty = q.get("difficulty", 2)
    if not isinstance(difficulty, int) or not 1 <= difficulty <= 3:
        errors.append(f"{w}: 'difficulty' must be 1, 2 or 3")
    _check_str(errors, q, "question", w)
    for key in ("question_de", "explanation_de", "explanation_en"):
        _check_str(errors, q, key, w, required=False)
    choices = q.get("choices")
    if not isinstance(choices, list) or not 2 <= len(choices) <= 6:
        errors.append(f"{w}: 'choices' must be a list with 2 to 6 entries")
    else:
        correct = 0
        for i, c in enumerate(choices):
            cw = f"{w} choice {i + 1}"
            if not isinstance(c, dict):
                errors.append(f"{cw}: must be an object")
                continue
            _check_str(errors, c, "text", cw)
            _check_str(errors, c, "text_de", cw, required=False)
            if not isinstance(c.get("correct", False), bool):
                errors.append(f"{cw}: 'correct' must be true or false")
            elif c.get("correct"):
                correct += 1
        if qtype == "single" and correct != 1:
            errors.append(f"{w}: a single-choice question needs exactly one correct choice")
        if qtype == "multiple" and correct < 2:
            errors.append(f"{w}: a multiple-choice question needs at least two correct choices")
        if qtype == "multiple" and correct == len(choices):
            errors.append(f"{w}: a multiple-choice question needs at least one wrong choice")
    if "terms" in q:
        validate_terms_list(errors, q["terms"], w)
    return errors


def validate_questions(data: dict) -> list[str]:
    errors: list[str] = []
    module = data.get("module")
    if not isinstance(module, str) or not re.fullmatch(r"\d{3}", module):
        errors.append("'module' must be a three digit module code")
    for key in ("license", "author", "source"):
        _check_str(errors, data, key, "file", required=False, max_len=255)
    if data.get("visibility", "private") not in VISIBILITIES:
        errors.append("'visibility' must be public or private")
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        return errors + ["'questions' must be a non-empty list"]
    seen: set[str] = set()
    for i, q in enumerate(questions):
        errors.extend(validate_question(q, i, seen))
    return errors


def validate_terms(data: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(data.get("terms"), list) or not data["terms"]:
        return ["'terms' must be a non-empty list"]
    validate_terms_list(errors, data["terms"], "file")
    return errors


def validate_labs(data: dict) -> list[str]:
    errors: list[str] = []
    module = data.get("module")
    if not isinstance(module, str) or not re.fullmatch(r"\d{3}", module):
        errors.append("'module' must be a three digit module code")
    _check_str(errors, data, "license", "file", required=False, max_len=255)
    if data.get("visibility", "public") not in VISIBILITIES:
        errors.append("'visibility' must be public or private")
    labs = data.get("labs")
    if not isinstance(labs, list) or not labs:
        return errors + ["'labs' must be a non-empty list"]
    seen: set[str] = set()
    for i, lab in enumerate(labs):
        w = f"lab {i + 1}"
        if not isinstance(lab, dict):
            errors.append(f"{w}: must be an object")
            continue
        lid = lab.get("id")
        if not isinstance(lid, str) or not ID_PATTERN.match(lid):
            errors.append(f"{w}: 'id' must match {ID_PATTERN.pattern}")
        elif lid in seen:
            errors.append(f"{w}: duplicate id '{lid}'")
        else:
            seen.add(lid)
            w = f"lab {lid}"
        if "objective" in lab and (
            not isinstance(lab["objective"], str) or not CODE_PATTERN.match(lab["objective"])
        ):
            errors.append(f"{w}: 'objective' must look like 301.1")
        _check_str(errors, lab, "title", w, max_len=160)
        _check_str(errors, lab, "goal_de", w)
        _check_str(errors, lab, "environment_de", w, required=False)
        duration = lab.get("duration_minutes", 30)
        if not isinstance(duration, int) or not 5 <= duration <= 600:
            errors.append(f"{w}: 'duration_minutes' must be between 5 and 600")
        steps = lab.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{w}: 'steps' must be a non-empty list")
        else:
            for j, step in enumerate(steps):
                sw = f"{w} step {j + 1}"
                if not isinstance(step, dict):
                    errors.append(f"{sw}: must be an object")
                    continue
                _check_str(errors, step, "title", sw, max_len=160)
                _check_str(errors, step, "text_de", sw)
                cmds = step.get("commands", [])
                if not isinstance(cmds, list) or not all(
                    _is_str(c, allow_empty=True, max_len=500) for c in cmds
                ):
                    errors.append(f"{sw}: 'commands' must be a list of strings")
        checks = lab.get("checks", [])
        if not isinstance(checks, list):
            errors.append(f"{w}: 'checks' must be a list")
        else:
            for j, check in enumerate(checks):
                cw = f"{w} check {j + 1}"
                if not isinstance(check, dict):
                    errors.append(f"{cw}: must be an object")
                    continue
                _check_str(errors, check, "question_de", cw)
                _check_str(errors, check, "answer_de", cw)
    return errors


def validate(data: dict) -> list[str]:
    """Return all validation errors of a content document (empty list means valid)."""
    errors = validate_envelope(data)
    if errors:
        return errors
    kind = data["kind"]
    if kind == "objectives":
        return validate_objectives(data)
    if kind == "terms":
        return validate_terms(data)
    if kind == "questions":
        return validate_questions(data)
    return validate_labs(data)


# ----------------------------------------------------------------------- import


def _upsert_term(db: Session, cache: dict[str, Term], raw: dict) -> Term:
    key = raw["term"].strip().lower()
    term = cache.get(key)
    if term is None:
        term = db.execute(select(Term).where(Term.term == key)).scalar_one_or_none()
    if term is None:
        term = Term(term=key, translation_de=raw["de"].strip(),
                    explanation_de=raw.get("explanation_de", "").strip())
        db.add(term)
        db.flush()
    else:
        term.translation_de = raw["de"].strip()
        if raw.get("explanation_de"):
            term.explanation_de = raw["explanation_de"].strip()
    cache[key] = term
    return term


def import_objectives(db: Session, data: dict) -> ImportResult:
    result = ImportResult(kind="objectives")
    m = data["module"]
    module = db.execute(select(Module).where(Module.code == m["code"])).scalar_one_or_none()
    if module is None:
        module = Module(code=m["code"], title=m["title"])
        db.add(module)
        result.created += 1
    else:
        result.updated += 1
    module.title = m["title"]
    module.title_de = m.get("title_de", "")
    module.description_de = m.get("description_de", "")
    module.version = m.get("version", "")
    module.source_url = m.get("source_url", "")
    module.position = int(m.get("position", 0))
    db.flush()
    for t in data["topics"]:
        topic = db.execute(select(Topic).where(Topic.code == t["code"])).scalar_one_or_none()
        if topic is None:
            topic = Topic(module_id=module.id, code=t["code"], title=t["title"])
            db.add(topic)
        topic.module_id = module.id
        topic.title = t["title"]
        topic.title_de = t.get("title_de", "")
        db.flush()
        for o in t["objectives"]:
            obj = db.execute(
                select(Objective).where(Objective.code == o["code"])
            ).scalar_one_or_none()
            if obj is None:
                obj = Objective(topic_id=topic.id, code=o["code"], title=o["title"])
                db.add(obj)
            obj.topic_id = topic.id
            obj.title = o["title"]
            obj.title_de = o.get("title_de", "")
            obj.weight = int(o.get("weight", 1))
            obj.summary_de = o.get("summary_de", "")
            obj.tools = o.get("tools", "")
    db.flush()
    return result


def import_terms(db: Session, data: dict) -> ImportResult:
    result = ImportResult(kind="terms")
    cache: dict[str, Term] = {}
    for raw in data["terms"]:
        key = raw["term"].strip().lower()
        existed = db.execute(select(Term.id).where(Term.term == key)).scalar_one_or_none()
        _upsert_term(db, cache, raw)
        if existed:
            result.updated += 1
        else:
            result.created += 1
    return result


def _objective_map(db: Session) -> dict[str, Objective]:
    return {o.code: o for o in db.execute(select(Objective)).scalars()}


def _batch(db: Session, kind: str, filename: str, bundled: bool) -> ImportBatch:
    """Bundled files reuse their batch row so re-syncs do not pile up batches."""
    if bundled:
        existing = db.execute(
            select(ImportBatch).where(ImportBatch.kind == kind, ImportBatch.filename == filename,
                                      ImportBatch.bundled.is_(True))
        ).scalar_one_or_none()
        if existing is not None:
            existing.imported_at = utcnow()
            return existing
    batch = ImportBatch(filename=filename, kind=kind, bundled=bundled)
    db.add(batch)
    db.flush()
    return batch


def document_checksum(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def import_questions(db: Session, data: dict, *, filename: str, imported_by: int | None,
                     visibility: str | None, bundled: bool, checksum: str = "") -> ImportResult:
    result = ImportResult(kind="questions")
    module = db.execute(select(Module).where(Module.code == data["module"])).scalar_one_or_none()
    if module is None:
        raise ContentError([f"module {data['module']} is unknown; import objectives first"])
    objectives = _objective_map(db)
    for q in data["questions"]:
        code = q.get("objective")
        if code and code not in objectives:
            raise ContentError([f"question {q['id']}: objective {code} does not exist"])
        if code and not code.startswith(module.code[0]) and objectives[code].topic.module_id != module.id:
            raise ContentError([f"question {q['id']}: objective {code} belongs to another module"])
    vis = visibility or data.get("visibility", "private")
    batch = _batch(db, "questions", filename, bundled)
    batch.module_code = module.code
    batch.license = data.get("license", "")
    batch.author = data.get("author", "")
    batch.visibility = vis
    batch.imported_by = imported_by
    batch.checksum = checksum
    db.flush()
    cache: dict[str, Term] = {}
    for q in data["questions"]:
        question = db.execute(
            select(Question).where(Question.external_id == q["id"])
        ).scalar_one_or_none()
        if question is None:
            question = Question(external_id=q["id"], module_id=module.id, text_en=q["question"])
            db.add(question)
            result.created += 1
        else:
            result.updated += 1
            for choice in list(question.choices):
                db.delete(choice)
            db.execute(QuestionTerm.__table__.delete().where(QuestionTerm.question_id == question.id))
        question.module_id = module.id
        question.objective_id = objectives[q["objective"]].id if q.get("objective") else None
        question.kind = q.get("type", "single")
        question.text_en = q["question"].strip()
        question.text_de = q.get("question_de", "").strip()
        question.explanation_de = q.get("explanation_de", "").strip()
        question.explanation_en = q.get("explanation_en", "").strip()
        question.difficulty = int(q.get("difficulty", 2))
        question.visibility = vis
        question.is_active = True
        question.import_batch_id = batch.id
        question.created_by = imported_by
        db.flush()
        for pos, c in enumerate(q["choices"]):
            db.add(Choice(question_id=question.id, position=pos, text_en=c["text"].strip(),
                          text_de=c.get("text_de", "").strip(), is_correct=bool(c.get("correct"))))
        for raw in q.get("terms", []):
            term = _upsert_term(db, cache, raw)
            db.add(QuestionTerm(question_id=question.id, term_id=term.id))
        db.flush()
    batch.item_count = result.total
    result.batch_id = batch.id
    return result


def import_labs(db: Session, data: dict, *, filename: str, imported_by: int | None,
                visibility: str | None, bundled: bool, checksum: str = "") -> ImportResult:
    result = ImportResult(kind="labs")
    module = db.execute(select(Module).where(Module.code == data["module"])).scalar_one_or_none()
    if module is None:
        raise ContentError([f"module {data['module']} is unknown; import objectives first"])
    objectives = _objective_map(db)
    for lab in data["labs"]:
        code = lab.get("objective")
        if code and code not in objectives:
            raise ContentError([f"lab {lab['id']}: objective {code} does not exist"])
    vis = visibility or data.get("visibility", "public")
    batch = _batch(db, "labs", filename, bundled)
    batch.module_code = module.code
    batch.license = data.get("license", "")
    batch.author = data.get("author", "")
    batch.visibility = vis
    batch.imported_by = imported_by
    batch.checksum = checksum
    db.flush()
    for raw in data["labs"]:
        lab = db.execute(select(Lab).where(Lab.external_id == raw["id"])).scalar_one_or_none()
        if lab is None:
            lab = Lab(external_id=raw["id"], module_id=module.id, title=raw["title"])
            db.add(lab)
            result.created += 1
        else:
            result.updated += 1
        lab.module_id = module.id
        lab.objective_id = objectives[raw["objective"]].id if raw.get("objective") else None
        lab.title = raw["title"].strip()
        lab.goal_de = raw["goal_de"].strip()
        lab.environment_de = raw.get("environment_de", "").strip()
        lab.duration_minutes = int(raw.get("duration_minutes", 30))
        lab.steps = [
            {"title": s["title"], "text_de": s["text_de"], "commands": s.get("commands", [])}
            for s in raw["steps"]
        ]
        lab.checks = [
            {"question_de": c["question_de"], "answer_de": c["answer_de"]}
            for c in raw.get("checks", [])
        ]
        lab.visibility = vis
        lab.import_batch_id = batch.id
    db.flush()
    batch.item_count = result.total
    result.batch_id = batch.id
    return result


def import_document(db: Session, data: dict, *, filename: str = "upload.json",
                    imported_by: int | None = None, visibility: str | None = None,
                    bundled: bool = False) -> ImportResult:
    """Validate and import one content document. Raises ContentError when invalid."""
    errors = validate(data)
    if errors:
        raise ContentError(errors)
    kind = data["kind"]
    checksum = document_checksum(data)
    if kind == "objectives":
        return import_objectives(db, data)
    if kind == "terms":
        return import_terms(db, data)
    if kind == "questions":
        return import_questions(db, data, filename=filename, imported_by=imported_by,
                                visibility=visibility, bundled=bundled, checksum=checksum)
    return import_labs(db, data, filename=filename, imported_by=imported_by,
                       visibility=visibility, bundled=bundled, checksum=checksum)


def import_path(db: Session, path: Path, **kwargs) -> ImportResult:
    data = load_json(path)
    return import_document(db, data, filename=path.name, **kwargs)


def content_files(content_dir: Path) -> list[Path]:
    """Return bundled content files in import order (objectives, terms, questions, labs)."""
    order = {"objectives": 0, "vocabulary": 1, "questions": 2, "labs": 3}
    files: list[tuple[int, Path]] = []
    for sub, rank in order.items():
        folder = content_dir / sub
        if folder.is_dir():
            files.extend((rank, p) for p in sorted(folder.glob("*.json")))
    return [p for _, p in sorted(files, key=lambda x: (x[0], x[1].name))]


def sync_bundled_content(db: Session, content_dir: Path) -> list[ImportResult]:
    """Import every bundled content file. Bundled content is public."""
    results: list[ImportResult] = []
    for path in content_files(content_dir):
        data = load_json(path)
        if data.get("kind") in ("questions", "labs"):
            existing = db.execute(
                select(ImportBatch.checksum).where(
                    ImportBatch.kind == data["kind"], ImportBatch.filename == path.name,
                    ImportBatch.bundled.is_(True))
            ).scalar_one_or_none()
            if existing and existing == document_checksum(data):
                results.append(ImportResult(kind=data["kind"], warnings=[f"{path.name}: unchanged"]))
                continue
        results.append(import_document(db, data, filename=path.name, visibility="public",
                                       bundled=True))
    return results
