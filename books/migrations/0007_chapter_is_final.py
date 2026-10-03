from django.db import migrations, models


class Migration(migrations.Migration):
	"""Let a book have a last chapter.

	The partial unique index is the point of the second operation rather than a
	formality. The rule "one last chapter per book" is checked in Chapter.clean,
	which the admin calls before saving -- but two admin tabs open on the same
	book both pass that check and then both save, so the database is the only
	place the rule can actually hold.

	Only rows that are endings are indexed, so a book keeps any number of
	chapters that are not the last one.

	Existing books are left open. Ending one is a decision, not a default.
	"""

	dependencies = [
		('books', '0006_auto_20220509_1519'),
	]

	operations = [
		migrations.AddField(
			model_name='chapter',
			name='is_final',
			field=models.BooleanField(default=False, verbose_name='Last chapter of the book'),
		),
		migrations.AddConstraint(
			model_name='chapter',
			constraint=models.UniqueConstraint(
				condition=models.Q(('is_final', True)),
				fields=('book_fk',),
				name='one_last_chapter_per_book',
			),
		),
	]