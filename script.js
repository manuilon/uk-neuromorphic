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

  var grid = document.getElementById("events-grid");
  if (!grid) return;

  var MAX_EVENTS = 6;

  function setStatus(text) {
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

    var meta = document.createElement("p");
    var metaParts = [];
    if (event.location) metaParts.push(event.location);
    metaParts.push("Hosted by " + (event.sourceLabel || "the ecosystem"));
    meta.textContent = metaParts.join(" · ");
    article.appendChild(meta);

    var link = document.createElement("a");
    link.className = "resource-link";
    link.href = event.url || "#";
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "Details →";
    article.appendChild(link);

    return article;
  }

  fetch("assets/events.json")
    .then(function (res) {
      if (!res.ok) throw new Error("events.json " + res.status);
      return res.json();
    })
    .then(function (data) {
      var events = Array.isArray(data.events) ? data.events.slice(0, MAX_EVENTS) : [];
      if (!events.length) {
        setStatus(grid.dataset.emptyText || "No upcoming events right now.");
        return;
      }
      grid.innerHTML = "";
      events.forEach(function (event) {
        grid.appendChild(buildCard(event));
      });
    })
    .catch(function () {
      setStatus(grid.dataset.errorText || "Couldn't load events right now.");
    });
})();
