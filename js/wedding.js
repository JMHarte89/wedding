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
    var input = document.getElementById('gate-input');
    var errorEl = document.getElementById('gate-error');
    var raw = (input.value || '').trim().toLowerCase();
    if (!raw) return;

    // Case-insensitive code match: both the typed input and the stored code
    // are trimmed and lowercased. "JHARTE", "jharte", "JHarte" all match.
    var guest = guests.find(function (g) {
      return String(g.code || '').trim().toLowerCase() === raw;
    });

    if (guest) {
      unseal(guest);
      return;
    }

    failures += 1;
    if (failures >= FAIL_LIMIT) {
      errorEl.textContent = "Let's not worry about the code — come in.";
      unseal(friendFallback());
      return;
    }
    errorEl.textContent = "We don't recognise that one — try again?";
    var gate = document.getElementById('gate');
    gate.classList.remove('is-shake');
    void gate.offsetWidth;
    gate.classList.add('is-shake');
    input.select();
  }

  // After FAIL_LIMIT misses we let people in anyway with a generic greeting.
  function friendFallback() {
    return {
      code: '',
      greeting: 'friend',
      members: [],
      day: true,
      evening: true,
      notes: ''
    };
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
