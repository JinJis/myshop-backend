from __future__ import annotations

from typing import Any
from typing import Dict
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth import logout
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .storage import DATA_STORE
from .storage import _uid

User = get_user_model()


def error_response(status_code: int, code: str, message: str, details: Any | None = None) -> Response:
    payload: Dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=status_code)


def serialize_user(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
    }


def require_auth(request) -> tuple[bool, Response | None]:
    if not request.user.is_authenticated:
        return False, error_response(
            status.HTTP_401_UNAUTHORIZED, "unauthenticated", "You need to sign in to use this endpoint."
        )
    return True, None


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, provider: str) -> Response:
        normalized = provider.lower()
        if normalized not in {"google", "apple", "naver"}:
            return error_response(
                status.HTTP_400_BAD_REQUEST, "unsupported_provider", f"Login with {provider} is not available."
            )
        redirect_url = request.data.get("redirectUrl") if isinstance(request.data, dict) else None
        defaults = {"name": f"{normalized.title()} Demo"}
        user, _created = User.objects.get_or_create(
            email=f"{normalized}_user@example.com",
            defaults=defaults,
        )
        if not user.name:
            user.name = defaults["name"]
            user.save(update_fields=["name"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        DATA_STORE.ensure_user_state(user.id)
        return Response({"user": serialize_user(user), "redirect": redirect_url or "/"})


class AuthLogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request) -> Response:
        logout(request)
        return Response({"ok": True})


class AuthSessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        if not request.user.is_authenticated:
            return error_response(
                status.HTTP_401_UNAUTHORIZED, "unauthenticated", "No active session for this request."
            )
        DATA_STORE.ensure_user_state(request.user.id)
        return Response(
            {"user": serialize_user(request.user), "storeId": DATA_STORE.get_default_store_id(request.user.id)}
        )


class StoreSearchView(APIView):
    def get(self, request) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        query = request.query_params.get("query", "") if hasattr(request, "query_params") else ""
        results = DATA_STORE.search_stores(query)
        return Response({"results": results})


class StoreIngestionStartView(APIView):
    def post(self, request, store_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        store = DATA_STORE.get_store(store_id)
        if not store:
            return error_response(status.HTTP_404_NOT_FOUND, "store_not_found", "Store was not found.")
        DATA_STORE.link_store(request.user.id, store_id)
        record = DATA_STORE.start_ingestion(store_id)
        DATA_STORE.record_selection(
            record.id,
            [
                asset["id"]
                for group in record.asset_groups
                for asset in group["assets"]
                if asset.get("selected")
            ],
        )
        return Response({"ingestionId": record.id, "status": record.status})


class IngestionDetailView(APIView):
    def get(self, request, ingestion_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        record = DATA_STORE.get_ingestion(ingestion_id)
        if not record:
            return error_response(status.HTTP_404_NOT_FOUND, "ingestion_not_found", "Ingestion was not found.")
        return Response(
            {
                "id": record.id,
                "storeId": record.store_id,
                "progress": record.progress,
                "steps": record.steps,
                "estimatedSecondsRemaining": record.estimated_seconds_remaining,
            }
        )


class IngestionCancelView(APIView):
    def post(self, request, ingestion_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        record = DATA_STORE.cancel_ingestion(ingestion_id)
        if not record:
            return error_response(status.HTTP_404_NOT_FOUND, "ingestion_not_found", "Ingestion was not found.")
        return Response({"id": record.id, "status": record.status})


class IngestionAssetsView(APIView):
    def get(self, request, ingestion_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        record = DATA_STORE.get_ingestion(ingestion_id)
        if not record:
            return error_response(status.HTTP_404_NOT_FOUND, "ingestion_not_found", "Ingestion was not found.")
        return Response({"storeId": record.store_id, "categories": record.asset_groups})


class IngestionSelectionView(APIView):
    def post(self, request, ingestion_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        selection = request.data.get("selectedAssetIds") if isinstance(request.data, dict) else None
        if not isinstance(selection, list):
            return error_response(
                status.HTTP_400_BAD_REQUEST, "invalid_payload", "selectedAssetIds must be a list of asset IDs."
            )
        updated = DATA_STORE.record_selection(ingestion_id, selection)
        if updated is None:
            return error_response(status.HTTP_404_NOT_FOUND, "ingestion_not_found", "Ingestion was not found.")
        return Response({"selectedAssetIds": list(updated)})


class IngestionFinalizeView(APIView):
    def post(self, request, ingestion_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        outcome = DATA_STORE.finalize_ingestion(ingestion_id)
        if not outcome:
            return error_response(status.HTTP_404_NOT_FOUND, "ingestion_not_found", "Ingestion was not found.")
        return Response(outcome)


class AssetUploadUrlView(APIView):
    def post(self, request) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        asset_id = _uid("asset")
        upload_url = f"https://uploads.example.com/{asset_id}"
        DATA_STORE.pending_uploads[asset_id] = {"uploadUrl": upload_url, "createdAt": timezone.now()}
        return Response({"uploadUrl": upload_url, "assetId": asset_id})


class AssetListCreateView(APIView):
    def get(self, request) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        store_id = request.query_params.get("storeId")
        category = request.query_params.get("category")
        assets = DATA_STORE.list_assets(store_id, category)
        return Response({"results": assets})

    def post(self, request) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        payload = request.data if isinstance(request.data, dict) else {}
        name = payload.get("name") or "Uploaded Asset"
        category = payload.get("category")
        if not category:
            return error_response(status.HTTP_400_BAD_REQUEST, "missing_category", "category is required.")
        store_id = payload.get("storeId") or DATA_STORE.get_default_store_id(request.user.id)
        if not store_id:
            return error_response(status.HTTP_400_BAD_REQUEST, "missing_store", "A storeId is required.")
        store = DATA_STORE.get_store(store_id)
        if not store:
            return error_response(status.HTTP_404_NOT_FOUND, "store_not_found", "Store was not found.")
        asset_id = payload.get("assetId")
        url = payload.get("url")
        if not url and asset_id and asset_id in DATA_STORE.pending_uploads:
            url = DATA_STORE.pending_uploads[asset_id]["uploadUrl"]
        DATA_STORE.link_store(request.user.id, store_id)
        asset = DATA_STORE.create_asset(name=name, category=category, store_id=store_id, asset_id=asset_id, url=url)
        if asset_id and asset_id in DATA_STORE.pending_uploads:
            DATA_STORE.pending_uploads.pop(asset_id, None)
        return Response(asset, status=status.HTTP_201_CREATED)


class AssetDetailView(APIView):
    def get(self, request, asset_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        asset = DATA_STORE.get_asset(asset_id)
        if not asset:
            return error_response(status.HTTP_404_NOT_FOUND, "asset_not_found", "Asset was not found.")
        return Response(asset)

    def patch(self, request, asset_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        asset = DATA_STORE.get_asset(asset_id)
        if not asset:
            return error_response(status.HTTP_404_NOT_FOUND, "asset_not_found", "Asset was not found.")
        payload = request.data if isinstance(request.data, dict) else {}
        if "name" in payload:
            asset["name"] = payload["name"]
        if "category" in payload and payload["category"]:
            asset["category"] = payload["category"]
        return Response(asset)

    def delete(self, request, asset_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        deleted = DATA_STORE.delete_asset(asset_id)
        if not deleted:
            return error_response(status.HTTP_404_NOT_FOUND, "asset_not_found", "Asset was not found.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetDownloadView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, asset_id: str) -> Response:
        asset = DATA_STORE.get_asset(asset_id)
        if not asset:
            return error_response(status.HTTP_404_NOT_FOUND, "asset_not_found", "Asset was not found.")
        return Response(status=status.HTTP_302_FOUND, headers={"Location": asset["url"]})


class PosterGenerationStartView(APIView):
    def post(self, request) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        job = DATA_STORE.create_poster_job(request.data if isinstance(request.data, dict) else {})
        return Response({"jobId": job["id"], "status": job["status"]})


class PosterGenerationDetailView(APIView):
    def get(self, request, job_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        job = DATA_STORE.get_poster_job(job_id)
        if not job:
            return error_response(status.HTTP_404_NOT_FOUND, "job_not_found", "Poster job was not found.")
        return Response(
            {
                "id": job["id"],
                "jobId": job["id"],
                "status": job["status"],
                "resultUrl": job["resultUrl"],
                "error": job["error"],
            }
        )


class PosterGenerationSaveView(APIView):
    def post(self, request, job_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        if job_id not in DATA_STORE.poster_jobs:
            return error_response(status.HTTP_404_NOT_FOUND, "job_not_found", "Poster job was not found.")
        asset_id = DATA_STORE.save_poster_job(job_id)
        if not asset_id:
            return error_response(status.HTTP_400_BAD_REQUEST, "job_not_ready", "Poster job is not ready yet.")
        return Response({"assetId": asset_id})


class StyleReferencesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        return Response({"results": DATA_STORE.style_refs})


class MenuBoardGenerationStartView(APIView):
    def post(self, request) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        job = DATA_STORE.create_menu_board_job(request.data if isinstance(request.data, dict) else {})
        return Response({"jobId": job["id"], "status": job["status"]})


class MenuBoardGenerationDetailView(APIView):
    def get(self, request, job_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        job = DATA_STORE.get_menu_board_job(job_id)
        if not job:
            return error_response(status.HTTP_404_NOT_FOUND, "job_not_found", "Menu board job was not found.")
        return Response(
            {
                "id": job["id"],
                "jobId": job["id"],
                "status": job["status"],
                "resultUrl": job["resultUrl"],
                "error": job["error"],
            }
        )


class MenuBoardGenerationSaveView(APIView):
    def post(self, request, job_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        if job_id not in DATA_STORE.menu_board_jobs:
            return error_response(status.HTTP_404_NOT_FOUND, "job_not_found", "Menu board job was not found.")
        asset_id = DATA_STORE.save_menu_board_job(job_id)
        if not asset_id:
            return error_response(status.HTTP_400_BAD_REQUEST, "job_not_ready", "Menu board job is not ready yet.")
        return Response({"assetId": asset_id})


class ProfileView(APIView):
    def get(self, request) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        DATA_STORE.ensure_user_state(request.user.id)
        return Response(
            {
                "id": request.user.id,
                "email": request.user.email,
                "name": request.user.name,
                "preferences": DATA_STORE.get_user_preferences(request.user.id),
                "stores": DATA_STORE.get_user_stores(request.user.id),
            }
        )

    def patch(self, request) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        payload = request.data if isinstance(request.data, dict) else {}
        if "name" in payload:
            request.user.name = payload["name"]
            request.user.save(update_fields=["name"])
        prefs_updates = payload.get("preferences", {})
        if prefs_updates:
            prefs = DATA_STORE.update_user_preferences(request.user.id, prefs_updates)
        else:
            prefs = DATA_STORE.get_user_preferences(request.user.id)
        return Response(
            {
                "id": request.user.id,
                "email": request.user.email,
                "name": request.user.name,
                "preferences": prefs,
                "stores": DATA_STORE.get_user_stores(request.user.id),
            }
        )


class UserStoresView(APIView):
    def get(self, request) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        return Response({"results": DATA_STORE.get_user_stores(request.user.id)})


class UserStoreDetailView(APIView):
    def delete(self, request, store_id: str) -> Response:
        ok, resp = require_auth(request)
        if not ok:
            return resp  # type: ignore[return-value]
        store = DATA_STORE.get_store(store_id)
        if not store:
            return error_response(status.HTTP_404_NOT_FOUND, "store_not_found", "Store was not found.")
        DATA_STORE.unlink_store(request.user.id, store_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
