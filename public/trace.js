/*
 * trace.js — Trace page logic for SheetShift.
 * Written by IBM Bob (task T10).
 *
 * Reads data/traceability.json and data/graph.json (same-origin fetch only).
 * Renders cell↔function traceability in #trace-coverage, #trace-cell-picker,
 * #trace-function-picker, #trace-cell-detail, #trace-function-detail.
 * Uses window.SheetShift helpers from site.js (loaded first).
 * No inline event handlers, no innerHTML, no external requests.
 */
(function () {
  "use strict";

  var SS = window.SheetShift;
  var el = SS.el;

  /* ------------------------------------------------------------------ utils */

  function $(id) { return document.getElementById(id); }

  function setText(id, text) {
    var node = $(id);
    if (node) node.textContent = text;
  }

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
      } else if (Array.isArray(val)) {
        val.forEach(function (v) { dd.appendChild(v && v.nodeType ? v : document.createTextNode(String(v))); });
      } else {
        dd.textContent = String(val);
      }
      dl.appendChild(dd);
    });
    return dl;
  }

  /* ------------------------------------------------------------------ state */

  var state = {
    site: null,
    trace: null,   /* data/traceability.json */
    graph: null,   /* data/graph.json */
    /* map from cell (e.g. "Calc!O") to graph column entry */
    colMap: {},
  };

  /* ------------------------------------------------------------------ coverage card */

  function renderCoverage(trace) {
    var cnt = trace.counts || {};
    var gate = trace.gate || "unknown";
    var gateCls = gate === "pass" ? "badge green" : gate === "warn" ? "badge warn" : "badge red";
    var box = $("trace-coverage");
    if (!box) return;
    clear(box);
    box.appendChild(kv([
      ["Gate", el("span", { class: gateCls, text: String(gate).toUpperCase() })],
      ["Covered", String(cnt.covered !== undefined ? cnt.covered : "–")],
      ["Out of scope", String(cnt.out_of_scope !== undefined ? cnt.out_of_scope : "–")],
      ["Uncovered", String(cnt.uncovered !== undefined ? cnt.uncovered : "–")],
      ["Total rules", String(cnt.total !== undefined ? cnt.total : "–")],
    ]));
  }

  /* ------------------------------------------------------------------ populate pickers */

  function matchesFilter(rule, q) {
    if (!q) return true;
    var lq = q.toLowerCase();
    return (
      (rule.cell && rule.cell.toLowerCase().indexOf(lq) >= 0) ||
      (rule.output_name && rule.output_name.toLowerCase().indexOf(lq) >= 0) ||
      (rule.functions && rule.functions.some(function (f) {
        return f.name && f.name.toLowerCase().indexOf(lq) >= 0;
      }))
    );
  }

  function populateCellPicker(rules, q) {
    var sel = $("trace-cell-picker");
    if (!sel) return;
    /* preserve selection */
    var prev = sel.value;
    clear(sel);
    sel.appendChild(el("option", { value: "", text: "Choose a cell…" }));
    var count = 0;
    (rules || []).forEach(function (rule) {
      if (!matchesFilter(rule, q)) return;
      var label = rule.cell + " — " + (rule.output_name || "");
      sel.appendChild(el("option", { value: rule.cell, text: label }));
      count++;
    });
    /* restore or clear */
    if (prev) sel.value = prev;
    return count;
  }

  function populateFunctionPicker(reverseIndex, q) {
    var sel = $("trace-function-picker");
    if (!sel) return;
    var prev = sel.value;
    clear(sel);
    sel.appendChild(el("option", { value: "", text: "Choose a function…" }));
    Object.keys(reverseIndex || {}).forEach(function (key) {
      /* key = "file:function"; match against function part for filter */
      if (q) {
        var lq = q.toLowerCase();
        var fnName = key.split(":").pop() || "";
        var filePart = key.split(":").slice(0, -1).join(":");
        if (fnName.toLowerCase().indexOf(lq) < 0 && filePart.toLowerCase().indexOf(lq) < 0) return;
      }
      sel.appendChild(el("option", { value: key, text: key }));
    });
    if (prev) sel.value = prev;
  }

  /* ------------------------------------------------------------------ detail panels */

  function renderCellDetail(cell, rule, graphCol) {
    var box = $("trace-cell-detail");
    if (!box) return;
    if (!rule) { fill("trace-cell-detail", SS.empty("No cell selected.")); return; }

    var pairs = [
      ["Cell", rule.cell],
      ["Output", rule.output_name || "–"],
      ["Status", el("span", { class: "badge " + (rule.status === "covered" ? "green" : rule.status === "out_of_scope" ? "decided" : "warn"), text: rule.status || "–" })],
    ];

    if (rule.template) pairs.push(["Template", el("code", { text: rule.template })]);

    if (graphCol) {
      if (graphCol.precedents && graphCol.precedents.length) {
        pairs.push(["Precedents", graphCol.precedents.join(", ")]);
      }
      if (graphCol.inputs && graphCol.inputs.length) {
        pairs.push(["Inputs", graphCol.inputs.join(", ")]);
      }
      if (graphCol.manual_rule) {
        pairs.push(["Manual rule", graphCol.manual_rule]);
      }
    }

    if (rule.out_of_scope) {
      pairs.push(["Reason", rule.out_of_scope.reason || "–"]);
    }

    /* functions with GitHub links */
    var fns = rule.functions || [];
    if (fns.length) {
      var fnNodes = [];
      fns.forEach(function (f, i) {
        var url = SS.githubUrl(state.site, f.file, f.line);
        var linkNode = SS.linkOr(url, f.file + ":" + f.line);
        if (i > 0) fnNodes.push(document.createTextNode(", "));
        fnNodes.push(linkNode);
        fnNodes.push(document.createTextNode(" (" + (f.name || "?") + ")"));
      });
      var fnSpan = el("span", {}, fnNodes);
      pairs.push(["Functions", fnSpan]);
    } else {
      pairs.push(["Functions", "–"]);
    }

    /* tests */
    var tests = rule.tests || [];
    if (tests.length) {
      var testNodes = [];
      tests.forEach(function (t, i) {
        /* t = "tests/foo.py:LINE" */
        var parts = t.split(":");
        var tFile = parts[0];
        var tLine = parts[1];
        var url = SS.githubUrl(state.site, tFile, tLine);
        var node = SS.linkOr(url, t);
        if (i > 0) testNodes.push(document.createTextNode(", "));
        testNodes.push(node);
      });
      pairs.push(["Tests", el("span", {}, testNodes)]);
    } else {
      pairs.push(["Tests", "–"]);
    }

    clear(box);
    box.appendChild(kv(pairs));
  }

  function renderFunctionDetail(key, reverseIndex) {
    var box = $("trace-function-detail");
    if (!box) return;
    if (!key || !reverseIndex || !reverseIndex[key]) {
      fill("trace-function-detail", SS.empty("No function selected."));
      return;
    }
    var cells = reverseIndex[key];
    clear(box);
    box.appendChild(el("p", { class: "status-line", text: key }));
    var ul = el("ul", { class: "plain-list" });
    cells.forEach(function (cell) {
      var li = el("li", {});
      var btn = el("button", { class: "secondary", text: cell, "aria-label": "Select cell " + cell });
      btn.addEventListener("click", function () {
        selectCell(cell, true);
      });
      li.appendChild(btn);
      ul.appendChild(li);
    });
    box.appendChild(ul);
  }

  /* ------------------------------------------------------------------ selection */

  function selectCell(cell, updateHash) {
    var sel = $("trace-cell-picker");
    if (sel) sel.value = cell || "";
    var rule = (state.trace.rules || []).find(function (r) { return r.cell === cell; });
    var graphCol = cell ? (state.colMap[cell] || null) : null;
    renderCellDetail(cell, rule, graphCol);
    if (updateHash && cell) {
      try { location.hash = cell; } catch (e) { /* ignore */ }
    }
    setText("trace-status", cell ? "Selected: " + cell : "");
  }

  function selectFunction(key) {
    var sel = $("trace-function-picker");
    if (sel) sel.value = key || "";
    renderFunctionDetail(key, state.trace.reverse_index);
  }

  /* ------------------------------------------------------------------ boot */

  function applyFilter() {
    var q = ($("trace-search") || {}).value || "";
    var count = populateCellPicker(state.trace.rules, q);
    populateFunctionPicker(state.trace.reverse_index, q);
    setText("trace-status", q ? count + " match" + (count === 1 ? "" : "es") : "");
  }

  function boot(site, trace, graph) {
    state.site = site;
    state.trace = trace;
    state.graph = graph;

    /* build cell → graph column map */
    (graph.columns || []).forEach(function (col) {
      if (col.cell) state.colMap[col.cell] = col;
    });

    renderCoverage(trace);
    populateCellPicker(trace.rules, "");
    populateFunctionPicker(trace.reverse_index, "");

    /* wire pickers */
    var cellSel = $("trace-cell-picker");
    if (cellSel) {
      cellSel.addEventListener("change", function () {
        selectCell(cellSel.value, true);
        /* clear function picker selection when cell changes */
        var fnSel = $("trace-function-picker");
        if (fnSel) fnSel.value = "";
        fill("trace-function-detail", SS.empty("No function selected."));
      });
    }
    var fnSel = $("trace-function-picker");
    if (fnSel) {
      fnSel.addEventListener("change", function () {
        selectFunction(fnSel.value);
      });
    }
    var search = $("trace-search");
    if (search) {
      search.addEventListener("input", applyFilter);
    }

    /* deep link */
    var hash = location.hash ? decodeURIComponent(location.hash.slice(1)) : "";
    if (hash) {
      selectCell(hash, false);
    } else {
      fill("trace-cell-detail", SS.empty("No cell selected."));
      fill("trace-function-detail", SS.empty("No function selected."));
    }
  }

  /* ------------------------------------------------------------------ init */

  document.addEventListener("DOMContentLoaded", function () {
    Promise.all([
      SS.loadJSON("site.json"),
      SS.loadJSON("traceability.json"),
      SS.loadJSON("graph.json"),
    ]).then(function (results) {
      var site = results[0];
      var trace = results[1];
      var graph = results[2];

      if (!trace || !trace.rules) {
        setText("trace-status", "Could not load traceability data.");
        fill("trace-coverage", SS.empty("traceability.json not available."));
        return;
      }
      if (!graph) {
        setText("trace-status", "Could not load graph.json.");
        graph = { columns: [] };
      }

      boot(site || {}, trace, graph);
    });
  });
}());
