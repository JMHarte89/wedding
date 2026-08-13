/* ------------------------------------------------------------------------
   Seating lookup — "Your Table" section (#tables)

   A guest types their invitation code (first initial + surname, e.g.
   CGould) and gets their tree table plus who else is on it.

   PRIVACY NOTE — READ BEFORE CHANGING
   The entire guest list ships in this file, so it is readable by anyone who
   views source on the published site. The code prompt is a convenience and a
   soft nudge, NOT access control. Treat every name here as public. Do not add
   anything genuinely private (addresses, phone numbers, dietaries) to this
   file on the assumption that the code gate protects it. It does not.

   No localStorage/sessionStorage is used; nothing is persisted between visits.
------------------------------------------------------------------------- */

(function () {
  'use strict';

  /* ======================================================================
     EDITABLE BLOCK — the seating plan. Everything else is machinery.

     One entry per table, in room order. `households` groups people exactly
     as they are seated together; that grouping and its order are preserved
     when the table is listed back to a guest.

     Conventions inside a household:
       'Robin (3)'  -> a child; the number is stored as an age and is NEVER
                       shown on the guest-facing card.
       '+ guest'    -> a real seat for someone whose name we don't have yet.
                       Shown in listings, excluded from the lookup index.

     `expected` is the head count this table should come to. It is checked
     on load and a console warning is logged if the data drifts.
     ====================================================================== */

  var ADMIN_CODES = [
    // Non-guest codes, deliberately not derived from anyone's name so they
    // can't be reached by guessing. Change these freely.
    'quarrygate77',
    'lanternfell24'
  ];

  var PLAN = [
    {
      tree: 'Top Table',
      where: 'Centre of the room, facing the stage',
      expected: 21,
      households: [
        ['Carole Blackshaw', 'Robert Blackshaw'],
        ['Jase Harte', 'Becki Harte', 'Robin (3)', 'Archie (1)'],
        ['Allan Harte'],
        ['Helen Harte', 'Noel Harte'],
        ['Beth Blackshaw', 'Taz Glover'],
        ['Jojo Tzu', 'Tony Tzu', 'Max (2)'],
        ['James Gould', 'Zoe Gould', 'Prim (4)', 'Felicity (2)'],
        ['Anna Carruthers', 'Craig Ferguson', 'Thomas Carruthers']
      ]
    },
    {
      tree: 'Oak',
      where: 'Left side, nearest the stage',
      expected: 6,
      households: [
        ['Emma Harte', 'Ben Maguire', 'Jerome (12)', 'Ruby (7)'],
        ['Raya Harte', 'Archie Burt']
      ]
    },
    {
      tree: 'Maple',
      where: 'Left side, under the bar',
      expected: 7,
      households: [
        ['Vicky Blackshaw', 'Jon Abbotts'],
        ['Jill Byrne', 'Bob Parkinson'],
        ['Diane George', 'Matthew George'],
        ['Graham Wright']
      ]
    },
    {
      tree: 'Willow',
      where: 'Back wall, second from the left',
      expected: 7,
      households: [
        ['Kristina Rowe', 'Daniel English', 'Jan Nicholson', 'Olivia (3)', 'Charlotte (1)'],
        ['Claire Gould'],
        ['Hannah Girvan']
      ]
    },
    {
      tree: 'Elm',
      where: 'Back wall, centre-left',
      expected: 7,
      households: [
        ['Robert Blackshaw', 'Marie Blackshaw'],
        ['Guy Blackshaw', 'Lu Blackshaw', 'Oliver', 'Rhys', 'Henry']
      ]
    },
    {
      tree: 'Ash',
      where: 'Back wall, centre-right',
      expected: 9,
      households: [
        ['George Slater', 'Kayleigh Thomas'],
        ['Mandy Slater', 'Steve Slater'],
        ['Craig Hargreaves', 'Dawn Porter Hargreaves', 'Florence'],
        ['Thomas Porter', '+ guest']
      ]
    },
    {
      tree: 'Magnolia',
      where: 'Back wall, nearest the entrance',
      expected: 9,
      households: [
        ['Rachael Arnold', 'Chris Arnold', 'Penelope (7)', 'Bonnie (3)'],
        ['Helen Lovatt', 'Dave Lovatt'],
        ['Hannah Lovatt-Thompson', 'Luke Lovatt-Thompson', '+ guest']
      ]
    },
    {
      tree: 'Acer',
      where: 'Right side, nearest the entrance',
      expected: 9,
      households: [
        ['Justin Harte', 'Nolene Harte'],
        ['Darren Harte'],
        ['Mark Harte', '+ guest'],
        ['Elliott Hyndman', 'Britt Hyndman', 'River', 'Oakley']
      ]
    },
    {
      tree: 'Rowan',
      where: 'Right side, middle',
      expected: 9,
      households: [
        ['Kathleen Humphries', '+ guest'],
        ['Kenny Earthling', 'Trevor Earthling'],
        ['Gill Bennett', 'Tim Bennett'],
        ['Tina Burke'],
        ['Marina Ward'],
        ['Pauline McCrann']
      ]
    },
    {
      tree: 'Holly',
      where: 'Right side, nearest the stage',
      expected: 12,
      households: [
        ['Rach Hoar', 'James Hoar', 'Catherine', 'Harry (7)', 'Lily (5)'],
        ['Ursula Carey', 'Martin Carey'],
        ['Wayne Harling', 'Lizzie Harling'],
        ['Mary Harte', 'Donald Harte', 'Dónal Harte']
      ]
    },
    {
      tree: 'Kids',
      where: 'Back wall, far left corner',
      expected: 0,
      note: 'Nobody is seated here — it’s a free activity table for the little ones to escape to.',
      households: []
    }
  ];

  var EXPECTED_TOTAL = 96;

  /* ================= end of editable block ================= */

  // Strip accents, case and punctuation so "Dónal", "O'Brien" and
  // "Lovatt-Thompson" all reduce to something a guest can actually type.
  function normalise(s) {
    return String(s || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '');
  }

  // 'Robin (3)' -> { display: 'Robin', age: 3 }
  function parseEntry(raw) {
    var m = String(raw).match(/^(.*?)\s*\((\d+)\)\s*$/);
    if (m) return { display: m[1].trim(), age: parseInt(m[2], 10) };
    return { display: String(raw).trim(), age: null };
  }

  function isPlaceholder(display) {
    return display.charAt(0) === '+';
  }

  // Flatten the editable block into the model the rest of the file uses:
  // { tree, guests: [ { name, household, age } ] }
  var SEATING = PLAN.map(function (t) {
    var guests = [];
    t.households.forEach(function (household, hIndex) {
      household.forEach(function (raw) {
        var p = parseEntry(raw);
        guests.push({
          name: p.display,
          household: hIndex,
          age: p.age,
          placeholder: isPlaceholder(p.display),
          tree: t.tree
        });
      });
    });
    return { tree: t.tree, where: t.where, note: t.note || '', expected: t.expected, guests: guests };
  });

  // ---- Integrity check -------------------------------------------------
  (function check() {
    var total = 0;
    SEATING.forEach(function (t) {
      total += t.guests.length;
      if (t.guests.length !== t.expected) {
        console.warn('[seating] ' + t.tree + ': expected ' + t.expected +
                     ' guests, found ' + t.guests.length);
      }
    });
    if (total !== EXPECTED_TOTAL) {
      console.warn('[seating] total headcount is ' + total +
                   ', expected ' + EXPECTED_TOTAL);
    }
  })();

  // ---- Lookup index ----------------------------------------------------
  // Two ways in, both consulted and merged:
  //   1. Invitation code — first initial + surname (CGould).
  //   2. First name — the only route for guests with no surname on the plan
  //      (Robin, Max, Prim…), and a friendly fallback for everyone else.
  // Placeholders ('+ guest') are seated but unnamed, so they are never indexed.
  var index = {};

  function addToIndex(key, guest) {
    if (!key) return;
    (index[key] = index[key] || []).push(guest);
  }

  SEATING.forEach(function (t) {
    t.guests.forEach(function (g) {
      if (g.placeholder) return;
      var words = g.name.split(/\s+/).filter(Boolean);
      var first = words[0];
      var last = words.length > 1 ? words[words.length - 1] : '';
      if (last) addToIndex(normalise(first.charAt(0) + last), g);
      addToIndex(normalise(first), g);
    });
  });

  function lookup(raw) {
    var q = normalise(raw);
    if (!q) return [];
    var hits = index[q] || [];
    var seen = [];
    return hits.filter(function (g) {
      if (seen.indexOf(g) !== -1) return false;
      seen.push(g);
      return true;
    });
  }

  function isAdmin(raw) {
    return ADMIN_CODES.map(normalise).indexOf(normalise(raw)) !== -1;
  }

  function tableOf(tree) {
    return SEATING.filter(function (t) { return t.tree === tree; })[0];
  }

  function firstNameOf(g) { return g.name.split(/\s+/)[0]; }

  // ---- Rendering -------------------------------------------------------
  var LEAF = 'M2 12c8-9 20-9 28-9 0 9-6 15-14 15-6 0-11-3-14-6Z';

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function leaf() {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'seat-leaf');
    svg.setAttribute('viewBox', '0 0 48 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    [LEAF, 'M2 12c9 0 18 2 26 6', 'M46 12h-8'].forEach(function (d) {
      var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', d);
      svg.appendChild(p);
    });
    return svg;
  }

  var out = null;

  function clear() { while (out.firstChild) out.removeChild(out.firstChild); }

  // Households joined by a middot, names within a household by commas —
  // the same shape the plan is written in.
  function tableRun(table, you) {
    var line = el('p', 'seat-card__people');
    var groups = [];
    table.guests.forEach(function (g) {
      (groups[g.household] = groups[g.household] || []).push(g);
    });

    groups.forEach(function (group, i) {
      if (i > 0) {
        line.appendChild(el('span', 'seat-card__sep', ' · '));
      }
      group.forEach(function (g, j) {
        if (j > 0) line.appendChild(document.createTextNode(', '));
        if (g === you) {
          var me = el('span', 'seat-card__you', g.name);
          me.appendChild(el('span', 'seat-card__you-tag', ' (you)'));
          line.appendChild(me);
        } else {
          line.appendChild(document.createTextNode(g.name));
        }
      });
    });
    return line;
  }

  function renderGuest(guest) {
    var table = tableOf(guest.tree);
    clear();

    var card = el('div', 'seat-card');
    card.appendChild(el('p', 'seat-card__hello', 'Hello ' + firstNameOf(guest)));
    card.appendChild(leaf());
    card.appendChild(el('p', 'seat-label', 'You’re on'));
    card.appendChild(el('p', 'seat-card__tree', table.tree));
    if (table.where) card.appendChild(el('p', 'seat-card__where', table.where));
    card.appendChild(el('hr', 'seat-rule'));
    card.appendChild(el('p', 'seat-label', 'Sharing your table'));
    card.appendChild(tableRun(table, guest));
    out.appendChild(card);
  }

  function renderChoice(matches) {
    clear();
    var box = el('div', 'seat-choice');
    box.appendChild(el('p', 'seat-choice__title', 'There’s more than one of you — which is it?'));
    var list = el('div', 'seat-choice__actions');
    matches.forEach(function (g) {
      var b = el('button', 'seat-choice__btn');
      b.type = 'button';
      b.appendChild(el('span', 'seat-choice__name', g.name));
      b.appendChild(el('span', 'seat-choice__tree', tableOf(g.tree).tree));
      b.addEventListener('click', function () { renderGuest(g); });
      list.appendChild(b);
    });
    box.appendChild(list);
    out.appendChild(box);
  }

  // Deliberately says nothing about who is or isn't on the list.
  function renderMiss() {
    clear();
    var box = el('div', 'seat-miss');
    box.appendChild(el('p', 'seat-miss__title', 'We can’t place that one — but that’s on us, not you.'));
    box.appendChild(el('p', null, 'Your code is the letter of your first name followed by your last name in full — Claire Gould would be CGould.'));
    box.appendChild(el('p', 'seat-miss__foot', 'Still nothing? Give Jase a nudge and we’ll sort it.'));
    out.appendChild(box);
  }

  function renderAll() {
    clear();
    var wrap = el('div', 'seat-all');
    SEATING.forEach(function (t) {
      var card = el('div', 'seat-all__table');
      var head = el('h3', 'seat-all__tree', t.tree);
      head.appendChild(el('span', 'seat-all__count', t.guests.length + ' seated'));
      card.appendChild(head);
      if (t.where) card.appendChild(el('p', 'seat-all__where', t.where));

      if (!t.guests.length) {
        card.appendChild(el('p', 'seat-all__note', t.note || 'Nobody seated.'));
      } else {
        var ul = el('ul', 'seat-all__list');
        t.guests.forEach(function (g) {
          var li = el('li', 'seat-all__name', g.name);
          if (g.age != null) li.appendChild(el('span', 'seat-all__age', ' (' + g.age + ')'));
          ul.appendChild(li);
        });
        card.appendChild(ul);
      }
      wrap.appendChild(card);
    });
    out.appendChild(wrap);
  }

  function onSubmit(ev) {
    ev.preventDefault();
    var input = document.getElementById('seat-input');
    var raw = (input.value || '').trim();
    if (!raw) { clear(); return; }
    if (isAdmin(raw)) { renderAll(); return; }
    var matches = lookup(raw);
    if (matches.length === 1) renderGuest(matches[0]);
    else if (matches.length > 1) renderChoice(matches);
    else renderMiss();
  }

  document.addEventListener('DOMContentLoaded', function () {
    out = document.getElementById('seat-result');
    var form = document.getElementById('seat-form');
    if (form) form.addEventListener('submit', onSubmit);
  });
})();
