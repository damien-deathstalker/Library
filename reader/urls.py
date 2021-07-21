from django.urls import path
from .views import *
urlpatterns = [
	path('book/<int:book_id>/', book_index, name='reader_index'),
	path('read/<int:book_id>/<int:chapter_id>/', read_chapter, name='reader_chapter'),
	path('comments/<int:chapter_id>/', chapter_comments, name='chapter_comments')
]