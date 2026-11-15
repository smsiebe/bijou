/* ==========================================================================
   Bijou v2 Offline Snapshot Data Store
   In standard online mode, this holds null.
   In exported offline snapshot archives, this holds precomputed portfolio data.
   ========================================================================== */

(function (global) {
  "use strict";

  global.__BIJOU_SNAPSHOT__ = global.__BIJOU_SNAPSHOT__ || null;
})(window);

