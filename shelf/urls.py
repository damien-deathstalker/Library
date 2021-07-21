from django.urls.conf import path
from .views import index

urlpatterns = [
	path('', index, name='shelf_index'),
]