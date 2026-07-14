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
      var upcoming = all.filter(function (e) { return e.status === "upcoming"; }).slice(0, MAX_UPCOMING);
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
