"""
Utility script that inspects the stored ChromaDB embeddings and reports on
dispersion quality. It runs three diagnostics commonly used for RAG vetting:

1) Pairwise cosine similarity distribution.
2) PCA/t-SNE projections for visual inspection.
3) Nearest-neighbor distance statistics.

Example:
    python evaluation/scripts/embedding_dispersion.py --sample-size 1000 --tsne
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import chromadb
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.neighbors import NearestNeighbors

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
EVAL_DIR = REPO_ROOT / "evaluation"
if BACKEND_DIR.exists():
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from config import settings

    DEFAULT_COLLECTION = settings.CHROMA_COLLECTION
except Exception:  # pragma: no cover - env may be missing during standalone runs
    DEFAULT_COLLECTION = os.getenv("CHROMA_COLLECTION", "kid_program_collection")

DEFAULT_PERSIST = BACKEND_DIR / "chroma_data"
DEFAULT_OUTPUT_DIR = (EVAL_DIR / "embedding_reports") if EVAL_DIR.exists() else BACKEND_DIR / "embedding_reports"

logger = logging.getLogger("embedding_dispersion")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze embedding dispersion from ChromaDB data.")
    parser.add_argument(
        "--persist-dir",
        default=str(DEFAULT_PERSIST),
        help="Path to the ChromaDB persist directory (defaults to backend/chroma_data).",
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help="Collection name to inspect.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=800,
        help="Number of vectors to sample for the diagnostics.",
    )
    parser.add_argument(
        "--pairwise-samples",
        type=int,
        default=5000,
        help="Number of random pair comparisons for cosine statistics (exact if small).",
    )
    parser.add_argument(
        "--tsne",
        action="store_true",
        help="Also compute t-SNE projection (can take ~1-2 minutes).",
    )
    parser.add_argument(
        "--tsne-perplexity",
        type=float,
        default=30.0,
        help="Perplexity to use for t-SNE (ignored if --tsne is not set).",
    )
    parser.add_argument(
        "--projection-sample",
        type=int,
        default=800,
        help="Number of samples used for PCA/t-SNE projections.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where JSON/CSV reports will be written.",
    )
    parser.add_argument(
        "--collapse-threshold",
        type=float,
        default=0.3,
        help="Mean similarity threshold that flags potential embedding collapse.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling.",
    )
    return parser.parse_args()


def connect_collection(persist_dir: Path, collection_name: str):
    if not persist_dir.exists():
        raise FileNotFoundError(f"Persist directory not found: {persist_dir}")

    logger.info("Connecting to Chroma persist dir %s", persist_dir)
    client = chromadb.PersistentClient(path=str(persist_dir))

    try:
        collection = client.get_collection(collection_name)
    except Exception as exc:  # pragma: no cover - network/path errors
        raise RuntimeError(f"Failed to load collection '{collection_name}'") from exc

    return collection


def load_embedding_sample(collection, sample_size: int, seed: int) -> Tuple[List[str], List[Dict[str, Any]], np.ndarray]:
    raw = collection.get(include=["embeddings", "metadatas"])
    embeddings = raw.get("embeddings")
    metadatas = raw.get("metadatas")
    ids = raw.get("ids")

    if embeddings is None or len(embeddings) == 0:
        raise RuntimeError("Collection did not return any embeddings. Is the persist directory correct?")

    metadatas = metadatas or []
    ids = ids or []

    total = len(embeddings)
    actual_size = min(sample_size, total)
    index_pool = list(range(total))
    random.Random(seed).shuffle(index_pool)
    selected_idx = index_pool[:actual_size]

    sample_embeddings = np.asarray([embeddings[i] for i in selected_idx], dtype=np.float32)
    sample_meta = [metadatas[i] if i < len(metadatas) else {} for i in selected_idx]
    sample_ids = [ids[i] if i < len(ids) else f"row_{i}" for i in selected_idx]

    logger.info("Loaded %s/%s embeddings for analysis", len(sample_embeddings), total)
    return sample_ids, sample_meta, sample_embeddings


def _normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1e-12
    return embeddings / norms


def _describe(values: np.ndarray) -> Dict[str, float]:
    if values.size == 0:
        return {}

    return {
        "count": int(values.size),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "p10": float(np.percentile(values, 10)),
        "p90": float(np.percentile(values, 90)),
    }


def pairwise_similarity(normed_embeddings: np.ndarray, pairwise_samples: int, seed: int) -> np.ndarray:
    n = normed_embeddings.shape[0]
    if n < 2:
        return np.array([])

    total_pairs = n * (n - 1) // 2
    if pairwise_samples >= total_pairs or n <= 250:
        sims = normed_embeddings @ normed_embeddings.T
        rows, cols = np.triu_indices(n, k=1)
        return sims[rows, cols]

    rng = np.random.default_rng(seed)
    i_idx = rng.integers(0, n, size=pairwise_samples * 2)
    j_idx = rng.integers(0, n, size=pairwise_samples * 2)
    mask = i_idx != j_idx
    i_idx, j_idx = i_idx[mask], j_idx[mask]

    while i_idx.size < pairwise_samples:
        needed = pairwise_samples - i_idx.size
        extra_i = rng.integers(0, n, size=needed * 2)
        extra_j = rng.integers(0, n, size=needed * 2)
        extra_mask = extra_i != extra_j
        i_idx = np.concatenate([i_idx, extra_i[extra_mask]])
        j_idx = np.concatenate([j_idx, extra_j[extra_mask]])

    i_idx = i_idx[:pairwise_samples]
    j_idx = j_idx[:pairwise_samples]
    return np.sum(normed_embeddings[i_idx] * normed_embeddings[j_idx], axis=1)


def nearest_neighbor_stats(normed_embeddings: np.ndarray) -> Dict[str, Dict[str, float]]:
    n = normed_embeddings.shape[0]
    if n < 2:
        return {}

    neighbors = min(6, n)
    nn = NearestNeighbors(n_neighbors=neighbors, metric="cosine")
    nn.fit(normed_embeddings)
    distances, _ = nn.kneighbors(normed_embeddings)
    first_neighbor = distances[:, 1] if neighbors > 1 else distances[:, 0]
    similarities = 1.0 - first_neighbor

    return {
        "distance": _describe(first_neighbor),
        "similarity": _describe(similarities),
    }


def _metadata_name(meta: Dict[str, Any], fallback: str) -> str:
    if not meta:
        return fallback

    for key in ("Name", "name", "시설명"):
        value = meta.get(key)
        if value:
            return str(value)
    return fallback


def projection_report(
    normed_embeddings: np.ndarray,
    ids: Sequence[str],
    metadatas: Sequence[Dict[str, Any]],
    output_dir: Path,
    run_tsne: bool,
    tsne_perplexity: float,
    projection_sample: int,
    seed: int,
) -> Path | None:
    if normed_embeddings.shape[0] < 2:
        logger.warning("Not enough samples for PCA/TSNE projection.")
        return None

    sample_count = min(projection_sample, normed_embeddings.shape[0])
    rng = np.random.default_rng(seed)
    sample_indices = (
        rng.choice(normed_embeddings.shape[0], size=sample_count, replace=False)
        if sample_count < normed_embeddings.shape[0]
        else np.arange(sample_count)
    )

    subset = normed_embeddings[sample_indices]
    labels = [_metadata_name(metadatas[i], ids[i]) for i in sample_indices]

    pca_coords = PCA(n_components=2, random_state=seed).fit_transform(subset)

    tsne_coords = None
    if run_tsne and subset.shape[0] >= 50:
        perplexity = max(5.0, min(tsne_perplexity, subset.shape[0] - 1))
        logger.info("Running t-SNE on %s samples (perplexity=%s)", subset.shape[0], perplexity)
        tsne = TSNE(
            n_components=2,
            perplexity=perplexity,
            init="random",
            learning_rate="auto",
            random_state=seed,
        )
        tsne_coords = tsne.fit_transform(subset)
    elif run_tsne:
        logger.warning("Skipping t-SNE because at least 50 samples are required.")

    rows = []
    for idx, sample_idx in enumerate(sample_indices):
        row = {
            "id": ids[sample_idx],
            "name": labels[idx],
            "pca_x": float(pca_coords[idx, 0]),
            "pca_y": float(pca_coords[idx, 1]),
        }
        if tsne_coords is not None:
            row["tsne_x"] = float(tsne_coords[idx, 0])
            row["tsne_y"] = float(tsne_coords[idx, 1])
        rows.append(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "embedding_projection.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    logger.info("Projection data saved to %s", csv_path)
    return csv_path


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    persist_dir = Path(args.persist_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    collection = connect_collection(persist_dir, args.collection)
    total_count = collection.count()

    ids, metadatas, embeddings = load_embedding_sample(collection, args.sample_size, args.seed)
    normed = _normalize_embeddings(embeddings)

    pairwise_values = pairwise_similarity(normed, args.pairwise_samples, args.seed)
    pairwise_stats = _describe(pairwise_values)

    neighbor_stats = nearest_neighbor_stats(normed)
    projection_csv = projection_report(
        normed,
        ids,
        metadatas,
        output_dir,
        args.tsne,
        args.tsne_perplexity,
        args.projection_sample,
        args.seed,
    )

    collapse_risk = bool(pairwise_stats) and pairwise_stats.get("mean", 0.0) >= args.collapse_threshold
    report = {
        "collection": args.collection,
        "total_vectors": int(total_count),
        "sampled_vectors": len(ids),
        "analysis_settings": {
            "sample_size": args.sample_size,
            "pairwise_samples": args.pairwise_samples,
            "projection_sample": args.projection_sample,
            "tsne_enabled": bool(args.tsne),
            "collapse_threshold": args.collapse_threshold,
        },
        "pairwise_similarity": {
            "stats": pairwise_stats,
            "collapse_risk": collapse_risk,
        },
        "nearest_neighbor": neighbor_stats,
        "projection_csv": str(projection_csv) if projection_csv else None,
    }

    report_path = output_dir / "embedding_dispersion_report.json"
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    logger.info("Dispersion report saved to %s", report_path)

    print("\n=== Embedding Dispersion Summary ===")
    print(f" Collection     : {args.collection}")
    print(f" Persist Dir    : {persist_dir}")
    print(f" Total Vectors  : {total_count}")
    print(f" Sampled Vectors: {len(ids)}")
    print("\n[Pairwise Cosine Similarity]")
    if pairwise_stats:
        print(f" Mean: {pairwise_stats['mean']:.4f} | Median: {pairwise_stats['median']:.4f} | Std: {pairwise_stats['std']:.4f}")
        print(f" Min : {pairwise_stats['min']:.4f} | Max: {pairwise_stats['max']:.4f}")
        print(f" P10 : {pairwise_stats['p10']:.4f} | P90: {pairwise_stats['p90']:.4f}")
        if collapse_risk:
            print(" ⚠️  Mean similarity is above the collapse threshold. Inspect sample sentences or use richer text.")
        else:
            print(" ✅ Mean similarity is below the collapse threshold.")
    else:
        print("Not enough data to compute pairwise statistics.")

    print("\n[Nearest Neighbor Similarity]")
    if neighbor_stats:
        nn_stats = neighbor_stats.get("similarity", {})
        if nn_stats:
            print(f" Mean NN similarity: {nn_stats['mean']:.4f} (higher = vectors clump together)")
    else:
        print("Not enough data to compute nearest-neighbor statistics.")

    if projection_csv:
        print(f"\nPCA/TSNE samples written to: {projection_csv}")


if __name__ == "__main__":
    main()
