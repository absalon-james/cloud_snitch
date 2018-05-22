from .views import ModelViewSet
from .views import ObjectDiffViewSet
from .views import PathViewSet
from .views import PropertyViewSet
from .views import ObjectViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'models', ModelViewSet, base_name='models')
router.register(r'paths', PathViewSet, base_name='paths')
router.register(r'properties', PropertyViewSet, base_name='properties')
router.register(r'objects', ObjectViewSet, base_name='objects')
router.register(r'objectdiffs', ObjectDiffViewSet, base_name='objectdiffs')
urlpatterns = router.urls
