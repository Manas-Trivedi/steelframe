/* Reader interaction. Plain JavaScript, no dependencies. Everything a reader creates stays in this browser. */
(function () {
  "use strict";
  var L = window.SFLogic;
  var root = document.body.getAttribute("data-root") || "";

  // ---- storage: every access is guarded, because it can throw (private windows, blocked site data) ----
  function load(key, fallback) {
    try { var raw = localStorage.getItem("sf." + key); return raw === null ? fallback : JSON.parse(raw); } catch (e) { return fallback; }
  }
  function save(key, value) {
    try { localStorage.setItem("sf." + key, JSON.stringify(value)); return true; } catch (e) { return false; }
  }
  function today() { return new Date().toISOString().slice(0, 10); }
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") node.textContent = attrs[k]; else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }

  var piece = document.querySelector(".piece");
  var meta = piece ? JSON.parse(piece.getAttribute("data-meta")) : null;

  // ---- reading depth ----
  function setDepth(depth) {
    document.querySelectorAll(".depths button[data-depth]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-depth") === depth));
    });
    document.querySelectorAll("#text section[data-depth]").forEach(function (s) {
      s.hidden = s.getAttribute("data-depth") !== depth;
    });
    save("depth", depth);
  }

  // ---- source drawer ----
  var lastClaim = null;
  function openDrawer(ids, trigger) {
    var data = JSON.parse(document.getElementById("claims").textContent);
    var body = document.getElementById("drawer-body");
    body.textContent = "";
    ids.forEach(function (id) {
      var c = data[id];
      if (!c) return;
      var passage = el("blockquote", {});
      passage.innerHTML = c.passage_html; // built and escaped at build time from the stored passage
      body.appendChild(el("div", { "class": "source" }, [
        el("p", { "class": "meta", text: "Claim" }),
        el("p", { text: c.claim }),
        el("p", { "class": "meta", text: "Passage, copied from " + c.source + " on " + c.fetched }),
        passage,
        el("p", {}, [el("a", { href: c.url, text: "Open the original page" })])
      ]));
    });
    var drawer = document.getElementById("drawer");
    drawer.hidden = false;
    lastClaim = trigger;
    document.getElementById("drawer-close").focus();
  }
  function closeDrawer() {
    var drawer = document.getElementById("drawer");
    if (drawer.hidden) return;
    drawer.hidden = true;
    if (lastClaim) lastClaim.focus();
  }

  // ---- recall questions ----
  function questionData(fieldset) {
    return {
      slug: meta.slug, title: meta.title, q: Number(fieldset.getAttribute("data-q")),
      question: fieldset.querySelector("legend").textContent.replace(/^\d+\.\s*/, ""),
      options: Array.prototype.map.call(fieldset.querySelectorAll("label span"), function (s) { return s.textContent; }),
      answer: Number(fieldset.getAttribute("data-answer")),
      explanation: fieldset.querySelector(".explain").textContent
    };
  }
  function checkQuiz(event) {
    event.preventDefault();
    var queue = load("revision", []);
    document.querySelectorAll("#quiz fieldset").forEach(function (fs) {
      var chosen = fs.querySelector("input:checked");
      var note = fs.querySelector(".explain");
      var right = chosen && Number(chosen.value) === Number(fs.getAttribute("data-answer"));
      fs.classList.toggle("right", !!right);
      fs.classList.toggle("wrong", !right);
      var verdict = chosen ? (right ? "Correct. " : "Not quite. ") : "No answer chosen. ";
      note.textContent = verdict + questionData(fs).explanation.replace(/^(Correct\. |Not quite\. |No answer chosen\. )/, "");
      note.hidden = false;
      if (!right) queue = L.enqueue(queue, questionData(fs), today());
    });
    save("revision", queue);
  }

  // ---- save, highlights, notes ----
  function initSave() {
    var button = document.getElementById("save");
    var saved = load("saved", []);
    function paint() { button.setAttribute("aria-pressed", String(saved.some(function (s) { return s.slug === meta.slug; }))); button.textContent = button.getAttribute("aria-pressed") === "true" ? "Saved" : "Save"; }
    paint();
    button.addEventListener("click", function () {
      saved = saved.some(function (s) { return s.slug === meta.slug; })
        ? saved.filter(function (s) { return s.slug !== meta.slug; })
        : saved.concat([{ slug: meta.slug, title: meta.title, date: meta.date, topic: meta.topic }]);
      save("saved", saved);
      paint();
    });
  }
  function applyHighlights() {
    var marks = load("highlights", []).filter(function (h) { return h.slug === meta.slug; });
    marks.forEach(function (h) {
      var walker = document.createTreeWalker(document.getElementById("text"), NodeFilter.SHOW_TEXT);
      var node;
      while ((node = walker.nextNode())) {
        var at = node.nodeValue.indexOf(h.text);
        if (at === -1 || node.parentNode.closest("mark.mine")) continue;
        var range = document.createRange();
        range.setStart(node, at); range.setEnd(node, at + h.text.length);
        var mark = el("mark", { "class": "mine", title: h.note || "Your highlight" });
        range.surroundContents(mark);
        break;
      }
    });
  }
  function initSelection() {
    var bar = el("div", { "class": "selbar", hidden: "" }, [
      el("button", { type: "button", "data-act": "highlight", text: "Highlight" }),
      el("button", { type: "button", "data-act": "note", text: "Add note" })
    ]);
    document.body.appendChild(bar);
    var current = "";
    document.getElementById("text").addEventListener("mouseup", function () {
      var sel = window.getSelection();
      var text = sel ? sel.toString().trim() : "";
      var single = sel && sel.rangeCount && sel.getRangeAt(0).startContainer === sel.getRangeAt(0).endContainer;
      if (!text || text.length > 400 || !single) { bar.hidden = true; return; }
      current = text;
      var rect = sel.getRangeAt(0).getBoundingClientRect();
      bar.style.top = (window.scrollY + rect.top - 44) + "px";
      bar.style.left = (window.scrollX + rect.left) + "px";
      bar.hidden = false;
    });
    bar.addEventListener("click", function (event) {
      var act = event.target.getAttribute("data-act");
      if (!act) return;
      var note = act === "note" ? window.prompt("Your note") : "";
      if (act === "note" && note === null) return;
      var list = load("highlights", []);
      list.push({ slug: meta.slug, title: meta.title, text: current, note: note || "", at: today() });
      save("highlights", list);
      bar.hidden = true;
      window.getSelection().removeAllRanges();
      applyHighlights();
    });
  }

  // ---- pages ----
  function initPiece() {
    var depth = load("depth", "editorial");
    setDepth(depth);
    document.querySelector(".depths").addEventListener("click", function (event) {
      var d = event.target.closest("button[data-depth]");
      if (d) setDepth(d.getAttribute("data-depth"));
    });
    document.getElementById("text").addEventListener("click", function (event) {
      var c = event.target.closest(".claim");
      if (c) openDrawer(c.getAttribute("data-claims").split(" "), c);
    });
    document.getElementById("text").addEventListener("keydown", function (event) {
      var c = event.target.closest(".claim");
      if (c && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); openDrawer(c.getAttribute("data-claims").split(" "), c); }
    });
    document.getElementById("drawer-close").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", function (event) { if (event.key === "Escape") closeDrawer(); });
    document.getElementById("quiz").addEventListener("submit", checkQuiz);
    initSave();
    applyHighlights();
    initSelection();
    var days = load("days", []);
    if (days.indexOf(today()) === -1) { days.push(today()); save("days", days); }
  }

  function initRevision() {
    var host = document.getElementById("revision");
    var queue = load("revision", []);
    var due = L.due(queue, today());
    host.textContent = "";
    if (!due.length) {
      host.appendChild(el("p", { text: queue.length ? "Nothing is due today. " + queue.length + " question(s) are waiting for their day." : "No missed questions yet. Answer the recall questions at the end of a piece." }));
      return;
    }
    due.forEach(function (entry) {
      var fs = el("fieldset", { "class": "q" }, [el("legend", { text: entry.question })]);
      var note = el("p", { "class": "explain", hidden: "" });
      entry.options.forEach(function (text, i) {
        fs.appendChild(el("label", {}, [el("input", { type: "radio", name: "r" + entry.slug + entry.q, value: String(i) }), document.createTextNode(" "), el("span", { text: text })]));
      });
      var button = el("button", { type: "button", text: "Check" });
      button.addEventListener("click", function () {
        var chosen = fs.querySelector("input:checked");
        if (!chosen) return;
        var right = Number(chosen.value) === entry.answer;
        var updated = L.review(entry, today(), right);
        var rest = load("revision", []).filter(function (e) { return !(e.slug === entry.slug && e.q === entry.q); });
        save("revision", updated ? rest.concat([updated]) : rest);
        note.textContent = (right ? "Correct. " : "Not quite. ") + entry.explanation + (right ? (updated ? " It comes back in " + (L.INTERVALS[updated.step]) + " day(s)." : " You have it. It leaves the queue.") : " It comes back tomorrow.");
        note.hidden = false;
        button.disabled = true;
      });
      fs.appendChild(button); fs.appendChild(note);
      fs.appendChild(el("p", { "class": "meta" }, [el("a", { href: root + "p/" + entry.slug + ".html", text: entry.title })]));
      host.appendChild(fs);
    });
  }

  function initMe() {
    var host = document.getElementById("me");
    host.textContent = "";
    var days = load("days", []);
    var t = today();
    host.appendChild(el("h2", { text: "Streak" }));
    host.appendChild(el("p", { text: L.streak(days, t) + " day(s) in a row. " + days.length + " day(s) read in all." }));
    var grid = el("div", { "class": "calendar", role: "list", "aria-label": "Last 28 days" });
    L.lastDays(t, 28).forEach(function (d) {
      var read = days.indexOf(d) !== -1;
      grid.appendChild(el("span", { role: "listitem", "class": read ? "day read" : "day", "aria-label": d + (read ? ", read" : ", not read"), title: d, text: read ? "●" : "○" }));
    });
    host.appendChild(grid);

    host.appendChild(el("h2", { text: "Preferences" }));
    var depth = el("select", { id: "pref-depth" }, ["brief", "editorial", "deep"].map(function (d) { return el("option", { value: d, text: d === "deep" ? "Deep dive" : d.charAt(0).toUpperCase() + d.slice(1) }); }));
    depth.value = load("depth", "editorial");
    depth.addEventListener("change", function () { save("depth", depth.value); });
    var theme = el("select", { id: "pref-theme" }, [el("option", { value: "", text: "Follow my device" }), el("option", { value: "light", text: "Light" }), el("option", { value: "dark", text: "Dark" })]);
    theme.value = load("theme", "");
    theme.addEventListener("change", function () {
      save("theme", theme.value);
      if (theme.value) document.documentElement.dataset.theme = theme.value; else delete document.documentElement.dataset.theme;
    });
    host.appendChild(el("p", {}, [el("label", { "for": "pref-depth", text: "Default reading depth " }), depth]));
    host.appendChild(el("p", {}, [el("label", { "for": "pref-theme", text: "Theme " }), theme]));

    host.appendChild(el("h2", { text: "Saved" }));
    var saved = load("saved", []);
    host.appendChild(saved.length ? el("ul", { "class": "plain" }, saved.map(function (s) {
      return el("li", {}, [el("a", { href: root + "p/" + s.slug + ".html", text: s.title }), document.createTextNode(" (" + s.date + ")")]);
    })) : el("p", { text: "Nothing saved yet." }));

    host.appendChild(el("h2", { text: "Highlights and notes" }));
    var marks = load("highlights", []);
    host.appendChild(marks.length ? el("ul", { "class": "plain" }, marks.map(function (h, i) {
      var remove = el("button", { type: "button", text: "Delete" });
      remove.addEventListener("click", function () { var m = load("highlights", []); m.splice(i, 1); save("highlights", m); initMe(); });
      return el("li", {}, [el("blockquote", { text: h.text }), h.note ? el("p", { text: "Note: " + h.note }) : document.createTextNode(""),
        el("p", { "class": "meta" }, [el("a", { href: root + "p/" + h.slug + ".html", text: h.title }), document.createTextNode(" · "), remove])]);
    })) : el("p", { text: "No highlights yet. Select text in a piece to add one." }));

    host.appendChild(el("h2", { text: "Your data" }));
    var download = el("button", { type: "button", text: "Download my data" });
    download.addEventListener("click", function () {
      var all = {};
      ["depth", "theme", "saved", "highlights", "days", "revision"].forEach(function (k) { all[k] = load(k, null); });
      var link = el("a", { href: URL.createObjectURL(new Blob([JSON.stringify(all, null, 2)], { type: "application/json" })), download: "steelframe-data.json" });
      document.body.appendChild(link); link.click(); link.remove();
    });
    var input = el("input", { type: "file", accept: "application/json", id: "import" });
    input.addEventListener("change", function () {
      var file = input.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function () {
        try {
          var data = JSON.parse(reader.result);
          ["depth", "theme", "saved", "highlights", "days", "revision"].forEach(function (k) { if (data[k] !== null && data[k] !== undefined) save(k, data[k]); });
          initMe();
        } catch (e) { host.appendChild(el("p", { "class": "bad", role: "alert", text: "That file could not be read." })); }
      };
      reader.readAsText(file);
    });
    host.appendChild(el("p", {}, [download]));
    host.appendChild(el("p", {}, [el("label", { "for": "import", text: "Restore from a file " }), input]));
  }

  if (piece) initPiece();
  if (document.getElementById("revision")) initRevision();
  if (document.getElementById("me")) initMe();
})();
