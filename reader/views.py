from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from books.models import Book, Chapter, Comment, Bookmark


# Create your views here.
def book_index(request, book_id):
	book = get_object_or_404(Book, pk=book_id)
	return render(request, 'reader/index.html', {
		'book': book,
		'chapters': book.get_chapters(),
	})


def read_chapter(request, book_id, chapter_id):
	chapter = get_object_or_404(Chapter, pk=chapter_id, book_fk__id=book_id)
	chapters = list(Chapter.objects.filter(book_fk__id=book_id).order_by('pk'))
	index = chapters.index(chapter)

	# Get the reader's bookmark for this book, if any.
	user = request.user if request.user.is_authenticated else None
	session_key = request.session.session_key
	if not session_key:
		request.session.save()
		session_key = request.session.session_key
	bookmark = Bookmark.get_for_reader(chapter.book_fk, user=user, session_key=session_key)

	context = {
		'book': chapter.book_fk,
		'chapter': chapter,
		'chapters': chapters,
		'chapter_number': index + 1,
		'comments': Comment.objects.filter(chapter_fk=chapter),
		'bookmark': bookmark,
	}
	if index > 0:
		context['previous_chapter'] = chapters[index - 1]
	if index < len(chapters) - 1:
		context['next_chapter'] = chapters[index + 1]

	return render(request, 'reader/read.html', context)


def chapter_comments(request, chapter_id):
	"""List comments for a chapter, or post one.

	Always answers with JSON: {'html': ...} for a rendered fragment, or
	{'error': ...} with a 400. Replaces the old request.is_ajax() check,
	which Django removed in 4.0.
	"""
	chapter = get_object_or_404(Chapter, pk=chapter_id)

	if request.method == 'POST':
		name = (request.POST.get('name') or '').strip()
		body = (request.POST.get('comment') or '').strip()

		if len(name) < 2:
			return JsonResponse({'error': 'Add your name so I know who is reading.'}, status=400)
		if len(body) < 5:
			return JsonResponse({'error': 'Write a little more than that.'}, status=400)

		Comment.objects.create(
			chapter_fk=chapter,
			name=name[:50],
			comment_post=body,
		)
	elif request.method != 'GET':
		return JsonResponse({'error': 'Method not allowed.'}, status=405)

	comments = Comment.objects.filter(chapter_fk=chapter)
	return JsonResponse({
		'html': render_to_string('reader/comments.html', {'comments': comments}),
		'count': comments.count(),
	})


@require_http_methods(['GET', 'POST', 'DELETE'])
def chapter_bookmark(request, chapter_id):
	"""Get, set, or delete the bookmark for the current reader on this chapter's book.

	GET  -> {'paragraph_index': int, 'chapter_id': int} or null
	POST -> set bookmark to this chapter/paragraph, returns same shape
	DELETE -> remove bookmark, returns {'deleted': true}
	"""
	chapter = get_object_or_404(Chapter, pk=chapter_id)
	book = chapter.book_fk

	# Identify the reader: authenticated user first, then session.
	user = request.user if request.user.is_authenticated else None
	session_key = request.session.session_key
	if not session_key:
		request.session.save()
		session_key = request.session.session_key

	if request.method == 'GET':
		bm = Bookmark.get_for_reader(book, user=user, session_key=session_key)
		if bm:
			return JsonResponse({
				'paragraph_index': bm.paragraph_index,
				'chapter_id': bm.chapter_id,
			})
		return JsonResponse({'bookmark': None})

	if request.method == 'POST':
		try:
			paragraph_index = int(request.POST.get('paragraph_index', 0))
		except (TypeError, ValueError):
			return JsonResponse({'error': 'Invalid paragraph index.'}, status=400)

		bm = Bookmark.set_for_reader(
			book, chapter, paragraph_index,
			user=user, session_key=session_key,
		)
		return JsonResponse({
			'paragraph_index': bm.paragraph_index,
			'chapter_id': bm.chapter_id,
		})

	# DELETE
	Bookmark.delete_for_reader(book, user=user, session_key=session_key)
	return JsonResponse({'deleted': True})