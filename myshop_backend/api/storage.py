from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from uuid import uuid4

from django.utils import timezone


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass(slots=True)
class IngestionRecord:
    id: str
    store_id: str
    status: str
    progress: int
    steps: List[dict]
    estimated_seconds_remaining: int
    started_at: datetime = field(default_factory=timezone.now)
    selected_asset_ids: Set[str] = field(default_factory=set)
    asset_groups: List[dict] = field(default_factory=list)


class DemoDataStore:
    """Lightweight in-memory data store to back the demo API contract."""

    def __init__(self) -> None:
        self.stores: List[dict] = [
            {
                "id": "s1",
                "name": "The Morning Brew",
                "address": "123 Main St",
                "category": "Cafe",
                "imageUrl": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?q=80&w=1200",
            },
            {
                "id": "s2",
                "name": "Golden Spoon Diner",
                "address": "22 Oak Avenue",
                "category": "Diner",
                "imageUrl": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?q=80&w=1200",
            },
            {
                "id": "s3",
                "name": "Lotus Garden",
                "address": "8 Park Lane",
                "category": "Restaurant",
                "imageUrl": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=1200",
            },
            {
                "id": "s4",
                "name": "Neon Noodles",
                "address": "77 Sunset Blvd",
                "category": "Street Food",
                "imageUrl": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=1200",
            },
        ]
        self.user_preferences: Dict[int, dict] = {}
        self.user_store_links: Dict[int, List[str]] = {}
        self.ingestions: Dict[str, IngestionRecord] = {}
        self.assets: Dict[str, dict] = {}
        self.pending_uploads: Dict[str, dict] = {}
        self.poster_jobs: Dict[str, dict] = {}
        self.menu_board_jobs: Dict[str, dict] = {}
        self.asset_library_id = "library_default"
        self.style_refs: List[dict] = [
            {
                "id": "style_classic",
                "name": "Classic Bistro",
                "previewUrl": "https://images.unsplash.com/photo-1521017432531-fbd92d768814?q=80&w=1200",
                "description": "Warm colors, serif type, friendly texture.",
            },
            {
                "id": "style_modern",
                "name": "Modern Minimal",
                "previewUrl": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?q=80&w=1200",
                "description": "Bold sans-serif, high contrast, clean layout.",
            },
            {
                "id": "style_bold",
                "name": "Bold Neon",
                "previewUrl": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=1200",
                "description": "Electric palette with punchy gradients.",
            },
            {
                "id": "style_organic",
                "name": "Organic Fresh",
                "previewUrl": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?q=80&w=1200",
                "description": "Handwritten accents and leafy greens.",
            },
        ]
        self._seed_assets()

    # ---- user state -----------------------------------------------------
    def ensure_user_state(self, user_id: int) -> None:
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {"theme": "light", "notifications": True}
        if user_id not in self.user_store_links:
            self.user_store_links[user_id] = [self.stores[0]["id"]]

    def get_user_preferences(self, user_id: int) -> dict:
        self.ensure_user_state(user_id)
        return self.user_preferences[user_id]

    def update_user_preferences(self, user_id: int, updates: dict) -> dict:
        prefs = self.get_user_preferences(user_id)
        prefs.update({k: v for k, v in updates.items() if v is not None})
        return prefs

    def get_user_stores(self, user_id: int) -> List[dict]:
        self.ensure_user_state(user_id)
        linked_ids = set(self.user_store_links[user_id])
        return [store for store in self.stores if store["id"] in linked_ids]

    def link_store(self, user_id: int, store_id: str) -> None:
        self.ensure_user_state(user_id)
        if store_id not in self.user_store_links[user_id]:
            self.user_store_links[user_id].append(store_id)

    def unlink_store(self, user_id: int, store_id: str) -> None:
        self.ensure_user_state(user_id)
        self.user_store_links[user_id] = [
            _id for _id in self.user_store_links[user_id] if _id != store_id
        ]

    def get_default_store_id(self, user_id: int) -> Optional[str]:
        self.ensure_user_state(user_id)
        return self.user_store_links[user_id][0] if self.user_store_links[user_id] else None

    # ---- stores & search -------------------------------------------------
    def search_stores(self, query: str) -> List[dict]:
        if not query:
            return self.stores
        normalized = query.lower()
        return [
            store
            for store in self.stores
            if normalized in store["name"].lower()
            or normalized in store["category"].lower()
            or normalized in store["address"].lower()
        ]

    def get_store(self, store_id: str) -> Optional[dict]:
        return next((store for store in self.stores if store["id"] == store_id), None)

    # ---- ingestions ------------------------------------------------------
    def start_ingestion(self, store_id: str) -> IngestionRecord:
        ingestion_id = _uid("ing")
        steps = [
            {"id": "collect_basics", "label": "Collecting basic information", "status": "in_progress"},
            {"id": "find_logo", "label": "Finding store logo", "status": "pending"},
            {"id": "catalog_products", "label": "Cataloging products", "status": "pending"},
            {"id": "gather_photos", "label": "Gathering photos", "status": "pending"},
        ]
        record = IngestionRecord(
            id=ingestion_id,
            store_id=store_id,
            status="in_progress",
            progress=5,
            steps=steps,
            estimated_seconds_remaining=90,
            asset_groups=self._build_ingestion_assets(store_id),
        )
        self.ingestions[ingestion_id] = record
        return record

    def get_ingestion(self, ingestion_id: str) -> Optional[IngestionRecord]:
        record = self.ingestions.get(ingestion_id)
        if record:
            self._refresh_ingestion_progress(record)
        return record

    def cancel_ingestion(self, ingestion_id: str) -> Optional[IngestionRecord]:
        record = self.ingestions.get(ingestion_id)
        if record:
            record.status = "canceled"
            record.estimated_seconds_remaining = 0
            record.progress = min(record.progress, 80)
            for step in record.steps:
                if step["status"] == "in_progress":
                    step["status"] = "canceled"
        return record

    def record_selection(self, ingestion_id: str, selected_ids: List[str]) -> Optional[Set[str]]:
        record = self.ingestions.get(ingestion_id)
        if not record:
            return None
        record.selected_asset_ids = set(selected_ids)
        for group in record.asset_groups:
            for asset in group["assets"]:
                asset["selected"] = asset["id"] in record.selected_asset_ids
        return record.selected_asset_ids

    def finalize_ingestion(self, ingestion_id: str) -> Optional[dict]:
        record = self.ingestions.get(ingestion_id)
        if not record:
            return None
        record.status = "completed"
        record.progress = 100
        record.estimated_seconds_remaining = 0
        for step in record.steps:
            step["status"] = "completed"
        selected_assets: List[dict] = []
        for group in record.asset_groups:
            for asset in group["assets"]:
                if asset["id"] in record.selected_asset_ids or asset.get("selected"):
                    selected_assets.append(asset)
        for asset in selected_assets:
            asset_copy = {
                "id": asset["id"],
                "name": asset["name"],
                "url": asset["url"],
                "category": group_id_from_asset(asset),
                "storeId": record.store_id,
            }
            self.assets[asset_copy["id"]] = asset_copy
        self.link_store_for_asset(record.store_id)
        return {"assetLibraryId": self.asset_library_id, "totalAssets": len(selected_assets)}

    def _refresh_ingestion_progress(self, record: IngestionRecord) -> None:
        if record.status != "in_progress":
            return
        elapsed = (timezone.now() - record.started_at).total_seconds()
        step_durations = [8, 10, 12, 20]
        cumulative = 0
        progress_points = []
        for duration in step_durations:
            cumulative += duration
            progress_points.append(cumulative)
        total_time = progress_points[-1]
        steps_completed = 0
        for idx, cutoff in enumerate(progress_points):
            if elapsed >= cutoff:
                steps_completed = idx + 1
                record.steps[idx]["status"] = "completed"
                continue
            if record.steps[idx]["status"] == "pending":
                record.steps[idx]["status"] = "in_progress"
            break
        if elapsed >= total_time:
            record.status = "completed"
            record.progress = 100
            record.estimated_seconds_remaining = 0
            for step in record.steps:
                step["status"] = "completed"
            return
        record.progress = min(95, int((elapsed / total_time) * 100))
        record.estimated_seconds_remaining = max(10, int(total_time - elapsed))

    def _build_ingestion_assets(self, store_id: str) -> List[dict]:
        base_images = [
            "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=800",
            "https://images.unsplash.com/photo-1509042239860-f550ce710b93?q=80&w=800",
            "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=800",
            "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?q=80&w=800",
        ]
        categories = [
            ("logo", "Store Logo"),
            ("menu", "Menu"),
            ("products", "Product Images"),
            ("interior", "Interior"),
        ]
        groups: List[dict] = []
        for idx, (category_id, name) in enumerate(categories):
            assets = []
            for variant in range(1, 3):
                asset_id = f"{category_id}_{variant}_{store_id}"
                assets.append(
                    {
                        "id": asset_id,
                        "name": f"{name} {variant}",
                        "url": base_images[(idx + variant) % len(base_images)],
                        "selected": variant == 1,
                    }
                )
            groups.append({"id": category_id, "name": name, "assets": assets})
        return groups

    # ---- assets ---------------------------------------------------------
    def _seed_assets(self) -> None:
        for store in self.stores[:2]:
            for idx, category in enumerate(["logo", "menu", "products", "interior"]):
                asset_id = f"{category}_{store['id']}"
                self.assets[asset_id] = {
                    "id": asset_id,
                    "name": f"{store['name']} {category.title()}",
                    "url": f"https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w={800 + idx*50}",
                    "category": category,
                    "storeId": store["id"],
                }

    def link_store_for_asset(self, store_id: str) -> None:
        for user_id in self.user_store_links:
            self.link_store(user_id, store_id)

    def list_assets(self, store_id: Optional[str], category: Optional[str]) -> List[dict]:
        assets = list(self.assets.values())
        if store_id:
            assets = [asset for asset in assets if asset["storeId"] == store_id]
        if category and category != "all":
            assets = [asset for asset in assets if asset["category"] == category]
        return assets

    def get_asset(self, asset_id: str) -> Optional[dict]:
        return self.assets.get(asset_id)

    def create_asset(
        self,
        name: str,
        category: str,
        store_id: str,
        asset_id: Optional[str] = None,
        url: Optional[str] = None,
    ) -> dict:
        final_id = asset_id or _uid("asset")
        asset = {
            "id": final_id,
            "name": name,
            "category": category,
            "storeId": store_id,
            "url": url or f"https://images.unsplash.com/photo-1509042239860-f550ce710b93?q=80&w=900",
        }
        self.assets[final_id] = asset
        return asset

    def delete_asset(self, asset_id: str) -> bool:
        if asset_id in self.assets:
            del self.assets[asset_id]
            return True
        return False

    # ---- generations ----------------------------------------------------
    def create_poster_job(self, payload: dict) -> dict:
        job_id = _uid("poster_job")
        job = {
            "id": job_id,
            "status": "queued",
            "resultUrl": None,
            "error": None,
            "assetIds": payload.get("assetIds", []),
            "headline": payload.get("headline"),
            "subtext": payload.get("subtext"),
            "styleRefIds": payload.get("styleRefIds", []),
            "stylePrompt": payload.get("stylePrompt"),
            "createdAt": timezone.now(),
        }
        self.poster_jobs[job_id] = job
        return job

    def get_poster_job(self, job_id: str) -> Optional[dict]:
        job = self.poster_jobs.get(job_id)
        if job:
            self._progress_job(job, "poster")
        return job

    def save_poster_job(self, job_id: str) -> Optional[str]:
        job = self.poster_jobs.get(job_id)
        if not job:
            return None
        if job["status"] != "succeeded":
            job["status"] = "failed"
            job["error"] = "Job is not finished yet."
            return None
        asset = self.create_asset(
            name=job.get("headline") or "Generated Poster",
            category="poster",
            store_id=self.stores[0]["id"],
        )
        return asset["id"]

    def create_menu_board_job(self, payload: dict) -> dict:
        job_id = _uid("menu_job")
        job = {
            "id": job_id,
            "status": "queued",
            "resultUrl": None,
            "error": None,
            "items": payload.get("items", []),
            "templateStyle": payload.get("templateStyle"),
            "logoAssetId": payload.get("logoAssetId"),
            "productAssetIds": payload.get("productAssetIds", []),
            "createdAt": timezone.now(),
        }
        self.menu_board_jobs[job_id] = job
        return job

    def get_menu_board_job(self, job_id: str) -> Optional[dict]:
        job = self.menu_board_jobs.get(job_id)
        if job:
            self._progress_job(job, "menu")
        return job

    def save_menu_board_job(self, job_id: str) -> Optional[str]:
        job = self.menu_board_jobs.get(job_id)
        if not job:
            return None
        if job["status"] != "succeeded":
            job["status"] = "failed"
            job["error"] = "Job is not finished yet."
            return None
        asset = self.create_asset(
            name="Menu Board",
            category="menu",
            store_id=self.stores[0]["id"],
        )
        return asset["id"]

    def _progress_job(self, job: dict, kind: str) -> None:
        if job["status"] in {"failed", "succeeded"}:
            return
        elapsed = (timezone.now() - job["createdAt"]).total_seconds()
        if elapsed > 10:
            job["status"] = "succeeded"
            job["resultUrl"] = f"https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=1200&{job['id']}"
        elif elapsed > 2:
            job["status"] = "running"
        else:
            job["status"] = "queued"


def group_id_from_asset(asset: dict) -> str:
    if asset.get("category"):
        return asset["category"]
    asset_id: str = asset.get("id", "")
    if "_" in asset_id:
        return asset_id.split("_", 1)[0]
    return "products"


DATA_STORE = DemoDataStore()
