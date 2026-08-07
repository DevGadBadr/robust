(function () {
  "use strict";

  if (window.__robustPicker) {
    try { window.__robustPicker.destroy(); } catch (e) {}
  }

  var STYLE_ID = "__robust_pick_style";
  var SHIELD_ID = "__robust_pick_shield";
  var HIGHLIGHT_ID = "__robust_pick_highlight";
  var MENU_ID = "__robust_pick_menu";
  var MESSAGE_KEY = "__robustPickMessage";

  var MAX_ROWS = 8;
  var MAX_PATH_STEPS = 15;
  var MAX_CLASSES = 4;

  // Events the page must never see while picking. Selection itself runs on
  // pointerdown, the earliest point at which a site can still be beaten to the
  // event, so nothing downstream (navigation, overlays, inline previews) fires.
  var BLOCKED_EVENTS = [
    "mousedown", "mouseup", "pointerup", "pointercancel",
    "click", "auxclick", "dblclick", "contextmenu",
    "mouseover", "mouseout", "mouseenter", "mouseleave",
    "pointerover", "pointerout", "pointerenter", "pointerleave",
    "touchstart", "touchend", "touchmove",
    "submit", "dragstart", "select",
    "keydown", "keyup", "keypress"
  ];

  var TEST_ATTRS = ["data-testid", "data-test-id", "data-qa", "data-test", "data-cy", "data-automation-id"];
  var STABLE_ATTRS = ["type", "placeholder", "title", "alt", "role", "for", "href", "src", "value"];
  var STATE_CLASSES = /^(style-scope|active|inactive|focus|focused|hover|hovered|selected|unselected|checked|unchecked|disabled|enabled|open|opened|closed|collapsed|expanded|hidden|visible|show|shown|animating|iron-selected|dark|light|loading|loaded|empty)$/;
  var NOISE_CLASS_PREFIX = /^(ng-|css-|jsx-|sc-|emotion-|_|ember)/;
  var HASHED_CLASS = /^[A-Za-z][\w-]*[-_][0-9a-f]{5,}$/;
  var NOISE_ID = /(^\d|\d{4,}|^:r[0-9a-z]+:$|^[0-9a-f]{8}-[0-9a-f]{4}-)/i;
  var INTERACTIVE_TAGS = /^(a|button|input|select|textarea|summary|label|option)$/;
  var INTERACTIVE_ROLES = /^(button|link|tab|menuitem|menuitemcheckbox|menuitemradio|checkbox|radio|switch|option|combobox|textbox|searchbox|slider)$/;
  var MAX_INTERACTIVE_CLIMB = 5;

  // Captured before anything is patched, so the picker can always stop an event
  // for real even while the page's own attempts to stop one are neutered.
  var nativeStopImmediate = Event.prototype.stopImmediatePropagation;
  var nativeStopPropagation = Event.prototype.stopPropagation;
  var propagationPatched = false;

  var state = {
    jobuuid: null,
    framePath: [],
    frameChain: [],
    armed: false,
    relayInstalled: false,
    shield: null,
    highlight: null,
    menu: null,
    hoverEl: null,
    lastPoint: null,
    frameHole: null,
    rafPending: false,
    listeners: []
  };

  // ---------------------------------------------------------------- utilities

  function isTop() {
    try { return window.top === window; } catch (e) { return false; }
  }

  function stopHard(ev) {
    try { nativeStopImmediate.call(ev); } catch (e) { ev.stopImmediatePropagation(); }
    if (ev.cancelable) ev.preventDefault();
  }

  // A page listener registered before the picker's cannot be un-registered, but
  // it can be stopped from silencing the picker. Without this, a site that calls
  // stopImmediatePropagation from a window capture listener swallows every click
  // and picking appears to do nothing at all.
  function patchPropagation() {
    if (propagationPatched) return;
    try {
      Event.prototype.stopImmediatePropagation = function () {};
      Event.prototype.stopPropagation = function () {};
      propagationPatched = true;
    } catch (e) {
      propagationPatched = false;
    }
  }

  function unpatchPropagation() {
    if (!propagationPatched) return;
    try {
      Event.prototype.stopImmediatePropagation = nativeStopImmediate;
      Event.prototype.stopPropagation = nativeStopPropagation;
    } catch (e) {}
    propagationPatched = false;
  }

  function cssEscape(value) {
    if (window.CSS && CSS.escape) return CSS.escape(value);
    return String(value).replace(/([^\w-])/g, "\\$1");
  }

  function cssQuote(value) {
    return '"' + String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
  }

  function xpathLiteral(value) {
    var text = String(value);
    if (text.indexOf('"') < 0) return '"' + text + '"';
    if (text.indexOf("'") < 0) return "'" + text + "'";
    var parts = text.split('"');
    var pieces = [];
    for (var i = 0; i < parts.length; i++) {
      if (parts[i]) pieces.push('"' + parts[i] + '"');
      if (i < parts.length - 1) pieces.push("'\"'");
    }
    return "concat(" + pieces.join(",") + ")";
  }

  function rootOf(el) {
    var root = el && el.getRootNode ? el.getRootNode() : document;
    return root || document;
  }

  function isShadowRoot(root) {
    return !!root && root.nodeType === 11 && !!root.host;
  }

  function tagOf(el) {
    return el.tagName ? el.tagName.toLowerCase() : "";
  }

  // Polymer and friends mirror the custom element tag name into a class on every
  // scoped child ("style-scope ytd-rich-grid-media"), which is never selective.
  var scopeClassCache = {};

  function isScopeClass(name) {
    if (name.indexOf("-") < 0) return false;
    if (scopeClassCache.hasOwnProperty(name)) return scopeClassCache[name];
    var isScope = false;
    try { isScope = document.getElementsByTagName(name).length > 0; } catch (e) { isScope = false; }
    scopeClassCache[name] = isScope;
    return isScope;
  }

  function isNoiseClass(name) {
    if (!name || name.length > 40) return true;
    if (/\d{4,}/.test(name)) return true;
    if (STATE_CLASSES.test(name)) return true;
    if (NOISE_CLASS_PREFIX.test(name)) return true;
    if (HASHED_CLASS.test(name)) return true;
    return isScopeClass(name);
  }

  function stableClasses(el) {
    var out = [];
    if (!el.classList) return out;
    for (var i = 0; i < el.classList.length && out.length < MAX_CLASSES; i++) {
      var name = el.classList[i];
      if (!isNoiseClass(name)) out.push(name);
    }
    return out;
  }

  function isNoiseId(value) {
    return !value || value.length > 60 || NOISE_ID.test(value);
  }

  function isInteractive(el) {
    if (!el || el.nodeType !== 1) return false;
    if (INTERACTIVE_TAGS.test(tagOf(el))) return true;
    var role = el.getAttribute("role");
    if (role && INTERACTIVE_ROLES.test(role.trim())) return true;
    if (el.hasAttribute("onclick")) return true;
    var tabindex = el.getAttribute("tabindex");
    if (tabindex !== null && parseInt(tabindex, 10) >= 0) return true;
    return el.isContentEditable === true;
  }

  // Icons and labels are usually built from a few nested decorative elements, so
  // a click lands on something that carries no identity of its own while the
  // button or link wrapping it does. Both are offered.
  function interactiveAncestor(el) {
    var cur = el.parentElement;
    var guard = 0;
    while (cur && cur.nodeType === 1 && guard++ < MAX_INTERACTIVE_CLIMB) {
      if (isInteractive(cur)) return cur;
      cur = cur.parentElement;
    }
    return null;
  }

  // ------------------------------------------------------------- verification

  function queryAll(root, selector) {
    try { return root.querySelectorAll(selector); } catch (e) { return null; }
  }

  // A candidate is usable when Selenium's own lookup lands on the picked
  // element. Selenium takes the first match in document order, so leading
  // match is the requirement and uniqueness only affects the score.
  function matchInfo(root, type, value, el) {
    var nodes = null;
    try {
      if (type === "ID") nodes = root.querySelectorAll("#" + cssEscape(value));
      else if (type === "NAME") nodes = root.querySelectorAll("[name=" + cssQuote(value) + "]");
      else if (type === "CLASS_NAME") nodes = root.querySelectorAll("." + cssEscape(value));
      else if (type === "TAG_NAME") nodes = root.querySelectorAll(value);
      else if (type === "CSS_SELECTOR") nodes = root.querySelectorAll(value);
      else if (type === "XPATH") {
        if (isShadowRoot(root)) return null;
        var snap = document.evaluate(value, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        if (!snap.snapshotLength || snap.snapshotItem(0) !== el) return null;
        return { count: snap.snapshotLength };
      }
    } catch (e) {
      return null;
    }
    if (!nodes || !nodes.length || nodes[0] !== el) return null;
    return { count: nodes.length };
  }

  // A locator that happens to match the picked element first is usable, but the
  // more elements it also matches the less it is really identifying it, so the
  // penalty grows with the match count.
  function ambiguityPenalty(count) {
    if (count <= 1) return 0;
    if (count === 2) return 10;
    if (count <= 5) return 18;
    if (count <= 20) return 26;
    return 34;
  }

  function shortSelectorFor(el, root) {
    if (!el || el.nodeType !== 1) return null;
    var tag = tagOf(el);
    var tries = [];
    var id = el.getAttribute("id");
    if (id && !isNoiseId(id)) tries.push("#" + cssEscape(id));
    for (var t = 0; t < TEST_ATTRS.length; t++) {
      var testValue = el.getAttribute(TEST_ATTRS[t]);
      if (testValue) tries.push(tag + "[" + TEST_ATTRS[t] + "=" + cssQuote(testValue) + "]");
    }
    var aria = el.getAttribute("aria-label");
    if (aria && aria.length <= 80) tries.push(tag + "[aria-label=" + cssQuote(aria) + "]");
    var name = el.getAttribute("name");
    if (name) tries.push(tag + "[name=" + cssQuote(name) + "]");
    var classes = stableClasses(el);
    if (classes.length) tries.push(tag + "." + classes.map(cssEscape).join("."));
    // A custom element tag is often selective on its own, which keeps anchors and
    // shadow host chains short on component heavy pages.
    if (tag.indexOf("-") > 0) tries.push(tag);
    for (var i = 0; i < tries.length; i++) {
      if (matchInfo(root, "CSS_SELECTOR", tries[i], el)) return tries[i];
    }
    return null;
  }

  // ----------------------------------------------------------------- paths

  function childStep(el) {
    var tag = tagOf(el);
    var parent = el.parentElement;
    if (!parent) return tag;
    var sameTag = 0;
    var index = 0;
    for (var i = 0; i < parent.children.length; i++) {
      if (parent.children[i].tagName === el.tagName) {
        sameTag++;
        if (parent.children[i] === el) index = sameTag;
      }
    }
    return sameTag > 1 ? tag + ":nth-of-type(" + index + ")" : tag;
  }

  // Walk up until an ancestor has a selector of its own, then hang the relative
  // chain off it. This replaces giving up after a fixed depth, which is what
  // deep component trees (YouTube) always ran into.
  function anchoredPath(el, root) {
    var steps = [];
    var cur = el;
    var guard = 0;
    while (cur && cur.nodeType === 1 && guard++ < MAX_PATH_STEPS) {
      steps.unshift(childStep(cur));
      var parent = cur.parentElement;
      if (!parent) break;
      var anchor = shortSelectorFor(parent, root);
      if (anchor) return { value: anchor + " > " + steps.join(" > "), steps: steps.length };
      if (parent === document.body || parent === document.documentElement) {
        return { value: tagOf(parent) + " > " + steps.join(" > "), steps: steps.length };
      }
      cur = parent;
    }
    return steps.length ? { value: steps.join(" > "), steps: steps.length } : null;
  }

  function childIndex(el) {
    var index = 1;
    var sibling = el;
    while ((sibling = sibling.previousElementSibling)) index++;
    return index;
  }

  // Fully qualified path from the root: always resolves, so the chooser can
  // never come up empty.
  function fullCssPath(el, root) {
    var parts = [];
    var cur = el;
    var guard = 0;
    while (cur && cur.nodeType === 1 && guard++ < 60) {
      var parent = cur.parentElement;
      if (!parent && cur === document.documentElement) parts.unshift(tagOf(cur));
      else parts.unshift(tagOf(cur) + ":nth-child(" + childIndex(cur) + ")");
      if (!parent) break;
      cur = parent;
    }
    return parts.join(" > ");
  }

  function absoluteXPath(el) {
    var parts = [];
    var cur = el;
    var guard = 0;
    while (cur && cur.nodeType === 1 && guard++ < 60) {
      var parent = cur.parentElement;
      if (!parent) {
        parts.unshift(tagOf(cur));
        break;
      }
      var sameTag = 0;
      var index = 0;
      for (var i = 0; i < parent.children.length; i++) {
        if (parent.children[i].tagName === cur.tagName) {
          sameTag++;
          if (parent.children[i] === cur) index = sameTag;
        }
      }
      parts.unshift(sameTag > 1 ? tagOf(cur) + "[" + index + "]" : tagOf(cur));
      cur = parent;
    }
    return "/" + parts.join("/");
  }

  // ------------------------------------------------------------- candidates

  function collectCandidates(el, root, out, options) {
    var shadow = isShadowRoot(root);
    var tag = tagOf(el);
    var on = options && options.on ? options.on : null;
    var withFallbacks = !options || options.fallbacks !== false;

    function add(type, value, score, fallback) {
      if (value) {
        out.push({
          type: type,
          value: value,
          score: score,
          fallback: !!fallback,
          target: el,
          on: on
        });
      }
    }
    // Selenium can only run CSS lookups against a shadow root, so shadow-scoped
    // picks express every locator as CSS.
    function addCss(type, cssValue, plainValue, score) {
      if (shadow) add("CSS_SELECTOR", cssValue, score);
      else add(type, plainValue, score);
    }

    var id = el.getAttribute("id");
    if (id && !isNoiseId(id)) {
      addCss("ID", "#" + cssEscape(id), id, 100);
      if (!shadow) add("XPATH", '//*[@id=' + xpathLiteral(id) + ']', 70);
    }

    var name = el.getAttribute("name");
    if (name) addCss("NAME", tag + "[name=" + cssQuote(name) + "]", name, 95);

    for (var t = 0; t < TEST_ATTRS.length; t++) {
      var testValue = el.getAttribute(TEST_ATTRS[t]);
      if (testValue) add("CSS_SELECTOR", tag + "[" + TEST_ATTRS[t] + "=" + cssQuote(testValue) + "]", 92);
    }

    var aria = el.getAttribute("aria-label");
    if (aria) aria = aria.trim();
    if (aria && aria.length <= 80) {
      add("CSS_SELECTOR", tag + "[aria-label=" + cssQuote(aria) + "]", 88);
      var role = el.getAttribute("role");
      if (role) add("CSS_SELECTOR", tag + "[role=" + cssQuote(role) + "][aria-label=" + cssQuote(aria) + "]", 87);
      if (!shadow) add("XPATH", "//" + tag + "[@aria-label=" + xpathLiteral(aria) + "]", 64);
    }

    var classes = stableClasses(el);
    if (classes.length) {
      add("CSS_SELECTOR", tag + "." + classes.map(cssEscape).join("."), 85);
      if (classes.length > 1) add("CSS_SELECTOR", "." + classes.map(cssEscape).join("."), 84);
      for (var c = 0; c < Math.min(classes.length, 2); c++) {
        addCss("CLASS_NAME", "." + cssEscape(classes[c]), classes[c], 80 - c);
      }
    }

    for (var s = 0; s < STABLE_ATTRS.length; s++) {
      var attr = STABLE_ATTRS[s];
      var attrValue = el.getAttribute(attr);
      if (attrValue && attrValue.length <= 120) {
        add("CSS_SELECTOR", tag + "[" + attr + "=" + cssQuote(attrValue) + "]", 75);
      }
    }

    if (!shadow) {
      var text = (el.textContent || "").trim().replace(/\s+/g, " ");
      if (text && text.length <= 60) {
        add("XPATH", "//" + tag + "[normalize-space(.)=" + xpathLiteral(text) + "]", 65);
      }
    }

    addCss("TAG_NAME", tag, tag, 60);

    var anchored = anchoredPath(el, root);
    if (anchored) add("CSS_SELECTOR", anchored.value, Math.max(40, 72 - anchored.steps * 3));

    if (withFallbacks) {
      add("CSS_SELECTOR", fullCssPath(el, root), 25, true);
      if (!shadow) add("XPATH", absoluteXPath(el), 20, true);
    }
    return out;
  }

  function buildCandidates(el) {
    if (!el || el.nodeType !== 1 || !el.isConnected) return [];
    var root = rootOf(el);
    var raw = collectCandidates(el, root, []);
    if (!isInteractive(el)) {
      var actionable = interactiveAncestor(el);
      if (actionable) {
        collectCandidates(actionable, root, raw, {
          on: "<" + tagOf(actionable) + ">",
          fallbacks: false
        });
      }
    }

    var seen = {};
    var primary = [];
    var fallback = [];
    for (var i = 0; i < raw.length; i++) {
      var candidate = raw[i];
      var key = candidate.type + "\0" + candidate.value;
      if (seen[key]) continue;
      seen[key] = true;
      var info = matchInfo(root, candidate.type, candidate.value, candidate.target);
      if (!info) continue;
      candidate.count = info.count;
      candidate.score -= ambiguityPenalty(info.count);
      (candidate.fallback ? fallback : primary).push(candidate);
    }
    function byScore(a, b) { return b.score - a.score; }
    primary.sort(byScore);
    fallback.sort(byScore);
    // The fully qualified paths always resolve, so they keep reserved rows and
    // the chooser can never come up empty.
    return primary.slice(0, Math.max(1, MAX_ROWS - fallback.length)).concat(fallback);
  }

  function contextFor(hosts) {
    var context = {};
    if (state.frameChain && state.frameChain.length) context.frames = state.frameChain;
    if (hosts && hosts.length) {
      var selectors = [];
      for (var i = 0; i < hosts.length; i++) {
        var host = hosts[i];
        var hostRoot = rootOf(host);
        var anchored = anchoredPath(host, hostRoot);
        var selector = shortSelectorFor(host, hostRoot)
          || (anchored && matchInfo(hostRoot, "CSS_SELECTOR", anchored.value, host) ? anchored.value : null)
          || fullCssPath(host, hostRoot);
        if (!selector) return context;
        selectors.push(selector);
      }
      context.hosts = selectors;
    }
    return context;
  }

  function describeContext(context) {
    var parts = [];
    if (context.frames && context.frames.length) {
      var frameNames = [];
      for (var f = 0; f < context.frames.length; f++) {
        frameNames.push(context.frames[f].selector || ("frame[" + context.frames[f].index + "]"));
      }
      parts.push("in " + frameNames.join(" \u203a "));
    }
    if (context.hosts && context.hosts.length) {
      parts.push("shadow: " + context.hosts.join(" \u203a "));
    }
    return parts.join("  |  ");
  }

  // --------------------------------------------------------------- overlays

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent =
      "#" + SHIELD_ID + "{" +
      "position:fixed;left:0;top:0;right:0;bottom:0;z-index:2147483645;" +
      "background:transparent;cursor:crosshair;}" +
      "#" + HIGHLIGHT_ID + "{" +
      "position:fixed;pointer-events:none;z-index:2147483646;" +
      "border:2px solid #42a5f5;background:rgba(66,165,245,0.15);" +
      "box-sizing:border-box;}" +
      "#" + MENU_ID + "{" +
      "position:fixed;z-index:2147483647;background:#1e1e1e;color:#f0f0f0;" +
      "border:1px solid #555;border-radius:4px;font:12px/1.4 Consolas,monospace;" +
      "min-width:220px;max-width:480px;box-shadow:0 4px 16px rgba(0,0,0,.4);}" +
      "#" + MENU_ID + " .rp-row{" +
      "padding:6px 10px;cursor:pointer;border-bottom:1px solid #333;" +
      "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}" +
      "#" + MENU_ID + " .rp-row:hover{background:#2a4a6a;}" +
      "#" + MENU_ID + " .rp-row.rp-cancel{color:#f88;}" +
      "#" + MENU_ID + " .rp-head{padding:6px 10px;cursor:default;background:#262626;" +
      "border-bottom:1px solid #333;color:#9ad;white-space:nowrap;overflow:hidden;" +
      "text-overflow:ellipsis;}" +
      "#" + MENU_ID + " .rp-type{font-weight:bold;}" +
      "#" + MENU_ID + " .rp-meta{opacity:.7;margin-left:8px;}";
    (document.head || document.documentElement).appendChild(style);
  }

  function isOwnNode(node) {
    if (!node) return false;
    if (node === state.shield || node === state.highlight || node === state.menu) return true;
    if (state.menu && state.menu.contains && state.menu.contains(node)) return true;
    var id = node.id;
    return id === SHIELD_ID || id === HIGHLIGHT_ID || id === MENU_ID;
  }

  function isMenuNode(node) {
    return !!(state.menu && node && state.menu.contains && state.menu.contains(node));
  }

  function ensureShield() {
    if (!document.documentElement) return null;
    if (state.shield && state.shield.isConnected) return state.shield;
    ensureStyle();
    var shield = document.createElement("div");
    shield.id = SHIELD_ID;
    document.documentElement.appendChild(shield);
    state.shield = shield;
    return shield;
  }

  function setShieldPassThrough(passThrough) {
    if (state.shield) state.shield.style.pointerEvents = passThrough ? "none" : "auto";
  }

  function removeNode(node) {
    if (node && node.parentNode) node.parentNode.removeChild(node);
  }

  function removeShield() {
    removeNode(state.shield);
    state.shield = null;
    state.frameHole = null;
  }

  function removeHighlight() {
    removeNode(state.highlight);
    state.highlight = null;
    state.hoverEl = null;
    state.lastPoint = null;
  }

  function removeMenu() {
    removeNode(state.menu);
    state.menu = null;
  }

  function positionHighlight(el) {
    if (!state.highlight) {
      ensureStyle();
      state.highlight = document.createElement("div");
      state.highlight.id = HIGHLIGHT_ID;
      document.documentElement.appendChild(state.highlight);
    }
    var rect = el.getBoundingClientRect();
    state.highlight.style.left = rect.left + "px";
    state.highlight.style.top = rect.top + "px";
    state.highlight.style.width = Math.max(rect.width, 1) + "px";
    state.highlight.style.height = Math.max(rect.height, 1) + "px";
  }

  function scheduleReposition() {
    if (state.rafPending) return;
    state.rafPending = true;
    var raf = window.requestAnimationFrame || function (fn) { return setTimeout(fn, 16); };
    raf(function () {
      state.rafPending = false;
      if (state.hoverEl && state.hoverEl.isConnected) positionHighlight(state.hoverEl);
      else removeHighlight();
    });
  }

  // -------------------------------------------------------------- hit testing

  function hitTest(x, y) {
    // The shield has to drop out of hit testing entirely for the duration: while
    // it is the topmost element, ShadowRoot.elementFromPoint retargets against
    // it instead of the shadow content and the descent below never happens.
    var shieldEvents = state.shield ? state.shield.style.pointerEvents : null;
    if (state.shield) state.shield.style.pointerEvents = "none";
    try {
      var stack = null;
      try {
        stack = document.elementsFromPoint ? document.elementsFromPoint(x, y) : null;
      } catch (e) {
        stack = null;
      }
      if (!stack) {
        var single = null;
        try { single = document.elementFromPoint(x, y); } catch (e) { single = null; }
        stack = single ? [single] : [];
      }
      var el = null;
      for (var i = 0; i < stack.length; i++) {
        if (!isOwnNode(stack[i])) { el = stack[i]; break; }
      }
      if (!el) return null;
      var hosts = [];
      var guard = 0;
      while (el.shadowRoot && guard++ < 20) {
        var inner = null;
        try { inner = el.shadowRoot.elementFromPoint(x, y); } catch (e) { inner = null; }
        if (!inner || inner === el || isOwnNode(inner)) break;
        hosts.push(el);
        el = inner;
      }
      return { el: el, hosts: hosts };
    } finally {
      if (state.shield) state.shield.style.pointerEvents = shieldEvents || "auto";
    }
  }

  // --------------------------------------------------------------- chooser

  function makeRow(className) {
    var row = document.createElement("div");
    row.className = className;
    return row;
  }

  function showChooser(el, hosts, x, y) {
    removeMenu();
    ensureStyle();
    var context = contextFor(hosts);
    var candidates = buildCandidates(el);
    var menu = document.createElement("div");
    menu.id = MENU_ID;

    var contextText = describeContext(context);
    if (contextText) {
      var head = makeRow("rp-head");
      head.textContent = contextText;
      head.title = contextText;
      menu.appendChild(head);
    }

    if (!candidates.length) {
      var empty = makeRow("rp-row");
      empty.textContent = "No locator could be built for <" + tagOf(el) + ">";
      menu.appendChild(empty);
    } else {
      candidates.forEach(function (candidate) {
        var row = makeRow("rp-row");
        row.title = candidate.type + "  " + candidate.value;
        var type = document.createElement("span");
        type.className = "rp-type";
        type.textContent = candidate.type;
        var value = document.createElement("span");
        value.textContent = " " + candidate.value;
        var notes = [String(candidate.score)];
        if (candidate.count > 1) notes.push("1 of " + candidate.count);
        if (candidate.on) notes.push(candidate.on);
        var meta = document.createElement("span");
        meta.className = "rp-meta";
        meta.textContent = "(" + notes.join(", ") + ")";
        row.appendChild(type);
        row.appendChild(value);
        row.appendChild(meta);
        // Selection is driven from the picker's own pointerdown handler rather
        // than a listener here, so a page that swallows events cannot make the
        // chooser unclickable.
        row.__rpPick = {
          status: "picked",
          jobuuid: state.jobuuid,
          type: candidate.type,
          value: candidate.value,
          context: context
        };
        menu.appendChild(row);
      });
    }

    var cancelRow = makeRow("rp-row rp-cancel");
    cancelRow.textContent = "Cancel";
    cancelRow.__rpPick = { status: "cancelled", jobuuid: state.jobuuid };
    menu.appendChild(cancelRow);

    document.documentElement.appendChild(menu);
    state.menu = menu;

    var width = menu.offsetWidth || 220;
    var height = menu.offsetHeight || 100;
    menu.style.left = Math.min(Math.max(8, x), Math.max(8, window.innerWidth - width - 8)) + "px";
    menu.style.top = Math.min(Math.max(8, y), Math.max(8, window.innerHeight - height - 8)) + "px";
  }

  // --------------------------------------------------------------- delivery

  function postUp(payload) {
    try { window.parent.postMessage(makeMessage(payload), "*"); } catch (e) {}
  }

  function makeMessage(payload) {
    var message = {};
    message[MESSAGE_KEY] = payload;
    return message;
  }

  function deliver(payload) {
    if (isTop()) {
      window.__robustPickResult = payload;
      return;
    }
    postUp(payload);
  }

  function finishPick(payload) {
    deliver(payload);
    disarm();
  }

  function onMessage(ev) {
    var data = ev && ev.data;
    if (!data || typeof data !== "object") return;
    var payload = data[MESSAGE_KEY];
    if (!payload || typeof payload !== "object") return;
    if (payload.kind === "hoverOut") {
      // A nested frame reports the cursor left it, so this frame takes the
      // pointer events back.
      if (state.armed) {
        state.frameHole = null;
        setShieldPassThrough(false);
      }
      return;
    }
    if (!payload.status) return;
    // A pick finished in a descendant frame: relay it and stand down.
    deliver(payload);
    disarm();
  }

  // --------------------------------------------------------------- listeners

  function listen(target, type, handler, options) {
    target.addEventListener(type, handler, options);
    state.listeners.push([target, type, handler, options]);
  }

  function unlistenAll() {
    for (var i = 0; i < state.listeners.length; i++) {
      var entry = state.listeners[i];
      try { entry[0].removeEventListener(entry[1], entry[2], entry[3]); } catch (e) {}
    }
    state.listeners = [];
  }

  function blockEvent(ev) {
    if (!state.armed) return;
    if (ev.type === "keydown" && (ev.key === "Escape" || ev.keyCode === 27)) {
      stopHard(ev);
      finishPick({ status: "cancelled", jobuuid: state.jobuuid });
      return;
    }
    // The cursor left this document entirely: an ancestor frame must take its
    // pointer events back. Detected here because the leave events are blocked
    // before any document level listener could see them.
    if ((ev.type === "mouseout" || ev.type === "mouseleave") && !ev.relatedTarget && !isTop()) {
      postUp({ kind: "hoverOut" });
    }
    stopHard(ev);
  }

  function onMove(ev) {
    if (!state.armed) return;
    if (state.frameHole) {
      // The cursor is back over this document, so stop letting events through.
      state.frameHole = null;
      setShieldPassThrough(false);
    }
    try { nativeStopImmediate.call(ev); } catch (e) {}
    if (state.menu || isMenuNode(ev.target)) return;
    // pointermove and mousemove both arrive for the same position.
    var point = ev.clientX + ":" + ev.clientY;
    if (point === state.lastPoint) return;
    state.lastPoint = point;
    var hit = hitTest(ev.clientX, ev.clientY);
    if (!hit) return;
    var tag = tagOf(hit.el);
    if (tag === "iframe" || tag === "frame") {
      // Hand the pointer to the nested document, which runs its own picker.
      state.frameHole = hit.el;
      setShieldPassThrough(true);
      state.hoverEl = hit.el;
      positionHighlight(hit.el);
      return;
    }
    state.hoverEl = hit.el;
    positionHighlight(hit.el);
  }

  function chosenRow(target) {
    if (!state.menu || !target || !target.closest) return null;
    var row = target.closest(".rp-row");
    return row && state.menu.contains(row) ? row : null;
  }

  function onPointerDown(ev) {
    if (!state.armed) return;
    stopHard(ev);
    if (state.menu) {
      var row = chosenRow(ev.target);
      if (row && row.__rpPick) finishPick(row.__rpPick);
      else if (!isMenuNode(ev.target)) removeMenu();
      return;
    }
    var hit = hitTest(ev.clientX, ev.clientY);
    if (!hit || !hit.el.isConnected) return;
    state.hoverEl = hit.el;
    positionHighlight(hit.el);
    showChooser(hit.el, hit.hosts, ev.clientX, ev.clientY);
  }

  function installRelay() {
    if (state.relayInstalled) return;
    window.addEventListener("message", onMessage, false);
    state.relayInstalled = true;
  }

  function installListeners() {
    listen(window, "pointerdown", onPointerDown, true);
    listen(window, "pointermove", onMove, true);
    listen(window, "mousemove", onMove, true);
    for (var i = 0; i < BLOCKED_EVENTS.length; i++) {
      listen(window, BLOCKED_EVENTS[i], blockEvent, true);
    }
    listen(window, "scroll", scheduleReposition, true);
    listen(window, "resize", scheduleReposition, true);
  }

  // ------------------------------------------------------------------- api

  function init(options) {
    installRelay();
    options = options || {};
    state.framePath = options.framePath || [];
    state.frameChain = options.frames || [];
    return true;
  }

  function disarm() {
    unlistenAll();
    unpatchPropagation();
    removeMenu();
    removeHighlight();
    removeShield();
    state.armed = false;
    state.jobuuid = null;
  }

  function start(jobuuid) {
    disarm();
    installRelay();
    ensureStyle();
    state.jobuuid = jobuuid == null ? null : String(jobuuid);
    state.armed = true;
    if (isTop()) {
      try { delete window.__robustPickResult; } catch (e) { window.__robustPickResult = null; }
    }
    ensureShield();
    installListeners();
    patchPropagation();
    return true;
  }

  function armWhenReady(jobuuid) {
    if (document.documentElement) return start(jobuuid);
    document.addEventListener("DOMContentLoaded", function () { start(jobuuid); }, true);
    return false;
  }

  function cancel() {
    disarm();
    if (isTop()) {
      try { delete window.__robustPickResult; } catch (e) { window.__robustPickResult = null; }
    }
  }

  function destroy() {
    cancel();
    unlistenAll();
    if (state.relayInstalled) {
      try { window.removeEventListener("message", onMessage, false); } catch (e) {}
      state.relayInstalled = false;
    }
    removeNode(document.getElementById(STYLE_ID));
    try { delete window.__robustPicker; } catch (e) { window.__robustPicker = null; }
  }

  function status() {
    return {
      alive: true,
      armed: !!state.armed,
      jobuuid: state.jobuuid,
      framePath: state.framePath,
      top: isTop(),
      ready: !!document.documentElement
    };
  }

  // Used by the Python side while walking frames, so a frame can be described
  // with the same selector logic the picker uses for elements.
  function describeFrame(frameEl) {
    if (!frameEl || frameEl.nodeType !== 1) return null;
    var root = rootOf(frameEl);
    var frames = document.querySelectorAll("iframe, frame");
    var index = -1;
    for (var i = 0; i < frames.length; i++) {
      if (frames[i] === frameEl) { index = i; break; }
    }
    return {
      selector: shortSelectorFor(frameEl, root) || fullCssPath(frameEl, root),
      index: index,
      name: frameEl.getAttribute("name") || "",
      id: frameEl.getAttribute("id") || "",
      src: frameEl.getAttribute("src") || ""
    };
  }

  window.__robustPicker = {
    init: init,
    start: start,
    armWhenReady: armWhenReady,
    cancel: cancel,
    destroy: destroy,
    status: status,
    describeFrame: describeFrame,
    buildCandidates: buildCandidates
  };
  window.__robustPickerInit = init;
  installRelay();
})();
