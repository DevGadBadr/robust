(function () {
  if (window.__robustPicker) {
    try { window.__robustPicker.destroy(); } catch (e) {}
  }

  var HIGHLIGHT_ID = "__robust_pick_highlight";
  var MENU_ID = "__robust_pick_menu";
  var STYLE_ID = "__robust_pick_style";
  var state = {
    jobuuid: null,
    armed: false,
    highlight: null,
    menu: null,
    lastEl: null,
    onMove: null,
    onClick: null,
    onKey: null
  };

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent =
      "#" + HIGHLIGHT_ID + "{" +
      "position:fixed;pointer-events:none;z-index:2147483646;" +
      "border:2px solid #42a5f5;background:rgba(66,165,245,0.15);" +
      "box-sizing:border-box;}" +
      "#" + MENU_ID + "{" +
      "position:fixed;z-index:2147483647;background:#1e1e1e;color:#f0f0f0;" +
      "border:1px solid #555;border-radius:4px;font:12px/1.4 Consolas,monospace;" +
      "min-width:220px;max-width:420px;box-shadow:0 4px 16px rgba(0,0,0,.4);}" +
      "#" + MENU_ID + " .rp-row{" +
      "padding:6px 10px;cursor:pointer;border-bottom:1px solid #333;" +
      "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}" +
      "#" + MENU_ID + " .rp-row:hover{background:#2a4a6a;}" +
      "#" + MENU_ID + " .rp-row.rp-cancel{color:#f88;}" +
      "#" + MENU_ID + " .rp-meta{opacity:.7;margin-left:8px;}";
    (document.head || document.documentElement).appendChild(style);
  }

  function cssEscape(value) {
    if (window.CSS && CSS.escape) return CSS.escape(value);
    return String(value).replace(/([^\w-])/g, "\\$1");
  }

  function isUnique(selector, mode) {
    try {
      var nodes;
      if (mode === "css") nodes = document.querySelectorAll(selector);
      else if (mode === "xpath") {
        var snap = document.evaluate(selector, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        return snap.snapshotLength === 1;
      } else if (mode === "id") {
        return !!document.getElementById(selector) && document.querySelectorAll("#" + cssEscape(selector)).length === 1;
      } else if (mode === "name") {
        return document.getElementsByName(selector).length === 1;
      }
      return nodes && nodes.length === 1;
    } catch (e) {
      return false;
    }
  }

  function isNoiseClass(c) {
    return /^(ng-|css-|jsx-|sc-|_|ember)/.test(c) || c.length > 40 || /\d{4,}/.test(c);
  }

  function buildCandidates(el) {
    var out = [];
    if (!el || el === document.documentElement || el === document.body) return out;

    var id = el.getAttribute("id");
    if (id && isUnique(id, "id")) {
      out.push({ type: "ID", value: id, score: 100 });
    }

    var name = el.getAttribute("name");
    if (name && isUnique(name, "name")) {
      out.push({ type: "NAME", value: name, score: 95 });
    }

    var testAttrs = ["data-testid", "data-qa", "data-test", "data-cy"];
    for (var i = 0; i < testAttrs.length; i++) {
      var attr = testAttrs[i];
      var val = el.getAttribute(attr);
      if (val) {
        var sel = el.tagName.toLowerCase() + "[" + attr + '="' + val.replace(/"/g, '\\"') + '"]';
        if (isUnique(sel, "css")) {
          out.push({ type: "CSS_SELECTOR", value: sel, score: 92 });
          break;
        }
      }
    }

    if (el.classList && el.classList.length) {
      var classes = [];
      for (var c = 0; c < el.classList.length; c++) {
        var cn = el.classList[c];
        if (!isNoiseClass(cn)) classes.push(cn);
      }
      if (classes.length) {
        var classSel = el.tagName.toLowerCase() + "." + classes.map(cssEscape).join(".");
        if (isUnique(classSel, "css")) {
          out.push({ type: "CSS_SELECTOR", value: classSel, score: 85 });
        } else if (classes.length === 1 && isUnique(classes[0], "css") === false) {
          try {
            if (document.getElementsByClassName(classes[0]).length === 1) {
              out.push({ type: "CLASS_NAME", value: classes[0], score: 80 });
            }
          } catch (e) {}
        }
      }
    }

    var path = [];
    var cur = el;
    while (cur && cur.nodeType === 1 && cur !== document.body && cur !== document.documentElement) {
      var part = cur.tagName.toLowerCase();
      var parent = cur.parentElement;
      if (parent) {
        var siblings = parent.children;
        var sameTag = [];
        for (var s = 0; s < siblings.length; s++) {
          if (siblings[s].tagName === cur.tagName) sameTag.push(siblings[s]);
        }
        if (sameTag.length > 1) {
          var idx = sameTag.indexOf(cur) + 1;
          part += ":nth-of-type(" + idx + ")";
        }
      }
      path.unshift(part);
      var trial = path.join(" > ");
      if (isUnique(trial, "css")) {
        out.push({ type: "CSS_SELECTOR", value: trial, score: Math.max(50, 78 - path.length * 3) });
        break;
      }
      cur = parent;
      if (path.length > 6) break;
    }

    if (id) {
      var xpId = '//*[@id="' + id.replace(/"/g, '\\"') + '"]';
      if (isUnique(xpId, "xpath")) {
        out.push({ type: "XPATH", value: xpId, score: 70 });
      }
    }

    var text = (el.innerText || el.textContent || "").trim().replace(/\s+/g, " ");
    if (text && text.length > 0 && text.length <= 40) {
      var tag = el.tagName.toLowerCase();
      var xpText = "//" + tag + '[normalize-space()="' + text.replace(/"/g, '\\"') + '"]';
      if (isUnique(xpText, "xpath")) {
        out.push({ type: "XPATH", value: xpText, score: 65 });
      }
    }

    // Deduplicate by type+value
    var seen = {};
    var uniq = [];
    for (var u = 0; u < out.length; u++) {
      var key = out[u].type + "\0" + out[u].value;
      if (!seen[key]) {
        seen[key] = true;
        uniq.push(out[u]);
      }
    }
    uniq.sort(function (a, b) { return b.score - a.score; });
    return uniq;
  }

  function removeHighlight() {
    if (state.highlight && state.highlight.parentNode) {
      state.highlight.parentNode.removeChild(state.highlight);
    }
    state.highlight = null;
    state.lastEl = null;
  }

  function removeMenu() {
    if (state.menu && state.menu.parentNode) {
      state.menu.parentNode.removeChild(state.menu);
    }
    state.menu = null;
  }

  function updateHighlight(el) {
    if (!el || el === state.lastEl) return;
    if (el.id === HIGHLIGHT_ID || el.id === MENU_ID || (state.menu && state.menu.contains(el))) return;
    state.lastEl = el;
    ensureStyle();
    if (!state.highlight) {
      state.highlight = document.createElement("div");
      state.highlight.id = HIGHLIGHT_ID;
      document.documentElement.appendChild(state.highlight);
    }
    var r = el.getBoundingClientRect();
    state.highlight.style.left = r.left + "px";
    state.highlight.style.top = r.top + "px";
    state.highlight.style.width = Math.max(r.width, 1) + "px";
    state.highlight.style.height = Math.max(r.height, 1) + "px";
  }

  function setResult(payload) {
    window.__robustPickResult = payload;
  }

  function finishPick(payload) {
    setResult(payload);
    cleanupListeners(false);
    removeHighlight();
    removeMenu();
    state.armed = false;
    state.jobuuid = null;
  }

  function showChooser(el, x, y) {
    removeMenu();
    ensureStyle();
    var candidates = buildCandidates(el);
    var menu = document.createElement("div");
    menu.id = MENU_ID;

    if (!candidates.length) {
      var empty = document.createElement("div");
      empty.className = "rp-row";
      empty.textContent = "No unique locator found";
      menu.appendChild(empty);
    } else {
      candidates.forEach(function (c) {
        var row = document.createElement("div");
        row.className = "rp-row";
        row.title = c.value;
        row.innerHTML =
          "<strong>" + c.type + "</strong> " +
          "<span>" + c.value + "</span>" +
          '<span class="rp-meta">(' + c.score + ")</span>";
        row.addEventListener("click", function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          finishPick({
            status: "picked",
            jobuuid: state.jobuuid,
            type: c.type,
            value: c.value
          });
        }, true);
        menu.appendChild(row);
      });
    }

    var cancel = document.createElement("div");
    cancel.className = "rp-row rp-cancel";
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      finishPick({ status: "cancelled", jobuuid: state.jobuuid });
    }, true);
    menu.appendChild(cancel);

    document.documentElement.appendChild(menu);
    state.menu = menu;

    var mw = menu.offsetWidth || 220;
    var mh = menu.offsetHeight || 100;
    var left = Math.min(Math.max(8, x), window.innerWidth - mw - 8);
    var top = Math.min(Math.max(8, y), window.innerHeight - mh - 8);
    menu.style.left = left + "px";
    menu.style.top = top + "px";
  }

  function onMove(ev) {
    if (!state.armed || state.menu) return;
    var el = document.elementFromPoint(ev.clientX, ev.clientY);
    if (el) updateHighlight(el);
  }

  function onClick(ev) {
    if (!state.armed) return;
    if (state.menu && state.menu.contains(ev.target)) return;
    ev.preventDefault();
    ev.stopPropagation();
    var el = state.lastEl || document.elementFromPoint(ev.clientX, ev.clientY);
    if (!el || el === document.documentElement || el === document.body) return;
    showChooser(el, ev.clientX, ev.clientY);
  }

  function onKey(ev) {
    if (!state.armed) return;
    if (ev.key === "Escape" || ev.keyCode === 27) {
      ev.preventDefault();
      finishPick({ status: "cancelled", jobuuid: state.jobuuid });
    }
  }

  function cleanupListeners(clearResult) {
    if (state.onMove) document.removeEventListener("mousemove", state.onMove, true);
    if (state.onClick) document.removeEventListener("click", state.onClick, true);
    if (state.onKey) document.removeEventListener("keydown", state.onKey, true);
    state.onMove = null;
    state.onClick = null;
    state.onKey = null;
    if (clearResult) {
      try { delete window.__robustPickResult; } catch (e) { window.__robustPickResult = null; }
    }
  }

  function cancel() {
    cleanupListeners(true);
    removeHighlight();
    removeMenu();
    state.armed = false;
    state.jobuuid = null;
  }

  function destroy() {
    cancel();
    var style = document.getElementById(STYLE_ID);
    if (style && style.parentNode) style.parentNode.removeChild(style);
    try { delete window.__robustPicker; } catch (e) { window.__robustPicker = null; }
  }

  function start(jobuuid) {
    cancel();
    ensureStyle();
    state.jobuuid = jobuuid;
    state.armed = true;
    try { delete window.__robustPickResult; } catch (e) { window.__robustPickResult = null; }
    state.onMove = onMove;
    state.onClick = onClick;
    state.onKey = onKey;
    document.addEventListener("mousemove", state.onMove, true);
    document.addEventListener("click", state.onClick, true);
    document.addEventListener("keydown", state.onKey, true);
  }

  window.__robustPicker = {
    start: start,
    cancel: cancel,
    destroy: destroy
  };
})();
