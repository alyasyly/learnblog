(function () {
  "use strict";

  var form = document.getElementById("post-form");
  if (!form) return;

  var $ = function (id) { return document.getElementById(id); };
  var ta = $("id_body");
  var titleInput = $("id_title");
  var summaryInput = $("id_summary");
  var preview = $("preview");
  var previewPane = $("preview-pane");
  var previewEmpty = $("preview-empty");
  var saveState = $("save-state");
  var csrf = form.querySelector("input[name=csrfmiddlewaretoken]").value;
  var previewUrl = form.getAttribute("data-preview-url");
  var draftKey = "studio-draft:" + form.getAttribute("data-draft-key");
  var serverUpdated = parseInt(form.getAttribute("data-updated") || "0", 10) * 1000;
  var faNumber = new Intl.NumberFormat("fa");

  // Persian date with a fixed word order (browsers' own "full" patterns differ).
  var faParts = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    day: "numeric", month: "long", year: "numeric",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23"
  });
  function faDateTime(d) {
    var v = {};
    faParts.formatToParts(d).forEach(function (part) { v[part.type] = part.value; });
    return v.day + " " + v.month + " " + v.year + "، ساعت " + v.hour + ":" + v.minute;
  }


  var dirty = false;
  var submitting = false;
  var ready = false;

  function store(key, value) { try { localStorage.setItem(key, value); } catch (e) {} }
  function load(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function drop(key) { try { localStorage.removeItem(key); } catch (e) {} }

  // ------------------------------------------------------------------ modes
  var modeButtons = form.querySelectorAll("[data-mode]");
  var narrow = window.matchMedia("(max-width: 900px)");

  // `interactive` is false for the initial call and for viewport changes, so
  // nothing is fetched or focused before the rest of the script has loaded.
  function setMode(mode, remember, interactive) {
    if (narrow.matches && mode === "split") mode = "write";
    form.classList.remove("mode-write", "mode-split", "mode-preview");
    form.classList.add("mode-" + mode);
    modeButtons.forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-mode") === mode));
    });
    if (remember) store("studio-mode", mode);
    if (!interactive) return;
    if (mode !== "write") renderPreview();
    if (mode === "write") ta.focus();
  }
  modeButtons.forEach(function (b) {
    b.addEventListener("click", function () { setMode(b.getAttribute("data-mode"), true, true); });
  });
  setMode(load("studio-mode") || "split", false, false);
  narrow.addEventListener("change", function () {
    var current = form.classList.contains("mode-preview") ? "preview" : form.classList.contains("mode-write") ? "write" : "split";
    setMode(current, false, true);
  });

  // ------------------------------------------------------------ inspector
  var side = $("inspector");
  var sideToggle = $("toggle-side");
  var wide = window.matchMedia("(min-width: 1101px)");
  function sideIsOpen() {
    return wide.matches ? !form.classList.contains("side-closed") : form.classList.contains("side-open");
  }
  function syncSideAria() { sideToggle.setAttribute("aria-expanded", String(sideIsOpen())); }
  sideToggle.addEventListener("click", function () {
    if (wide.matches) {
      var closed = form.classList.toggle("side-closed");
      store("studio-side-closed", closed ? "1" : "0");
    } else {
      form.classList.toggle("side-open");
    }
    syncSideAria();
  });
  if (load("studio-side-closed") === "1") form.classList.add("side-closed");
  wide.addEventListener("change", syncSideAria);
  syncSideAria();
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !wide.matches && form.classList.contains("side-open")) {
      form.classList.remove("side-open");
      syncSideAria();
    }
  });

  // -------------------------------------------------------- text insertion
  // execCommand keeps the browser's undo stack; setRangeText is the fallback.
  function replaceRange(start, end, text) {
    ta.focus();
    ta.setSelectionRange(start, end);
    var ok = false;
    try { ok = document.execCommand("insertText", false, text); } catch (e) {}
    if (!ok) {
      ta.setRangeText(text, start, end, "end");
      ta.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  function wrap(before, after, placeholder) {
    var s = ta.selectionStart, e = ta.selectionEnd;
    var selected = ta.value.slice(s, e) || placeholder;
    replaceRange(s, e, before + selected + after);
    ta.setSelectionRange(s + before.length, s + before.length + selected.length);
  }

  function lineRange() {
    var v = ta.value;
    var s = v.lastIndexOf("\n", ta.selectionStart - 1) + 1;
    var e = v.indexOf("\n", ta.selectionEnd);
    if (e === -1) e = v.length;
    return [s, e];
  }

  function prefixLines(makePrefix) {
    var collapsed = ta.selectionStart === ta.selectionEnd;
    var r = lineRange();
    var block = ta.value.slice(r[0], r[1]);
    var lines = block.split("\n").map(function (line, i) { return makePrefix(i) + line; });
    var out = lines.join("\n");
    replaceRange(r[0], r[1], out);
    // No selection: leave the caret at the end of the line so typing continues
    // after the marker. With a selection: keep the changed lines selected.
    ta.setSelectionRange(collapsed ? r[0] + out.length : r[0], r[0] + out.length);
  }

  function insertBlock(text) {
    var s = ta.selectionStart, e = ta.selectionEnd;
    var v = ta.value;
    var lead = s > 0 && v[s - 1] !== "\n" ? "\n\n" : s > 0 && v[s - 2] !== "\n" && s > 1 ? "\n" : "";
    replaceRange(s, e, lead + text + "\n");
  }

  var commands = {
    bold: function () { wrap("**", "**", "متن پررنگ"); },
    italic: function () { wrap("*", "*", "متن کج"); },
    code: function () { wrap("`", "`", "کد"); },
    h2: function () { prefixLines(function () { return "## "; }); },
    h3: function () { prefixLines(function () { return "### "; }); },
    ul: function () { prefixLines(function () { return "- "; }); },
    ol: function () { prefixLines(function (i) { return (i + 1) + ". "; }); },
    quote: function () { prefixLines(function () { return "> "; }); },
    hr: function () { insertBlock("---"); },
    table: function () {
      insertBlock("| ستون اول | ستون دوم |\n|---|---|\n| مقدار | مقدار |");
    },
    codeblock: function () {
      var s = ta.selectionStart, e = ta.selectionEnd;
      var selected = ta.value.slice(s, e) || "کد را اینجا بنویس";
      var lead = s > 0 && ta.value[s - 1] !== "\n" ? "\n" : "";
      var text = lead + "```python\n" + selected + "\n```\n";
      replaceRange(s, e, text);
      var from = s + lead.length + 10;
      ta.setSelectionRange(from, from + selected.length);
    },
    link: function () {
      var s = ta.selectionStart, e = ta.selectionEnd;
      var selected = ta.value.slice(s, e) || "متن پیوند";
      var url = "https://";
      replaceRange(s, e, "[" + selected + "](" + url + ")");
      var urlStart = s + selected.length + 3;
      ta.setSelectionRange(urlStart, urlStart + url.length);
    }
  };

  form.querySelectorAll("[data-cmd]").forEach(function (btn) {
    btn.addEventListener("mousedown", function (e) { e.preventDefault(); }); // keep selection
    btn.addEventListener("click", function () { commands[btn.getAttribute("data-cmd")](); });
  });

  // ------------------------------------------------------- keyboard shortcuts
  var saveBtn = form.querySelector("button[name=action][value=save]");
  document.addEventListener("keydown", function (e) {
    var mod = e.ctrlKey || e.metaKey;
    if (!mod || e.altKey) return;
    var key = e.key.toLowerCase();
    if (key === "s") {
      e.preventDefault();
      form.requestSubmit(saveBtn);
    } else if (document.activeElement === ta) {
      if (key === "b") { e.preventDefault(); commands.bold(); }
      else if (key === "i") { e.preventDefault(); commands.italic(); }
      else if (key === "k") { e.preventDefault(); commands.link(); }
    }
  });

  // Enter inside a list continues it; Enter on an empty item ends it.
  ta.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" || e.shiftKey || e.isComposing || e.ctrlKey || e.metaKey) return;
    if (ta.selectionStart !== ta.selectionEnd) return;
    var pos = ta.selectionStart;
    var lineStart = ta.value.lastIndexOf("\n", pos - 1) + 1;
    var line = ta.value.slice(lineStart, pos);
    var m = /^(\s*)([-*]|\d+\.)\s+(.*)$/.exec(line);
    if (!m) return;
    e.preventDefault();
    if (!m[3]) {
      replaceRange(lineStart, pos, "");
      return;
    }
    var marker = /\d/.test(m[2]) ? (parseInt(m[2], 10) + 1) + "." : m[2];
    replaceRange(pos, pos, "\n" + m[1] + marker + " ");
  });

  // ---------------------------------------------------------------- stats
  var statWords = $("stat-words");
  var statMinutes = $("stat-minutes");
  var summaryCount = $("summary-count");

  function updateStats() {
    var text = ta.value.trim();
    var words = text ? text.split(/\s+/).length : 0;
    statWords.textContent = faNumber.format(words);
    statMinutes.textContent = faNumber.format(Math.max(1, Math.round(words / 200)));
    summaryCount.textContent = faNumber.format(summaryInput.value.length);
  }

  // -------------------------------------------------------------- preview
  var seq = 0;
  var timer = null;
  var lastRendered = null;

  function previewVisible() { return !form.classList.contains("mode-write"); }

  function renderPreview() {
    if (!previewVisible()) return;
    var text = ta.value;
    if (text === lastRendered) return;
    var mine = ++seq;
    var data = new FormData();
    data.append("body", text);
    fetch(previewUrl, {
      method: "POST",
      body: data,
      headers: { "X-CSRFToken": csrf },
      credentials: "same-origin"
    }).then(function (r) {
      if (!r.ok) throw new Error("preview " + r.status);
      return r.json();
    }).then(function (json) {
      if (mine !== seq) return; // a newer request is on its way
      lastRendered = text;
      var top = previewPane.scrollTop;
      preview.innerHTML = json.html;
      previewEmpty.hidden = !!text.trim();
      previewPane.scrollTop = top;
    }).catch(function () {
      previewEmpty.hidden = false;
      previewEmpty.textContent = "پیش‌نمایش بارگذاری نشد. اتصال یا ورود دوباره‌ات را بررسی کن.";
    });
  }
  function schedulePreview() {
    clearTimeout(timer);
    timer = setTimeout(renderPreview, 350);
  }

  // Keep the preview roughly aligned with the writing position.
  ta.addEventListener("scroll", function () {
    if (!form.classList.contains("mode-split")) return;
    var max = ta.scrollHeight - ta.clientHeight;
    if (max <= 0) return;
    var ratio = ta.scrollTop / max;
    previewPane.scrollTop = ratio * (previewPane.scrollHeight - previewPane.clientHeight);
  });

  // ------------------------------------------------- dirty state + local draft
  function setDirty(value) {
    dirty = value;
    saveState.classList.toggle("is-dirty", value);
    if (value) saveState.textContent = "تغییرات ذخیره‌نشده";
    else saveState.textContent = form.getAttribute("data-draft-key") === "new" ? "نوشته‌ی جدید" : "ذخیره‌شده";
  }

  var draftTimer = null;
  function saveLocalDraft() {
    if (!ta.value.trim() && !titleInput.value.trim()) { drop(draftKey); return; }
    store(draftKey, JSON.stringify({
      title: titleInput.value,
      summary: summaryInput.value,
      body: ta.value,
      savedAt: Date.now()
    }));
  }

  function onChange() {
    if (!ready) return;
    updateStats();
    setDirty(true);
    schedulePreview();
    clearTimeout(draftTimer);
    draftTimer = setTimeout(saveLocalDraft, 800);
  }
  [ta, titleInput, summaryInput].forEach(function (el) { el.addEventListener("input", onChange); });
  form.querySelectorAll("input[type=radio], input[type=datetime-local], #id_slug").forEach(function (el) {
    el.addEventListener("change", function () { if (ready) setDirty(true); });
  });

  form.addEventListener("submit", function () {
    submitting = true;
    drop(draftKey);
  });
  window.addEventListener("beforeunload", function (e) {
    if (dirty && !submitting) { e.preventDefault(); e.returnValue = ""; }
  });

  // Offer to restore a newer, unsaved copy kept in this browser.
  (function offerRestore() {
    var raw = load(draftKey);
    if (!raw) return;
    var saved;
    try { saved = JSON.parse(raw); } catch (e) { drop(draftKey); return; }
    var same = saved.body === ta.value && saved.title === titleInput.value && saved.summary === summaryInput.value;
    if (same || saved.savedAt <= serverUpdated) { drop(draftKey); return; }

    var box = $("restore");
    $("restore-time").textContent = faDateTime(new Date(saved.savedAt));
    box.hidden = false;
    $("restore-yes").addEventListener("click", function () {
      titleInput.value = saved.title;
      summaryInput.value = saved.summary;
      ta.value = saved.body;
      box.hidden = true;
      updateStats();
      setDirty(true);
      renderPreview();
      ta.focus();
    });
    $("restore-no").addEventListener("click", function () {
      drop(draftKey);
      box.hidden = true;
    });
  })();

  // ------------------------------------------------------------ tag chips
  var chips = $("chips");
  var tagInput = $("tag-input");
  var tagsField = $("id_tags_text");
  var tags = [];

  function parseTags(text) {
    return text.split(/[,،\n]/).map(function (t) { return t.replace(/\s+/g, " ").trim(); }).filter(Boolean);
  }
  function hasTag(name) {
    return tags.some(function (t) { return t.toLowerCase() === name.toLowerCase(); });
  }
  function renderChips() {
    chips.querySelectorAll(".chip").forEach(function (c) { c.remove(); });
    tags.forEach(function (name, i) {
      var chip = document.createElement("span");
      chip.className = "chip";
      chip.appendChild(document.createTextNode(name));
      var rm = document.createElement("button");
      rm.type = "button";
      rm.setAttribute("aria-label", "حذف برچسب " + name);
      rm.textContent = "×";
      rm.addEventListener("click", function () {
        tags.splice(i, 1);
        syncTags(true);
        tagInput.focus();
      });
      chip.appendChild(rm);
      chips.insertBefore(chip, tagInput);
    });
  }
  function syncTags(markDirty) {
    tagsField.value = tags.join(", ");
    renderChips();
    if (markDirty && ready) setDirty(true);
  }
  function addTagsFrom(text) {
    parseTags(text).forEach(function (name) {
      if (name.length > 50) name = name.slice(0, 50);
      if (!hasTag(name)) tags.push(name);
    });
    tagInput.value = "";
    syncTags(true);
  }
  tagInput.addEventListener("keydown", function (e) {
    if (e.isComposing) return;
    if (e.key === "Enter" || e.key === "," || e.key === "،") {
      e.preventDefault();
      if (tagInput.value.trim()) addTagsFrom(tagInput.value);
    } else if (e.key === "Backspace" && !tagInput.value && tags.length) {
      tags.pop();
      syncTags(true);
    }
  });
  // Picking a suggestion from the datalist fires "input" with a whole value.
  tagInput.addEventListener("input", function (e) {
    if (e.inputType === "insertReplacementText" || (!e.inputType && tagInput.value)) addTagsFrom(tagInput.value);
  });
  tagInput.addEventListener("blur", function () {
    if (tagInput.value.trim()) addTagsFrom(tagInput.value);
  });
  chips.addEventListener("click", function (e) { if (e.target === chips) tagInput.focus(); });
  tags = parseTags(tagsField.value);
  syncTags(false);

  // ------------------------------------------------ publish date in Persian
  var dateInput = $("id_published_at");
  var dateHint = $("date-hint");
  var defaultHint = dateHint.textContent;
  function updateDateHint() {
    if (!dateInput.value) { dateHint.textContent = defaultHint; return; }
    var d = new Date(dateInput.value);
    dateHint.textContent = isNaN(d) ? defaultHint : faDateTime(d) + (d > new Date() ? " (در آینده؛ زمان‌بندی‌شده)" : "");
  }
  dateInput.addEventListener("input", updateDateHint);
  updateDateHint();

  // ------------------------------------------------------------------ boot
  updateStats();
  renderPreview();
  ready = true;
  if (!titleInput.value) titleInput.focus();
  else ta.focus();
})();
