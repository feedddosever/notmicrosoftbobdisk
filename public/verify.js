/*
 * verify.js — Verify page logic for SheetShift.
 * Written by IBM Bob (task T10).
 *
 * Wires #verify-form → GET /api/verify?n=&sample_seed= and renders the result.
 * Falls back to data/verify_sample_results.json when the API is unreachable.
 * Wires #quote-form → POST /api/quote and renders all 43 outputs.
 * #quote-example fills the textarea from data/quote_examples.json.
 * No inline event handlers, no innerHTML, no external requests.
 */
(function () {
  "use strict";

  var SS = window.SheetShift;
  var el = SS.el;

  /* ------------------------------------------------------------------ utils */

  function $(id) { return document.getElementById(id); }

  function clear(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
    return node;
  }

  function fill(id, nodes) {
    var node = $(id);
    if (!node) return;
    clear(node);
    (Array.isArray(nodes) ? nodes : [nodes]).forEach(function (n) {
      if (n) node.appendChild(n);
    });
  }

  function setText(id, text) {
    var node = $(id);
    if (node) node.textContent = String(text || "");
  }

  function kv(pairs) {
    var dl = el("dl", { class: "kv" });
    pairs.forEach(function (p) {
      dl.appendChild(el("dt", { text: p[0] }));
      var val = p[1];
      var dd = el("dd", {});
      if (val === null || val === undefined) {
        dd.textContent = "–";
      } else if (val && val.nodeType) {
        dd.appendChild(val);
      } else {
        dd.textContent = String(val);
      }
      dl.appendChild(dd);
    });
    return dl;
  }

  /** Build a <div class="table-wrap"><table>…</table></div> */
  function buildTable(headers, rows, numericCols) {
    numericCols = numericCols || [];
    var thead = el("thead", {}, [el("tr", {}, headers.map(function (h, i) {
      return el("th", { class: numericCols.indexOf(i) >= 0 ? "num" : null, scope: "col", text: h });
    }))]);
    var tbody = el("tbody", {}, rows.map(function (r) {
      return el("tr", {}, r.map(function (c, i) {
        var cls = numericCols.indexOf(i) >= 0 ? "num" : null;
        var td = el("td", { class: cls });
        if (c === null || c === undefined) {
          td.textContent = "–";
        } else if (c && c.nodeType) {
          td.appendChild(c);
        } else {
          td.textContent = String(c);
        }
        return td;
      }));
    }));
    return el("div", { class: "table-wrap" }, [el("table", {}, [thead, tbody])]);
  }

  /* ------------------------------------------------------------------ format helpers */

  function fmtVal(v) {
    if (v === null || v === undefined) return "–";
    if (typeof v === "object" && v.error) return v.error;
    if (typeof v === "object" && v.date) return v.date;
    return String(v);
  }

  /* ------------------------------------------------------------------ verify rendering */

  function renderSummary(data, precomputed) {
    var nodes = [];
    var label = precomputed
      ? "Precomputed — " + (data.rows || "?") + " rows, seed " + (data.sample_seed || "–")
      : (data.rows || "?") + " rows sampled";
    nodes.push(el("p", {}, [
      el("strong", { text: label })
    ]));
    nodes.push(kv([
      ["Rows compared", SS.fmtInt(data.rows)],
      ["Rows equal", SS.fmtInt(data.rows_equal !== undefined ? data.rows_equal : data.rows)],
      ["Cells compared", SS.fmtInt(data.cells_compared)],
      ["Cells equal", SS.fmtInt(data.cells_equal !== undefined ? data.cells_equal : data.cells_matched)],
      ["Cells mismatched", SS.fmtInt(
        data.cells_mismatched !== undefined ? data.cells_mismatched
          : (data.cells_compared - (data.cells_equal !== undefined ? data.cells_equal : (data.cells_matched || 0)))
      )],
      ["Service", data.service || data.commit || "–"],
    ]));
    fill("verify-summary", nodes);
  }

  function renderOracle(data) {
    var box = $("verify-oracle");
    if (!box) return;
    clear(box);
    /* show oracle string verbatim — may be a plain string or object with label/recalc */
    var oracle = data.oracle;
    if (oracle && typeof oracle === "object") {
      var parts = [];
      if (oracle.label) parts.push(oracle.label);
      if (oracle.recalc) parts.push("recalc: " + oracle.recalc);
      if (oracle.version) parts.push("v" + oracle.version);
      box.textContent = parts.join(" — ") || JSON.stringify(oracle);
    } else if (oracle) {
      box.textContent = String(oracle);
    } else {
      box.textContent = "–";
    }
    /* oracle_variant if present */
    if (data.oracle_variant) {
      box.appendChild(el("p", { class: "status-line", text: "Variant: " + data.oracle_variant }));
    }
  }

  function renderTolerance(data) {
    var box = $("verify-tolerance");
    if (!box) return;
    clear(box);
    var tol = data.tolerance;
    if (!tol) { box.textContent = "–"; return; }
    box.appendChild(kv([
      ["Numbers", tol.numbers !== undefined ? String(tol.numbers) : "–"],
      ["Dates", tol.dates || "exact"],
      ["Text", tol.text || "exact"],
      ["Errors", tol.errors || "by code"],
      ["Blank/0/\"\"", tol.blank_zero_empty || "different"],
    ]));
  }

  function renderMismatches(data) {
    var box = $("verify-mismatches");
    if (!box) return;
    clear(box);

    /* mismatches_by_output (precomputed shape) */
    var byOutput = data.mismatches_by_output;
    if (byOutput && Object.keys(byOutput).length > 0) {
      var sumRows = Object.keys(byOutput).map(function (name) {
        return [name, byOutput[name]];
      });
      box.appendChild(el("h4", { text: "By output" }));
      box.appendChild(buildTable(["Output", "Count"], sumRows, [1]));
    }

    var mm = data.mismatches || [];
    if (mm.length === 0 && !byOutput) {
      box.appendChild(el("p", { class: "empty", text: "None." }));
      return;
    }
    if (mm.length === 0) return;

    if (byOutput) box.appendChild(el("h4", { text: "Detail (first " + mm.length + ")" }));

    var rows = mm.map(function (m) {
      return [
        m.row !== undefined ? String(m.row) : "–",
        m.policy_id || "–",
        m.output_name || "–",
        m.kind || "–",
        fmtVal(m.expected),
        fmtVal(m.service !== undefined ? m.service : m.actual),
      ];
    });
    box.appendChild(buildTable(
      ["Row", "Policy ID", "Output", "Kind", "Expected", "Service"],
      rows,
      [0]
    ));

    if (data.mismatches_truncated) {
      box.appendChild(el("p", { class: "status-line", text: "Results truncated to first " + mm.length + " mismatches." }));
    }
  }

  function renderVerifyResult(data, precomputed) {
    renderSummary(data, precomputed);
    renderOracle(data);
    renderTolerance(data);
    renderMismatches(data);
  }

  /* ------------------------------------------------------------------ verify form */

  function setRunning(running) {
    var btn = $("verify-run");
    if (btn) btn.disabled = running;
    setText("verify-status", running ? "Running…" : "");
  }

  function loadFallback() {
    SS.loadJSON("verify_sample_results.json").then(function (data) {
      var banner = $("verify-offline-banner");
      if (banner) {
        banner.hidden = false;
        clear(banner);
        banner.appendChild(el("p", { text: "API offline: showing precomputed results." }));
      }
      if (!data) {
        fill("verify-summary", SS.empty("verify_sample_results.json is not available."));
        setText("verify-status", "API unreachable and no precomputed data.");
        return;
      }
      renderVerifyResult(data, true);
      setText("verify-status", "Showing precomputed results.");
    });
  }

  function runVerify(n, seed) {
    setRunning(true);
    var url = "/api/verify?n=" + encodeURIComponent(n) + "&sample_seed=" + encodeURIComponent(seed);
    fetch(url, { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) return Promise.reject(new Error("HTTP " + r.status));
        return r.json();
      })
      .then(function (data) {
        var banner = $("verify-offline-banner");
        if (banner) banner.hidden = true;
        renderVerifyResult(data, false);
        setText("verify-status", "Done.");
      })
      .catch(function (err) {
        setText("verify-status", "API error: " + (err && err.message ? err.message : "unreachable") + ". Loading precomputed results…");
        loadFallback();
      })
      .then(function () { setRunning(false); }, function () { setRunning(false); });
  }

  /* ------------------------------------------------------------------ quote form */

  var _quoteExamples = null;
  var _quoteExampleIndex = 0;

  /** Convert quote_examples.json policy to the form POST /api/quote expects. */
  function encodePolicy(policy) {
    var out = {};
    Object.keys(policy).forEach(function (k) {
      var v = policy[k];
      if (v === null || v === undefined) {
        out[k] = null;
      } else if (typeof v === "object" && v.date) {
        /* {"date": "YYYY-MM-DD"} → "YYYY-MM-DD" string */
        out[k] = v.date;
      } else {
        out[k] = v;
      }
    });
    return out;
  }

  function fmtExpected(v) {
    if (v === null || v === undefined) return "null";
    if (typeof v === "object" && v.error) return v.error;
    if (typeof v === "object" && v.date) return v.date;
    return String(v);
  }

  function renderQuoteOutput(result, expected) {
    var box = $("quote-output");
    if (!box) return;
    clear(box);
    var keys = Object.keys(result);
    if (!keys.length) {
      box.appendChild(SS.empty("No outputs returned."));
      return;
    }
    var hasExpected = expected && typeof expected === "object";
    var headers = hasExpected ? ["Output", "Value", "Expected", "Match"] : ["Output", "Value"];
    var rows = keys.map(function (k) {
      var v = result[k];
      var vStr = v === null || v === undefined ? "null" : String(v);
      if (!hasExpected) return [k, el("code", { text: vStr })];
      var expStr = fmtExpected(expected[k]);
      var match = vStr === expStr || (typeof result[k] === "number" && Math.abs(result[k] - Number(expStr)) < 1e-6);
      var matchNode = el("span", {
        class: "badge " + (match ? "green" : "warn"),
        text: match ? "✓" : "≠"
      });
      return [k, el("code", { text: vStr }), el("code", { text: expStr }), matchNode];
    });
    box.appendChild(buildTable(headers, rows, []));
  }

  function submitQuote() {
    var textarea = $("quote-input");
    var statusEl = $("quote-status");
    if (!textarea) return;
    var raw = textarea.value.trim();
    if (!raw) {
      if (statusEl) statusEl.textContent = "Enter a policy JSON first.";
      return;
    }
    var policy;
    try {
      policy = JSON.parse(raw);
    } catch (e) {
      if (statusEl) statusEl.textContent = "JSON parse error: " + (e && e.message ? e.message : String(e));
      return;
    }
    var btn = $("quote-submit");
    if (btn) btn.disabled = true;
    if (statusEl) statusEl.textContent = "Quoting…";

    fetch("/api/quote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(policy),
    })
      .then(function (r) {
        if (r.status === 422) {
          return r.json().then(function (body) {
            /* pydantic 422 details */
            var detail = body && body.detail;
            var msg;
            if (Array.isArray(detail)) {
              msg = detail.map(function (d) {
                var loc = Array.isArray(d.loc) ? d.loc.join(".") : String(d.loc || "");
                return (loc ? loc + ": " : "") + (d.msg || JSON.stringify(d));
              }).join("; ");
            } else {
              msg = detail ? String(detail) : "Validation error (422).";
            }
            if (statusEl) statusEl.textContent = msg;
            return null;
          });
        }
        if (!r.ok) return Promise.reject(new Error("HTTP " + r.status));
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        if (statusEl) statusEl.textContent = "";
        /* find matching expected values if an example was loaded */
        var expected = null;
        if (_quoteExamples) {
          var examples = _quoteExamples.examples || [];
          var cur = examples[_quoteExampleIndex % examples.length];
          if (cur && cur.expected) expected = cur.expected;
        }
        renderQuoteOutput(data, expected);
      })
      .catch(function (err) {
        if (statusEl) statusEl.textContent = "API error: " + (err && err.message ? err.message : "unreachable");
      })
      .then(function () {
        if (btn) btn.disabled = false;
      }, function () {
        if (btn) btn.disabled = false;
      });
  }

  function loadExample() {
    var textarea = $("quote-input");
    var statusEl = $("quote-status");
    if (!textarea) return;

    function setExample(examples) {
      if (!examples || !examples.length) {
        if (statusEl) statusEl.textContent = "No examples available.";
        return;
      }
      var ex = examples[_quoteExampleIndex % examples.length];
      _quoteExampleIndex++;
      var policy = encodePolicy(ex.policy);
      textarea.value = JSON.stringify(policy, null, 2);
      if (statusEl) {
        statusEl.textContent = "Loaded example: " + (ex.label || ("row " + (ex.row || "?")));
      }
    }

    if (_quoteExamples) {
      setExample(_quoteExamples.examples);
      return;
    }
    SS.loadJSON("quote_examples.json").then(function (data) {
      _quoteExamples = data;
      setExample(data ? data.examples : null);
    });
  }

  /* ------------------------------------------------------------------ site.json / static mode */

  function checkStaticMode(site) {
    if (site && site.mode === "static") {
      /* In static mode, don't bother hitting the API */
      loadFallback();
    }
  }

  /* ------------------------------------------------------------------ boot */

  document.addEventListener("DOMContentLoaded", function () {
    /* Wire verify form */
    var form = $("verify-form");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var n = parseInt(($("verify-n") || {}).value, 10) || 200;
        var seed = parseInt(($("verify-seed") || {}).value, 10);
        if (isNaN(seed)) seed = 7;
        if (n < 1) n = 1;
        if (n > 500) n = 500;
        runVerify(n, seed);
      });
    }

    /* Wire quote form */
    var quoteForm = $("quote-form");
    if (quoteForm) {
      quoteForm.addEventListener("submit", function (e) {
        e.preventDefault();
        submitQuote();
      });
    }

    var exampleBtn = $("quote-example");
    if (exampleBtn) {
      exampleBtn.addEventListener("click", loadExample);
    }

    /* Check site.json for static mode */
    SS.loadJSON("site.json").then(function (site) {
      checkStaticMode(site);
    });
  });
}());
