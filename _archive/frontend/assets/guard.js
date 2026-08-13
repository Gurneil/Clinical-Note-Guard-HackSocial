/* The guard page: pick any of the 60 synthetic encounters and run the check.
   Every flag rendered here is the pipeline's REAL output for that case,
   baked from eval/raw_outputs.json by frontend/build_cases.py. Nothing is
   invented in the browser - if the page and the docs ever disagree, the
   page is stale and rebuilding fixes it. */
(function () {
  "use strict";
  var CASES = window.GUARD_CASES || [];
  var select = document.getElementById("caseSelect");
  if (!select || !CASES.length) return;

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var search = document.getElementById("caseSearch"),
      meta = document.getElementById("caseMeta"),
      title = document.getElementById("caseTitle"),
      transcriptEl = document.getElementById("gTranscript"),
      noteEl = document.getElementById("gNote"),
      stepsEl = document.getElementById("gSteps"),
      resultEl = document.getElementById("gResult"),
      baselineBox = document.getElementById("gBaselineBox"),
      btnRun = document.getElementById("gRun"),
      btnReset = document.getElementById("gReset"),
      btnBaseline = document.getElementById("gBaseline");

  var STEPS = ["2 · extract claims", "3 · entailment", "4 · numeric check",
               "5 · omission", "6 · classify", "7 · your review"];
  var SEVERITY = {
    numeric_medication_error: "critical", negation_error: "critical",
    fabrication: "high", distortion: "medium",
    misattribution: "medium", omission: "medium",
    transcript_uncertainty: "high"
  };

  var current = null, timers = [], running = false;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function prettyId(id) {
    return id.replace(/^case_\d+_?/, "").replace(/_/g, " ") || id;
  }
  function clearTimers() { timers.forEach(clearTimeout); timers = []; }

  /* ── the picker ── */
  function optionLabel(c) {
    var n = (c.id.match(/^case_(\d+)/) || [, "?"])[1];
    return n + " · " + (c.specialty || prettyId(c.id));
  }

  function fillSelect(filter) {
    var q = (filter || "").trim().toLowerCase();
    var matches = CASES.filter(function (c) {
      if (!q) return true;
      return (c.id + " " + c.specialty + " " + c.transcript + " " + c.note)
        .toLowerCase().indexOf(q) > -1;
    });
    select.innerHTML = "";
    matches.forEach(function (c) {
      var o = document.createElement("option");
      o.value = c.id;
      o.textContent = optionLabel(c);
      select.appendChild(o);
    });
    if (!matches.length) {
      var none = document.createElement("option");
      none.textContent = "no encounter matches “" + filter + "”";
      none.disabled = true;
      select.appendChild(none);
    }
    return matches;
  }

  /* ── rendering a case ── */
  function speakerLines(text) {
    return String(text).split("\n").map(function (line) {
      var m = line.match(/^([A-Za-z ]+):\s*(.*)$/);
      return m
        ? '<p><span class="spk">' + esc(m[1]) + ':</span> ' + esc(m[2]) + "</p>"
        : "<p>" + esc(line) + "</p>";
    }).join("");
  }

  function noteLines(text) {
    return String(text).split("\n").filter(function (l) { return l.trim(); })
      .map(function (line, i) {
        return '<div class="note-line" data-i="' + i + '">' + esc(line) + "</div>";
      }).join("");
  }

  function show(caseId) {
    current = CASES.filter(function (c) { return c.id === caseId; })[0] || CASES[0];
    clearTimers(); running = false;

    title.innerHTML = "<b>" + esc(current.id) + "</b> · " + esc(current.specialty);
    transcriptEl.innerHTML = speakerLines(current.transcript);
    noteEl.innerHTML = noteLines(current.note);
    stepsEl.innerHTML = "";
    baselineBox.hidden = true;
    btnBaseline.setAttribute("aria-pressed", "false");
    btnRun.disabled = false;
    btnRun.textContent = "Run the check";

    var bits = [];
    bits.push(current.hasError
      ? "planted error: <b>" + esc(current.planted.category) + "</b>"
      : "<b>clean control</b> — nothing was planted in this note");
    if (current.claims.length) bits.push(current.claims.length + " claims extracted");
    if (current.model) bits.push("checked by <span class='mono'>" + esc(current.model) + "</span>");
    meta.innerHTML = bits.join(" &nbsp;·&nbsp; ");

    resultEl.innerHTML = current.errored
      ? '<p class="empty">This case <b>errored out during the eval run</b> — a model exhausted its '
        + 'JSON-retry budget, so there is no committed output to show. It is excluded from the '
        + 'reported numbers rather than counted as a miss.</p>'
      : '<p class="empty">Press <b>Run the check</b> to decompose the note and verify each claim '
        + 'against the transcript.</p>';
  }

  /* ── running it ── */
  function renderSteps(active) {
    stepsEl.innerHTML = "";
    STEPS.forEach(function (label, i) {
      var s = document.createElement("span");
      s.className = "pstep";
      s.textContent = label;
      if (active > i) s.dataset.on = "done";
      else if (active === i) s.dataset.on = "run";
      stepsEl.appendChild(s);
    });
  }

  function flagCard(flag, index, total) {
    var sev = SEVERITY[flag.category] || "medium";
    return '<div class="flagcard" style="border-left-color:' +
      (sev === "critical" ? "var(--vermilion)" : sev === "high" ? "var(--amber)" : "var(--clinic-2)") + '">'
      + '<div class="flag-top"><span class="sev" style="' +
        (sev === "critical" ? "" : "background:rgba(180,128,31,.14);color:var(--amber)") + '">' + sev + "</span>"
      + '<span class="cat mono">' + esc(flag.category || "unclassified")
      + " · flag " + (index + 1) + " of " + total + "</span></div>"
      + '<div class="flag-q">' + esc(flag.claim) + "</div>"
      + (flag.why ? '<div class="evrow">' + esc(flag.why) + "</div>" : "")
      + (flag.evidence ? '<div class="evrow">Transcript: “<b>' + esc(flag.evidence) + "</b>”</div>" : "")
      + '<div class="corro"><span>' + esc(flag.source || "pipeline") + "</span></div>"
      + "</div>";
  }

  function finish() {
    renderSteps(STEPS.length);
    var flags = current.flags || [];
    if (!flags.length) {
      resultEl.innerHTML = '<div class="done-strip"><span>✓</span><span>No flags raised. '
        + (current.hasError
            ? "This case had a planted error, so this is a <b>miss</b> — shown as it happened."
            : "This is a clean control, so raising nothing is the right answer.")
        + "</span></div>";
      return;
    }
    resultEl.innerHTML = flags.map(function (f, i) {
      return flagCard(f, i, flags.length);
    }).join("")
      + '<div class="done-strip"><span>✓</span><span>' + flags.length + " flag(s) for a human to "
      + "confirm or dismiss. Nothing was changed automatically.</span></div>";
  }

  function run() {
    if (running || !current || current.errored) return;
    running = true;
    clearTimers();
    btnRun.disabled = true;
    btnRun.textContent = "Checking…";
    resultEl.innerHTML = '<p class="empty">Decomposing the note into atomic claims…</p>';

    var gap = reduce ? 40 : 380;
    renderSteps(0);
    var lines = [].slice.call(noteEl.querySelectorAll(".note-line"));

    lines.forEach(function (line, i) {
      timers.push(setTimeout(function () {
        line.dataset.state = "checking";
      }, gap * (i + 1)));
      timers.push(setTimeout(function () {
        /* a line is "flagged" if any real flag quotes text from it */
        var hit = (current.flags || []).some(function (f) {
          var claim = (f.claim || "").toLowerCase().split(/\s+/).filter(function (w) { return w.length > 4; });
          var text = line.textContent.toLowerCase();
          return claim.length && claim.filter(function (w) { return text.indexOf(w) > -1; }).length >= Math.min(2, claim.length);
        });
        line.dataset.state = hit ? "flag" : "ok";
      }, gap * (i + 1) + gap * 0.6));
    });

    var end = gap * (lines.length + 2);
    [1, 2, 3, 4].forEach(function (step, k) {
      timers.push(setTimeout(function () { renderSteps(step); }, end + k * gap * 0.5));
    });
    timers.push(setTimeout(function () {
      finish();
      running = false;
      btnRun.disabled = false;
      btnRun.textContent = "Run again";
    }, end + gap * 2.5));
  }

  function reset() {
    clearTimers(); running = false;
    show(current ? current.id : CASES[0].id);
  }

  /* ── wiring ── */
  search.addEventListener("input", function () {
    var matches = fillSelect(search.value);
    if (matches.length) show(matches[0].id);
  });
  select.addEventListener("change", function () { show(select.value); });
  btnRun.addEventListener("click", run);
  btnReset.addEventListener("click", reset);
  btnBaseline.addEventListener("click", function () {
    var on = btnBaseline.getAttribute("aria-pressed") === "true";
    btnBaseline.setAttribute("aria-pressed", on ? "false" : "true");
    baselineBox.hidden = on;
    if (!on) {
      var items = current.baseline || [];
      baselineBox.innerHTML = '<div class="baseline-box"><b>Single-prompt baseline, same case:</b> '
        + (items.length
            ? "it reported " + items.length + " issue(s).<br>" +
              items.map(function (i) { return "· " + esc(i); }).join("<br>")
            : "it reported <b>nothing at all</b> on this case.")
        + "</div>";
    }
  });

  fillSelect("");
  show(CASES[0].id);
})();
