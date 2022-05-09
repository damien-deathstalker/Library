from django.contrib import admin
from .models import Book, Chapter, Comment
from django.contrib.auth.models import Group
# Register your models here.

class adminBook(admin.ModelAdmin):
	list_display = ['cover', 'name', 'blurb', 'font']
	list_display_links = ['name']
	list_editable = ['blurb', 'font']
	
	def cover(self, obj):
		return obj.get_cover_image(height=140, width=140)

class adminComment(admin.ModelAdmin):
	list_display = ['name', 'comment', 'chapter_name', 'book_name']
	list_display_links = ['comment']
	list_filter = ['chapter_fk__book_fk__name']
	search_fields = ['name', 'chapter_fk__book_fk__name']

	def chapter_name(self, obj):
		return obj.chapter_fk.title
	
	def book_name(self, obj):
		return obj.chapter_fk.book_fk.name
	
	def comment(self, obj):
		return obj.comment_post
	
	def has_add_permission(self, request) -> bool:
		return False

class adminChapter(admin.ModelAdmin):
	list_display = ['book_fk', 'title']
	list_filter = ['book_fk__name']
	ordering = ['book_fk', 'id']
	list_display_links = ['title']

admin.site.register(Book, adminBook)
admin.site.register(Chapter, adminChapter)
admin.site.register(Comment, adminComment)

# Unregister your models here.
admin.site.unregister(Group)

admin.site.site_title = "Damien's Bookshelf - Administration Site"
admin.site.site_header = "Damien's Bookshelf - Administration"
admin.site.index_title  =  "Damien's Bookshelf - Administration"