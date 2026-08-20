/* ------------------------------------------------------------
   Becki & Jase — the food on the day.

   SINGLE SOURCE OF TRUTH. Read by index.html, agenda.html and
   scripts/build-print.py (which parses this file to build print/menu.docx).
   Change the menu here and nowhere else.

   DIETARY MARKERS ARE PROVISIONAL — confirm every V/VG label with
   Cracking Spread and the wrap supplier before printing or
   publishing. Do not treat as allergen guidance.

   (The warning above is intentionally a JS comment, not a literal HTML
   comment: `-->` inside a .js file is only tolerated by browsers as a legacy
   quirk in classic scripts and breaks outright in modules, bundlers and
   minifiers. Same words, same prominence, no landmine.)
------------------------------------------------------------ */
(function (root) {
  'use strict';

  root.WEDDING_MENU = {
    kicker: 'Food on the day',
    title: 'What’s on the menu',

    blocks: [
      {
        heading: 'Pizza & Buffet',
        time: 'served from 2:00',
        groups: [
          {
            subheading: 'Stone-baked pizza',
            items: [
              {
                name: 'Margherita (V)',
                detail: 'Tomato, mozzarella, basil, oregano'
              },
              {
                name: 'Roasted Veg (V)',
                detail: 'Tomato, mozzarella, red onion, red pepper, green pepper, chestnut mushroom, thyme, basil, oregano'
              },
              {
                name: 'Bee Sting Pepperoni',
                detail: 'Tomato, mozzarella, pepperoni, Sriracha chilli sauce, roquito peppers, Mark’s hot honey, basil, oregano'
              }
            ]
          },
          {
            subheading: 'Served alongside a buffet of',
            items: [
              { name: 'Selection of English and continental cheeses with crackers, olives and chutney (V)' },
              { name: 'Sicilian roast potatoes with lemon zest and parmesan (V)' },
              { name: 'Pesto and sun-dried tomato pasta salad (V)' },
              { name: 'Mediterranean salad with a red wine vinegar and oregano dressing (VG)' },
              { name: 'Orzo with roasted vegetables (VG)' },
              { name: 'Tomato, feta and basil salad (V)' },
              { name: 'Mushroom pâté and brussels pâté (V)' },
              { name: 'Sticky sausages in a cranberry and orange glaze' },
              { name: 'Coleslaw (V)' },
              { name: 'Hummus with olives and vine tomatoes (VG)' },
              { name: 'Selection of artisan breads (V)' }
            ]
          }
        ]
      },

      {
        heading: 'Pancakes & Ice Cream',
        time: 'served 3:00–4:00',
        groups: [
          {
            items: [
              { name: 'Something sweet to follow.' }
            ]
          }
        ]
      },

      {
        heading: 'Wraps & Chips',
        time: 'served 7:30–9:30',
        groups: [
          {
            items: [
              {
                name: 'Cajun Chicken Wrap',
                detail: 'Spicy Cajun chicken, pickled red cabbage, sweetcorn and lime salsa, lettuce and homemade Cajun sauce'
              },
              {
                name: 'Halloumi Wrap (V)',
                detail: 'Halloumi in place of the chicken, with the same pickled red cabbage, sweetcorn and lime salsa, lettuce and Cajun sauce'
              },
              {
                name: 'Tofu Wrap (VG)',
                detail: 'Tofu in place of the chicken, with the same pickled red cabbage, sweetcorn and lime salsa, lettuce and Cajun sauce'
              },
              {
                name: 'Plain Chicken Wrap',
                detail: 'Chicken and lettuce, no spice — for children and anyone who’d rather keep it gentle'
              },
              { name: 'Rosemary salted fries (VG)' }
            ]
          }
        ]
      }
    ],

    footnote: '(V) vegetarian · (VG) vegan. Please let us know about any allergies or dietary needs — we’ll pass it on to our caterers.'
  };

})(typeof window !== 'undefined' ? window : this);
