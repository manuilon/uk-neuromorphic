(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var revealEls = document.querySelectorAll("[data-reveal], .hero-visual");

  if (reduceMotion || !("IntersectionObserver" in window)) {
    return;
  }

  document.documentElement.classList.add("reveal-armed");

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );

  revealEls.forEach(function (el) {
    observer.observe(el);
  });
})();

(function () {
  "use strict";

  // Hide hand-added featured events once their day has passed.
  var todayIso = new Date().toISOString().slice(0, 10);
  // Visible featured titles are also dropped from the scraped grid, so they don't show twice.
  function titleKey(text) { return (text || "").toLowerCase().replace(/[^a-z0-9]+/g, ""); }
  var featuredKeys = {};
  Array.prototype.forEach.call(document.querySelectorAll(".event-featured[data-until]"), function (el) {
    if (el.dataset.until < todayIso) { el.hidden = true; return; }
    var h3 = el.querySelector("h3");
    if (h3) featuredKeys[titleKey(h3.textContent)] = true;
  });

  var grid = document.getElementById("events-grid");
  var pastSection = document.getElementById("events-past");
  var pastList = document.getElementById("events-past-list");
  if (!grid) return;

  var MAX_UPCOMING = 6;
  var MAX_PAST = 10;

  function setGridStatus(text) {
    grid.innerHTML = "";
    var p = document.createElement("p");
    p.className = "events-status";
    p.textContent = text;
    grid.appendChild(p);
  }

  function buildCard(event) {
    var article = document.createElement("article");
    article.className = "resource-card";

    var date = document.createElement("p");
    date.className = "event-date";
    date.textContent = event.date || "";
    article.appendChild(date);

    var h3 = document.createElement("h3");
    h3.textContent = event.title || "";
    article.appendChild(h3);

    var link = document.createElement("a");
    link.className = "resource-link";
    link.href = event.url || "#";
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "Details →";
    article.appendChild(link);

    return article;
  }

  function buildPastRow(event) {
    var li = document.createElement("li");
    li.className = "events-past-row";

    var link = document.createElement("a");
    link.href = event.url || "#";
    link.target = "_blank";
    link.rel = "noopener";

    var date = document.createElement("span");
    date.className = "events-past-date";
    date.textContent = event.date || "";
    link.appendChild(date);

    var title = document.createElement("span");
    title.className = "events-past-title";
    title.textContent = event.title || "";
    link.appendChild(title);

    li.appendChild(link);
    return li;
  }

  fetch("assets/events.json")
    .then(function (res) {
      if (!res.ok) throw new Error("events.json " + res.status);
      return res.json();
    })
    .then(function (data) {
      var all = Array.isArray(data.events) ? data.events : [];
      var upcoming = all.filter(function (e) {
        return e.status === "upcoming" && !featuredKeys[titleKey(e.title)];
      }).slice(0, MAX_UPCOMING);
      var past = all.filter(function (e) { return e.status === "past"; }).slice(-MAX_PAST).reverse();

      if (!upcoming.length) {
        setGridStatus(grid.dataset.emptyText || "No upcoming events right now.");
      } else {
        grid.innerHTML = "";
        upcoming.forEach(function (event) {
          grid.appendChild(buildCard(event));
        });
      }

      if (pastSection && pastList) {
        if (!past.length) {
          pastSection.hidden = true;
        } else {
          pastList.innerHTML = "";
          past.forEach(function (event) {
            pastList.appendChild(buildPastRow(event));
          });
          pastSection.hidden = false;
        }
      }
    })
    .catch(function () {
      setGridStatus(grid.dataset.errorText || "Couldn't load events right now.");
      if (pastSection) pastSection.hidden = true;
    });
})();

(function () {
  "use strict";

  var grid = document.getElementById("news-grid");
  if (!grid) return;

  var PER_SOURCE = 3;
  var columns = grid.querySelectorAll(".news-col");

  function formatDate(iso) {
    var d = new Date(iso + "T00:00:00Z");
    if (isNaN(d.getTime())) return iso || "";
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  }

  function setStatus(list, text) {
    list.innerHTML = "";
    var li = document.createElement("li");
    li.className = "news-status";
    li.textContent = text;
    list.appendChild(li);
  }

  function buildItem(item) {
    var li = document.createElement("li");

    var link = document.createElement("a");
    link.href = item.url || "#";
    link.target = "_blank";
    link.rel = "noopener";
    if (item.summary) link.title = item.summary;

    var date = document.createElement("span");
    date.className = "news-date";
    date.textContent = formatDate(item.date);
    link.appendChild(date);

    var title = document.createElement("span");
    title.className = "news-title";
    title.textContent = item.title || "";
    link.appendChild(title);

    li.appendChild(link);
    return li;
  }

  fetch("assets/news.json")
    .then(function (res) {
      if (!res.ok) throw new Error("news.json " + res.status);
      return res.json();
    })
    .then(function (data) {
      var all = Array.isArray(data.news) ? data.news : [];
      columns.forEach(function (col) {
        var list = col.querySelector(".news-list");
        var items = all
          .filter(function (n) { return n.source === col.dataset.source; })
          .sort(function (a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : 0; })
          .slice(0, PER_SOURCE);

        if (!items.length) {
          setStatus(list, grid.dataset.emptyText || "No recent posts.");
          return;
        }
        list.innerHTML = "";
        items.forEach(function (item) {
          list.appendChild(buildItem(item));
        });
      });
    })
    .catch(function () {
      columns.forEach(function (col) {
        setStatus(col.querySelector(".news-list"), grid.dataset.errorText || "Couldn't load news right now.");
      });
    });
})();

(function () {
  "use strict";

  var mapEl = document.getElementById("network-map");
  if (!mapEl) return;

  var legendEl = document.getElementById("network-legend");
  var listWrap = document.getElementById("network-list-wrap");
  var listEl = document.getElementById("network-list");
  var listToggle = document.getElementById("network-list-toggle");

  // Same tokens as styles.css: anchor, companion, accent.
  var TYPE_COLOURS = { Academia: "#423E8C", Industry: "#A85BA3", Other: "#007A6E" };
  var TYPE_ORDER = ["Academia", "Industry", "Other"];

  function colourFor(type) {
    return TYPE_COLOURS[type] || "#625F78";
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function safeUrl(url) {
    return /^https?:\/\//i.test(url || "") ? url : "";
  }

  function showStatus(text) {
    mapEl.innerHTML = "";
    mapEl.appendChild(el("p", "events-status", text));
  }

  function buildPopup(orgs) {
    var wrap = el("div", "map-popup");
    orgs.forEach(function (org) {
      var block = el("div", "map-popup-org");
      block.appendChild(el("div", "map-popup-name", org.name));
      block.appendChild(el("div", "map-popup-type", org.type));
      if (org.specialisms && org.specialisms.length) {
        block.appendChild(el("div", "map-popup-specialisms", org.specialisms.join(" · ")));
      }
      var url = safeUrl(org.website);
      if (url) {
        var link = el("a", "map-popup-link", "Website →");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener";
        block.appendChild(link);
      }
      wrap.appendChild(block);
    });
    return wrap;
  }

  function buildLegend(orgs) {
    if (!legendEl) return;
    var counts = {};
    orgs.forEach(function (o) { counts[o.type] = (counts[o.type] || 0) + 1; });
    var types = TYPE_ORDER.filter(function (t) { return counts[t]; });
    Object.keys(counts).forEach(function (t) {
      if (types.indexOf(t) === -1) types.push(t);
    });
    types.forEach(function (type) {
      var li = el("li");
      var dot = el("span", "legend-dot");
      dot.style.background = colourFor(type);
      li.appendChild(dot);
      li.appendChild(document.createTextNode(type + " (" + counts[type] + ")"));
      legendEl.appendChild(li);
    });
  }

  function buildList(orgs) {
    if (!listWrap || !listEl) return;
    orgs.slice().sort(function (a, b) { return a.name.localeCompare(b.name); }).forEach(function (org) {
      var li = el("li", "events-past-row");
      var url = safeUrl(org.website);
      var row = el(url ? "a" : "div");
      if (url) {
        row.href = url;
        row.target = "_blank";
        row.rel = "noopener";
      }
      row.appendChild(el("span", "events-past-date", org.type));
      row.appendChild(el("span", "events-past-title", org.name));
      li.appendChild(row);
      listEl.appendChild(li);
    });
    if (listToggle) listToggle.textContent = "All organisations (" + orgs.length + ")";
    listWrap.hidden = false;
  }

  fetch("assets/network.json")
    .then(function (res) {
      if (!res.ok) throw new Error("network.json " + res.status);
      return res.json();
    })
    .then(function (data) {
      var orgs = (Array.isArray(data.organisations) ? data.organisations : []).filter(function (o) {
        return isFinite(o.lat) && isFinite(o.lng) && o.name;
      });
      if (!orgs.length) {
        showStatus("The network map is being updated — see the NeuMat site in the meantime.");
        return;
      }

      buildLegend(orgs);
      buildList(orgs);

      if (typeof L === "undefined") {
        showStatus("Couldn't load the map right now — the full list is below.");
        return;
      }

      var map = L.map(mapEl, { scrollWheelZoom: false, zoomSnap: 0.25 });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(map);

      // Several organisations share a building (e.g. two Imperial departments);
      // one marker per location keeps them all reachable.
      var groups = {};
      orgs.forEach(function (org) {
        var key = Number(org.lat).toFixed(4) + "," + Number(org.lng).toFixed(4);
        (groups[key] = groups[key] || []).push(org);
      });

      // Academia first, so the few industry/other markers draw on top in London.
      function rank(key) {
        var i = TYPE_ORDER.indexOf(groups[key][0].type);
        return i === -1 ? TYPE_ORDER.length : i;
      }
      var markers = Object.keys(groups).sort(function (a, b) { return rank(a) - rank(b); }).map(function (key) {
        var group = groups[key];
        var marker = L.circleMarker([group[0].lat, group[0].lng], {
          radius: group.length > 1 ? 9 : 7,
          color: "#fff",
          weight: 2,
          fillColor: colourFor(group[0].type),
          fillOpacity: 0.9
        });
        marker.bindPopup(buildPopup(group), { maxWidth: 280 });
        if (!L.Browser.mobile) {
          marker.bindTooltip(group.map(function (o) { return o.name; }).join(" / "), { direction: "top", offset: [0, -6] });
        }
        return marker.addTo(map);
      });

      map.fitBounds(L.featureGroup(markers).getBounds(), { padding: [30, 30] });

      // Scroll-wheel zoom only after the visitor engages with the map,
      // so scrolling down the page doesn't get trapped.
      map.on("click focus", function () { map.scrollWheelZoom.enable(); });
      mapEl.addEventListener("mouseleave", function () { map.scrollWheelZoom.disable(); });
    })
    .catch(function () {
      showStatus("Couldn't load the network map right now — please check back later.");
      if (listWrap) listWrap.hidden = true;
    });
})();
