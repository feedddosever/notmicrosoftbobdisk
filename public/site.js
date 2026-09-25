/*
 * SheetShift site shell: shared chrome plus the renderers for the overview (/),
 * certificate and replay pages. It reads only same-origin files in data/ (written by
 * tools/build_site_data.py) and never makes an external request.
 *
 * Bob's trace.js and verify.js own the #trace-* and #verify-* regions (see the
 * "Site DOM contract" in docs/CONTRACT.md). They may use the helpers on window.SheetShift,
 * but they do not have to.
 *
 * Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
 */
(function () {
  "use strict";

  var SS = (window.SheetShift = window.SheetShift || {});
  var DEFAULT_SERVICE = "service.sheetshift_ho3.rater";
  var NOT_GENERATED = "Not generated yet. Run make certify, then make site.";
  var cache = {};

  // ------------------------------------------------------------------ helpers
  /** Fetch data/<name> as JSON. Resolves to null when missing or unreadable. */
  SS.loadJSON = function (name) {
    if (!cache[name]) {
      cache[name] = fetch("data/" + name, { cache: "no-cache" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; });
    }
    return cache[name];
  };

  /** Create an element. attrs: {class, href, id, text, ...}; children: nodes or strings. */
  SS.el = function (tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "text") node.textContent = String(v);
      else if (k === "class") node.className = v;
      else node.setAttribute(k, v === true ? "" : String(v));
    });
    (children || []).forEach(function (c) {
      if (c === null || c === undefined) return;
      node.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    });
    return node;
  };
  var el = SS.el;

  SS.fmtInt = function (n) {
    return typeof n === "number" && isFinite(n) ? Math.round(n).toLocaleString("en-US") : "–";
  };
  SS.fmtPct = function (x, digits) {
    return typeof x === "number" && isFinite(x) ? (x * 100).toFixed(digits === undefined ? 1 : digits) + "%" : "–";
  };
  SS.empty = function (msg) { return el("p", { class: "empty", text: msg || NOT_GENERATED }); };

  /** GitHub link for a repo path (optionally a line) at the built commit; null if no repo URL. */
  SS.githubUrl = function (site, path, line) {
    if (!site || !site.repo_url || !path || path.indexOf("<") === 0) return null;
    var ref = site.commit || "HEAD";
    return site.repo_url + "/blob/" + ref + "/" + path.replace(/^\/+/, "") + (line ? "#L" + line : "");
  };
  SS.commitUrl = function (site, sha) {
    return site && site.repo_url && sha ? site.repo_url + "/commit/" + sha : null;
  };
  /** A link when a URL exists, else the text in <code>. */
  SS.linkOr = function (url, text) {
    return url ? el("a", { href: url, text: text }) : el("code", { text: text });
  };

  function clear(node) { while (node && node.firstChild) node.removeChild(node.firstChild); return node; }
  function $(id) { return document.getElementById(id); }
  function fill(id, nodes) {
    var node = $(id);
    if (!node) return;
    clear(node);
    (Array.isArray(nodes) ? nodes : [nodes]).forEach(function (n) { if (n) node.appendChild(n); });
  }

  /** Cells decided: accepts a number or {total, by_decision}. */
  function decidedTotal(d) {
    if (typeof d === "number") return d;
    if (d && typeof d.total === "number") return d.total;
    if (d && d.by_decision) return Object.keys(d.by_decision).reduce(function (s, k) { return s + (d.by_decision[k] || 0); }, 0);
    return 0;
  }
  function signedDecisions(cert, log) {
    var rows = (log && log.log) || [];
    if (rows.length) return rows.length;
    var list = (cert && cert.decisions) || [];
    return list.filter(function (d) { return d && d.by && d.option; }).length;
  }
  SS.headlineNumbers = function (cert, decisions) {
    var o = (cert && cert.original) || {};
    return {
      C: o.cells_compared, E: o.cells_equal, D: decidedTotal(o.decided_cells),
      A: signedDecisions(cert, decisions), U: o.unexplained_cells,
      roots: o.root_cells_explaining_all_diffs
    };
  };

  function statusBadge(status) {
    var s = String(status || "pending").toUpperCase();
    var cls = s === "GREEN" ? "green" : s === "RED" ? "red" : "pending";
    return el("span", { class: "badge " + cls, text: s });
  }

  // ------------------------------------------------------------------ chrome
  function markNav() {
    var page = document.body.getAttribute("data-page");
    document.querySelectorAll(".site-nav a").forEach(function (a) {
      if (a.getAttribute("data-page") === page) a.setAttribute("aria-current", "page");
    });
  }

  /** One banner line about the API, stated only from what this page can check. */
  function apiStatus(site, line) {
    if (site && site.mode === "static") {
      line.textContent = "Precomputed results from commit " + (site.commit_short || "unknown") +
        "; the API is not connected here.";
      return;
    }
    var unavailable = function () { line.textContent = "The quote API is unavailable right now; results shown are precomputed."; };
    fetch("/api/health", { cache: "no-cache" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (body) {
        if (!body) { unavailable(); return; }
        if (body.status === "stub") { line.textContent = "The quote API is not deployed yet; results shown are precomputed."; return; }
        return fetch("trace.js", { method: "HEAD", cache: "no-cache" })
          .then(function (r) { return r.ok; }, function () { return false; })
          .then(function (trace) {
            line.textContent = "The quote API and spot-check are live" + (trace ? ", and so is traceability." : ".");
          });
      })
      .catch(unavailable);
  }

  function chrome(site, cert) {
    var banner = $("site-banner");
    if (banner) {
      clear(banner);
      var rec = site && site.recorded;
      if (rec && rec.first) {
        var when = rec.first === rec.last ? rec.first : rec.first + " to " + rec.last;
        var sources = site.exports_available === true ? "task exports and hook logs" : "hook logs";
        banner.appendChild(el("p", { text: "The Bob run was recorded on " + when + " and is replayed from " + sources + "." }));
      }
      var line = el("p", { text: "Checking the API..." });
      banner.appendChild(line);
      banner.appendChild(el("p", { text: "No Bob key is deployed." }));
      apiStatus(site, line);
    }
    var standin = $("standin-notice");
    var svc = (cert && cert.service) || (site && site.service && site.service.module);
    if (standin && svc && svc !== DEFAULT_SERVICE) {
      standin.hidden = false;
      clear(standin).appendChild(el("p", {}, [el("strong", { text: "Stand-in service. " }),
        "These numbers were produced with ", el("code", { text: svc }),
        ", a stand-in used to test the harness. They are not results of IBM Bob's service."]));
    }
    var foot = $("build-commit");
    if (foot && site && site.commit_short) {
      clear(foot).appendChild(SS.linkOr(SS.commitUrl(site, site.commit), site.commit_short));
    }
  }

  /** verify.html / trace.html: say so if Bob's page script is not deployed yet. */
  function checkPageScript(name, noticeId) {
    var notice = $(noticeId);
    if (!notice) return;
    fetch(name, { method: "HEAD", cache: "no-cache" })
      .then(function (r) { notice.hidden = r.ok; })
      .catch(function () { notice.hidden = false; });
  }

  // ------------------------------------------------------------------ overview (/)
  function renderHeadline(cert, decisions) {
    var box = $("headline");
    if (!box) return;
    if (!cert || !cert.original) { fill("headline", SS.empty()); return; }
    var h = SS.headlineNumbers(cert, decisions);
    clear(box);
    box.appendChild(el("p", { class: "headline" }, [
      el("strong", { text: SS.fmtInt(h.C) }), " cells compared: ",
      el("strong", { text: SS.fmtInt(h.E) }), " identical to the workbook, ",
      el("strong", { text: SS.fmtInt(h.D) }), " differing only in rows traced to ",
      el("strong", { text: SS.fmtInt(h.A) }), " human-signed decision" + (h.A === 1 ? "" : "s") + ", ",
      el("strong", { text: SS.fmtInt(h.U) }), " unexplained."
    ]));
    var bar = el("div", { class: "recon-bar", role: "img",
      "aria-label": "Identical " + SS.fmtInt(h.E) + ", decided " + SS.fmtInt(h.D) + ", unexplained " + SS.fmtInt(h.U) });
    [["equal", h.E], ["decided", h.D], ["unexplained", h.U]].forEach(function (p) {
      var span = el("span", { class: p[0] });
      span.style.width = h.C ? (100 * (p[1] || 0) / h.C) + "%" : "0";
      bar.appendChild(span);
    });
    box.appendChild(bar);
    box.appendChild(el("ul", { class: "legend" }, [
      el("li", { class: "equal", text: "Identical" }), el("li", { class: "decided", text: "Decided by a person" }),
      el("li", { class: "unexplained", text: "Unexplained" })
    ]));
    var meta = el("p", { class: "status-line" }, [
      "Certificate ", statusBadge(cert.status), " · seed ", String(cert.seed), " · ",
      SS.fmtInt(cert.policies) + " policies (" + SS.fmtInt(cert.boundary_policies) + " boundary) · ",
      "oracle: " + ((cert.oracle && cert.oracle.label) || "–")
    ]);
    box.appendChild(meta);
    if (cert.patched) {
      box.appendChild(el("p", { class: "status-line" }, [
        "Decision-patched workbook: " + SS.fmtInt(cert.patched.cells_equal) + " of " +
        SS.fmtInt(cert.patched.cells_compared) + " cells identical, " +
        SS.fmtInt(cert.patched.unexplained_cells) + " unexplained."]));
    } else {
      box.appendChild(el("p", { class: "status-line", text: "Decision-patched comparison: not run yet (no signed decisions)." }));
    }
    if (cert.status && String(cert.status).toUpperCase() !== "GREEN" && (cert.status_reasons || []).length) {
      box.appendChild(el("ul", { class: "plain-list status-line" }, cert.status_reasons.map(function (r) {
        return el("li", { text: typeof r === "string" ? r : JSON.stringify(r) });
      })));
    }
  }

  function stat(value, label, source) {
    return el("div", { class: "stat" }, [
      el("span", { class: "value", text: value }), el("span", { class: "label", text: label }),
      source ? el("span", { class: "source" }, [el("a", { href: source, text: "source" })]) : null
    ]);
  }

  function renderMeasures(cert, baseline) {
    var mut = cert && cert.mutation;
    fill("measure-mutation", mut && mut.total ? [
      stat(SS.fmtInt(mut.killed) + " of " + SS.fmtInt(mut.total), "mutants of the service caught by the harness", "data/mutation.json"),
      mut.stale ? el("p", { class: "status-line", text: "Mutation report is from an earlier service tree; rerun make mutate." }) : null
    ] : SS.empty("Mutation self-test not run yet."));

    var nb = cert && cert.naive_baseline && cert.naive_baseline.naive_round;
    var sp = cert && cert.spotcheck && cert.spotcheck.naive_baseline && cert.spotcheck.naive_baseline.naive_round;
    fill("measure-spotcheck", nb && sp ? [
      stat(SS.fmtPct(1 - sp.p_detect_20, 1), "chance that a 20-quote spot check misses naive rounding", "data/spotcheck.json"),
      el("p", { class: "status-line", text: "Naive Python round() changes " + SS.fmtInt(nb.rows_affected) + " of " + SS.fmtInt(cert.policies) + " quotes." })
    ] : SS.empty("Spot-check not computed yet."));

    fill("measure-time", baseline && baseline.hand_minutes ? [
      stat(baseline.hand_minutes + " min vs " + (baseline.bob_minutes === undefined ? "–" : baseline.bob_minutes) + " min",
        "unit " + (baseline.unit || "?") + " translated by hand vs with Bob (n = " + (baseline.n || 1) + ")", "data/baseline.json")
    ] : SS.empty("Hand-translation baseline not measured yet."));

    var tr = cert && cert.traceability;
    fill("measure-trace", tr && tr.counts ? [
      stat(SS.fmtInt(tr.counts.covered) + " of " + SS.fmtInt(tr.total_rules), "workbook rules traced to a service function", "trace.html"),
      el("p", { class: "status-line", text: SS.fmtInt(tr.counts.out_of_scope) + " declared out of scope, " +
        SS.fmtInt(tr.counts.uncovered) + " uncovered; gate " + String(tr.gate || "–").toUpperCase() + "." })
    ] : SS.empty("Traceability not generated yet."));
  }

  function renderLimits(cert) {
    var list = $("limits-from-certificate");
    if (!list || !cert || !(cert.limits || []).length) return;
    clear(list);
    cert.limits.forEach(function (l) {
      list.appendChild(el("li", { text: typeof l === "string" ? l : (l.text || l.limit || JSON.stringify(l)) }));
    });
    var fallback = $("limits-static");
    if (fallback) fallback.hidden = true;
    list.hidden = false;
  }

  // ------------------------------------------------------------------ certificate page
  function kv(pairs) {
    var dl = el("dl", { class: "kv" });
    pairs.forEach(function (p) {
      dl.appendChild(el("dt", { text: p[0] }));
      dl.appendChild(el("dd", {}, [p[1] === null || p[1] === undefined ? "–" : (p[1].nodeType ? p[1] : String(p[1]))]));
    });
    return dl;
  }

  function table(headers, rows, numeric) {
    numeric = numeric || [];
    var thead = el("thead", {}, [el("tr", {}, headers.map(function (h, i) {
      return el("th", { class: numeric.indexOf(i) >= 0 ? "num" : null, scope: "col", text: h });
    }))]);
    var tbody = el("tbody", {}, rows.map(function (r) {
      return el("tr", {}, r.map(function (c, i) {
        var cls = numeric.indexOf(i) >= 0 ? "num" : null;
        return el("td", { class: cls }, [c === null || c === undefined ? "–" : (c.nodeType ? c : String(c))]);
      }));
    }));
    return el("div", { class: "table-wrap" }, [el("table", {}, [thead, tbody])]);
  }

  function renderCertificate(site, cert, decisions, lints, mutation) {
    if (!cert) {
      ["cert-identity", "cert-original", "cert-groups", "cert-mutation", "cert-spotcheck", "cert-hashes", "cert-limits"]
        .forEach(function (id) { fill(id, SS.empty()); });
    } else {
      var o = cert.original || {}, p = cert.patched;
      fill("cert-identity", [el("p", {}, ["Status ", statusBadge(cert.status)]), kv([
        ["Run ID", cert.run_id], ["Service", el("code", { text: cert.service || "–" })], ["Seed", cert.seed],
        ["Policies", SS.fmtInt(cert.policies)], ["Boundary policies", SS.fmtInt(cert.boundary_policies)],
        ["Lint-guided rows", (cert.lint_guided_rows || []).map(function (r) { return typeof r === "object" ? (r.row || JSON.stringify(r)) : r; }).join(", ") || "–"],
        ["Oracle", (cert.oracle && cert.oracle.label) || "–"],
        ["Recalculation", (cert.oracle && cert.oracle.recalc) || "–"],
        ["Excel cross-check", cert.excel_crosscheck ? JSON.stringify(cert.excel_crosscheck) : "not run (Excel parity is unverified)"],
        ["Git commit", SS.linkOr(SS.commitUrl(site, cert.git_commit && cert.git_commit !== "HEAD" ? cert.git_commit : null), cert.git_commit || "–")]
      ]), (cert.status_reasons || []).length ? el("ul", { class: "plain-list" }, cert.status_reasons.map(function (r) {
        return el("li", { text: typeof r === "string" ? r : JSON.stringify(r) });
      })) : null]);

      var byDec = (o.decided_cells && o.decided_cells.by_decision) || {};
      fill("cert-original", table(["Comparison", "Cells compared", "Identical", "Decided", "Unexplained", "Root cells"], [
        ["Original workbook", SS.fmtInt(o.cells_compared), SS.fmtInt(o.cells_equal), SS.fmtInt(decidedTotal(o.decided_cells)),
          SS.fmtInt(o.unexplained_cells), SS.fmtInt(o.root_cells_explaining_all_diffs)],
        ["Decision-patched workbook", p ? SS.fmtInt(p.cells_compared) : "not run", p ? SS.fmtInt(p.cells_equal) : "–", "–",
          p ? SS.fmtInt(p.unexplained_cells) : "–", "–"]
      ], [1, 2, 3, 4, 5]));
      if (Object.keys(byDec).length) {
        $("cert-original").appendChild(el("p", { class: "status-line", text: "Decided cells by decision: " +
          Object.keys(byDec).sort().map(function (k) { return k + " " + SS.fmtInt(byDec[k]); }).join(", ") }));
      }

      var rows = [];
      Object.keys(cert.groups_by_class || {}).sort().forEach(function (cls) {
        (cert.groups_by_class[cls] || []).forEach(function (g) {
          rows.push([g.id, el("span", { class: "badge " + (cls === "decided" ? "decided" : cls.indexOf("bug") >= 0 ? "red" : "warn"), text: cls }),
            el("code", { text: g.cell || "–" }), SS.fmtInt(g.rows), SS.fmtInt(g.cells), g.lint || "–", g.decision || "–", g.signature || "–"]);
        });
      });
      fill("cert-groups", rows.length ? table(["Group", "Class", "Root", "Rows", "Cells", "Lint", "Decision", "Signature"], rows, [3, 4])
        : el("p", { text: "No mismatch groups: every compared cell is identical." }));
      if ((cert.static_only_anomalies || []).length) {
        $("cert-groups").appendChild(el("p", { class: "status-line", text: "Static-only anomalies (found by the lint, not seen at runtime): " +
          cert.static_only_anomalies.map(function (a) { return a.id || JSON.stringify(a); }).join(", ") }));
      }

      var m = cert.mutation;
      var survivors = (mutation && mutation.survivors) || (m && m.survivors) || [];
      fill("cert-mutation", m ? [
        kv([["Caught", SS.fmtInt(m.killed) + " of " + SS.fmtInt(m.total) + " (" + SS.fmtPct(m.catch_rate) + ")"],
          ["Caught using boundary rows", SS.fmtInt(m.caught_using_boundary_rows)],
          ["Caught using random rows", SS.fmtInt(m.caught_using_random_rows)],
          ["Caught only by boundary rows", (m.caught_only_by_boundary_rows || []).length],
          ["Report matches this service tree", m.stale ? "no (rerun make mutate)" : "yes"],
          ["Control run (unmutated copy)", m.status === "ok" ? "matched the service" : "INVALID: the counts above are not meaningful"]]),
        el("h3", { class: "section", text: "Survivors (never hidden)" }),
        survivors.length ? table(["Mutant", "Operator", "Where", "Change", "Label"], survivors.map(function (s) {
          return [s.id, s.op, SS.linkOr(SS.githubUrl(site, s.file, s.line), (s.file || "?") + ":" + (s.line || "?")), s.change, s.label || "unlabelled"];
        })) : el("p", { text: "No surviving mutants." }),
        el("h3", { class: "section", text: "Naive translations (the opening number)" }),
        cert.naive_baseline ? table(["Operator", "Quotes affected", "Cells affected", "Boundary rows", "Method"],
          Object.keys(cert.naive_baseline).filter(function (k) { return typeof cert.naive_baseline[k] === "object"; }).sort().map(function (k) {
            var n = cert.naive_baseline[k];
            return [el("code", { text: k }), SS.fmtInt(n.rows_affected), SS.fmtInt(n.cells_affected), SS.fmtInt(n.boundary_rows), n.method || "–"];
          }), [1, 2, 3]) : SS.empty()
      ] : SS.empty("Mutation self-test not run yet."));

      var sp = cert.spotcheck;
      fill("cert-spotcheck", sp ? [
        el("p", { text: "Chance that 20 randomly chosen quotes show each problem at least once: p = 1 − (1 − rows/N)^20." }),
        table(["Problem", "Quotes affected", "Found by a 20-quote spot check", "Missed"],
          (sp.groups || []).map(function (g) { return [g.id + " " + (g.cell || ""), SS.fmtInt(g.rows), SS.fmtPct(g.p_detect_20), SS.fmtPct(1 - g.p_detect_20)]; })
            .concat(Object.keys(sp.naive_baseline || {}).sort().map(function (k) {
              var n = sp.naive_baseline[k];
              return [k, SS.fmtInt(n.rows), SS.fmtPct(n.p_detect_20), SS.fmtPct(1 - n.p_detect_20)];
            })), [1, 2, 3])
      ] : SS.empty("Spot-check not computed yet."));

      fill("cert-hashes", cert.hashes ? table(["Artefact", "SHA-256"], Object.keys(cert.hashes).sort().map(function (k) {
        return [k, el("span", { class: "hash", text: cert.hashes[k] || "–" })];
      })) : SS.empty());

      fill("cert-limits", (cert.limits || []).length ? el("ul", { class: "plain-list" }, cert.limits.map(function (l) {
        return el("li", { text: typeof l === "string" ? l : (l.text || JSON.stringify(l)) });
      })) : SS.empty());
    }

    // Decisions: queue (from the harness) and the signed log (from people).
    var queue = (decisions && decisions.queue) || [];
    var log = (decisions && decisions.log) || [];
    fill("cert-decisions", [
      log.length ? table(["Decision", "Cell", "Lint", "Option", "Manual rule", "By", "At", "Why"], log.map(function (d) {
        return [d.id, el("code", { text: d.cell || "–" }), d.lint, d.option, d.rule, d.by, d.at, d.why];
      })) : el("p", { class: "empty", text: "No decisions signed yet. A person signs each one with tools/decide.py." }),
      queue.length ? el("h3", { class: "section", text: "Decision queue" }) : null,
      queue.length ? table(["Decision", "Lint", "Type", "Cell", "Manual rule", "Allowed options", "Status", "Rows at runtime"], queue.map(function (q) {
        return [q.id, q.lint, q.type, el("code", { text: q.cell || "–" }), q.manual_rule, (q.options || []).join(", "),
          q.status, q.runtime ? SS.fmtInt(q.runtime.rows) : (q.static_only ? "static only" : "–")];
      })) : null
    ]);

    fill("cert-lints", lints && (lints.lints || []).length ? table(["Lint", "Type", "Cell", "Formula", "Column rule", "Manual rule"],
      lints.lints.map(function (l) {
        return [l.id, l.type, el("code", { text: l.cells || l.cell }), el("code", { text: l.formula }), el("code", { text: l.column_rule }), l.manual_rule];
      })) : SS.empty());
  }

  // ------------------------------------------------------------------ replay page
  var KIND_LABEL = {
    task: "Bob task", commit: "Commit", edit: "Edit", guard_block: "Guard blocked", guard_allow: "Guard allowed",
    smoke: "Smoke check", decision: "Human decision", note: "Note"
  };

  function eventNode(site, ev) {
    var links = [];
    if (ev.commit) links.push(SS.linkOr(SS.commitUrl(site, ev.commit), "commit " + ev.commit.slice(0, 7)));
    if (ev.screenshot) links.push(SS.linkOr(SS.githubUrl(site, ev.screenshot), "screenshot"));
    if (ev.export) links.push(SS.linkOr(SS.githubUrl(site, ev.export), "task export"));
    if (ev.path) links.push(SS.linkOr(SS.githubUrl(site, ev.path), ev.path));
    return el("li", { class: "kind-" + ev.kind }, [el("div", { class: "event" }, [
      el("div", { class: "meta", text: [ev.ts || "", ev.handle || "", ev.task || "", KIND_LABEL[ev.kind] || ev.kind].filter(Boolean).join(" · ") }),
      el("div", { text: ev.title || "" }),
      ev.detail ? el("div", { class: "meta", text: ev.detail }) : null,
      links.length ? el("div", { class: "links" }, links) : null
    ])]);
  }

  function renderReplayTasks(site, replay) {
    var tasks = (replay && replay.tasks) || [];
    fill("replay-tasks", tasks.length ? table(["Task", "Member", "Mode", "Subagents", "Commit", "Gauge", "Evidence", "Status"],
      tasks.map(function (t) {
        return [t.task, t.member, t.mode, t.subagents, t.commit ? SS.linkOr(SS.commitUrl(site, t.commit), t.commit.slice(0, 7)) : "–",
          (t.gauge_before || "–") + " → " + (t.gauge_after || "–"),
          el("span", {}, [t.screenshot ? SS.linkOr(SS.githubUrl(site, t.screenshot), "screenshot") : "–", " ",
            t.export ? SS.linkOr(SS.githubUrl(site, t.export), "export") : ""]), t.status];
      })) : SS.empty("bob_sessions/INDEX.md has no task rows yet."));
    var src = replay && replay.sources;
    if (src && $("replay-sources")) {
      fill("replay-sources", el("p", { class: "status-line", text: "Built from " + Object.keys(src).sort().map(function (k) {
        return k + " (" + src[k] + ")";
      }).join(", ") + "." }));
    }
  }

  function renderReplay(site, replay) {
    renderReplayTasks(site, replay);  // task table and sources show even with no events
    var list = $("replay-timeline");
    if (!list) return;
    var events = (replay && replay.events) || [];
    if (!events.length) {
      list.parentNode.replaceChild(SS.empty("No recorded Bob run yet. The timeline is built from audit logs, the run log, " +
        "bob_sessions/INDEX.md and commits once tasks have run."), list);
      var ctl = $("replay-controls");
      if (ctl) ctl.hidden = true;
      return;
    }
    var filter = $("replay-member");
    var handles = {};
    events.forEach(function (e) { if (e.handle) handles[e.handle] = true; });
    if (filter) {
      Object.keys(handles).sort().forEach(function (h) { filter.appendChild(el("option", { value: h, text: h })); });
    }
    var shown = [], pos = 0, timer = null;
    var status = $("replay-status");

    function draw() {
      var who = filter ? filter.value : "";
      shown = events.filter(function (e) { return !who || e.handle === who; });
      clear(list);
      shown.forEach(function (e) { list.appendChild(eventNode(site, e)); });
      pos = Math.min(pos, shown.length - 1);
      mark();
    }
    function mark() {
      var items = list.children;
      for (var i = 0; i < items.length; i++) {
        items[i].classList.toggle("future", i > pos);
        items[i].classList.toggle("current", i === pos);
      }
      if (status) status.textContent = "Event " + (pos + 1) + " of " + shown.length + (timer ? " (playing)" : "");
      var cur = items[pos];
      if (cur && timer && cur.scrollIntoView) cur.scrollIntoView({ block: "nearest" });
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; } setPlayLabel(); mark(); }
    function setPlayLabel() { var b = $("replay-play"); if (b) b.textContent = timer ? "Pause" : "Play from start"; }
    function play() {
      if (timer) { stop(); return; }
      pos = 0;
      var speed = Number(($("replay-speed") || {}).value || 1);
      timer = setInterval(function () {
        if (pos >= shown.length - 1) { stop(); return; }
        pos += 1; mark();
      }, 800 / speed);
      setPlayLabel(); mark();
    }
    function step(d) { stop(); pos = Math.max(0, Math.min(shown.length - 1, pos + d)); mark(); }

    var bind = function (id, fn) { var b = $(id); if (b) b.addEventListener("click", fn); };
    bind("replay-play", play);
    bind("replay-prev", function () { step(-1); });
    bind("replay-next", function () { step(1); });
    bind("replay-end", function () { stop(); pos = shown.length - 1; mark(); });
    if (filter) filter.addEventListener("change", function () { stop(); pos = Infinity; draw(); });
    pos = events.length - 1;
    draw();
  }

  // ------------------------------------------------------------------ boot
  function boot() {
    markNav();
    var page = document.body.getAttribute("data-page");
    Promise.all([SS.loadJSON("site.json"), SS.loadJSON("certificate.json")]).then(function (base) {
      var site = base[0], cert = base[1];
      SS.site = site;
      chrome(site, cert);
      if (page === "index") {
        // baseline.json is optional: fetch it only when site.json lists it (avoids a 404 in the console).
        var hasBaseline = !!(site && site.files && site.files["baseline.json"]);
        Promise.all([SS.loadJSON("decisions.json"),
                     hasBaseline ? SS.loadJSON("baseline.json") : Promise.resolve(null)]).then(function (r) {
          renderHeadline(cert, r[0]);
          renderMeasures(cert, r[1]);
          renderLimits(cert);
        });
      } else if (page === "certificate") {
        Promise.all([SS.loadJSON("decisions.json"), SS.loadJSON("lints.json"), SS.loadJSON("mutation.json")]).then(function (r) {
          renderCertificate(site, cert, r[0], r[1], r[2]);
        });
      } else if (page === "replay") {
        SS.loadJSON("replay.json").then(function (replay) { renderReplay(site, replay); });
      } else if (page === "verify") {
        checkPageScript("verify.js", "verify-pending");
      } else if (page === "trace") {
        checkPageScript("trace.js", "trace-pending");
      }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
