/* Pure functions for revision and streaks. No DOM, so they can be tested with Node (tests/js/logic.test.js). */
(function (root) {
  "use strict";
  var INTERVALS = [1, 3, 7, 14]; // days until a missed question comes back, after each correct answer in turn

  function addDays(dateStr, n) {
    var d = new Date(dateStr + "T00:00:00Z");
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  }

  // A question was missed: it returns tomorrow, at the start of the ladder.
  function miss(entry, today) {
    return Object.assign({}, entry, { step: 0, due: addDays(today, INTERVALS[0]) });
  }

  // A revision answer. Returns the updated entry, or null once the last step is answered correctly.
  function review(entry, today, correct) {
    if (!correct) return miss(entry, today);
    var next = entry.step + 1;
    if (next >= INTERVALS.length) return null;
    return Object.assign({}, entry, { step: next, due: addDays(today, INTERVALS[next]) });
  }

  function due(queue, today) {
    return queue.filter(function (e) { return e.due <= today; });
  }

  // Add a missed question unless the same one is already queued.
  function enqueue(queue, entry, today) {
    var same = queue.some(function (e) { return e.slug === entry.slug && e.q === entry.q; });
    return same ? queue : queue.concat([miss(entry, today)]);
  }

  // Days in a row ending today. If today has no visit yet, count back from yesterday so a streak is not shown as lost.
  function streak(days, today) {
    var seen = {};
    days.forEach(function (d) { seen[d] = true; });
    var cursor = seen[today] ? today : addDays(today, -1);
    var count = 0;
    while (seen[cursor]) { count += 1; cursor = addDays(cursor, -1); }
    return count;
  }

  function lastDays(today, n) {
    var out = [];
    for (var i = n - 1; i >= 0; i--) out.push(addDays(today, -i));
    return out;
  }

  var api = { INTERVALS: INTERVALS, addDays: addDays, miss: miss, review: review, due: due, enqueue: enqueue, streak: streak, lastDays: lastDays };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SFLogic = api;
})(typeof window !== "undefined" ? window : this);
