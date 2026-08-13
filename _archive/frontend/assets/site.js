(function(){
  "use strict";
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── toast ── */
  var toastEl = document.getElementById("toast"), toastT;
  function toast(msg){
    if (!toastEl) return;
    toastEl.textContent = msg; toastEl.dataset.show = "true";
    clearTimeout(toastT); toastT = setTimeout(function(){ toastEl.dataset.show = "false"; }, 2600);
  }

  /* ── nav: dropdowns, burger, colour swap over dark layers ── */
  var drops = [].slice.call(document.querySelectorAll("[data-drop]"));
  drops.forEach(function(d){
    var btn = d.querySelector("[data-drop-toggle]");
    btn.addEventListener("click", function(e){
      e.stopPropagation();
      var open = d.dataset.open === "true";
      drops.forEach(function(o){ o.dataset.open = "false"; o.querySelector("[data-drop-toggle]").setAttribute("aria-expanded","false"); });
      d.dataset.open = open ? "false" : "true";
      btn.setAttribute("aria-expanded", open ? "false" : "true");
    });
  });
  document.addEventListener("click", function(){
    drops.forEach(function(o){ o.dataset.open = "false"; o.querySelector("[data-drop-toggle]").setAttribute("aria-expanded","false"); });
  });
  /* on a pointer, hovering opens them too — clicking still works either way */
  if (window.matchMedia("(hover: hover)").matches) {
    drops.forEach(function(d){
      var btn = d.querySelector("[data-drop-toggle]"), leaveT;
      d.addEventListener("mouseenter", function(){
        clearTimeout(leaveT);
        drops.forEach(function(o){ if (o !== d) { o.dataset.open = "false"; o.querySelector("[data-drop-toggle]").setAttribute("aria-expanded","false"); } });
        d.dataset.open = "true"; btn.setAttribute("aria-expanded","true");
      });
      d.addEventListener("mouseleave", function(){
        leaveT = setTimeout(function(){ d.dataset.open = "false"; btn.setAttribute("aria-expanded","false"); }, 180);
      });
    });
  }

  /* the wordmark goes home */
  document.querySelector(".brand").addEventListener("click", function(e){
    e.preventDefault();
    navlinks.dataset.open = "false"; burger.setAttribute("aria-expanded","false");
    window.scrollTo({top:0, behavior: reduce ? "auto" : "smooth"});
    if (history.replaceState) history.replaceState(null, "", location.pathname);
  });
  document.addEventListener("keydown", function(e){
    if (e.key === "Escape") drops.forEach(function(o){ o.dataset.open = "false"; o.querySelector("[data-drop-toggle]").setAttribute("aria-expanded","false"); });
  });

  var burger = document.getElementById("burger"), navlinks = document.getElementById("navlinks");
  if (burger && navlinks) {
  burger.addEventListener("click", function(e){
    e.stopPropagation();
    var open = navlinks.dataset.open === "true";
    navlinks.dataset.open = open ? "false" : "true";
    burger.setAttribute("aria-expanded", open ? "false" : "true");
  });
  navlinks.addEventListener("click", function(e){
    if (e.target.closest("a")) { navlinks.dataset.open = "false"; burger.setAttribute("aria-expanded","false"); }
  });
  }

  var nav = document.getElementById("nav"), lightLayer = document.querySelector(".layer-light");
  function paintNav(){
    if (!nav || !lightLayer) return;
    var y = window.scrollY + 40;
    var top = lightLayer.offsetTop, bottom = top + lightLayer.offsetHeight;
    nav.dataset.over = (y > top && y < bottom) ? "light" : "dark";
  }
  paintNav();
  window.addEventListener("scroll", paintNav, {passive:true});
  window.addEventListener("resize", paintNav);

  /* ── hero: drifting clinical fragments ── */
  if (!reduce) {
    var frags = ["10 mg","20 mg","128/82","denies","sulfa","no nausea","2 days","father","once daily","PRN","afebrile","BP","3 months","allergy","hives","x2 weeks"];
    var field = document.getElementById("driftfield");
    if (field) for (var i = 0; i < 26; i++) {
      var s = document.createElement("span");
      s.className = "drift" + (Math.random() < .18 ? " hot" : "");
      s.textContent = frags[i % frags.length];
      s.style.left = (Math.random() * 96) + "%";
      s.style.top = (Math.random() * 92) + "%";
      s.style.animationDuration = (9 + Math.random() * 11).toFixed(1) + "s";
      s.style.animationDelay = (-Math.random() * 14).toFixed(1) + "s";
      field.appendChild(s);
    }
  }

  /* ── the encounter search ───────────────────────────────────────────
     Cards leave with a fade, and the survivors are FLIP-animated into
     their new grid positions - grid can't transition layout on its own,
     so without this the remaining cards would snap. */
  (function(){
    var input = document.getElementById("mockSearch");
    if (!input) return;
    var grid = document.getElementById("mockGrid"),
        countEl = document.getElementById("mockCount"),
        clearBtn = document.getElementById("mockClear"),
        empty = document.getElementById("mockEmpty"),
        emptyQ = document.getElementById("mockEmptyQ"),
        emptyClear = document.getElementById("mockEmptyClear"),
        live = document.getElementById("mockLive"),
        cards = [].slice.call(grid.querySelectorAll(".mock-card")),
        fadeT = [];

    /* searchable text per card, built once */
    cards.forEach(function(c){ c.dataset.hay = c.textContent.toLowerCase().replace(/\s+/g, " "); });

    function apply(query){
      var q = query.trim().toLowerCase();
      var matches = cards.filter(function(c){ return !q || c.dataset.hay.indexOf(q) > -1; });

      /* FIRST: where is everything now */
      var first = new Map();
      cards.forEach(function(c){ if (c.dataset.out !== "true") first.set(c, c.getBoundingClientRect()); });

      fadeT.forEach(clearTimeout); fadeT = [];

      var returning = [];
      cards.forEach(function(c){
        var keep = matches.indexOf(c) > -1;
        if (!keep) { c.dataset.fading = "true"; return; }
        if (c.dataset.out === "true") {
          /* coming back from display:none - it has to be laid out in the
             faded state before un-fading, or there's nothing to
             transition from and the card just pops */
          c.dataset.out = "false";
          returning.push(c);
        } else {
          c.dataset.fading = "false";
        }
      });
      /* forcing layout synchronously rather than waiting on rAF: rAF does
         not fire while the page isn't compositing (backgrounded tab), and
         a card left mid-fade would be stranded invisible */
      returning.forEach(function(c){
        void c.offsetWidth;
        c.dataset.fading = "false";
      });

      /* let the outgoing cards fade before they leave the flow */
      var settle = function(){
        cards.forEach(function(c){ if (c.dataset.fading === "true") c.dataset.out = "true"; });

        /* LAST + INVERT + PLAY */
        matches.forEach(function(c){
          var f = first.get(c);
          if (!f) return;
          var l = c.getBoundingClientRect();
          var dx = f.left - l.left, dy = f.top - l.top;
          if (!dx && !dy) return;
          c.style.transition = "none";
          c.style.transform = "translate(" + dx + "px," + dy + "px)";
          void c.offsetWidth;              /* commit the inverted position */
          c.style.transition = "";
          c.style.transform = "";          /* ...then let it travel home */
        });
      };
      if (reduce) settle(); else fadeT.push(setTimeout(settle, 190));

      empty.hidden = matches.length > 0;
      emptyQ.textContent = '"' + query.trim() + '"';
      clearBtn.hidden = !q;

      if (countEl.textContent !== String(matches.length)) {
        countEl.textContent = matches.length;
        countEl.dataset.bump = "true";
        fadeT.push(setTimeout(function(){ countEl.dataset.bump = "false"; }, 250));
      }
      live.textContent = matches.length === cards.length
        ? "Showing all " + cards.length + " encounters."
        : matches.length + " of " + cards.length + " encounters match.";
    }

    function clear(){ input.value = ""; apply(""); input.focus(); }

    input.addEventListener("input", function(){ apply(input.value); });
    input.addEventListener("keydown", function(e){ if (e.key === "Escape") clear(); });
    clearBtn.addEventListener("click", clear);
    emptyClear.addEventListener("click", clear);
  })();

  /* ── the headline types itself ──────────────────────────────────────
     Runs on arrival and again whenever the hero is scrolled back into
     view, so returning to the top replays it rather than finding it done. */
  (function(){
    var hero = document.getElementById("hero"), out = document.getElementById("typed");
    if (!hero || !out) return;
    var TEXT = "Verify like a\nclinician.", timers = [], typing = false;

    function paint(n){
      out.innerHTML = "";
      TEXT.slice(0, n).split("\n").forEach(function(line, i){
        if (i) out.appendChild(document.createElement("br"));
        out.appendChild(document.createTextNode(line));
      });
    }
    function done(){ typing = false; hero.dataset.typed = "true"; }

    function type(){
      if (typing) return;
      typing = true;
      timers.forEach(clearTimeout); timers = [];
      hero.dataset.typed = "false";
      paint(0);
      var t = 260;
      for (var i = 1; i <= TEXT.length; i++) {
        /* a touch slower on the line break, and a beat before the full stop */
        var ch = TEXT[i - 1];
        t += ch === "\n" ? 190 : ch === "." ? 150 : 52;
        (function(n){ timers.push(setTimeout(function(){ paint(n); }, t)); })(i);
      }
      timers.push(setTimeout(done, t + 220));
    }

    if (reduce) { paint(TEXT.length); done(); return; }

    if ("IntersectionObserver" in window) {
      /* Never blank the headline on exit — a late-delivered "left the view"
         callback would then wipe it while it is back on screen. Exit only
         arms the replay; the clear happens inside type(), on the way in. */
      var armed = true;
      new IntersectionObserver(function(entries){
        entries.forEach(function(e){
          if (e.isIntersecting && e.intersectionRatio >= .45) {
            if (armed) { armed = false; type(); }
          } else if (e.intersectionRatio === 0) {
            armed = true;
          }
        });
      }, {threshold:[0, .45]}).observe(hero);
    } else type();
  })();

  /* ── rotating word ── */
  var words = [
    ["wrong doses", "#B0402D"],
    ["flipped denials", "#B4801F"],
    ["invented symptoms", "#5B5BD6"],
    ["missing allergies", "#17656A"],
    ["borrowed histories", "#3E8E6B"]
  ];
  var cyc = document.getElementById("cycler"), wi = 0;
  if (cyc && !reduce) {
    setInterval(function(){
      wi = (wi + 1) % words.length;
      cyc.style.opacity = 0;
      setTimeout(function(){
        cyc.textContent = words[wi][0];
        cyc.style.color = words[wi][1];
        cyc.style.opacity = 1;
      }, 260);
    }, 2600);
    cyc.style.transition = "opacity .26s ease, color .26s ease";
    cyc.style.color = words[0][1];
  }

  /* ── scroll-linked waves ──────────────────────────────────────────
     Scrolling down grows the crest upward, so the light layer flows over
     the chart; scrolling back up lets it fall away again. The svg is
     anchored bottom-centre, so growing it can never open a seam. */
  (function(){
    if (reduce) return;
    var mockStage = document.querySelector(".mock-stage");
    var waves = [].slice.call(document.querySelectorAll(".wave-wrap")).map(function(wrap){
      return {
        wrap: wrap,
        svg: wrap.querySelector("svg"),
        path: wrap.querySelector("path"),
        base: wrap.querySelector("path").getAttribute("d"),
        lead: wrap.classList.contains("light") ? 1 : 0,
        now: 0
      };
    });

    /* rebuild the crest with its control points nudged by `a` px */
    function shape(w, a){
      return w.lead
        ? "M0," + (96 - a) + " C210," + (150 - a * .4) + " 400," + (30 + a * .7) + " 640," + (52 - a * .5) +
          " C880," + (74 + a * .6) + " 1080," + (132 - a * .3) + " 1440," + (66 - a) + " L1440,150 L0,150 Z"
        : "M0," + (70 - a) + " C300," + (20 + a * .6) + " 520," + (120 - a * .4) + " 780," + (88 - a * .6) +
          " C1030," + (58 + a * .5) + " 1220," + (10 + a * .7) + " 1440," + (58 - a) + " L1440,130 L0,130 Z";
    }

    function frame(){
      var vh = window.innerHeight;
      waves.forEach(function(w){
        var r = w.wrap.getBoundingClientRect();
        /* 0 while the crest is still below the fold, 1 once it has risen past it */
        var p = (vh - r.top) / (vh * .85);
        p = p < 0 ? 0 : p > 1 ? 1 : p;
        p = p * p * (3 - 2 * p);                    /* ease, so it settles rather than tracks 1:1 */
        w.now += (p - w.now) * .12;                 /* lag behind the scroll — this is the "flow" */
        if (Math.abs(p - w.now) < .0005) w.now = p;

        w.svg.style.transform = "scaleY(" + (1 + w.now * 1.15) + ")";
        w.path.setAttribute("d", shape(w, 26 * Math.sin(w.now * Math.PI)));

        /* the chart sinks as the crest climbs over it */
        if (w.lead && mockStage) mockStage.style.transform = "translateY(" + (w.now * 62) + "px)";
      });
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  })();

  /* ── the flow film ─────────────────────────────────────────────────
     The film carries the eight nodes; the track under it is the index.
     Playhead drives the chips, chips drive the playhead. */
  (function(){
    var NODES = [
      {n:0, tag:"input",  title:"Transcript in",              desc:"The encounter recording is the ground truth everything downstream is checked against — never another model's opinion."},
      {n:1, tag:"draft",  title:"Draft the note",             desc:"Stands in for whatever ambient scribe a clinic already runs. Routed through a failover chain so one outage can't take it down."},
      {n:2, tag:"split",  title:"Extract atomic claims",      desc:"You can't reliably verify a whole note at once; you can verify one fact at a time. Decomposition happens before any judgment."},
      {n:3, tag:"check",  title:"Entailment, claim by claim", desc:"Supported, contradicted, or not mentioned — one verdict per claim, each with a quoted excerpt. A count mismatch raises an error."},
      {n:"3b", tag:"source", title:"Is the transcript itself trustworthy?", desc:"Only on audio runs. Every verdict above assumed the transcript was ground truth — but a transcript from a recogniser is a model output too. Claims resting on audio the recogniser was unsure of come back unverifiable, with a timestamp.", kind:"audio"},
      {n:4, tag:"exact",  title:"Deterministic numeric check",desc:"Doses and vitals don't need judgment, they need an exact match. Plain Python regex on the highest-severity category there is.", kind:"exact"},
      {n:5, tag:"mirror", title:"Omission check",             desc:"The mirror image: extract facts from the transcript, then ask whether each appears in the note. Nothing else can see what's missing."},
      {n:6, tag:"label",  title:"Classify each flag",         desc:"A flag names which of the six categories it is, not just “this seems wrong.” A fixed taxonomy keeps it auditable."},
      {n:7, tag:"sign",   title:"Human review checkpoint",    desc:"Required, not optional. Every flag is a suggestion with its evidence attached, and a person decides. Nothing is edited automatically.", kind:"human"}
    ];

    var video = document.getElementById("flowVideo");
    if (!video) return;
    var track = document.getElementById("filmTrack"),
        titleEl = document.getElementById("filmTitle"),
        descEl = document.getElementById("filmDesc"),
        playBtn = document.getElementById("filmPlay"),
        active = -1;

    NODES.forEach(function(node, i){
      var chip = document.createElement("button");
      chip.className = "film-chip";
      chip.type = "button";
      if (node.kind) chip.dataset.kind = node.kind;
      chip.innerHTML = "<b>" + node.n + "</b><i>" + node.tag + "</i>";
      chip.setAttribute("aria-label", "Node " + node.n + ": " + node.title);
      chip.addEventListener("click", function(){
        show(i);
        restartTicker();                                  /* a fresh full hold on the node you picked */
        if (video.paused) video.play().catch(function(){});
      });
      track.appendChild(chip);
    });
    var chips = [].slice.call(track.children);

    var nowEl = document.querySelector(".film-now"), swapT;
    function show(i){
      if (i === active) return;
      active = i;
      chips.forEach(function(c, ci){ c.setAttribute("aria-current", String(ci === i)); });
      /* fade the caption out, swap, fade back — a hard cut at this pace reads as a glitch */
      nowEl.dataset.swap = "true";
      clearTimeout(swapT);
      swapT = setTimeout(function(){
        titleEl.textContent = NODES[i].title;
        descEl.textContent = NODES[i].desc;
        nowEl.dataset.swap = "false";
      }, reduce ? 0 : 300);
    }

    /* The film plays at its own natural speed and loops. The node timeline is
       driven separately, on its own timer, so a caption can hold far longer
       than a 6s clip allows — slowing the footage itself made it judder. */
    var HOLD = 4500, tick = null;
    function step(){ show((active + 1) % NODES.length); }
    function startTicker(){ if (!tick && !video.paused) tick = setInterval(step, HOLD); }
    function stopTicker(){ clearInterval(tick); tick = null; }
    function restartTicker(){ stopTicker(); startTicker(); }

    video.playbackRate = 1;
    track.style.setProperty("--seg", (HOLD / 1000) + "s");

    function setPlayLabel(){
      playBtn.textContent = video.paused ? "▶" : "❚❚";
      playBtn.setAttribute("aria-label", video.paused ? "Play the film" : "Pause the film");
    }
    playBtn.addEventListener("click", function(){
      if (video.paused) video.play().catch(function(){}); else video.pause();
      setPlayLabel();
    });
    /* pausing the film pauses the captions too — otherwise they'd march on
       over a frozen frame */
    video.addEventListener("play", function(){ setPlayLabel(); startTicker(); });
    video.addEventListener("pause", function(){ setPlayLabel(); stopTicker(); });

    /* don't burn a timer while the section is off screen */
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function(entries){
        entries.forEach(function(e){
          if (e.isIntersecting) { if (!video.paused) startTicker(); }
          else stopTicker();
        });
      }, {threshold:.15}).observe(track.parentNode);
    }

    show(0);
    if (reduce) { video.pause(); setPlayLabel(); }
    else video.play().then(function(){ setPlayLabel(); startTicker(); }).catch(setPlayLabel);
  })();

  /* ── demo ── */
  var CLAIMS = [
    {id:"c1", text:"Patient reports feeling well since medication adjustment", verdict:"supported", ev:"Pretty good, actually."},
    {id:"c2", text:"Denies headaches, dizziness, cough, leg swelling", verdict:"supported", ev:"No, nothing like that."},
    {id:"c3", text:"Lisinopril dose is 20 mg once daily", verdict:"contradicted", ev:"the lisinopril 10 milligrams once a day"},
    {id:"c4", text:"Blood pressure 128/82", verdict:"supported", ev:"it's reading 128 over 82"},
    {id:"c5", text:"Hypertension well-controlled", verdict:"supported", ev:"That's a nice improvement from last visit."},
    {id:"c6", text:"Return in 3 months for recheck", verdict:"supported", ev:"come back in three months for a recheck"}
  ];
  var STEPS = ["2 · extract claims","3 · entailment","4 · numeric check","5 · omission","6 · classify","7 · your review"];

  var stepsEl = document.getElementById("pipeSteps"),
      resultEl = document.getElementById("demoResult"),
      btnRun = document.getElementById("btnRun"),
      btnReset = document.getElementById("btnReset"),
      btnBaseline = document.getElementById("btnBaseline"),
      baselineBox = document.getElementById("baselineBox"),
      timers = [], running = false, decided = null;
  if (stepsEl && resultEl && btnRun) {

  function renderSteps(active){
    stepsEl.innerHTML = "";
    STEPS.forEach(function(label, i){
      var s = document.createElement("span");
      s.className = "pstep";
      s.textContent = label;
      if (active > i) s.dataset.on = "done";
      else if (active === i) s.dataset.on = "run";
      stepsEl.appendChild(s);
    });
  }
  function clearTimers(){ timers.forEach(clearTimeout); timers = []; }
  function setLine(id, state){
    var line = document.querySelector('.note-line[data-claim="' + id + '"]');
    if (!line) return;
    line.dataset.state = state;
    var old = line.querySelector(".verdict");
    if (old) old.remove();
    if (state === "checking" || state === "ok" || state === "flag") {
      var v = document.createElement("span");
      v.className = "verdict " + (state === "flag" ? "v-flag" : state === "ok" ? "v-ok" : "v-run");
      v.textContent = state === "flag" ? "contradicted" : state === "ok" ? "supported" : "checking…";
      line.insertBefore(v, line.firstChild);
    }
  }
  function markEvidence(id, hot){
    document.querySelectorAll("mark.ev").forEach(function(m){ m.classList.remove("hot"); });
    var m = document.querySelector('mark.ev[data-ev="' + id + '"]');
    if (m && hot) m.classList.add("hot");
  }
  function reset(quiet){
    clearTimers(); running = false; decided = null;
    document.querySelectorAll(".note-line").forEach(function(l){ l.removeAttribute("data-state"); var v = l.querySelector(".verdict"); if (v) v.remove(); });
    document.querySelectorAll("mark.ev").forEach(function(m){ m.classList.remove("hot"); });
    stepsEl.innerHTML = "";
    resultEl.innerHTML = '<p class="empty">Nothing checked yet. Press <b>Run the check</b> to decompose the note and verify each claim against the transcript.</p>';
    btnRun.disabled = false; btnRun.textContent = "Run the check";
    if (!quiet) toast("Demo reset.");
  }
  function flagCard(){
    resultEl.innerHTML =
      '<div class="flagcard">' +
        '<div class="flag-top"><span class="sev">Critical</span><span class="cat mono">numeric_medication_error · claim 3 of 6</span></div>' +
        '<div class="flag-q">The note says 20 mg. The transcript says 10 mg.</div>' +
        '<div class="corro"><span>node 3 · entailment: contradicted</span><span>node 4 · regex: 20 ≠ 10</span><span>node 5 · “10 milligrams” never appears in the note</span></div>' +
        '<div class="evrow">Transcript, verbatim: “Are you still taking the <b>lisinopril 10 milligrams</b> once a day?” — Patient: “Yes, every morning with breakfast.”</div>' +
        '<div class="decide">' +
          '<button class="btn-sm" id="btnConfirm">Confirm — dose is wrong</button>' +
          '<button class="btn-sm ghost" id="btnDismiss">Dismiss — note is fine</button>' +
          '<span class="decide-note">Your call. The note is not edited either way.</span>' +
        '</div>' +
      '</div>';
    document.getElementById("btnConfirm").addEventListener("click", function(){ decide("confirmed"); });
    document.getElementById("btnDismiss").addEventListener("click", function(){ decide("dismissed"); });
  }
  function decide(what){
    if (decided) return;
    decided = what;
    var time = new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
    var strip = document.createElement("div");
    strip.className = "done-strip";
    strip.innerHTML = what === "confirmed"
      ? "<span>✓</span><span>Flag confirmed at " + time + ". Routed back for correction before signing — nothing was changed automatically.</span>"
      : "<span>✓</span><span>Flag dismissed at " + time + ". Recorded with your name against it; the note is untouched.</span>";
    resultEl.querySelector(".decide").replaceWith(strip);
    renderSteps(STEPS.length);
    toast(what === "confirmed" ? "Flag confirmed. Node 7 is you." : "Flag dismissed and logged.");
  }
  function run(){
    if (running) return;
    reset(true);
    running = true;
    btnRun.disabled = true; btnRun.textContent = "Checking…";
    resultEl.innerHTML = '<p class="empty">Decomposing the note into atomic claims…</p>';

    var t = 0, gap = reduce ? 60 : 430;
    renderSteps(0);
    timers.push(setTimeout(function(){ renderSteps(1); }, gap));

    CLAIMS.forEach(function(c, i){
      t = gap * (i + 1.4);
      timers.push(setTimeout(function(){
        setLine(c.id, "checking");
        markEvidence(c.id, c.verdict === "contradicted");
      }, t));
      timers.push(setTimeout(function(){
        setLine(c.id, c.verdict === "contradicted" ? "flag" : "ok");
        if (c.verdict === "contradicted") renderSteps(2);
      }, t + gap * .66));
    });

    var end = gap * (CLAIMS.length + 2);
    timers.push(setTimeout(function(){ renderSteps(3); }, end));
    timers.push(setTimeout(function(){ renderSteps(4); }, end + gap));
    timers.push(setTimeout(function(){
      renderSteps(5);
      flagCard();
      markEvidence("c3", true);
      running = false;
      btnRun.disabled = false; btnRun.textContent = "Run again";
    }, end + gap * 2));
  }

  btnRun.addEventListener("click", run);
  btnReset.addEventListener("click", function(){ reset(false); });
  btnBaseline.addEventListener("click", function(){
    var on = btnBaseline.getAttribute("aria-pressed") === "true";
    btnBaseline.setAttribute("aria-pressed", on ? "false" : "true");
    baselineBox.hidden = on;
    if (!on) baselineBox.scrollIntoView({block:"nearest", behavior: reduce ? "auto" : "smooth"});
  });

  /* hovering a note line lights up its transcript evidence */
  document.querySelectorAll(".note-line").forEach(function(line){
    line.addEventListener("mouseenter", function(){
      if (running) return;
      var id = line.dataset.claim;
      markEvidence(id, line.dataset.state === "flag");
      var m = document.querySelector('mark.ev[data-ev="' + id + '"]');
      if (m && !m.classList.contains("hot")) m.classList.add("hot");
    });
  });

  /* any "run the demo" link scrolls here and starts it */
  document.querySelectorAll("[data-run-demo]").forEach(function(a){
    a.addEventListener("click", function(){ setTimeout(run, reduce ? 0 : 620); });
  });

  }   /* end demo guard */

  /* ── metrics ── */
  var METRICS = {
    recall:{pipe:[88,"45/51"], base:[76,"39/51"], note:"Planted errors caught across 60 synthetic cases. Six more catches out of 51 — on a benchmark three times the size of the first run, which is what moved this from a suggestive gap to a usable one."},
    severity:{pipe:[92,"92%"], base:[83,"83%"], note:"Weighted toward numeric/medication and negation errors — the two categories where a small text change carries the largest clinical consequence."},
    fp:{pipe:[15,"15"], base:[11,"11"], note:"False positives raised on the 6 clean control notes. The pipeline raises more, and that is the honest cost of decomposition: more claims checked means more chances to flag something fine. A reviewer reads every flag either way."}
  };
  var barPipe = document.getElementById("barPipe"), barBase = document.getElementById("barBase"),
      valPipe = document.getElementById("valPipe"), valBase = document.getElementById("valBase"),
      metricNote = document.getElementById("metricNote"),
      metricBtns = [].slice.call(document.querySelectorAll("[data-metric]"));

  function showMetric(key){
    if (!barPipe || !barBase || !metricNote) return;
    var m = METRICS[key], scale = key === "fp" ? 20 : 100;
    barPipe.style.width = (m.pipe[0] / scale * 100) + "%";
    barBase.style.width = (m.base[0] / scale * 100) + "%";
    valPipe.textContent = m.pipe[1];
    valBase.textContent = m.base[1];
    metricNote.textContent = m.note;
    metricBtns.forEach(function(b){ b.setAttribute("aria-pressed", String(b.dataset.metric === key)); });
  }
  metricBtns.forEach(function(b){ b.addEventListener("click", function(){ showMetric(b.dataset.metric); }); });
  showMetric("recall");

  /* animate the bars in when the section first appears */
  if ("IntersectionObserver" in window) {
    var seen = false;
    var barsEl = document.getElementById("bars");
    if (barsEl) new IntersectionObserver(function(entries, obs){
      entries.forEach(function(e){
        if (e.isIntersecting && !seen) { seen = true; showMetric("recall"); obs.disconnect(); }
      });
    }, {threshold:.3}).observe(barsEl);
  }

  /* ── taxonomy cards ── */
  document.querySelectorAll("#taxgrid .tax").forEach(function(card){
    card.addEventListener("click", function(){
      var open = card.getAttribute("aria-expanded") === "true";
      document.querySelectorAll("#taxgrid .tax").forEach(function(c){ c.setAttribute("aria-expanded","false"); });
      card.setAttribute("aria-expanded", open ? "false" : "true");
    });
  });
})();
