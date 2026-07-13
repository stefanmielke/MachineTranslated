/*
 * Machine Translated — chapter reader enhancements.
 *
 * Tags the two text layers found in generated chapter documents
 * (source Japanese: h2 headings and em runs; translation: h4 blocks),
 * wires the visibility toggles, and lifts the document's own
 * previous/next links into the reader toolbar. Everything degrades
 * gracefully: without JavaScript the in-content links stay visible
 * and both layers simply remain shown.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'mt-reader';
  var root = document.documentElement;

  function loadState() {
    try {
      return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '{}');
    } catch (err) {
      return {};
    }
  }

  function saveState(patch) {
    try {
      var state = loadState();
      Object.keys(patch).forEach(function (key) {
        state[key] = patch[key];
      });
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (err) {
      /* private mode or storage disabled — state just won't persist */
    }
  }

  /* ---- text layer tagging -------------------------------------------- */

  function isOnlyContentOfParagraph(el) {
    var parent = el.parentElement;
    return !!parent &&
      parent.tagName === 'P' &&
      parent.children.length === 1 &&
      parent.textContent.trim() === el.textContent.trim();
  }

  function tagLayers(article) {
    article.querySelectorAll('h2').forEach(function (heading) {
      heading.classList.add('layer-source');
      heading.setAttribute('lang', 'ja');
    });

    article.querySelectorAll('em').forEach(function (em) {
      if (em.closest('h1, h2, h3, h4, h5, h6')) {
        return; // genuine emphasis inside a heading, not a source run
      }
      em.setAttribute('lang', 'ja');
      var block = isOnlyContentOfParagraph(em) ? em.parentElement : em;
      block.classList.add('layer-source');
    });

    article.querySelectorAll('h4').forEach(function (heading) {
      heading.classList.add('layer-translation');
    });

    // Empty "&nbsp;" spacer paragraphs become styleable beat separators.
    article.querySelectorAll('p').forEach(function (p) {
      if (p.children.length === 0 && p.textContent.trim() === '') {
        p.classList.add('reader-spacer');
      }
    });
  }

  /* ---- chapter navigation --------------------------------------------- */

  function extractNav(article) {
    var nav = { prev: null, next: null };
    article.querySelectorAll('h6').forEach(function (heading) {
      var link = heading.querySelector('a[href]');
      if (!link) {
        return;
      }
      var label = link.textContent.toLowerCase();
      if (label.indexOf('prev') !== -1) {
        nav.prev = nav.prev || link.getAttribute('href');
      } else if (label.indexOf('next') !== -1) {
        nav.next = nav.next || link.getAttribute('href');
      } else {
        return;
      }
      heading.classList.add('reader-legacy-nav');
    });
    return nav;
  }

  function fillNavLink(id, href) {
    var link = document.getElementById(id);
    if (link && href) {
      link.setAttribute('href', href);
      link.hidden = false;
    }
  }

  function hideTrailingRule(article) {
    var node = article.lastElementChild;
    while (node && (node.classList.contains('reader-legacy-nav') ||
                    node.classList.contains('reader-spacer'))) {
      node = node.previousElementSibling;
    }
    if (!node || node.tagName !== 'HR') {
      return;
    }
    // The end-of-chapter nav draws its own rule; drop the document's
    // trailing one plus any spacer paragraphs directly above it.
    node.classList.add('reader-hidden-rule');
    node = node.previousElementSibling;
    while (node && node.classList.contains('reader-spacer')) {
      node.classList.add('reader-hidden-rule');
      node = node.previousElementSibling;
    }
  }

  function buildEndNav(article, bar, nav) {
    if (!nav.prev && !nav.next) {
      return;
    }
    hideTrailingRule(article);
    var endNav = bar.querySelector('.reader-nav').cloneNode(true);
    endNav.classList.add('reader-endnav');
    endNav.setAttribute('aria-label', 'Chapter navigation (end of chapter)');
    endNav.querySelectorAll('[id]').forEach(function (el) {
      el.removeAttribute('id');
    });
    article.appendChild(endNav);
  }

  /* ---- visibility toggles ---------------------------------------------- */

  function updateEmptyNote() {
    var note = document.getElementById('reader-empty-note');
    if (note) {
      note.hidden = !(root.classList.contains('reader-hide-source') &&
                      root.classList.contains('reader-hide-translation'));
    }
  }

  function setupToggle(id, options) {
    var button = document.getElementById(id);
    if (!button) {
      return;
    }

    function apply(visible, persist) {
      root.classList.toggle(options.className, !visible);
      button.setAttribute('aria-pressed', visible ? 'true' : 'false');
      button.classList.toggle('is-off', !visible);
      button.querySelector('.reader-toggle-label').textContent =
        options.name + (visible ? ' visible' : ' hidden');
      if (persist) {
        var patch = {};
        patch[options.stateKey] = visible;
        saveState(patch);
      }
      updateEmptyNote();
    }

    button.addEventListener('click', function () {
      apply(root.classList.contains(options.className), true);
    });

    // Sync the control with the state applied before first paint.
    apply(!root.classList.contains(options.className), false);
  }

  /* ---- init ------------------------------------------------------------- */

  function init() {
    if (!document.body.classList.contains('page-chapter')) {
      return;
    }
    var article = document.querySelector('.page-content');
    var bar = document.getElementById('reader-bar');
    if (!article || !bar) {
      return;
    }

    tagLayers(article);

    var nav = extractNav(article);
    fillNavLink('nav-prev', nav.prev);
    fillNavLink('nav-next', nav.next);

    // Place the toolbar after the title block (h1 plus the source h2 when
    // it directly follows), mirroring the accepted concept layout.
    var title = article.querySelector('h1');
    if (title) {
      var anchor = title;
      var sibling = title.nextElementSibling;
      if (sibling && sibling.tagName === 'H2') {
        anchor = sibling;
      }
      anchor.insertAdjacentElement('afterend', bar);
    }
    bar.hidden = false;

    buildEndNav(article, bar, nav);

    var toggles = document.getElementById('reader-toggles');
    if (toggles) {
      toggles.hidden = false;
    }
    setupToggle('toggle-source', {
      className: 'reader-hide-source',
      stateKey: 'source',
      name: 'Source'
    });
    setupToggle('toggle-translation', {
      className: 'reader-hide-translation',
      stateKey: 'translation',
      name: 'Translation'
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
