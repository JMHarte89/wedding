(function () {
  'use strict';

  var TIMELINE = [
    { time: '11:45',      event: 'Arrive at church',                  note: 'Holy Trinity Church, Kendal. Find a pew, say your hellos, grab a service sheet.' },
    { time: '12:00',      event: 'The ceremony',                      note: 'The bit we’re most nervous about.' },
    { time: '1:00',       event: 'Photographs outside the church',    note: 'The bridal party will guide everyone out. Confetti welcome — biodegradable only please.' },
    { time: '1:30',       event: 'Make your way to the venue',        note: 'The groomsmen and bridesmaids will point you in the right direction. It’s not far.' },
    { time: '2:00',       event: 'Welcome drinks — the newlyweds arrive', note: 'Raise a glass. The hard part is done.' },
    { time: '2:00–4:00',  event: 'Grazing, pizza & pancakes',         note: 'A sharing grazing buffet — [BUFFET DETAIL TO BE ADDED], plus wood-fired pizza and fresh pancakes. There’s also a magician wandering about — yes, really.' },
    { time: '4:30',       event: 'Speeches',                          note: 'Sit down, top up your glass, and be kind.' },
    { time: '5:30',       event: 'Evening guests arrive',             note: 'Welcome — you’ve missed the nerves, caught the fun.' },
    { time: '6:30',       event: 'First dance & the band',            note: 'An acoustic first dance, then the band takes over — dance floor open, no excuses.' },
    { time: '7:30–9:30',  event: 'Ninja Wraps',                       note: 'Evening food. Fuel for the dancefloor.' },
    { time: '12:00',      event: 'Carriages',                         note: 'Taxis turn into pumpkins. Thank you for being here.' }
  ];

  var EVENING_START_INDEX = TIMELINE.findIndex(function (s) { return s.time === '5:30'; });
  var FAIL_LIMIT = 3;
  var failures = 0;
  var guests = [];

  // ---------- Boot ----------
  document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('gate-form');
    if (form) form.addEventListener('submit', onGateSubmit);

    // data/guests.json is auto-generated from data/guestlist.csv
    // (run: node scripts/build-guests.js). Do not edit it by hand.
    fetch('data/guests.json', { cache: 'no-cache' })
      .then(function (r) { return r.json(); })
      .then(function (data) { guests = Array.isArray(data) ? data : []; })
      .catch(function () { guests = []; });
  });

  // ---------- Gate ----------
  function onGateSubmit(ev) {
    ev.preventDefault();
    clearConfirm();
    var input = document.getElementById('gate-input');
    var errorEl = document.getElementById('gate-error');
    var raw = (input.value || '').trim().toLowerCase();
    if (!raw) return;

    // Case-insensitive code match: both the typed input and the stored code
    // are trimmed and lowercased. "JHARTE", "jharte", "JHarte" all match.
    // Also matches any alternative codes listed in a guest's "aliases".
    var guest = guests.find(function (g) {
      if (String(g.code || '').trim().toLowerCase() === raw) return true;
      return Array.isArray(g.aliases) && g.aliases.some(function (a) {
        return String(a || '').trim().toLowerCase() === raw;
      });
    });

    if (guest) {
      // Some codes are shared by similarly-named households (e.g. two Robert
      // Blackshaws). If this guest has a confirm question, check before opening.
      if (guest.confirm) {
        askConfirm(guest);
      } else {
        unseal(guest);
      }
      return;
    }

    failures += 1;
    if (failures >= FAIL_LIMIT) {
      showChooser();
      return;
    }
    errorEl.textContent = "We don't recognise that one — try again?";
    var gate = document.getElementById('gate');
    gate.classList.remove('is-shake');
    void gate.offsetWidth;
    gate.classList.add('is-shake');
    input.select();
  }

  // After FAIL_LIMIT misses we show a friendly chooser instead of guessing.
  // Each choice maps to a generic "fallback" guest, flagged so the letter
  // shows a P.S. that real, matched guests never see.
  function fallbackGuest(kind) {
    if (kind === 'day') {
      return { code: '', greeting: 'mystery guest', members: [], day: true,  evening: true, notes: '', isFallback: true };
    }
    if (kind === 'evening') {
      return { code: '', greeting: 'evening guest', members: [], day: false, evening: true, notes: '', isFallback: true };
    }
    // 'unsure'
    return { code: '', greeting: 'friend', members: [], day: true, evening: true, notes: '', isFallback: true };
  }

  // Friendly chooser shown after FAIL_LIMIT unrecognised attempts: hides the
  // code input and offers day / evening / not-sure entry.
  function showChooser() {
    var gate = document.getElementById('gate');
    var form = document.getElementById('gate-form');
    clearConfirm();
    if (form) form.style.display = 'none';
    if (document.getElementById('gate-chooser')) return;

    var box = document.createElement('div');
    box.id = 'gate-chooser';
    box.className = 'gate__chooser';

    var h = document.createElement('h2');
    h.className = 'gate__chooser-title';
    h.textContent = "Hmm, we can't place you — but that's on us, not you.";

    var p = document.createElement('p');
    p.className = 'gate__chooser-body';
    p.textContent = "We may have your code slightly wrong in our very sophisticated system. No judgement. Are you joining us for the full day, or sneaking in for the evening do?";

    var actions = document.createElement('div');
    actions.className = 'gate__chooser-actions';

    var choices = [
      { label: 'Here for the whole day', kind: 'day' },
      { label: 'Evening only', kind: 'evening' },
      { label: "I'm not sure yet", kind: 'unsure' }
    ];
    choices.forEach(function (c) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'gate__choice';
      b.textContent = c.label;
      b.addEventListener('click', function () { unseal(fallbackGuest(c.kind)); });
      actions.appendChild(b);
    });

    box.appendChild(h);
    box.appendChild(p);
    box.appendChild(actions);
    gate.appendChild(box);
  }

  // Remove any open confirmation prompt.
  function clearConfirm() {
    var existing = document.getElementById('gate-confirm');
    if (existing && existing.parentNode) existing.parentNode.removeChild(existing);
  }

  // Friendly "are you the right person?" step for shared/ambiguous codes.
  function askConfirm(guest) {
    clearConfirm();
    var form = document.getElementById('gate-form');
    var errorEl = document.getElementById('gate-error');
    if (!form) { unseal(guest); return; }
    if (errorEl) errorEl.textContent = '';

    var box = document.createElement('div');
    box.id = 'gate-confirm';
    box.className = 'gate__confirm';

    var q = document.createElement('p');
    q.className = 'gate__confirm-q';
    q.textContent = guest.confirm;
    box.appendChild(q);

    var actions = document.createElement('div');
    actions.className = 'gate__confirm-actions';

    var yes = document.createElement('button');
    yes.type = 'button';
    yes.className = 'gate__button';
    yes.textContent = 'Yes, that’s me';
    yes.addEventListener('click', function () {
      clearConfirm();
      unseal(guest);
    });

    var no = document.createElement('button');
    no.type = 'button';
    no.className = 'gate__button gate__button--ghost';
    no.textContent = 'No, that’s not me';
    no.addEventListener('click', function () {
      clearConfirm();
      if (errorEl) {
        errorEl.textContent = guest.confirmElse || 'No problem — double-check your code and try again.';
      }
      var input = document.getElementById('gate-input');
      if (input) { input.value = ''; input.focus(); }
    });

    actions.appendChild(yes);
    actions.appendChild(no);
    box.appendChild(actions);
    form.appendChild(box);
  }

  function unseal(guest) {
    var gate = document.getElementById('gate');
    var envelope = gate.querySelector('.envelope');
    envelope.classList.add('is-open');

    populate(guest);

    // Crack + flap lift first, then fade the gate away and open the page.
    setTimeout(function () {
      gate.classList.add('is-gone');
      document.body.classList.add('is-open');
    }, 1100);
  }

  // ---------- Populate ----------
  function populate(guest) {
    // The letter salutation is "Dear <greeting>," — the span holds the greeting.
    var greetEl = document.getElementById('guest-name');
    if (greetEl) greetEl.textContent = guest.greeting || 'friend';
    // The P.S. note appears only for fallback guests, never for real matches.
    var ps = document.getElementById('letter-ps');
    if (ps) ps.hidden = !guest.isFallback;
    renderDay(guest);
  }

  function renderDay(guest) {
    var ul = document.getElementById('timeline');
    if (!ul) return;
    ul.innerHTML = '';
    var noteEl = document.getElementById('timeline-note');
    var stops;
    if (guest.day === false && guest.evening) {
      stops = TIMELINE.slice(EVENING_START_INDEX);
      if (noteEl) noteEl.textContent = "We'll see you from 5:30pm — the party is just getting started.";
    } else {
      stops = TIMELINE.slice();
      if (noteEl) noteEl.textContent = '';
    }

    stops.forEach(function (s) {
      var li = document.createElement('li');
      li.className = 'timeline__item';
      var time = document.createElement('span'); time.className = 'timeline__time'; time.textContent = s.time;
      var event = document.createElement('span'); event.className = 'timeline__event'; event.textContent = s.event;
      var note = document.createElement('span'); note.className = 'timeline__note'; note.textContent = s.note;
      li.appendChild(time); li.appendChild(event); li.appendChild(note);
      ul.appendChild(li);
    });
  }
})();
