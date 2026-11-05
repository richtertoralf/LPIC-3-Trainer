/* LPIC-3 Trainer front-end helpers (no frameworks). */
(function () {
  "use strict";

  // Navigation toggle (mobile)
  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.querySelector("[data-nav]");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Offline banner
  var banner = document.querySelector("[data-offline-banner]");
  function updateOnline() { if (banner) { banner.hidden = navigator.onLine; } }
  window.addEventListener("online", updateOnline);
  window.addEventListener("offline", updateOnline);
  updateOnline();

  // Service worker
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(function () { /* offline support unavailable */ });
  }

  // Confirmation dialogs
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (ev) {
      if (!window.confirm(form.getAttribute("data-confirm"))) { ev.preventDefault(); }
    });
  });

  // Language help: translation toggle, term highlighting, popover
  document.querySelectorAll("[data-help-panel]").forEach(function (panel) {
    var scope = panel.closest("[data-question-form]") || document;
    var usedHelp = scope.querySelector("[data-used-help]");
    var terms = [];
    try { terms = JSON.parse(panel.getAttribute("data-terms") || "[]"); } catch (e) { terms = []; }
    var popover = panel.querySelector("[data-term-popover]");
    var highlighted = false;

    function markHelp() { if (usedHelp) { usedHelp.value = "1"; } }

    var translationBtn = panel.querySelector("[data-toggle-translation]");
    if (translationBtn) {
      translationBtn.addEventListener("click", function () {
        var nodes = scope.querySelectorAll("[data-translation]");
        var show = nodes.length && nodes[0].hidden;
        nodes.forEach(function (n) { n.hidden = !show; });
        translationBtn.textContent = show ? "Übersetzung ausblenden" : "Übersetzung anzeigen";
        if (show) { markHelp(); }
      });
    }

    function escapeRegExp(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

    function highlight() {
      if (!terms.length) { return; }
      var sorted = terms.slice().sort(function (a, b) { return b.term.length - a.term.length; });
      var pattern = new RegExp("(?<![A-Za-z0-9])(" + sorted.map(function (t) { return escapeRegExp(t.term); }).join("|") + ")(?![A-Za-z0-9])", "gi");
      scope.querySelectorAll("[data-question-text]").forEach(function (el) {
        var text = el.textContent;
        var frag = document.createDocumentFragment();
        var last = 0, m;
        pattern.lastIndex = 0;
        while ((m = pattern.exec(text)) !== null) {
          if (m.index > last) { frag.appendChild(document.createTextNode(text.slice(last, m.index))); }
          var span = document.createElement("span");
          span.className = "term";
          span.textContent = m[0];
          var key = m[0].toLowerCase();
          var term = sorted.find(function (t) { return t.term.toLowerCase() === key; });
          if (term) { span.setAttribute("data-term-id", term.id); }
          span.setAttribute("role", "button");
          span.setAttribute("tabindex", "0");
          frag.appendChild(span);
          last = m.index + m[0].length;
        }
        if (last < text.length) { frag.appendChild(document.createTextNode(text.slice(last))); }
        el.textContent = "";
        el.appendChild(frag);
      });
    }

    function unhighlight() {
      scope.querySelectorAll("[data-question-text]").forEach(function (el) { el.textContent = el.textContent; });
      if (popover) { popover.hidden = true; }
    }

    var termsBtn = panel.querySelector("[data-toggle-terms]");
    if (termsBtn) {
      if (!terms.length) { termsBtn.disabled = true; termsBtn.textContent = "Keine Fachbegriffe hinterlegt"; }
      termsBtn.addEventListener("click", function () {
        highlighted = !highlighted;
        if (highlighted) { highlight(); markHelp(); } else { unhighlight(); }
        termsBtn.textContent = highlighted ? "Markierung ausblenden" : "Fachbegriffe markieren";
      });
    }

    function showTerm(id) {
      var term = terms.find(function (t) { return String(t.id) === String(id); });
      if (!term || !popover) { return; }
      popover.querySelector("[data-popover-term]").textContent = term.term;
      popover.querySelector("[data-popover-de]").textContent = "– " + term.de;
      popover.querySelector("[data-popover-explanation]").textContent = term.explanation || "";
      var learnBtn = popover.querySelector("[data-popover-learn]");
      learnBtn.setAttribute("data-learn-term", term.id);
      learnBtn.disabled = false;
      learnBtn.textContent = term.status === "learning" ? "Wird gelernt" : (term.status === "known" ? "Gelernt" : "Begriff merken");
      if (term.status) { learnBtn.disabled = true; }
      popover.hidden = false;
      markHelp();
    }

    scope.addEventListener("click", function (ev) {
      var t = ev.target.closest(".term[data-term-id]");
      if (t) { ev.preventDefault(); showTerm(t.getAttribute("data-term-id")); }
    });
    scope.addEventListener("keydown", function (ev) {
      var t = ev.target.closest(".term[data-term-id]");
      if (t && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); showTerm(t.getAttribute("data-term-id")); }
    });
    var closeBtn = panel.querySelector("[data-popover-close]");
    if (closeBtn) { closeBtn.addEventListener("click", function () { popover.hidden = true; }); }

    panel.addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-learn-term]");
      if (!btn || btn.disabled) { return; }
      var id = btn.getAttribute("data-learn-term");
      btn.disabled = true;
      fetch("/api/terms/" + id + "/learn", { method: "POST", headers: { "Accept": "application/json" } })
        .then(function (r) { if (!r.ok) { throw new Error("failed"); } return r.json(); })
        .then(function () {
          btn.textContent = "Wird gelernt";
          var term = terms.find(function (t) { return String(t.id) === id; });
          if (term) { term.status = "learning"; }
          var span = document.createElement("span"); span.className = "tag"; span.textContent = "wird gelernt";
          if (btn.classList.contains("link")) { btn.replaceWith(span); }
        })
        .catch(function () { btn.disabled = false; btn.textContent = "Offline – später erneut"; });
    });
  });

  // Exam: timer and answered counter
  var examForm = document.querySelector("[data-exam-form]");
  if (examForm) {
    var counter = examForm.querySelector("[data-answered-count]");
    var sections = examForm.querySelectorAll(".question-card");
    var isAnswered = function (s) {
      if (s.querySelector("input:checked")) { return true; }
      var text = s.querySelector("input[type=text]");
      return !!(text && text.value.trim());
    };
    function updateCount() {
      var answered = 0;
      sections.forEach(function (s) { if (isAnswered(s)) { answered += 1; } });
      if (counter) { counter.textContent = answered + " von " + sections.length + " beantwortet"; }
    }
    examForm.addEventListener("change", updateCount);
    examForm.addEventListener("input", updateCount);
    updateCount();
    var autoSubmit = false;
    examForm.addEventListener("submit", function (ev) {
      if (autoSubmit) { return; }
      var open = 0;
      sections.forEach(function (s) { if (!isAnswered(s)) { open += 1; } });
      if (open > 0 && !window.confirm(open + " Frage(n) sind noch unbeantwortet. Trotzdem abgeben?")) {
        ev.preventDefault();
      }
    });
    var timer = document.querySelector("[data-timer]");
    if (timer) {
      var remaining = parseInt(timer.getAttribute("data-remaining"), 10);
      function tick() {
        var m = Math.floor(remaining / 60), s = remaining % 60;
        timer.textContent = (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
        if (remaining <= 300) { timer.classList.add("timer-warn"); }
        if (remaining <= 0) { autoSubmit = true; examForm.submit(); return; }
        remaining -= 1;
        setTimeout(tick, 1000);
      }
      tick();
    }
  }

  // Flashcards
  document.querySelectorAll("[data-flashcard]").forEach(function (card) {
    var btn = card.querySelector("[data-reveal]");
    var answer = card.querySelector("[data-answer]");
    if (btn && answer) { btn.addEventListener("click", function () { answer.hidden = false; btn.hidden = true; }); }
  });
})();
