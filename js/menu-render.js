/* ------------------------------------------------------------
   Renders window.WEDDING_MENU into a container.

   Shared by index.html and agenda.html so neither page carries its own
   copy of the markup. Load js/menu.js before this file.

   Built with createElement/textContent rather than innerHTML: the menu is
   full of apostrophes and accents (pâté, Mark’s) and this way the browser
   handles them as text rather than us hand-escaping entities.
------------------------------------------------------------ */
(function (root) {
  'use strict';

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function renderMenu(opts) {
    var menu = root.WEDDING_MENU;
    if (!menu) return false;

    var host = document.getElementById((opts && opts.into) || 'menu');
    if (!host) return false;
    host.innerHTML = '';

    var kicker = opts && opts.kicker && document.getElementById(opts.kicker);
    if (kicker) kicker.textContent = menu.kicker;
    var title = opts && opts.title && document.getElementById(opts.title);
    if (title) title.textContent = menu.title;

    (menu.blocks || []).forEach(function (block) {
      var section = el('div', 'menu-block');
      section.appendChild(el('h3', 'menu-block__heading', block.heading));
      if (block.time) {
        section.appendChild(el('p', 'menu-block__time', block.time));
      }

      (block.groups || []).forEach(function (group) {
        if (group.subheading) {
          section.appendChild(
            el('p', 'menu-group__subheading', group.subheading));
        }
        var list = el('ul', 'menu-list');
        (group.items || []).forEach(function (item) {
          var li = el('li', 'menu-item');
          li.appendChild(el('span', 'menu-item__name', item.name));
          if (item.detail) {
            li.appendChild(el('span', 'menu-item__detail', item.detail));
          }
          list.appendChild(li);
        });
        section.appendChild(list);
      });

      host.appendChild(section);
    });

    var foot = opts && opts.footnote && document.getElementById(opts.footnote);
    if (foot) foot.textContent = menu.footnote;
    return true;
  }

  root.renderWeddingMenu = renderMenu;

})(typeof window !== 'undefined' ? window : this);
