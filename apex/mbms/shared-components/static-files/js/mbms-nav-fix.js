/*
 * MBMS - workaround side navigation menu di layar kecil (Universal Theme 26.2.1).
 *
 * Masalah: di lebar < breakpoint lg, onExpand tree nav memanggil delayResize(), yang
 * memicu "resize"; handler onResize tree nav lalu memanggil collapse(). Akibatnya menu
 * langsung menutup lagi setelah dibuka (juga terjadi di aplikasi wizard/starter app).
 *
 * Workaround: abaikan event resize sintetis pada window selama 800 ms setelah menu dibuka,
 * HANYA jika ukuran viewport tidak berubah. Resize sungguhan (rotasi layar) tetap diproses.
 * Hapus file ini bila Oracle sudah memperbaiki Universal Theme.
 */
(function (apex) {
  "use strict";
  var $ = apex && apex.jQuery;
  if (!$ || window.__mbmsNavFix) { return; }
  window.__mbmsNavFix = true;

  var GRACE_MS = 800,
      lastExpand = 0,
      expandSize = "";

  function size() { return window.innerWidth + "x" + window.innerHeight; }

  function suppress() {
    return Date.now() - lastExpand < GRACE_MS &&
      expandSize === size() &&
      document.body && document.body.classList.contains("js-navExpanded");
  }

  $(document).on("theme42layoutchanged", function (e, data) {
    if (data && data.action === "expand" && $(e.target).is("#t_TreeNav")) {
      lastExpand = Date.now();
      expandSize = size();
    }
  });

  // jQuery: $(window).trigger("resize" | "apexwindowresized")
  var origTrigger = $.event.trigger;
  $.event.trigger = function (event, data, elem) {
    var type = typeof event === "string" ? event : (event && event.type);
    if (elem === window && (type === "resize" || type === "apexwindowresized") && suppress()) {
      return;
    }
    return origTrigger.apply(this, arguments);
  };

  // Native: window.dispatchEvent(new Event("resize"))
  var origDispatch = window.dispatchEvent;
  window.dispatchEvent = function (ev) {
    if (ev && ev.type === "resize" && suppress()) { return true; }
    return origDispatch.apply(window, arguments);
  };
})(window.apex);
