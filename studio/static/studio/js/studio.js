(function () {
  "use strict";

  var root = document.documentElement;

  // ---- Theme toggle (initial theme is set by an inline script in <head>) ----
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("studio-theme", next); } catch (e) {}
    });
  });

  // ---- Off-canvas menu on small screens ----
  var shell = document.querySelector(".shell");
  if (shell) {
    var setOpen = function (open) { shell.classList.toggle("rail-open", open); };
    document.querySelectorAll("[data-rail-open]").forEach(function (el) {
      el.addEventListener("click", function () { setOpen(true); });
    });
    document.querySelectorAll("[data-rail-close]").forEach(function (el) {
      el.addEventListener("click", function () { setOpen(false); });
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") setOpen(false);
    });
  }

  // ---- Confirm before submitting destructive forms ----
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  // ---- Submit filter selects on change ----
  document.querySelectorAll("select[data-autosubmit]").forEach(function (sel) {
    sel.addEventListener("change", function () { sel.form.submit(); });
  });

  // ---- Toasts fade out on their own ----
  document.querySelectorAll(".toast").forEach(function (toast, i) {
    setTimeout(function () {
      toast.classList.add("is-leaving");
      setTimeout(function () { toast.remove(); }, 400);
    }, 4000 + i * 600);
  });
})();
