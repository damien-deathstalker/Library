from django.db.models import Count, Exists, OuterRef, Prefetch, Subquery
from django.shortcuts import render
from django.urls import reverse

from books.models import Book, Chapter
from shelf.templatetags.text import split_paragraphs

# Create your views here.
def index(request):
	# Three questions the shelf asks about every book, all answered here rather
	# than in the template, so a shelf of titles costs the same however many
	# titles are standing on it.
	#
	#   chapter_count    how long it is, said under the cover before you commit
	#   is_complete      whether it has an ending, which is what the filter
	#                    divides the shelf on
	#   last_chapter_id  which chapter ends it, so a reader who has arrived
	#                    there is told they finished rather than handed a
	#                    "continue" link to the thing they have already read
	#
	# The shelf is one board. Whether a book is going or completed is a filter
	# over it rather than a second shelf, because the two groups are the same
	# thing seen two ways -- a reader choosing what to read cares about the
	# cover and the title, not which side of a divide it came from.
	books = Book.objects.annotate(
		chapter_count=Count('chapter'),
		is_complete=Exists(
			Chapter.objects.filter(book_fk=OuterRef('pk'), is_final=True)
		),
		last_chapter_id=Subquery(
			Chapter.objects.filter(book_fk=OuterRef('pk'), is_final=True).values('pk')[:1]
		),
	).prefetch_related(
		# chapter_set rather than chapter: with no related_name on the foreign
		# key, `chapter` is the query name Count() takes but not the attribute
		# prefetch_related() looks for.
		Prefetch('chapter_set', queryset=Chapter.objects.order_by('pk'))
	).order_by('id')

	# What the book card needs when it is lifted off the board, so that lifting
	# it costs nothing. This is the whole modal's payload, and it is
	# deliberately the cheap half of the page: all four books come to 796 bytes
	# gzipped, which took the shelf from 2521 to 3328 -- against 8.0 MB of
	# covers that the card does not touch, because it asks for the same image
	# URL the cover on the board already used.
	#
	# Fetching this on click instead would trade a request and a round trip --
	# and a state where the reader is waiting on the author rather than on the
	# book -- for a fraction of what the page already carries. The chapter list
	# is here regardless, because naming the chapter a reader is resuming from
	# needs the title, and a stored copy of it would only be able to go stale.
	for book in books:
		book.card = {
			'name': book.name,
			'href': reverse('reader_index', args=[book.pk]),
			'cover': book.cover_image.url,
			# Resolved against FONT_STACKS on the model, so a book's prose is
			# set in the face its author asked for, never in whatever text came
			# out of the admin field.
			'font': book.font_stack,
			'blurb': split_paragraphs(book.blurb),
			'chapters': [
				{
					'id': chapter.pk,
					'title': chapter.title,
					'url': reverse('reader_chapter', args=[book.pk, chapter.pk]),
				}
				for chapter in book.chapter_set.all()
			],
		}

	return render(request, 'shelf/index.html', {'books': books})
