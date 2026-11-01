const test = require("node:test");
const assert = require("node:assert");
const L = require("../../site/assets/logic.js");

test("addDays crosses month and year ends", () => {
  assert.equal(L.addDays("2026-11-30", 1), "2026-12-01");
  assert.equal(L.addDays("2026-12-31", 1), "2027-01-01");
  assert.equal(L.addDays("2026-03-01", -1), "2026-02-28");
});

test("a missed question returns tomorrow at step 0", () => {
  const e = L.miss({ slug: "a", q: 0 }, "2026-11-01");
  assert.deepEqual([e.step, e.due], [0, "2026-11-02"]);
});

test("correct answers climb the ladder 1, 3, 7, 14 days and then finish", () => {
  let e = L.miss({ slug: "a", q: 0 }, "2026-11-01");
  e = L.review(e, "2026-11-02", true);
  assert.deepEqual([e.step, e.due], [1, "2026-11-05"]);
  e = L.review(e, "2026-11-05", true);
  assert.deepEqual([e.step, e.due], [2, "2026-11-12"]);
  e = L.review(e, "2026-11-12", true);
  assert.deepEqual([e.step, e.due], [3, "2026-11-26"]);
  assert.equal(L.review(e, "2026-11-26", true), null);
});

test("a wrong answer in revision goes back to the start", () => {
  let e = { slug: "a", q: 0, step: 2, due: "2026-11-12" };
  e = L.review(e, "2026-11-12", false);
  assert.deepEqual([e.step, e.due], [0, "2026-11-13"]);
});

test("due returns only entries due today or earlier", () => {
  const q = [{ due: "2026-11-01" }, { due: "2026-11-02" }, { due: "2026-10-30" }];
  assert.equal(L.due(q, "2026-11-01").length, 2);
});

test("enqueue ignores a question that is already queued", () => {
  let q = L.enqueue([], { slug: "a", q: 1 }, "2026-11-01");
  q = L.enqueue(q, { slug: "a", q: 1 }, "2026-11-01");
  q = L.enqueue(q, { slug: "a", q: 2 }, "2026-11-01");
  assert.equal(q.length, 2);
});

test("streak counts days in a row, and does not drop to zero before today's visit", () => {
  assert.equal(L.streak(["2026-10-30", "2026-10-31", "2026-11-01"], "2026-11-01"), 3);
  assert.equal(L.streak(["2026-10-30", "2026-10-31"], "2026-11-01"), 2);
  assert.equal(L.streak(["2026-10-28", "2026-10-31"], "2026-11-01"), 1);
  assert.equal(L.streak([], "2026-11-01"), 0);
  assert.equal(L.streak(["2026-10-25"], "2026-11-01"), 0);
});

test("lastDays gives n days ending today", () => {
  const d = L.lastDays("2026-11-01", 3);
  assert.deepEqual(d, ["2026-10-30", "2026-10-31", "2026-11-01"]);
});
