(function () {
  "use strict";

  // ---- Theme toggle (the initial theme is applied by an inline script in <head>) ----
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  // ---- Reading progress bar (only on post pages) ----
  var bar = document.getElementById("progress");
  var content = document.getElementById("post-content");
  if (bar && content) {
    var update = function () {
      var rect = content.getBoundingClientRect();
      var total = rect.height - window.innerHeight * 0.5;
      var done = Math.min(Math.max(-rect.top, 0), Math.max(total, 1));
      bar.style.width = (total > 0 ? (done / total) * 100 : 100) + "%";
    };
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  }

  // ---- "Copy" button on code blocks ----
  document.querySelectorAll(".codehilite").forEach(function (block) {
    var pre = block.querySelector("pre");
    if (!pre) return;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.textContent = "کپی";
    btn.addEventListener("click", function () {
      var text = pre.innerText;
      var done = function () {
        btn.textContent = "کپی شد ✓";
        setTimeout(function () { btn.textContent = "کپی"; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () {});
      } else {
        var area = document.createElement("textarea");
        area.value = text;
        document.body.appendChild(area);
        area.select();
        try { document.execCommand("copy"); done(); } catch (e) {}
        document.body.removeChild(area);
      }
    });
    block.appendChild(btn);
  });
})();

// Ask before submitting forms that carry data-confirm="..." (e.g. deleting a comment).
document.addEventListener("submit", function (event) {
  var message = event.target.getAttribute && event.target.getAttribute("data-confirm");
  if (message && !window.confirm(message)) event.preventDefault();
});
