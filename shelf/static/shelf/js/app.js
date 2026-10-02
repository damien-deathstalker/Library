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

  /* ---- Theme ---------------------------------------------------------- */

  (function themeToggle() {
    var root = document.documentElement;
    var toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    function label() {
      var isDay = root.getAttribute('data-theme') === 'day';
      toggle.setAttribute('aria-label', isDay ? 'Switch to night theme' : 'Switch to day theme');
    }

    label();

    toggle.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'day' ? 'night' : 'day';
      root.setAttribute('data-theme', next);
      try {
        localStorage.setItem('bookshelf:theme', next);
      } catch (e) { /* ignore */ }
      label();
    });
  })();

  /* ---- Reading size ---------------------------------------------------- */

  (function readingSize() {
    var stepper = document.querySelector('[data-stepper]');
    if (!stepper) return;

    var down = stepper.querySelector('[data-step-down]');
    var up = stepper.querySelector('[data-step-up]');
    var reset = stepper.querySelector('[data-step-reset]');

    var size = readStore('bookshelf:reading-size', null);
    if (typeof size !== 'number' || isNaN(size)) size = defaultSize();
    size = Math.min(MAX_SIZE, Math.max(MIN_SIZE, size));

    function apply() {
      document.documentElement.style.setProperty('--reading-size', size + 'px');
      reset.textContent = size + 'px';
      down.disabled = size <= MIN_SIZE;
      up.disabled = size >= MAX_SIZE;
    }

    function set(next) {
      size = Math.min(MAX_SIZE, Math.max(MIN_SIZE, next));
      writeStore('bookshelf:reading-size', size);
      apply();
    }

    down.addEventListener('click', function () { set(size - 1); });
    up.addEventListener('click', function () { set(size + 1); });
    reset.addEventListener('click', function () { set(defaultSize()); });

    apply();
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

    var status = form.querySelector('[data-comment-status]');
    var submit = form.querySelector('[data-comment-submit]');
    var counter = document.querySelector('[data-comment-count]');
    var body = form.querySelector('[name="comment"]');
    var name = form.querySelector('[name="name"]');
    var token = form.querySelector('[name="csrfmiddlewaretoken"]');

    var savedName = readStore('bookshelf:name', '');
    if (savedName && !name.value) name.value = savedName;

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      submit.disabled = true;
      status.textContent = 'Posting your comment…';

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
          if (counter && typeof payload.count === 'number') counter.textContent = payload.count;
          body.value = '';
          writeStore('bookshelf:name', name.value.trim());
          status.textContent = 'Posted. Thank you for reading.';
        } else {
          status.textContent = payload.error || 'That did not save. Try again in a moment.';
        }
      };

      request.onerror = function () {
        submit.disabled = false;
        status.textContent = 'Could not reach the server. Check your connection and try again.';
      };

      request.send(new FormData(form));
    });
  })();
})();
