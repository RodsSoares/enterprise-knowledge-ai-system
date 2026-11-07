"""Reproducible local corpus manifest. Registry is control data, never evidence."""
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess

from app.chunking.schemas import RetrievalChunk
from app.ingestion.registry import load_document_registry
from app.orchestration.contracts import digest


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def chunk_record(chunk):
    return json.loads(json.dumps(dict(asdict(chunk), source_path=chunk.source_path.as_posix())))


def canonical_hash(chunks):
    return digest([chunk_record(c) for c in sorted(chunks, key=lambda c:c.chunk_id)])


def _relative(path):
    path = Path(path)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Snapshot paths must be repository-relative')
    return path


@dataclass(frozen=True)
class CorpusSnapshot:
    serialized: str

    @property
    def payload(self):
        return json.loads(self.serialized)

    @property
    def snapshot_id(self):
        return digest(self.payload)

    @property
    def metadata(self):
        return self.payload['metadata']

    @property
    def chunks(self):
        result=[]
        for raw in self.payload['chunks']:
            raw['source_path']=Path(raw['source_path'])
            for key in ('source_block_ids','section_path','page_numbers','slide_numbers','sheet_names','content_types'):
                raw[key]=tuple(raw[key])
            result.append(RetrievalChunk(**raw))
        return tuple(result)

    def verify(self, chunks=None):
        p=self.payload
        if p['schema_version'] != '1.0':
            raise ValueError('Unsupported snapshot version')
        for record in p['files']+[p['registry']]:
            if file_hash(_relative(record['path'])) != record['sha256']:
                raise ValueError('Physical source/registry changed; prepare a new snapshot')
        stored=self.chunks
        if not stored or len({c.chunk_id for c in stored}) != len(stored):
            raise ValueError('Unique nonempty chunks required')
        if canonical_hash(stored) != p['canonical_hash']:
            raise ValueError('Chunk fingerprint mismatch')
        if chunks is not None and canonical_hash(chunks) != p['canonical_hash']:
            raise ValueError('Catalog does not match snapshot')
        files={f['document_id']:f for f in p['files']}
        if len(files)!=len(p['files']) or set(files)!={c.document_id for c in stored}:
            raise ValueError('Document/file mapping mismatch')
        registry=load_document_registry(Path(p['registry']['path']))
        metadata={doc:json.loads(json.dumps(asdict(registry.by_id(doc)),default=str)) for doc in files}
        if metadata!=p['metadata']:
            raise ValueError('Registry metadata mismatch')
        for c in stored:
            if c.source_path.as_posix()!=files[c.document_id]['path']:
                raise ValueError('Chunk path differs from manifest')
        return self


def prepare_snapshot(paths, registry_path, loader):
    paths=[_relative(p) for p in paths]
    registry_path=_relative(registry_path)
    before={p.as_posix():file_hash(p) for p in paths+[registry_path]}
    registry=load_document_registry(registry_path)
    chunks=tuple(loader(paths))
    metadata={c.document_id:json.loads(json.dumps(asdict(registry.by_id(c.document_id)),default=str)) for c in chunks}
    versions={}
    for package in ('docling','openpyxl','numpy','openai'):
        try: versions[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: versions[package]='not_installed'
    try:
        sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):
        sha=None
    p=dict(schema_version='1.0', files=[dict(document_id=p.stem.split('_',1)[0],
        path=p.as_posix(),sha256=before[p.as_posix()]) for p in paths],
        registry=dict(path=registry_path.as_posix(),sha256=before[registry_path.as_posix()]),
        metadata=metadata, canonical_hash=canonical_hash(chunks),
        chunks=[chunk_record(c) for c in chunks], code_head=sha,
        configuration=dict(loader='app.scripts.ask_knowledge.load_chunks',chunker=[1200,1800],
            parser='IngestionRouter defaults',package_versions=versions,
            code_hashes={p.as_posix():file_hash(p) for folder in ('app/ingestion','app/chunking')
                         for p in sorted(Path(folder).glob('*.py'))}))
    return CorpusSnapshot(json.dumps(p,ensure_ascii=False)).verify(chunks)
