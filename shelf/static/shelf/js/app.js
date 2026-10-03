/* =========================================================================
   Bookshelf — shelf and reader behaviour
   ========================================================================= */

(function () {
  'use strict';

  var MIN_SIZE = 17;
  var MAX_SIZE = 26;
  var DESKTOP_SIZE = 19;
  var PHONE_SIZE = 17;

  function defaultSize() {
    return window.matchMedia('(max-width: 34rem)').matches ? PHONE_SIZE : DESKTOP_SIZE;
  }

  function readStore(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (e) {
      return fallback;
    }
  }

  function writeStore(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      /* ignore */
    }
  }

  /* ---- Book cards --------------------------------------------------------
     What the view left beside each slot: the blurb, the chapters, the cover
     file. Read on first use and kept, so a reader who never lifts a book never
     pays for one -- the JSON sits in the document as an inert script element,
     which costs nothing but the bytes it takes to arrive.
     -------------------------------------------------------------------- */

  var cards = null;

  function cardData(bookId) {
    if (cards === null) {
      cards = {};
      Array.prototype.forEach.call(document.querySelectorAll('script[type="application/json"]'), function (el) {
        try {
          cards[el.id] = JSON.parse(el.textContent);
        } catch (e) {
          /* One unparseable card costs that book its card, not the page. */
        }
      });
    }
    return cards['book-card-' + bookId] || null;
  }

  /* ---- Theme ----------------------------------------------------------
     Three rooms. The top bar carries one button that cycles through them; the
     reader's pill carries the full set so the choice can be made outright
     rather than guessed at. Both write the same attribute, so they can never
     disagree about which room you are in.
     -------------------------------------------------------------------- */

  (function themeToggle() {
    var root = document.documentElement;
    var toggle = document.getElementById('themeToggle');
    var picks = document.querySelectorAll('[data-theme-set]');
    if (!toggle && !picks.length) return;

    var THEMES = ['night', 'day', 'sepia'];
    var NAMES = { night: 'night', day: 'day', sepia: 'sepia' };

    function current() {
      var t = root.getAttribute('data-theme');
      return THEMES.indexOf(t) === -1 ? 'night' : t;
    }

    function label() {
      if (!toggle) return;
      /* The button cycles, so it says where it goes next. */
      var next = THEMES[(THEMES.indexOf(current()) + 1) % THEMES.length];
      toggle.setAttribute('aria-label', 'Switch to the ' + NAMES[next] + ' theme');
    }

    function apply(theme) {
      root.setAttribute('data-theme', theme);
      try {
        localStorage.setItem('bookshelf:theme', theme);
      } catch (e) { /* ignore */ }
      Array.prototype.forEach.call(picks, function (btn) {
        btn.setAttribute('aria-pressed', btn.getAttribute('data-theme-set') === theme ? 'true' : 'false');
      });
      label();
    }

    if (toggle) {
      toggle.addEventListener('click', function () {
        apply(THEMES[(THEMES.indexOf(current()) + 1) % THEMES.length]);
      });
    }

    Array.prototype.forEach.call(picks, function (btn) {
      btn.addEventListener('click', function () {
        apply(btn.getAttribute('data-theme-set'));
      });
    });

    label();
    Array.prototype.forEach.call(picks, function (btn) {
      btn.setAttribute('aria-pressed', btn.getAttribute('data-theme-set') === current() ? 'true' : 'false');
    });
  })();

  /* ---- Reading size ---------------------------------------------------- */

  (function readingSize() {
    /* Every set of controls in the page shares one size, so they are all wired
       to it. Today there is only the pill, but the query is written for the
       count rather than for the one. */
    var steppers = document.querySelectorAll('[data-stepper], [data-stepper-bar]');
    if (!steppers.length) return;

    var size = readStore('bookshelf:reading-size', null);
    if (typeof size !== 'number' || isNaN(size)) size = defaultSize();
    size = Math.min(MAX_SIZE, Math.max(MIN_SIZE, size));

    function apply() {
      document.documentElement.style.setProperty('--reading-size', size + 'px');
      Array.prototype.forEach.call(steppers, function (stepper) {
        var reset = stepper.querySelector('[data-step-reset]');
        var down = stepper.querySelector('[data-step-down]');
        var up = stepper.querySelector('[data-step-up]');
        /* The button draws an A at the current size, so the figure only has
           to be spoken and hovered, not printed. */
        if (reset) {
          var said = 'Text size ' + size + ' pixels. Reset to the default.';
          reset.setAttribute('aria-label', said);
          reset.setAttribute('title', said);
        }
        if (down) down.disabled = size <= MIN_SIZE;
        if (up) up.disabled = size >= MAX_SIZE;
      });
    }

    function set(next) {
      size = Math.min(MAX_SIZE, Math.max(MIN_SIZE, next));
      writeStore('bookshelf:reading-size', size);
      apply();
    }

    Array.prototype.forEach.call(steppers, function (stepper) {
      var down = stepper.querySelector('[data-step-down]');
      var up = stepper.querySelector('[data-step-up]');
      var reset = stepper.querySelector('[data-step-reset]');
      if (down) down.addEventListener('click', function () { set(size - 1); });
      if (up) up.addEventListener('click', function () { set(size + 1); });
      if (reset) reset.addEventListener('click', function () { set(defaultSize()); });
    });

    apply();
  })();

  /* ---- Reading view ----------------------------------------------------
     Two ways to read the same chapter. The immersive one clears the rail and
     the furniture out of the way and retracts the chrome as the reader moves
     down the page, bringing it straight back the moment they move up.
     ---------------------------------------------------------------------- */

  (function readingView() {
    var root = document.documentElement;
    var pill = document.querySelector('[data-reader-pill]');
    var progress = document.querySelector('[data-read-progress]');
    var fill = document.querySelector('[data-read-progress-fill]');
    var label = document.querySelector('[data-read-label]');
    if (!pill || !progress) return;

    var hideToggle = document.querySelector('[data-hide-controls]');
    var drawer = document.querySelector('[data-drawer]');
    var drawerToggle = document.querySelector('[data-drawer-toggle]');

    /* The top bar still gets out of the way on the way down. The pill does
       not: it is the only way to change how the page looks, so it stays
       until it is deliberately put away. */
    var COMMIT_AT = 120;
    var last = window.pageYOffset;
    var hidden = false;

    /* A field being typed into, or the chapter list being open, both mean the
       controls are wanted. They come back. */
    function chromeIsBusy() {
      var active = document.activeElement;
      if (active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName)) return true;
      return drawer && drawer.getAttribute('data-open') === 'true';
    }

    function setChrome(state) {
      root.setAttribute('data-chrome', state);
    }

    function setControls(state) {
      hidden = state === 'hidden';
      root.setAttribute('data-controls', state);
    }

    if (hideToggle) {
      hideToggle.addEventListener('click', function () {
        /* Only if the keyboard is actually on it. Otherwise taking focus away
           from wherever the reader was would be a rudeness. */
        var focused = document.activeElement === hideToggle;
        setControls('hidden');
        if (focused) {
          var landing = document.querySelector('.read .sheet');
          if (landing) landing.focus();
        }
      });
    }

    setChrome('shown');
    setControls('shown');
    last = window.pageYOffset;

    /* ---- Progress ------------------------------------------------------
       Where the browser can drive this from the scroll timeline it does, with
       no script and off the main thread. The listener below is only a
       fallback for the browsers that cannot.
       ------------------------------------------------------------------ */

    var nativeProgress = window.CSS && CSS.supports && CSS.supports('animation-timeline: scroll()');

    function percentRead() {
      var doc = document.documentElement;
      var span = doc.scrollHeight - window.innerHeight;
      if (span <= 0) return 0;
      return Math.min(100, Math.max(0, (window.pageYOffset / span) * 100));
    }

    function paintProgress() {
      var pct = percentRead();
      /* The bar itself is the browser's job where it can be. The readout is
         ours either way, so it is updated regardless of who drives the fill. */
      if (fill && !nativeProgress) fill.style.scale = pct + '% 100%';
      if (label) {
        label.textContent = pct >= 99.5 ? 'End of chapter' : Math.round(pct) + '% read';
      }
    }

    var ticking = false;

    /* ---- Direction ----------------------------------------------------- */

    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        ticking = false;
        var y = window.pageYOffset;

        paintProgress();

        var delta = y - last;
        /* Rubber-banding at either end produces deltas that lie about intent,
           and a stray few pixels should never move the chrome. */
        if (Math.abs(delta) < 6) {
          last = y;
          return;
        }

        /* Back at the top there is nothing to get out of the way of. */
        if (y <= 0) {
          setChrome('shown');
          setControls('shown');
          last = y;
          return;
        }

        if (y <= COMMIT_AT || chromeIsBusy()) {
          setChrome('shown');
          setControls('shown');
          last = y;
          return;
        }

        setChrome(delta > 0 ? 'hidden' : 'shown');

        /* Moving back up is how a reader says they want the controls again,
           whether or not they were the ones to put them away. */
        if (hidden && delta < 0) setControls('shown');

        last = y;
      });
    }

    window.addEventListener('scroll', onScroll, { passive: true });

    /* ---- Chapter drawer ------------------------------------------------ */

    function setDrawer(open) {
      if (!drawer) return;
      /* Inert rather than a class: it takes effect immediately, so the focus
         below lands on the chapter and not on the body. */
      drawer.inert = !open;
      drawer.setAttribute('data-open', open ? 'true' : 'false');
      if (drawerToggle) drawerToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) {
        setChrome('shown');
        setControls('shown');
        var active = drawer.querySelector('[aria-current]');
        if (active) active.focus();
      }
    }

    if (drawerToggle && drawer) {
      drawerToggle.addEventListener('click', function () {
        setDrawer(drawer.getAttribute('data-open') !== 'true');
      });
    }

    Array.prototype.forEach.call(document.querySelectorAll('[data-drawer-close]'), function (el) {
      el.addEventListener('click', function () {
        setDrawer(false);
        if (drawerToggle) drawerToggle.focus();
      });
    });

    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape' || !drawer) return;
      if (drawer.getAttribute('data-open') !== 'true') return;
      setDrawer(false);
      if (drawerToggle) drawerToggle.focus();
    });

    /* The reader may have arrived here with the drawer already open from a
       previous visit; nothing restores it, so this is belt and braces. */
    setDrawer(false);
  })();

  /* ---- Shelf filter ----------------------------------------------------
     One shelf of books, three ways of looking at it. The books are already on
     the page -- there is nothing to fetch and nothing to wait for -- so this
     only decides which of them are in the room.

     The choice is kept, like the theme and the reading size, because someone
     who came to the shelf to finish one book does not want to re-say so on
     every visit.
     -------------------------------------------------------------------- */

  (function shelfFilter() {
    var control = document.querySelector('.shelf-filter');
    var buttons = document.querySelectorAll('[data-filter]');
    var slots = document.querySelectorAll('[data-book]');
    if (!control || !buttons.length) return;

    /* A shelf with no books on it has nothing to divide, and three controls
       that would filter an empty room are worse than no controls at all. */
    if (!slots.length) {
      control.hidden = true;
      return;
    }

    var STORED = 'bookshelf:filter';
    var ALL = 'all';
    var CHOICES = { all: 1, completed: 1, ongoing: 1 };
    var LABEL = { all: 'all books', completed: 'completed books', ongoing: 'ongoing books' };

    var status = document.querySelector('[data-filter-status]');
    var empties = document.querySelectorAll('[data-empty]');

    function matches(slot, choice) {
      if (choice === ALL) return true;
      var complete = slot.getAttribute('data-complete') === 'true';
      return choice === 'completed' ? complete : !complete;
    }

    function apply(choice, announce) {
      var shown = 0;

      Array.prototype.forEach.call(slots, function (slot) {
        var keep = matches(slot, choice);
        slot.hidden = !keep;
        if (keep) shown++;
      });

      Array.prototype.forEach.call(buttons, function (button) {
        button.setAttribute('aria-pressed', String(button.getAttribute('data-filter') === choice));
      });

      /* Filtering to nothing is a real answer, not a broken shelf, so say
         which of the two reasons it is. */
      Array.prototype.forEach.call(empties, function (note) {
        note.hidden = shown !== 0 || note.getAttribute('data-empty') !== choice;
      });

      if (announce && status) {
        status.textContent = 'Showing ' + shown + ' of ' + slots.length + ' ' +
          LABEL[choice] + '.';
      }

      return shown;
    }

    var stored = readStore(STORED, ALL);
    apply(CHOICES[stored] ? stored : ALL, false);

    Array.prototype.forEach.call(buttons, function (button) {
      button.addEventListener('click', function () {
        var choice = button.getAttribute('data-filter');
        if (!CHOICES[choice]) return;
        /* Marks the shelf as somewhere the reader has been, which takes the
           set-down off the covers. Set on any use, not only a change, so a
           click back to where they already were counts too. */
        document.documentElement.setAttribute('data-shelf-filtered', choice);
        writeStore(STORED, choice);
        apply(choice, true);
      });
    });
  })();

  /* ---- Continue reading ------------------------------------------------ */

  (function continueReading() {
    var progress = readStore('bookshelf:progress', {}) || {};

    if (window.bookshelf) {
      progress[window.bookshelf.bookId] = {
        chapterId: window.bookshelf.chapterId,
        number: window.bookshelf.chapterNumber,
        total: window.bookshelf.chapterCount,
        url: window.location.pathname,
        at: Date.now()
      };
      writeStore('bookshelf:progress', progress);
    }

    var slots = document.querySelectorAll('[data-book]');
    if (!slots.length) return;

    Array.prototype.forEach.call(slots, function (slot) {
      var bookId = slot.getAttribute('data-book');
      var entry = progress[bookId];
      var total = parseInt(slot.getAttribute('data-chapters'), 10);
      /* Which chapter ends this book, or empty if it has not ended. Taken
         from the page rather than from the stored note: what was the ending
         is the author's decision and it can be taken back, so a reader who
         got to the end of a book that has since reopened should not still be
         told they finished it. The stored note records where they stopped,
         this says what that place now means. */
      var lastChapter = parseInt(slot.getAttribute('data-last-chapter'), 10);

      var bar = slot.querySelector('[data-progress]');
      var fill = slot.querySelector('.progress__fill');
      var resume = slot.querySelector('[data-resume]');
      if (!resume) return;

      function paint(pct) {
        if (!bar || !fill) return;
        fill.style.setProperty('--pct', pct + '%');
        bar.hidden = false;
      }

      function resumeLink(href, name) {
        var link = document.createElement('a');
        link.className = 'slot__resume-link';
        link.href = href;
        if (name) {
          /* "Resume from" upright, the chapter's own name in italic. A title
             set in italic is how the shelf says a thing is a thing rather than
             an instruction, and the upright prefix gives the name something to
             lean against instead of leaving the whole line to lean on its own.

             `cite` rather than `i`: this is the title of a piece of writing,
             which is precisely what the element is for. Its italic comes from
             the stylesheet below rather than from the browser's default, so a
             reset cannot quietly un-italicise it. */
          link.appendChild(document.createTextNode('Resume from '));
          var title = document.createElement('cite');
          title.textContent = name;
          link.appendChild(title);
        } else {
          /* Nothing to resume: the offer is an instruction, so it is not set
             as a title. */
          link.textContent = 'Start reading';
        }
        /* Chapter names run longer than the label is wide, so the name is
           clamped to two lines the way the title above it is. The whole of it
           is still on the link, for a pointer that stops there and for anyone
           reading the shelf aloud. */
        link.title = link.textContent;
        resume.textContent = '';
        resume.appendChild(link);
      }

      /* Finished. They have reached the chapter the book ends on, so there is
         nothing to carry on to and offering them a "continue" would be
         offering them the thing they have already done. The full bar says it
         structurally, this says it in words, and the cover stays the way back
         in -- it does not need a second door pointing at the ending. */
      if (entry && lastChapter && entry.chapterId === lastChapter) {
        paint(100);
        resume.className = 'slot__resume slot__resume--done';
        resume.textContent = 'You\'ve reached the end';
        resume.hidden = false;
        return;
      }

      /* The chapter they are on, named as it is named now. Taken from the
         page rather than from the stored note, which only knows the number:
         a chapter retitled since they last opened it should still be called
         by its present title. */
      var card = cardData(bookId);
      var chapters = (card && card.chapters) || [];
      var here = null;
      if (entry) {
        for (var i = 0; i < chapters.length; i++) {
          if (chapters[i].id === entry.chapterId) {
            here = chapters[i];
            break;
          }
        }
      }

      if (entry && here && total) {
        paint(Math.min(100, Math.round((entry.number / total) * 100)));
        resumeLink(here.url, here.title);
      } else if (chapters.length) {
        /* Nothing stored, or the chapter they were on is no longer in the book
           -- in which case there is nothing to go back to and the first
           chapter is the honest place to start. */
        resumeLink(chapters[0].url, null);
      }
      /* A book with no chapters says nothing at all, rather than offering a
         way in that leads nowhere. */
      resume.hidden = false;
    });
  })();

  /* ---- Book card ---------------------------------------------------------
     Lifting a book off the board. The shelf page already carries everything a
     card shows, so opening one is a rearrangement of what is on screen rather
     than a request: the same cover file, already in the browser's cache, and
     no second byte for it whatever size the card shows it at.

     The book page it stands in for is not withdrawn. The links are real, a
     modified click still opens it in a tab of the reader's own, and an address
     arriving from somewhere else still reaches the book itself -- a card is a
     moment and a page is a place, so only this one goes into the history.
     -------------------------------------------------------------------- */

  (function bookCard() {
    var dialog = document.querySelector('[data-book-card]');
    var body = document.querySelector('[data-card-body]');
    var closeMark = document.querySelector('[data-card-close]');
    if (!dialog || !body) return;

    var progress = readStore('bookshelf:progress', {}) || {};
    var historyDepth = 0;
    var returnFocus = null;

    function open(bookId, trigger, push) {
      var book = cardData(bookId);
      if (!book || dialog.open) return;

      returnFocus = trigger || document.activeElement;
      /* Rebuilt from scratch each time, so a book cannot show another book's
         chapters. */
      body.textContent = '';

      var cover = document.createElement('img');
      cover.className = 'book-card__cover';
      cover.src = book.cover;
      cover.alt = 'Cover of ' + book.name;
      cover.width = 1410;
      cover.height = 2250;
      cover.decoding = 'async';
      body.appendChild(cover);

      var text = document.createElement('div');

      /* Text goes in as text. A book name or a blurb is whatever an author
         typed in the admin, and this is where it enters the page. */
      var title = document.createElement('h2');
      title.className = 'book-card__title';
      title.id = 'book-card-title';
      title.textContent = book.name;
      text.appendChild(title);

      if (book.blurb && book.blurb.length) {
        var blurb = document.createElement('div');
        blurb.className = 'book-card__blurb';
        blurb.style.fontFamily = book.font;
        Array.prototype.forEach.call(book.blurb, function (line) {
          var para = document.createElement('p');
          para.textContent = line;
          blurb.appendChild(para);
        });
        text.appendChild(blurb);
      }

      if (book.chapters.length) {
        /* No heading above it. A list of chapters under a book's name does not
           need to be introduced as a list of chapters. */
        var toc = document.createElement('nav');
        toc.className = 'toc';
        toc.setAttribute('aria-label', 'Chapters');

        var list = document.createElement('ol');
        list.className = 'toc__list';
        var entry = progress[bookId];

        Array.prototype.forEach.call(book.chapters, function (chapter) {
          var item = document.createElement('li');
          item.className = 'toc__item';
          var link = document.createElement('a');
          link.className = 'toc__link';
          link.href = chapter.url;
          link.textContent = chapter.title;
          /* The row the reader is on. There is no Continue button for this to
             compete with: the list is the interface, and one lit row says
             where to pick up as plainly as a button would. */
          if (entry && entry.chapterId === chapter.id) {
            link.setAttribute('aria-current', 'true');
          }
          item.appendChild(link);
          list.appendChild(item);
        });

        toc.appendChild(list);
        text.appendChild(toc);
      } else {
        var none = document.createElement('p');
        none.className = 'book-card__none';
        none.textContent = 'The first chapter is still being written.';
        text.appendChild(none);
      }

      body.appendChild(text);
      dialog.setAttribute('aria-labelledby', 'book-card-title');
      dialog.showModal();

      /* The address becomes the book's own, so that Back is how a reader
         leaves a card and so the bar holds something they can copy or share.
         Pushed, not replaced: the shelf is still behind the card, and Back
         should arrive at it rather than at wherever the shelf was found. */
      historyDepth = 0;
      if (push && window.history.pushState) {
        window.history.pushState({ book: bookId }, '', book.href);
        historyDepth = 1;
      }

      /* On the chapter they are on if there is one, so the card opens where
         the reader was looking, and on the close mark otherwise. */
      var landing = body.querySelector('[aria-current]') || closeMark;
      landing.focus();
    }

    /* One exit for every route out -- Escape, the mark, the dimmed room behind
       -- so none of them can be forgotten. */
    dialog.addEventListener('close', function () {
      var back = historyDepth > 0;
      historyDepth = 0;
      if (back) window.history.back();

      var to = returnFocus;
      returnFocus = null;
      /* Deferred a frame, because a modal dialog will not have focus put
         behind it while it is still in the top layer, and the browser's own
         restoration puts it on the body instead -- clicking a link does not
         focus one on a Mac. Only if nothing has claimed focus in the meantime,
         so a reader who has already tabbed on is left where they are. */
      window.requestAnimationFrame(function () {
        var now = document.activeElement;
        var unclaimed = !now || now === document.body || now === document.documentElement ||
          dialog.contains(now);
        if (unclaimed && to && to.isConnected) to.focus();
      });
    });

    if (closeMark) closeMark.addEventListener('click', function () { dialog.close(); });

    dialog.addEventListener('click', function (event) {
      /* Clicking the dimmed room behind the card, in the browsers that
         deliver such a click at all. Judged by where the pointer landed
         rather than by what it hit: what it hits is a backdrop, and a backdrop
         is not an element. */
      var box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right ||
        event.clientY < box.top || event.clientY > box.bottom) {
        dialog.close();
      }
    });

    window.addEventListener('popstate', function () {
      var bookId = /^\/reader\/book\/(\d+)\/?$/.exec(window.location.pathname);

      /* Back is how a reader expects to leave a card, especially on a phone.
         The entry we pushed is already gone, so this closes the card without
         asking for another one -- that would send them off the site. */
      if (dialog.open) {
        historyDepth = 0;
        dialog.close();
        return;
      }

      /* And the other way, so the address never sits on a book with nothing
         showing: Forward reopens the card it came from. Pushing nothing here
         -- the entry is already in the history. */
      if (bookId) open(bookId[1], null, false);
    });

    Array.prototype.forEach.call(document.querySelectorAll('.slot__link, .slot__title'), function (link) {
      link.addEventListener('click', function (event) {
        /* A modified click is the reader asking for a page of their own -- a new
           tab, a new window, a download. Not ours to take over. */
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        var slot = link.closest('[data-book]');
        if (!slot) return;
        event.preventDefault();
        open(slot.getAttribute('data-book'), link, true);
      });
    });

    /* The title is the one click on a slot that can outrun the cover: it sits on
       the label under the board, so hovering it asks for a cover the reader
       has not scrolled to yet -- and one of these is 6 MB. Started when the
       pointer arrives, not when the shelf renders, so nobody pays for a book
       they only looked at. */
    Array.prototype.forEach.call(document.querySelectorAll('.slot__title'), function (link) {
      function warm() {
        var slot = link.closest('[data-book]');
        var card = slot && cardData(slot.getAttribute('data-book'));
        if (!card || slot.getAttribute('data-warmed')) return;
        slot.setAttribute('data-warmed', 'true');
        var img = new Image();
        img.src = card.cover;
      }
      link.addEventListener('mouseenter', warm, { once: true });
      link.addEventListener('focus', warm, { once: true });
    });
  })();

  /* ---- Comments -------------------------------------------------------- */

  (function comments() {
    var form = document.querySelector('[data-comment-form]');
    var list = document.querySelector('[data-comments-list]');
    if (!form || !list || !window.bookshelf) return;

    /* A short thread should not be given a scrollbar or a faded edge it has
       not earned. The cap only applies once the list genuinely overflows, and
       it is re-checked whenever the list changes. */
    var scroller = document.querySelector('[data-comments-scroll]');

    function fitComments() {
      if (!scroller) return;
      var fits = scroller.scrollHeight <= scroller.clientHeight + 1;
      scroller.setAttribute('data-fits', fits ? 'true' : 'false');
      /* The region is focusable so the overflow is reachable by keyboard. With
         nothing to scroll it should not be a tab stop. */
      scroller.setAttribute('tabindex', fits ? '-1' : '0');
    }

    fitComments();
    window.addEventListener('resize', fitComments);

    var status = form.querySelector('[data-comment-status]');
    var submit = form.querySelector('[data-comment-submit]');
    var counter = document.querySelector('[data-comment-count]');
    /* The count sits in a live region, so only the number is rewritten. The
       hidden label around it must survive the update. */
    var total = counter ? counter.querySelector('[data-comment-total]') : null;
    var body = form.querySelector('[name="comment"]');
    var name = form.querySelector('[name="name"]');
    var token = form.querySelector('[name="csrfmiddlewaretoken"]');

    var savedName = readStore('bookshelf:name', '');
    if (savedName && !name.value) name.value = savedName;

    /* Text and state land together so the stylesheet can colour the line
       without any colour being named in JS. The attribute is what the CSS
       keys off: [data-state='error'] turns it to --error, everything else
       stays sand. */
    function setStatus(message, state) {
      status.textContent = message;
      status.dataset.state = state;
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      submit.disabled = true;
      setStatus('Posting your comment…', 'pending');

      var request = new XMLHttpRequest();
      request.open('POST', window.bookshelf.commentsUrl, true);
      request.setRequestHeader('X-CSRFToken', token ? token.value : '');
      request.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

      request.onload = function () {
        submit.disabled = false;
        var payload = {};
        try {
          payload = JSON.parse(request.responseText);
        } catch (e) {}

        if (request.status >= 200 && request.status < 300 && payload.html) {
          list.innerHTML = payload.html;
          /* One more comment may have tipped the list into overflow. */
          fitComments();
          if (total && typeof payload.count === 'number') total.textContent = payload.count;
          body.value = '';
          writeStore('bookshelf:name', name.value.trim());
          setStatus('Posted. Thank you for reading.', 'ok');
        } else {
          /* Server wording or the fallback; either way it is a failure. */
          setStatus(payload.error || 'That did not save. Try again in a moment.', 'error');
        }
      };

      request.onerror = function () {
        submit.disabled = false;
        setStatus('Could not reach the server. Check your connection and try again.', 'error');
      };

      request.send(new FormData(form));
    });
  })();
})();
