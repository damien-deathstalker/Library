from django.contrib import admin
from django.db.models import Exists, OuterRef, Subquery
from .models import Book, Chapter, Comment
from django.contrib.auth.models import Group
# Register your models here.

class adminBook(admin.ModelAdmin):
	list_display = ['cover', 'name', 'blurb', 'font', 'status']
	list_display_links = ['name']
	list_editable = ['blurb', 'font']

	def cover(self, obj):
		return obj.get_cover_image(height=140, width=140)

	@admin.display(description='Status')
	def status(self, obj):
		"""Whether the book is still going or has reached its ending.

		Worth a column of its own: the difference decides how the shelf filter
		treats it, and from the chapter list alone there is no way to tell.
		"""
		if not obj.is_complete:
			return 'Ongoing'
		return f'Completed at “{obj.last_chapter_title}”'

	def get_queryset(self, request):
		"""The status column, without a query per row.

		Annotated rather than asked for on the model: see the note there about
		properties shadowing annotations of the same name.
		"""
		return super().get_queryset(request).annotate(
			is_complete=Exists(
				Chapter.objects.filter(book_fk=OuterRef('pk'), is_final=True)
			),
			last_chapter_title=Subquery(
				Chapter.objects.filter(book_fk=OuterRef('pk'), is_final=True).values('title')[:1]
			),
		)

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
	list_display = ['book_fk', 'title', 'is_final']
	# Filterable by it, so the chapters that have ended a book are one click
	# away rather than something to hunt for down the list.
	list_filter = ['book_fk__name', 'is_final']
	ordering = ['book_fk', 'id']
	list_display_links = ['title']
	# is_final above the content: it is a decision about the book, not part of
	# the writing, and it is the first thing to reach for.
	fields = ['book_fk', 'title', 'is_final', 'content']

	def get_queryset(self, request):
		return super().get_queryset(request).select_related('book_fk')

admin.site.register(Book, adminBook)
admin.site.register(Chapter, adminChapter)
admin.site.register(Comment, adminComment)

# Unregister your models here.
admin.site.unregister(Group)

admin.site.site_title = "Damien's Bookshelf - Administration Site"
admin.site.site_header = "Damien's Bookshelf - Administration"
admin.site.index_title  =  "Damien's Bookshelf - Administration"