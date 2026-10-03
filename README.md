# Library

Damien Ofei's bookshelf — speculative fiction, published a chapter at a time.

A Django site with three faces: a **shelf** of books, a **reader** for the
prose itself, and a **portfolio** that sits at the root. Books are written and
edited in the Django admin; everything a reader sees is generated from that.

---

## Running it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py build_covers      # see "Covers" below — this one matters
.venv/bin/python manage.py runserver 8765
```

Then `http://127.0.0.1:8765/shelf`. (8765 rather than the default 8000 only
because the test scripts in "Testing" assume it; anything works.)

`SECRET_KEY` and `DEBUG` are read from a `.env` at the repo root
(`python-decouple`). There is no `.env.example`; those two keys are the whole
contract:

```
SECRET_KEY=...
DEBUG=True
```

**No Node is needed to run the site.** Node is only for the stylesheet build
(see below), and the built stylesheet is committed.

### URLs

Note the shelf is `/shelf` with **no trailing slash**, and `/shelf/` is a hard
404 — not a redirect. `APPEND_SLASH` cannot save you here, because it works by
*adding* a slash, and the pattern that matches is the one without it. Every
other route in the project does take a trailing slash.

| path | what |
|---|---|
| `/` | portfolio |
| `/download/<slug>/` | the CV or resume. Slugs are `extended_cv` and `resume`; anything else 404s |
| `/shelf` | the shelf — all books, with the resume line under each title |
| `/reader/book/<id>/` | a book's page: cover, blurb, chapter list |
| `/reader/read/<book_id>/<chapter_id>/` | read one chapter |
| `/reader/comments/<chapter_id>/` | comments on a chapter |
| `/admin/` | everything an author touches |

---

## The apps

| app | what it owns |
|---|---|
| `books` | the models and the cover ladder. Its `views.py` is an untouched stub |
| `shelf` | the shelf page, its filter, and the book card that lifts off the board |
| `reader` | book pages, chapter pages, comments, and the reading chrome |
| `portfolio` | the CV and its downloads |
| `Library` | settings and root URLconf |

`shelf/templatetags/text.py` holds the one custom filter, `paragraphs`, which
splits a blurb on blank lines. The book card uses the same function, so the
blurb's paragraph rule has one source of truth.

### Models

```
Book      name, blurb, cover_image, font
Chapter   book_fk, title, content, is_final
Comment   chapter_fk, name, comment_post
```

Two things about these that are load-bearing and easy to trip over:

- **`Chapter.is_final`** marks the last chapter of a book. It is what lets the
  shelf tell "ongoing" from "finished", and the shelf filter offers both. See
  the note in `books/models.py` about why `Book` has no `is_complete`
  property — it would shadow the queryset annotation of the same name.
- **`Book.font`** is free text in the admin, so it is resolved against
  `FONT_STACKS` rather than dropped into a `style` attribute. Anything
  unrecognised falls back to `DEFAULT_READING_STACK` (Newsreader).

Reverse accessor is `chapter_set` — there is no `related_name` on the foreign
key. So `Count('chapter')` is right for a query name but
`prefetch_related('chapter')` 500s; the attribute is `chapter_set`.

---

## Covers

The originals are the masters and are committed at `media/cover_images/`. They
are 1410×2250 and are never what a page downloads: the largest any cover is
painted anywhere on the site is 660 CSS px, and the shelf slot is 152.

So `manage.py build_covers` derives a ladder of smaller WebP files beside them
— 160, 320, 640, 1280, and the master's own width — and the templates hand
those to `srcset`.

```bash
.venv/bin/python manage.py build_covers           # build
.venv/bin/python manage.py build_covers --check   # verify, exits non-zero if broken
```

**This has to run on the server after every deploy.** The derived files are
gitignored (`.gitignore:9`), so `git pull` will not bring them.

The reason it matters more than it looks: a missing ladder is **silent**. The
templates fall back to the original by design — a fresh checkout renders
correctly before anyone runs the command — so nothing errors, nothing warns,
every page looks right, and the shelf is quietly serving 7.88 MB of covers
instead of 128 KB. That is why `--check` exists and why it should be a deploy
gate:

```bash
git pull
.venv/bin/python manage.py build_covers
.venv/bin/python manage.py build_covers --check
```

It reports three states — `missing`, `stale`, `wrong size` — which between them
cover the four ways this goes wrong in practice: the ladder was never built at
all, one rung is absent out of many, a cover was replaced and its rungs were
not rebuilt, or a file is truncated, misnamed or not an image.

The per-rung table goes to stdout so it can still be read on a healthy run;
the failure and the fix go to **stderr**, and the exit code is 1.

Two honest caveats about how it decides "stale": the rung filenames carry the
width but no hash of the picture, so the only cheap signal is the file's
modification time. A fresh `git clone` stamps everything with checkout time, so
a rung can read as stale when it is not. The bias is deliberate — a false
positive costs one redundant re-encode, a false negative serves the wrong cover
indefinitely. It is documented at `is_stale()` in `books/covers.py`.

Nothing in the ladder is generated during a request. `srcset` only ever names
files a build step has already written.

---

## Styles

`src/css/` is the source of truth. `app.css` is the entry point and pulls in
the rest with `@import`.

```
tokens.css   colours, spacing, type scale, glass tokens — per theme
base.css     reset, layout, focus, reduced motion
intro.css    the landing page
shelf.css    the shelf, the slot, the book card
reader.css   book pages, chapter pages, the reading pill
```

Build with:

```bash
npm install
npm run build     # minified — this is what Django serves, and it is committed
npm run expand    # readable — for working
npm run dev       # readable, and watch
```

Two traps that are recorded in `postcss.config.js` because they cost real time:

- **`--minify` is not a postcss-cli 11 flag.** It is silently ignored, so for a
  long time `npm run build` read as though it minified while shipping the full
  65 KB with comments. Use `--env`, which the npm scripts already do.
- Minifying is the **default**, so a stray `npx postcss` cannot quietly produce
  an unminified file for someone to commit.

The themes (`night`, `day`, `sepia`) are CSS custom properties resolved from
`localStorage['bookshelf:theme']` in `shelf/templates/base.html`.

`shelf/static/shelf/js/app.js` is **hand-maintained source, not a build
artifact**, and is served as-is. It is deliberately unminified and lives
outside `src/` — see the note in `postcss.config.js` and the comment at the top
of that file.

---

## Testing

**`manage.py test` runs zero tests.** All four `tests.py` files are empty
Django stubs.

What verification does exist is a set of Puppeteer scripts that drive a real
Chrome and measure geometry and contrast — how wide a chapter title actually
paints, whether a ribbon clears the numeral beside it, the contrast ratio of a
lit row over the scrimmed shelf in each of the three themes. These are
throwaway and uncommitted, so they are currently one `rm` from being gone.
Moving them into the repo is the highest-value thing this project could do
next.

What they guard, and the numbers they hold:

| area | checks | what it pins down |
|---|---|---|
| book card | 69 | ribbon clears the chapter number; no horizontal scroll; `<cite>` is italic |
| contrast, 3 themes | 36 | every text/background pair on the card (tightest: 4.85:1, sepia, lit row) |
| shelf geometry | 120 | slot sizing and the filter pill at every width |
| shelf filter | 29 | ongoing/completed filtering |
| cover ladder | 19 | right rung chosen at 13 widths × 3 DPRs; no page fetches an original |
| `--check` gate | 18 | each fault exits non-zero and names itself correctly |
| fallback without ladder | 13 | pages still render with the derived files removed |
| states, rules, admin, edge | 53 | admin queries, fonts, comment edges |

Two of these started as bugs found by hand and then became permanent checks: a
negative margin on `.toc__link` that made the modal scroll sideways, and a
book page at 660 CSS px falling through to the 5.93 MB original because the
ladder topped out at 1280.

They need the dev server on `:8765` and `NODE_PATH=./node_modules`.

---

## Deploying

PythonAnywhere. **No Node on the server** — the stylesheet is committed already
built.

```bash
git pull
.venv/bin/python manage.py build_covers
.venv/bin/python manage.py build_covers --check
```

Do not skip the last two. See "Covers".

There is no nginx config, Dockerfile or `render.yaml` in this repo, so if
something sits in front of Django it is configured outside version control.
That matters for two things this project has not settled:

- **Compression.** Nothing in `MIDDLEWARE` gzips, and no `Content-Encoding` is
  sent. The CSS alone is 29 KB raw and 6.4 KB gzipped, so roughly 70% of every
  text response is being left on the table.
- **Cache headers.** None are set on static or media.

Both are cheap to fix at the proxy and are probably already handled by whatever
is in front — worth confirming rather than assuming.
