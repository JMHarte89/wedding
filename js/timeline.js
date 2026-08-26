/* ------------------------------------------------------------
   Becki & Jase — the running order for the day.

   SINGLE SOURCE OF TRUTH. Read by both index.html (via js/wedding.js)
   and the public agenda.html. Change the times here and nowhere else —
   editing one page's copy by hand is how the two drift apart.

   Load this BEFORE js/wedding.js.
------------------------------------------------------------ */
(function (root) {
  'use strict';

  root.WEDDING_TIMELINE = [
    { time: '11:00',      event: 'Arrive at church',                  note: 'Holy Trinity Church, Kendal. Doors open from 11am — find a pew, say your hellos, and grab a service sheet before the 11:30 start.' },
    { time: '11:30',      event: 'The ceremony',                      note: 'The bit we’re most nervous about.' },
    { time: '12:30',      event: 'Photographs outside the church',    note: 'The bridal party will guide everyone out. Confetti welcome — biodegradable only please.' },
    { time: '1:00–1:30',  event: 'Make your way to the venue',        note: 'The groomsmen and bridesmaids will point you in the right direction. It’s not far.' },
    { time: '2:00',       event: 'Welcome drinks — the newlyweds arrive', note: 'Raise a glass. The hard part is done.' },
    { time: '2:00–4:00',  event: 'Grazing, pizza & pancakes',         note: 'A sharing grazing buffet, plus wood-fired pizza and fresh pancakes — the full menu is further down this page. There’s also a magician wandering about — yes, really.' },
    { time: '4:30',       event: 'Speeches',                          note: 'Sit down, top up your glass, and be kind.' },
    { time: '6:30',       event: 'Evening guests arrive',             note: 'Welcome — you’ve missed the nerves, caught the fun.' },
    { time: '7:00',       event: 'First dance & the band',            note: 'An acoustic first dance, then the band takes over — dance floor open, no excuses.' },
    { time: '7:30–9:30',  event: 'Ninja Wraps',                       note: 'Evening food. Fuel for the dancefloor.' },
    { time: '12:00',      event: 'Carriages',                         note: 'Taxis turn into pumpkins. Thank you for being here.' }
  ];

  // The stop where evening-only guests join us. Matched by EVENT NAME, never
  // by time: two stops could easily share a time, and the time is the thing
  // most likely to be edited. Compared trimmed + lowercased at the call site
  // so a stray capital or space in a copy tweak can't break the filter.
  root.WEDDING_EVENING_START_EVENT = 'Evening guests arrive';

})(typeof window !== 'undefined' ? window : this);
