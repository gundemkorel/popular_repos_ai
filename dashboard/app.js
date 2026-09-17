(function () {
  var ORDER = ["coding_agents", "skills_plugins", "memory_context", "white_collar", "evals"];
  var FAV_KEY = "first-project-favs";
  var active = "all";
  var query = "";
  var data = null;
  var favs = [];

  function el(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtStars(n) {
    if (typeof n !== "number") return "–";
    return n.toLocaleString("en-US");
  }

  function fmtDate(iso) {
    if (!iso) return "–";
    return String(iso).slice(0, 10);
  }

  function fmtRanked(iso) {
    if (!iso) return "No ranked data yet";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return esc(iso);
    return esc(d.toLocaleString());
  }

  function totalCount() {
    var n = 0;
    ORDER.forEach(function (id) {
      var b = data.buckets && data.buckets[id];
      if (b && Array.isArray(b.items)) n += b.items.length;
    });
    return n;
  }

  function matches(it) {
    if (!query) return true;
    var hay = ((it.full_name || "") + " " + (it.description || "")).toLowerCase();
    return hay.indexOf(query) !== -1;
  }

  function cleanFavs(arr) {
    if (!Array.isArray(arr)) return null;
    return arr.filter(function (x) { return typeof x === "string" && x.length; });
  }

  function getEmbeddedFavs() {
    try {
      if (Array.isArray(window.__WATCH_FAVS__)) return cleanFavs(window.__WATCH_FAVS__);
    } catch (e) {}
    return null;
  }

  function loadLocalFavs() {
    try {
      var raw = window.localStorage.getItem(FAV_KEY);
      if (!raw) return null;
      return cleanFavs(JSON.parse(raw));
    } catch (e) { return null; }
  }

  function loadFavs() {
    var emb = getEmbeddedFavs();
    if (emb) { favs = emb; return; }
    var local = loadLocalFavs();
    favs = local || [];
  }

  function saveFavs() {
    try { window.localStorage.setItem(FAV_KEY, JSON.stringify(favs)); } catch (e) {}
  }

  function persistFavsRemote() {
    try {
      fetch("/api/favs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ favs: favs })
      }).catch(function () {});
    } catch (e) {}
  }

  function fetchLiveFavs() {
    fetch("/api/favs", { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error("bad"); return r.json(); })
      .then(function (j) {
        var arr = j && cleanFavs(j.favs);
        if (!arr) return;
        favs = arr;
        saveFavs();
        refreshFavoritesLane();
      })
      .catch(function () {});
  }

  function isFav(name) {
    return favs.indexOf(name) !== -1;
  }

  function findRepo(name) {
    var found = null;
    if (data && data.buckets) {
      ORDER.forEach(function (id) {
        var b = data.buckets[id];
        if (!b || !Array.isArray(b.items)) return;
        b.items.forEach(function (it) {
          if (it && it.full_name === name && !found) found = it;
        });
      });
    }
    if (found) return found;
    return { full_name: name, description: "", html_url: "https://github.com/" + name };
  }

  function allFavRepos() {
    return favs.slice().reverse().map(findRepo);
  }

  function favRepos() {
    return allFavRepos().filter(matches);
  }

  function todayStr() {
    var d = new Date();
    function p(n) { return (n < 10 ? "0" : "") + n; }
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }

  function buildFavText(items) {
    var lines = ["# My Favorites (Copied " + todayStr() + ")"];
    items.forEach(function (it) {
      var name = it.full_name || "(unnamed)";
      var desc = String(it.description || "").replace(/\s+/g, " ").trim();
      var url = it.html_url || ("https://github.com/" + name);
      lines.push("- " + name + (desc ? " \u2014 " + desc : ""));
      lines.push("  " + url);
    });
    return lines.join("\n");
  }

  function copyText(text, btn) {
    var orig = btn.getAttribute("data-label") || btn.textContent;
    function done() {
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = orig; }, 2000);
    }
    function fallback() {
      try {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "absolute";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        done();
      } catch (e) {}
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, fallback);
    } else {
      fallback();
    }
  }

  function toggleFav(name) {
    if (!name) return;
    var i = favs.indexOf(name);
    if (i === -1) favs.push(name);
    else favs.splice(i, 1);
    saveFavs();
    persistFavsRemote();
    updateFavStars(name);
    refreshFavoritesLane();
  }

  function updateFavStars(name) {
    var on = isFav(name);
    document.querySelectorAll(".star").forEach(function (btn) {
      if (btn.getAttribute("data-fav") !== name) return;
      btn.classList.toggle("on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.textContent = on ? "★" : "☆";
    });
  }

  function refreshFavoritesLane() {
    if (active === "favorites") { render(); return; }
    var chip = document.querySelector('.chip[data-id="favorites"]');
    if (chip) chip.textContent = "Favorites" + (favs.length ? " (" + favs.length + ")" : "");
    if (active !== "all") return;
    var lane = el("fav-lane");
    if (!lane) { render(); return; }
    if (!favs.length) { render(); return; }
    var tmp = document.createElement("div");
    tmp.innerHTML = favoritesSectionHTML();
    var fresh = tmp.firstElementChild;
    if (!fresh) return;
    lane.parentNode.replaceChild(fresh, lane);
    bindCards(fresh);
    bindStars(fresh);
    bindCopy(fresh);
  }

  function favoritesSectionHTML() {
    var items = favRepos();
    var h = '<section class="fav-lane" id="fav-lane">';
    h += '<div class="fav-head"><h2 class="lane fav-title">Favorites</h2>';
    if (favs.length) {
      h += '<button type="button" class="copy-btn" id="copy-favs" data-label="Copy favorites as text">Copy favorites as text</button>';
    }
    h += "</div>";
    if (!favs.length) {
      h += '<p class="empty">No favorites yet. Tap the \u2606 on any repo to save it here.</p>';
    } else if (!items.length) {
      h += '<p class="empty">No matching favorites.</p>';
    } else {
      h += items.map(card).join("");
    }
    h += "</section>";
    return h;
  }

  function card(it) {
    var delta = "";
    if (it.star_delta !== null && it.star_delta !== undefined) {
      var d = Number(it.star_delta);
      var sign = d > 0 ? "+" : "";
      delta = '<span class="delta">' + esc(sign + d + " / 2d") + "</span>";
    }
    var pill = it.is_new ? '<span class="pill">new</span>' : "";
    var lang = it.language ? "<span>" + esc(it.language) + "</span>" : "";
    var url = it.html_url || "";
    var name = it.full_name || "(unnamed)";
    var fav = isFav(it.full_name);
    return (
      '<article class="card" tabindex="0">' +
      '<div class="card-top"><span class="name">' + esc(name) + "</span>" + pill +
      '<button type="button" class="star' + (fav ? " on" : "") + '" data-fav="' + esc(it.full_name || "") + '" aria-pressed="' + (fav ? "true" : "false") + '" aria-label="Toggle favorite for ' + esc(name) + '" title="Toggle favorite">' + (fav ? "★" : "☆") + "</button></div>" +
      (it.description ? '<p class="desc">' + esc(it.description) + "</p>" : '<p class="desc muted">No description.</p>') +
      '<div class="row"><span>★ ' + esc(fmtStars(it.stars)) + "</span>" +
      "<span>" + esc(fmtDate(it.created_at)) + "</span>" + lang + delta + "</div>" +
      (url ? '<a class="repo" href="' + esc(url) + '" target="_blank" rel="noopener">Open GitHub ↗</a>' : "") +
      "</article>"
    );
  }

  function bindCards(root) {
    var out = root;
    out.querySelectorAll(".card").forEach(function (cardEl) {
      cardEl.addEventListener("click", function (e) {
        if (e.target.closest("a")) return;
        if (e.target.closest(".star")) return;
        var open = cardEl.classList.contains("open");
        out.querySelectorAll(".card.open").forEach(function (c) { c.classList.remove("open"); });
        if (!open) cardEl.classList.add("open");
      });
      cardEl.addEventListener("keydown", function (e) {
        if (e.target.closest && e.target.closest(".star")) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          cardEl.click();
        }
      });
    });
  }

  function bindStars(root) {
    root.querySelectorAll(".star").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        toggleFav(btn.getAttribute("data-fav"));
      });
    });
  }

  function bindCopy(root) {
    var btn = root.querySelector ? root.querySelector("#copy-favs") : null;
    if (!btn) return;
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      copyText(buildFavText(allFavRepos()), btn);
    });
  }

  function render() {
    var meta = el("meta");
    meta.innerHTML = fmtRanked(data.ranked_at) + " · " + totalCount() + " repos";
    var chips = el("chips");
    var html = '<button class="chip" data-id="all" aria-selected="' + (active === "all") + '">All</button>';
    ORDER.forEach(function (id) {
      var b = data.buckets && data.buckets[id];
      if (!b) return;
      html += '<button class="chip" data-id="' + id + '" aria-selected="' + (active === id) + '">' + esc(b.title || id) + "</button>";
    });
    html += '<button class="chip" data-id="favorites" aria-selected="' + (active === "favorites") + '">Favorites' + (favs.length ? " (" + favs.length + ")" : "") + "</button>";
    chips.innerHTML = html;
    var btns = chips.querySelectorAll(".chip");
    btns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        active = btn.getAttribute("data-id");
        render();
      });
    });

    var out = el("content");
    var parts = [];
    if (active === "favorites") {
      parts.push(favoritesSectionHTML());
    } else if (active === "all") {
      if (favs.length) parts.push(favoritesSectionHTML());
      ORDER.filter(function (id) { return data.buckets && data.buckets[id]; }).forEach(function (id) {
        var b = data.buckets[id];
        var items = (b.items || []).filter(matches);
        parts.push("<h2 class=\"lane\">" + esc(b.title || id) + "</h2>");
        if (!items.length) {
          parts.push('<p class="empty">No repos in this lane right now.</p>');
        } else {
          parts.push(items.map(card).join(""));
        }
      });
    } else {
      var b = data.buckets[active];
      if (b) {
        var items = (b.items || []).filter(matches);
        parts.push("<h2 class=\"lane\">" + esc(b.title || active) + "</h2>");
        if (!items.length) {
          parts.push('<p class="empty">No repos in this lane right now.</p>');
        } else {
          parts.push(items.map(card).join(""));
        }
      }
    }
    out.innerHTML = parts.join("") || '<p class="empty">No repos in this lane right now.</p>';
    bindCards(out);
    bindStars(out);
    bindCopy(out);
  }

  function fail() {
    el("meta").textContent = "No ranked data yet";
    el("chips").innerHTML = "";
    el("content").innerHTML = '<p class="notice">No ranked data yet</p>';
  }

  function init() {
    loadFavs();
    el("search").addEventListener("input", function (e) {
      query = (e.target.value || "").trim().toLowerCase();
      if (data) render();
    });
    if (window.__WATCH_DATA__) {
      data = window.__WATCH_DATA__;
      if (!data || !data.buckets || !Object.keys(data.buckets).length) { fail(); return; }
      render();
      fetchLiveFavs();
      return;
    }
    fetch("../data/ranked/latest.json", { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error("bad"); return r.json(); })
      .then(function (j) {
        data = j;
        if (!data || !data.buckets || !Object.keys(data.buckets).length) { fail(); return; }
        render();
        fetchLiveFavs();
      })
      .catch(fail);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
