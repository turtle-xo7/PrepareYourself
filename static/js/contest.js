/* PrepareYourself contest UI helpers — countdowns, leaderboard polling, badges. */
(function () {
  'use strict';

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  function fmt(secs) {
    if (secs < 0) secs = 0;
    var h = Math.floor(secs / 3600);
    var m = Math.floor((secs % 3600) / 60);
    var s = secs % 60;
    return pad(h) + 'h ' + pad(m) + 'm ' + pad(s) + 's';
  }

  /**
   * startCountdown(targetISO, element, options)
   *   options.onExpire - called when timer reaches zero
   *   options.warningSeconds - flip to red when remaining <= this (default 1800)
   */
  function startCountdown(targetISO, element, options) {
    options = options || {};
    var warn = options.warningSeconds == null ? 1800 : options.warningSeconds;
    var end = new Date(targetISO).getTime();
    if (isNaN(end)) return;

    function tick() {
      var now = Date.now();
      var remaining = Math.max(0, Math.floor((end - now) / 1000));
      element.textContent = fmt(remaining);
      if (remaining <= warn) {
        element.classList.add('warning');
        element.style.color = '#dc2626';
      }
      if (remaining <= 0) {
        element.textContent = '00h 00m 00s';
        if (typeof options.onExpire === 'function') options.onExpire();
        return;
      }
      setTimeout(tick, 1000);
    }
    tick();
  }

  /** Hover-display element with .contest-timer & data-end (used on cards). */
  function startContestTimer(el) {
    var endISO = el.dataset.end;
    var startISO = el.dataset.start;
    if (!endISO) return;
    var endMs = new Date(endISO).getTime();
    var startMs = startISO ? new Date(startISO).getTime() : 0;
    function tick() {
      var now = Date.now();
      var remaining;
      var prefix = '';
      if (startMs && now < startMs) {
        remaining = Math.max(0, Math.floor((startMs - now) / 1000));
        prefix = 'Starts in ';
      } else if (now < endMs) {
        remaining = Math.max(0, Math.floor((endMs - now) / 1000));
        prefix = 'Ends in ';
      } else {
        el.textContent = 'Ended';
        return;
      }
      el.textContent = prefix + fmt(remaining);
      setTimeout(tick, 1000);
    }
    tick();
  }

  /**
   * startLeaderboardPolling(contestId, tbodyId, updatedElId, intervalMs, currentUsername)
   * Polls /contests/<id>/leaderboard/data/ and re-renders the table body.
   */
  function startLeaderboardPolling(contestId, tbodyId, updatedElId, intervalMs, currentUsername) {
    intervalMs = intervalMs || 30000;
    var tbody = document.getElementById(tbodyId);
    var updatedEl = document.getElementById(updatedElId);
    if (!tbody) return;
    var lastFetch = 0;

    function refreshUpdatedCounter() {
      if (!updatedEl || !lastFetch) return;
      var secs = Math.floor((Date.now() - lastFetch) / 1000);
      updatedEl.textContent = 'Updated ' + secs + 's ago';
    }

    function rankIcon(r) {
      if (r === 1) return '🥇';
      if (r === 2) return '🥈';
      if (r === 3) return '🥉';
      return r;
    }

    function renderRow(row) {
      var ratingDelta = '';
      if (row.rating_change != null) {
        var up = row.rating_change >= 0;
        var arrow = up ? '↑' : '↓';
        ratingDelta = '<span style="color:' + (up ? '#16a34a' : '#dc2626') + ';font-weight:700;">' +
                      arrow + ' ' + row.rating_change + '</span>';
      } else {
        ratingDelta = '<span style="color:#9ca3af;">—</span>';
      }
      var pct = row.percentile != null ? Number(row.percentile).toFixed(1) : '—';
      var youTag = row.is_me ? '<span style="color:#2563eb;font-size:.7rem;font-weight:700;margin-left:6px;">YOU</span>' : '';
      var virtTag = row.is_virtual ? '<span class="virtual-badge">VIRTUAL</span>' : '';
      var timeStr = '';
      if (row.time_taken != null) {
        var m = Math.floor(row.time_taken / 60);
        var s = row.time_taken % 60;
        timeStr = m + 'm ' + (s < 10 ? '0' + s : s) + 's';
      }
      var rowCls = row.is_me ? 'row-me' : '';
      return '<tr class="' + rowCls + ' border-t border-gray-100">' +
             '<td class="font-bold">' + rankIcon(row.rank) + '</td>' +
             '<td><span class="avatar-mini">' + (row.username[0] || '?').toUpperCase() + '</span>' +
             ' <span style="color:' + (row.rank_color || '#374151') + ';font-weight:600;margin-left:6px;">' +
             row.username + '</span>' + virtTag + youTag + '</td>' +
             '<td class="text-right font-bold">' + row.score + '</td>' +
             '<td class="text-right text-sm text-gray-600">' + timeStr + '</td>' +
             '<td class="text-right">' + ratingDelta + '</td>' +
             '<td class="text-right text-sm">' + pct + '</td>' +
             '</tr>';
    }

    function fetchOnce() {
      fetch('/contests/' + contestId + '/leaderboard/data/', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          lastFetch = Date.now();
          if (data.hidden) return;
          var oldRanks = {};
          tbody.querySelectorAll('tr').forEach(function (tr) {
            var name = tr.querySelector('td:nth-child(2) span:nth-child(2)');
            if (name) oldRanks[name.textContent.trim()] = tr.children[0].textContent.trim();
          });
          tbody.innerHTML = data.rows.map(renderRow).join('') ||
              '<tr><td colspan="6" class="text-center py-12 text-gray-400">No submissions yet.</td></tr>';
          // Flash rows whose rank changed
          tbody.querySelectorAll('tr').forEach(function (tr) {
            var nameEl = tr.querySelector('td:nth-child(2) span:nth-child(2)');
            if (!nameEl) return;
            var nm = nameEl.textContent.trim();
            if (oldRanks[nm] && oldRanks[nm] !== tr.children[0].textContent.trim()) {
              tr.classList.add('flash');
              setTimeout(function () { tr.classList.remove('flash'); }, 1200);
            }
          });
        })
        .catch(function () { /* swallow */ });
    }

    fetchOnce();
    setInterval(fetchOnce, intervalMs);
    setInterval(refreshUpdatedCounter, 1000);
  }

  /**
   * showBadgeUnlock({name, icon, rarity, color_hex, description})
   * Shows a center-screen modal with an unlock animation.
   */
  function showBadgeUnlock(badge) {
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center;animation:fadein .2s;';
    overlay.innerHTML =
      '<div style="background:#fff;border-radius:1.25rem;padding:2rem;text-align:center;max-width:340px;box-shadow:0 20px 60px rgba(0,0,0,0.4);transform:scale(0.6);animation:pop .35s ease forwards;">' +
      '  <div style="width:96px;height:96px;border-radius:50%;background:' + (badge.color_hex || '#6c757d') + ';margin:0 auto 1rem;display:flex;align-items:center;justify-content:center;font-size:2.5rem;color:#fff;">' +
      '    <i class="bi ' + (badge.icon || 'bi-award') + '"></i>' +
      '  </div>' +
      '  <p style="font-size:.7rem;font-weight:700;color:#92400e;text-transform:uppercase;letter-spacing:.1em;">Badge unlocked!</p>' +
      '  <h3 style="font-size:1.5rem;font-weight:800;color:#111;margin:.25rem 0;">' + badge.name + '</h3>' +
      '  <p style="font-size:.875rem;color:#6b7280;margin:0;">' + (badge.description || '') + '</p>' +
      '  <p style="margin-top:1rem;font-weight:700;color:#92400e;">+ PrepCoins earned 🪙</p>' +
      '  <button style="margin-top:1rem;padding:.5rem 1.25rem;border-radius:.75rem;background:linear-gradient(135deg,#d97706,#b45309);color:#fff;font-weight:700;border:none;cursor:pointer;">Awesome</button>' +
      '</div>';
    document.body.appendChild(overlay);
    var btn = overlay.querySelector('button');
    btn.addEventListener('click', function () { overlay.remove(); });
    setTimeout(function () { if (overlay.parentNode) overlay.remove(); }, 6000);
  }

  /** updateCoinBalance: fetch latest balance into any .coin-balance elements. */
  function updateCoinBalance() {
    fetch('/api/coins/balance/', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        document.querySelectorAll('.coin-balance').forEach(function (el) {
          el.textContent = data.balance;
        });
      })
      .catch(function () {});
  }

  /** checkBadges: POST /api/badges/check/ — pops unlock modals for new badges. */
  function checkBadges() {
    var token = (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value;
    fetch('/api/badges/check/', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': token || '' },
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok && data.new_badges && data.new_badges.length) {
          data.new_badges.forEach(function (b, i) {
            setTimeout(function () { showBadgeUnlock(b); }, i * 1500);
          });
          updateCoinBalance();
        }
      })
      .catch(function () {});
  }

  // CSS for the unlock animation
  var style = document.createElement('style');
  style.textContent = '@keyframes fadein{from{opacity:0}to{opacity:1}}@keyframes pop{from{transform:scale(.6);opacity:0}to{transform:scale(1);opacity:1}}';
  document.head.appendChild(style);

  // Expose
  window.startCountdown = startCountdown;
  window.startContestTimer = startContestTimer;
  window.startLeaderboardPolling = startLeaderboardPolling;
  window.showBadgeUnlock = showBadgeUnlock;
  window.updateCoinBalance = updateCoinBalance;
  window.checkBadges = checkBadges;
})();
