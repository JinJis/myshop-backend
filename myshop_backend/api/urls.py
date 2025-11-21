from django.urls import path

from .views import AssetDetailView
from .views import AssetDownloadView
from .views import AssetListCreateView
from .views import AssetUploadUrlView
from .views import AuthLoginView
from .views import AuthLogoutView
from .views import AuthSessionView
from .views import IngestionAssetsView
from .views import IngestionCancelView
from .views import IngestionDetailView
from .views import IngestionFinalizeView
from .views import IngestionSelectionView
from .views import MenuBoardGenerationDetailView
from .views import MenuBoardGenerationSaveView
from .views import MenuBoardGenerationStartView
from .views import PosterGenerationDetailView
from .views import PosterGenerationSaveView
from .views import PosterGenerationStartView
from .views import ProfileView
from .views import StoreIngestionStartView
from .views import StoreSearchView
from .views import StyleReferencesView
from .views import UserStoreDetailView
from .views import UserStoresView

def allow_no_trailing_slash(route: str, view, name: str | None = None):
    urls = [path(route, view, name=name)]
    if route.endswith("/"):
        urls.append(path(route.rstrip("/"), view))
    return urls


routes = [
    ("auth/login/<str:provider>/", AuthLoginView.as_view(), "auth-login"),
    ("auth/logout/", AuthLogoutView.as_view(), "auth-logout"),
    ("auth/session/", AuthSessionView.as_view(), "auth-session"),
    ("stores/search/", StoreSearchView.as_view(), "stores-search"),
    ("stores/<str:store_id>/ingestions/", StoreIngestionStartView.as_view(), "store-ingestions"),
    ("stores/<str:store_id>/", UserStoreDetailView.as_view(), "store-detail"),
    ("stores/", UserStoresView.as_view(), "user-stores"),
    ("ingestions/<str:ingestion_id>/", IngestionDetailView.as_view(), "ingestion-detail"),
    ("ingestions/<str:ingestion_id>/cancel/", IngestionCancelView.as_view(), "ingestion-cancel"),
    ("ingestions/<str:ingestion_id>/assets/", IngestionAssetsView.as_view(), "ingestion-assets"),
    ("ingestions/<str:ingestion_id>/selection/", IngestionSelectionView.as_view(), "ingestion-selection"),
    ("ingestions/<str:ingestion_id>/finalize/", IngestionFinalizeView.as_view(), "ingestion-finalize"),
    ("assets/uploads/", AssetUploadUrlView.as_view(), "asset-upload"),
    ("assets/<str:asset_id>/download/", AssetDownloadView.as_view(), "asset-download"),
    ("assets/<str:asset_id>/", AssetDetailView.as_view(), "asset-detail"),
    ("assets/", AssetListCreateView.as_view(), "asset-list"),
    ("generations/posters/<str:job_id>/save/", PosterGenerationSaveView.as_view(), "poster-save"),
    ("generations/posters/<str:job_id>/", PosterGenerationDetailView.as_view(), "poster-detail"),
    ("generations/posters/", PosterGenerationStartView.as_view(), "poster-start"),
    ("generations/menu-boards/<str:job_id>/save/", MenuBoardGenerationSaveView.as_view(), "menu-board-save"),
    ("generations/menu-boards/<str:job_id>/", MenuBoardGenerationDetailView.as_view(), "menu-board-detail"),
    ("generations/menu-boards/", MenuBoardGenerationStartView.as_view(), "menu-board-start"),
    ("generations/styles/", StyleReferencesView.as_view(), "style-refs"),
    ("me/", ProfileView.as_view(), "me"),
]

urlpatterns = []
for route, view, name in routes:
    urlpatterns.extend(allow_no_trailing_slash(route, view, name))
