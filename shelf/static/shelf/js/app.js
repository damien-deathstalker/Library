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

      var bar = slot.querySelector('[data-progress]');
      var fill = slot.querySelector('.progress__fill');
      var resume = slot.querySelector('[data-resume]');
      if (!resume) return;

      if (entry && total) {
        if (bar && fill) {
          var pct = Math.min(100, Math.round((entry.number / total) * 100));
          fill.style.setProperty('--pct', pct + '%');
          bar.hidden = false;
        }
        var link = document.createElement('a');
        link.className = 'slot__resume-link';
        link.href = entry.url;
        link.textContent = 'Continue at chapter ' + entry.number;
        resume.textContent = '';
        resume.appendChild(link);
        resume.hidden = false;
      } else {
        var start = document.createElement('a');
        start.className = 'slot__resume-link';
        start.href = '/reader/book/' + bookId + '/';
        start.textContent = 'Start reading';
        resume.textContent = '';
        resume.appendChild(start);
        resume.hidden = false;
      }
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
