// The Maps tab: every place a chapter (or the whole book) names, on a map.
//
// Two kinds of book carry one:
//  - the Bible: /books/maps/bible/<BB>.json, one file per book of the Bible
//    (BB = the canonical number bibleKeyFromHeading uses). Locations come
//    from OpenBible.info's Bible Geocoding Data (CC BY 4.0), which records
//    for every place each verse that names it and how sure scholars are of
//    the site. Russian names are only shown where they are the Synodal
//    text's own word for the place (checked against Wikidata's label);
//    otherwise the English name stands in.
//  - a novel whose catalogue entry says "maps": "<name>" (War and Peace):
//    /books/maps/<name>.json lists real places with Wikidata coordinates and
//    a search pattern; which chapters mention a place is found here, by
//    searching the chapter texts the reader already has, so the data never
//    depends on how the FB2 was split into chapters.
//
// Leaflet is loaded from cdnjs the first time the tab opens, so it costs the
// rest of the site nothing.
import { useState, useEffect, useRef, useMemo } from "react";

var LEAFLET_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js";
var LEAFLET_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css";
var leafletPromise = null;
function loadLeaflet() {
  if (typeof window === "undefined") return Promise.reject(new Error("no window"));
  if (window.L && window.L.map) return Promise.resolve(window.L);
  if (leafletPromise) return leafletPromise;
  leafletPromise = new Promise(function(resolve, reject) {
    if (!document.querySelector('link[data-leaflet]')) {
      var css = document.createElement("link");
      css.rel = "stylesheet"; css.href = LEAFLET_CSS; css.setAttribute("data-leaflet", "1");
      document.head.appendChild(css);
    }
    var s = document.createElement("script");
    s.src = LEAFLET_JS; s.async = true;
    s.onload = function() { window.L ? resolve(window.L) : reject(new Error("Leaflet failed to load")); };
    s.onerror = function() { leafletPromise = null; reject(new Error("Leaflet failed to load")); };
    document.head.appendChild(s);
  });
  return leafletPromise;
}

var dataCache = {};
function loadJSON(url) {
  if (!dataCache[url]) {
    dataCache[url] = fetch(url, { credentials: "same-origin" }).then(function(r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).catch(function(e) { delete dataCache[url]; throw e; });
  }
  return dataCache[url];
}

// Base maps. Topographic first: coloured relief, rivers, and fine detail as
// you zoom in.
var BASEMAPS = [
  { id: "topo", label: "Terrain",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    attr: "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, FAO, NOAA, USGS, &copy; OpenStreetMap contributors", max: 19 },
  { id: "physical", label: "Relief",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}",
    attr: "Tiles &copy; Esri &mdash; US National Park Service", max: 8 },
  { id: "sat", label: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr: "Tiles &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics", max: 19 },
  { id: "street", label: "Modern map",
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr: "&copy; OpenStreetMap contributors", max: 19 },
];

// One colour per kind of place, shared by the pins and the legend.
var KINDS = [
  { k: "settlement", label: "Town or city", c: "#b8432f", match: /^(settlement|city|town|village)$/ },
  { k: "region", label: "Land or region", c: "#3d8a52", match: /^(region|natural area)$/ },
  { k: "mountain", label: "Mountain or hill", c: "#8a5a2b", match: /^(mountain|hill|mountain range|mountain pass|cliff|rock)$/ },
  { k: "water", label: "Sea, river or spring", c: "#2167b3", match: /^(river|body of water|spring|well|sea|lake|wadi|canal|pool|ford)$/ },
  { k: "valley", label: "Valley or plain", c: "#7a9a1e", match: /^(valley|plain|field|garden|forest|desert)$/ },
  { k: "island", label: "Island", c: "#0e8f8f", match: /^(island|peninsula|cape)$/ },
  { k: "camp", label: "Camp on the way", c: "#d08a12", match: /^(campsite)$/ },
  { k: "built", label: "Gate, building or road", c: "#7048b8", match: /^(gate|structure|road|tower|monastery|altar|tomb|special|people group)$/ },
  { k: "battle", label: "Battle", c: "#1b1613", match: /^battle$/ },
];
function kindOf(t) {
  for (var i = 0; i < KINDS.length; i++) if (KINDS[i].match.test(t || "")) return KINDS[i];
  return { k: "other", label: "Other", c: "#5b5b66" };
}
var CONF_TEXT = [
  "Site uncertain — scholars disagree or only guess at it",
  "Site probable",
  "Site well established",
];

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function(c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
// "Aphek 2" → "Aphek": OpenBible numbers places that share a name.
function cleanEn(s) { return String(s || "").replace(/\s+\d+$/, ""); }
var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function fmtDate(d) {
  var m = String(d || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return "";
  var mo = +m[2], day = +m[3];
  if (!mo) return m[1];
  return (day ? day + " " : "") + MONTHS[mo - 1] + " " + m[1];
}

// Where a verse starts in a chapter's text, and where the place's own word
// sits inside it, so a tap lands on the word rather than the chapter top.
function verseOffset(text, verse, form) {
  text = String(text || "");
  var re = new RegExp("(^|\\n)[ \\t]*" + verse + "(?=[\\s.)])");
  var m = re.exec(text);
  var at = m ? m.index + m[1].length : -1;
  if (form) {
    var from = at < 0 ? 0 : at;
    var f = text.indexOf(form, from);
    if (f >= 0 && (at < 0 || f - at < 1500)) return f;
  }
  return at < 0 ? 0 : at;
}

export function BookMaps(props) {
  var mode = props.mode;                 // "bible" | "novel"
  var chapters = props.chapters || [];
  var cidx = props.cidx || 0;
  var boxRef = useRef(null);
  var mapRef = useRef(null);
  var layerRef = useRef(null);
  var markersRef = useRef({});
  var [L, setL] = useState(null);
  var [err, setErr] = useState("");
  var [data, setData] = useState(null);
  var [scope, setScope] = useState("");  // "chapter" | "all"
  var [routesOn, setRoutesOn] = useState({});
  var [sel, setSel] = useState("");

  // Which Bible book and chapter the reader is in.
  var keyOf = props.keyOf || function() { return null; };
  var curKey = mode === "bible" ? keyOf(cidx) : null;
  var bookNo = curKey ? curKey.split("-")[0] : "";
  var chapNo = curKey ? String(+curKey.split("-")[1]) : "";

  useEffect(function() {
    var alive = true;
    loadLeaflet().then(function(l) { if (alive) setL(l); })
      .catch(function() { if (alive) setErr("The map library could not be loaded. Check the connection and open the tab again."); });
    return function() { alive = false; };
  }, []);

  var url = mode === "bible" ? (bookNo ? "/books/maps/bible/" + bookNo + ".json" : "")
                             : "/books/maps/" + props.name + ".json";
  useEffect(function() {
    if (!url) { setData(null); return; }
    var alive = true;
    setData(null);
    loadJSON(url).then(function(d) { if (alive) setData(d); })
      .catch(function() { if (alive) setData({ places: [], ch: {}, missing: true }); });
    return function() { alive = false; };
  }, [url]);

  // Chapter index for every Bible chapter of this book, by its number.
  var bibleCi = useMemo(function() {
    var m = {};
    if (mode !== "bible") return m;
    for (var i = 0; i < chapters.length; i++) {
      var k = keyOf(i);
      if (k && k.split("-")[0] === bookNo) m[String(+k.split("-")[1])] = i;
    }
    return m;
  }, [mode, chapters, bookNo]);

  // Novel: which chapters name which place, found by searching the text.
  var novelHits = useMemo(function() {
    if (mode !== "novel" || !data || !data.places) return null;
    var res = {};
    data.places.forEach(function(p) {
      var re;
      try { re = new RegExp(p.rx, "g"); } catch (e) { return; }
      var per = [];
      for (var i = 0; i < chapters.length; i++) {
        var t = (chapters[i] && chapters[i].text) || "";
        re.lastIndex = 0;
        var m = re.exec(t), n = 0, first = -1;
        while (m) { if (first < 0) first = m.index; n++; if (m[0] === "") re.lastIndex++; m = re.exec(t); }
        if (n) per.push({ ci: i, n: n, off: first });
      }
      res[p.id] = per;
    });
    return res;
  }, [mode, data, chapters]);

  // The places to draw, in reading order for a chapter.
  var view = useMemo(function() {
    if (!data || !data.places) return { items: [], hasChapter: false };
    var items = [];
    if (mode === "bible") {
      var rowsHere = (data.ch && data.ch[chapNo]) || [];
      var byPlace = {};
      var useAll = scope === "all" || (scope === "" && !rowsHere.length);
      var chKeys = useAll ? Object.keys(data.ch || {}) : [chapNo];
      chKeys.sort(function(a, b) { return +a - +b; });
      chKeys.forEach(function(c) {
        (data.ch[c] || []).forEach(function(r) {
          var pi = r[0];
          if (!byPlace[pi]) {
            var p = data.places[pi];
            byPlace[pi] = { id: "p" + pi, ru: p[0], en: cleanEn(p[1]), lat: p[2], lon: p[3], conf: p[4],
                            type: p[5], slug: p[6], refs: [] };
            items.push(byPlace[pi]);
          }
          byPlace[pi].refs.push({ c: c, v: r[1], form: r[2] || "" });
        });
      });
      return { items: items, hasChapter: rowsHere.length > 0, all: useAll };
    }
    var hereIds = {};
    (data.places || []).forEach(function(p) {
      var hits = (novelHits && novelHits[p.id]) || [];
      hits.forEach(function(h) { if (h.ci === cidx) hereIds[p.id] = h.off; });
    });
    var hasChapter = Object.keys(hereIds).length > 0;
    var useAllN = scope === "all" || (scope === "" && !hasChapter);
    (data.places || []).forEach(function(p) {
      var hits = (novelHits && novelHits[p.id]) || [];
      if (!hits.length) return;
      if (!useAllN && hereIds[p.id] == null) return;
      items.push({ id: p.id, ru: p.ru, en: p.en, lat: p.ll[0], lon: p.ll[1], conf: 2,
                   type: p.k, date: p.d || "", date2: p.d2 || "", hits: hits,
                   order: useAllN ? 0 : hereIds[p.id] });
    });
    if (!useAllN) items.sort(function(a, b) { return a.order - b.order; });
    return { items: items, hasChapter: hasChapter, all: useAllN };
  }, [data, mode, scope, chapNo, cidx, novelHits]);

  // Build the map once Leaflet and the box are both there.
  useEffect(function() {
    if (!L || !boxRef.current || mapRef.current) return;
    var map = L.map(boxRef.current, { zoomControl: true, worldCopyJump: true, attributionControl: true });
    var bases = {};
    BASEMAPS.forEach(function(b, i) {
      var layer = L.tileLayer(b.url, { attribution: b.attr, maxNativeZoom: b.max, maxZoom: 18, crossOrigin: true });
      bases[b.label] = layer;
      if (i === 0) layer.addTo(map);
    });
    L.control.layers(bases, null, { position: "topright", collapsed: true }).addTo(map);
    L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);
    map.setView([31.8, 35.2], 6);
    mapRef.current = map;
    layerRef.current = L.layerGroup().addTo(map);
    var ro = null;
    try {
      ro = new ResizeObserver(function() { map.invalidateSize(); });
      ro.observe(boxRef.current);
    } catch (e) {}
    setTimeout(function() { map.invalidateSize(); }, 50);
    return function() { try { ro && ro.disconnect(); } catch (e) {} map.remove(); mapRef.current = null; layerRef.current = null; };
  }, [L]);

  // Taps on the "go to the text" links inside popups.
  useEffect(function() {
    var box = boxRef.current;
    if (!box) return;
    var onClick = function(e) {
      var a = e.target && e.target.closest ? e.target.closest("[data-jump]") : null;
      if (!a) return;
      e.preventDefault();
      var ci = +a.getAttribute("data-ci"), off = +a.getAttribute("data-off");
      if (props.onJump) props.onJump(ci, off);
    };
    box.addEventListener("click", onClick);
    return function() { box.removeEventListener("click", onClick); };
  }, [props.onJump, L]);

  var refLink = function(item, r) {
    if (mode === "bible") {
      var ci = bibleCi[r.c];
      var lab = r.c + ":" + r.v;
      if (ci == null) return '<span class="bm-ref off">' + esc(lab) + "</span>";
      var off = verseOffset(chapters[ci] && chapters[ci].text, r.v, r.form);
      return '<a href="#" class="bm-ref" data-jump="1" data-ci="' + ci + '" data-off="' + off + '">' + esc(lab) +
             (r.form ? ' <i>' + esc(r.form) + "</i>" : "") + "</a>";
    }
    var label = props.chapterLabel ? props.chapterLabel(r.ci) : ("Chapter " + (r.ci + 1));
    return '<a href="#" class="bm-ref" data-jump="1" data-ci="' + r.ci + '" data-off="' + r.off + '">' + esc(label) +
           (r.n > 1 ? ' <i>×' + r.n + "</i>" : "") + "</a>";
  };

  var popupHtml = function(item, num) {
    var kd = kindOf(item.type);
    var h = '<div class="bm-pop">';
    h += '<div class="bm-pop-k" style="color:' + kd.c + '">' + (num ? num + " · " : "") + esc(kd.label) + "</div>";
    h += '<div class="bm-pop-ru">' + esc(item.ru || item.en) + "</div>";
    if (item.ru) h += '<div class="bm-pop-en">' + esc(item.en) + "</div>";
    if (item.date) h += '<div class="bm-pop-date">' + esc(fmtDate(item.date)) + (item.date2 ? " – " + esc(fmtDate(item.date2)) : "") + "</div>";
    if (mode === "bible") {
      h += '<div class="bm-pop-conf c' + item.conf + '">' + esc(CONF_TEXT[item.conf] || "") + "</div>";
      var refs = item.refs.slice(0, 40);
      h += '<div class="bm-pop-refs">' + refs.map(function(r) { return refLink(item, r); }).join("") +
           (item.refs.length > 40 ? '<span class="bm-ref off">+' + (item.refs.length - 40) + " more</span>" : "") + "</div>";
      if (item.slug) h += '<a class="bm-src" target="_blank" rel="noopener" href="https://www.openbible.info/geo/ancient/' +
                          esc(item.slug) + '">About this place — OpenBible.info ↗</a>';
    } else {
      var hits = item.hits;
      var show = view.all ? hits.slice(0, 30) : hits.filter(function(x) { return x.ci === cidx; }).concat(hits.filter(function(x) { return x.ci !== cidx; }).slice(0, 12));
      h += '<div class="bm-pop-n">' + hits.length + (hits.length === 1 ? " chapter mentions it" : " chapters mention it") + "</div>";
      h += '<div class="bm-pop-refs">' + show.map(function(r) { return refLink(item, r); }).join("") + "</div>";
    }
    return h + "</div>";
  };

  // Draw.
  useEffect(function() {
    var map = mapRef.current, group = layerRef.current;
    if (!L || !map || !group) return;
    group.clearLayers();
    markersRef.current = {};
    var items = view.items;
    var pts = [];
    var numbered = !view.all;
    var labelsAlways = items.length <= 30;

    // Routes (novel, whole-book view or when switched on).
    if (mode === "novel" && data && data.routes) {
      var byId = {};
      (data.places || []).forEach(function(p) { byId[p.id] = p; });
      data.routes.forEach(function(rt) {
        if (!routesOn[rt.id]) return;
        var ll = rt.via.map(function(id) { return byId[id] ? byId[id].ll : null; }).filter(Boolean);
        L.polyline(ll, { color: "#fff", weight: 7, opacity: 0.7 }).addTo(group);
        var line = L.polyline(ll, { color: rt.color, weight: 3.5, opacity: 0.95, dashArray: rt.dash ? "8 7" : null }).addTo(group);
        line.bindTooltip(rt.en, { sticky: true, className: "bm-tip" });
        // Arrowheads at each leg's middle show the direction of march.
        for (var i = 0; i + 1 < ll.length; i++) {
          var a = ll[i], b = ll[i + 1];
          var mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
          var ang = Math.atan2(b[0] - a[0], (b[1] - a[1]) * Math.cos(mid[0] * Math.PI / 180)) * 180 / Math.PI;
          L.marker(mid, { interactive: false, icon: L.divIcon({ className: "bm-arrow-wrap",
            html: '<span class="bm-arrow" style="color:' + rt.color + ';transform:rotate(' + (-ang) + 'deg)">➤</span>',
            iconSize: [16, 16], iconAnchor: [8, 8] }) }).addTo(group);
        }
        ll.forEach(function(p) { pts.push(p); });
      });
    }

    items.forEach(function(it, i) {
      var kd = kindOf(it.type);
      var count = mode === "bible" ? it.refs.length : it.hits.reduce(function(s, h) { return s + h.n; }, 0);
      var size = numbered ? 26 : Math.round(Math.min(34, 12 + Math.sqrt(count) * 3));
      var html;
      if (kd.k === "battle") {
        html = '<span class="bm-pin battle" style="width:' + (size + 4) + 'px;height:' + (size + 4) + 'px">⚔</span>';
        size += 4;
      } else {
        html = '<span class="bm-pin conf' + it.conf + '" style="--c:' + kd.c + ';width:' + size + 'px;height:' + size + 'px">' +
               (numbered ? (i + 1) : "") + "</span>";
      }
      var mk = L.marker([it.lat, it.lon], {
        icon: L.divIcon({ className: "bm-pin-wrap", html: html, iconSize: [size, size], iconAnchor: [size / 2, size / 2] }),
        riseOnHover: true, zIndexOffset: kd.k === "battle" ? 500 : count,
      });
      var name = (it.ru || it.en) + (mode === "bible" && it.conf === 0 ? "?" : "");
      mk.bindTooltip(esc(name), { permanent: labelsAlways, direction: "right", offset: [size / 2, 0], className: "bm-lbl" + (it.ru ? "" : " en") });
      mk.bindPopup(popupHtml(it, numbered ? i + 1 : 0), { maxWidth: 300, minWidth: 200, autoPanPadding: [24, 24] });
      mk.on("click", function() { setSel(it.id); });
      mk.addTo(group);
      markersRef.current[it.id] = mk;
      pts.push([it.lat, it.lon]);
    });
    if (pts.length === 1) map.setView(pts[0], 9);
    else if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.12), { maxZoom: 10 });
    // Labels shown always would pile up when zoomed far out; show them from
    // a sensible zoom on, and always on hover.
    if (!labelsAlways) {
      var sync = function() {
        var on = map.getZoom() >= 8;
        Object.keys(markersRef.current).forEach(function(id) {
          var m = markersRef.current[id], t = m.getTooltip();
          if (!t) return;
          if (on && !t.options.permanent) { m.unbindTooltip(); m.bindTooltip(t.getContent(), Object.assign({}, t.options, { permanent: true })); }
          else if (!on && t.options.permanent) { m.unbindTooltip(); m.bindTooltip(t.getContent(), Object.assign({}, t.options, { permanent: false })); }
        });
      };
      map.on("zoomend", sync);
      sync();
      return function() { map.off("zoomend", sync); };
    }
  }, [L, view, routesOn, data, mode]);

  var focus = function(it) {
    var map = mapRef.current, mk = markersRef.current[it.id];
    if (!map || !mk) return;
    setSel(it.id);
    map.flyTo(mk.getLatLng(), Math.max(map.getZoom(), 9), { duration: 0.6 });
    setTimeout(function() { mk.openPopup(); }, 650);
  };

  var kindsShown = {};
  view.items.forEach(function(it) { var k = kindOf(it.type); kindsShown[k.k] = k; });

  var title = mode === "bible"
    ? (view.all ? "Every place in " + (props.bookName || "this book") : "Places in chapter " + chapNo)
    : (view.all ? "Every place in the novel" : "Places in this chapter");

  return (
    <div className="bm">
      <style>{BM_CSS}</style>
      <div className="bm-head">
        <div className="bm-title">{title}</div>
        <div className="bm-seg">
          <button className={!view.all ? "on" : ""} disabled={!view.hasChapter}
            title={view.hasChapter ? "" : "No place is named in this chapter"}
            onClick={function() { setScope("chapter"); }}>This chapter</button>
          <button className={view.all ? "on" : ""} onClick={function() { setScope("all"); }}>
            {mode === "bible" ? "Whole book" : "Whole novel"}</button>
        </div>
      </div>
      {mode === "novel" && data && data.routes && (
        <div className="bm-routes">
          {data.routes.map(function(rt) {
            var on = !!routesOn[rt.id];
            return (
              <button key={rt.id} className={"bm-route" + (on ? " on" : "")}
                onClick={function() { var n = Object.assign({}, routesOn); n[rt.id] = !on; setRoutesOn(n); setScope("all"); }}>
                <span className={"bm-swatch" + (rt.dash ? " dash" : "")} style={{ background: rt.dash ? "none" : rt.color, borderColor: rt.color }} />
                {rt.en}
              </button>
            );
          })}
        </div>
      )}
      <div className="bm-frame">
        <div className="bm-map" ref={boxRef} />
        {!L && !err && <div className="bm-over">Unrolling the map…</div>}
        {err && <div className="bm-over">{err}</div>}
        {L && data && !view.items.length && !(mode === "novel" && Object.keys(routesOn).some(function(k){ return routesOn[k]; })) && (
          <div className="bm-over">{data.missing ? "No map for this book yet." : (mode === "bible" && !bookNo ? "Open a chapter of the Bible to see its places." : "No mapped places here.")}</div>
        )}
      </div>
      {Object.keys(kindsShown).length > 0 && (
        <div className="bm-legend">
          {Object.keys(kindsShown).map(function(k) {
            var kd = kindsShown[k];
            return <span key={k} className="bm-leg"><span className={"bm-dot" + (k === "battle" ? " battle" : "")} style={{ background: kd.c }}>{k === "battle" ? "⚔" : ""}</span>{kd.label}</span>;
          })}
          {mode === "bible" && <span className="bm-leg"><span className="bm-dot conf0" style={{ background: "#b8432f" }} />Site uncertain</span>}
        </div>
      )}
      {view.items.length > 0 && (
        <ol className={"bm-list" + (view.all ? " all" : "")}>
          {view.items.map(function(it, i) {
            var kd = kindOf(it.type);
            var count = mode === "bible" ? it.refs.length : it.hits.length;
            var first = mode === "bible" ? it.refs[0] : null;
            return (
              <li key={it.id} className={sel === it.id ? "on" : ""} onClick={function() { focus(it); }}>
                <span className={"bm-num" + (kd.k === "battle" ? " battle" : "")} style={{ background: kd.c }}>{kd.k === "battle" ? "⚔" : (view.all ? "" : i + 1)}</span>
                <span className="bm-name">{it.ru || it.en}{mode === "bible" && it.conf === 0 ? "?" : ""}</span>
                {it.ru && <span className="bm-en">{it.en}</span>}
                <span className="bm-meta">
                  {it.date ? fmtDate(it.date) + " · " : ""}
                  {mode === "bible"
                    ? (view.all ? count + (count === 1 ? " verse" : " verses") : "v. " + it.refs.map(function(r){ return r.v; }).join(", "))
                    : count + (count === 1 ? " chapter" : " chapters")}
                </span>
              </li>
            );
          })}
        </ol>
      )}
      <div className="bm-credit">
        {mode === "bible"
          ? <>Locations: <a href="https://www.openbible.info/geo/" target="_blank" rel="noopener">OpenBible.info</a> Bible Geocoding Data (CC BY 4.0). Russian names as written in the Synodal translation; places it names differently keep their English name. A “?” marks a site scholars are unsure of.</>
          : <>Coordinates and battle dates (new style) from <a href="https://www.wikidata.org" target="_blank" rel="noopener">Wikidata</a>. Chapters are found by searching the text; routes connect the places the novel names along the way.</>}
      </div>
    </div>
  );
}

var BM_CSS = [
  ".bm{display:flex;flex-direction:column;gap:10px;padding-bottom:24px}",
  ".bm-head{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px}",
  ".bm-title{font-family:var(--display,Georgia,serif);font-size:1.35rem;color:var(--ink,#1b1613)}",
  ".bm-seg{display:inline-flex;border:1px solid var(--rule,rgba(27,22,19,.24))}",
  ".bm-seg button{font:500 .78rem/1 var(--sans,system-ui);letter-spacing:.06em;text-transform:uppercase;padding:7px 12px;background:none;border:0;color:var(--ink-2,#555);cursor:pointer}",
  ".bm-seg button+button{border-left:1px solid var(--rule,rgba(27,22,19,.24))}",
  ".bm-seg button.on{background:var(--ink,#1b1613);color:var(--paper,#f4efe5)}",
  ".bm-seg button:disabled{opacity:.35;cursor:default}",
  ".bm-routes{display:flex;flex-wrap:wrap;gap:6px}",
  ".bm-route{display:inline-flex;align-items:center;gap:7px;font:.8rem/1.2 var(--sans,system-ui);padding:6px 10px;background:none;border:1px solid var(--rule-soft,rgba(27,22,19,.11));color:var(--ink-2,#555);cursor:pointer}",
  ".bm-route.on{border-color:var(--ink,#1b1613);color:var(--ink,#1b1613);background:var(--paper-3,#fbf8f2)}",
  ".bm-swatch{width:22px;height:0;border-top:3px solid;display:inline-block}",
  ".bm-swatch.dash{border-top-style:dashed}",
  ".bm-frame{position:relative;padding:6px;background:linear-gradient(135deg,#7a5a32,#c8a464 30%,#8a6638 52%,#d6b77a 75%,#6e4f2a);box-shadow:0 2px 14px rgba(40,25,10,.28)}",
  ".bm-map{height:min(62vh,560px);min-height:320px;width:100%;background:#d8cdb4;outline:1px solid rgba(0,0,0,.35)}",
  ".bm-over{position:absolute;inset:6px;display:flex;align-items:center;justify-content:center;text-align:center;padding:20px;background:rgba(244,239,229,.82);font-family:var(--serif,Georgia,serif);font-style:italic;color:var(--ink-2,#555);z-index:500}",
  ".bm-pin-wrap{background:none;border:0}",
  ".bm-pin{display:flex;align-items:center;justify-content:center;border-radius:50%;background:radial-gradient(circle at 35% 30%,rgba(255,255,255,.55),rgba(255,255,255,0) 45%),var(--c);border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.45),0 0 0 1px rgba(0,0,0,.25);color:#fff;font:700 12px/1 var(--sans,system-ui);text-shadow:0 1px 1px rgba(0,0,0,.4);box-sizing:border-box;transition:transform .15s}",
  ".bm-pin:hover{transform:scale(1.18)}",
  ".bm-pin.conf0{border-style:dashed;opacity:.82}",
  ".bm-pin.battle{background:radial-gradient(circle at 35% 30%,#fff3c4,#d4a62a 55%,#8a6410);border:2px solid #3b2a08;color:#2a1c04;font-size:15px;text-shadow:none}",
  ".leaflet-tooltip.bm-lbl{background:none;border:0;box-shadow:none;padding:0 2px;font:600 13px/1.1 var(--display,Georgia,serif);color:#1b1613;text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 2px #fff,0 0 1px #fff}",
  ".leaflet-tooltip.bm-lbl.en{font-style:italic;font-weight:400}",
  ".leaflet-tooltip.bm-lbl:before{display:none}",
  ".leaflet-tooltip.bm-tip{font:12px var(--sans,system-ui)}",
  ".bm-arrow-wrap{background:none;border:0}",
  ".bm-arrow{display:block;font-size:14px;line-height:16px;text-align:center;text-shadow:0 0 2px #fff,0 0 2px #fff}",
  ".bm .leaflet-popup-content-wrapper{border-radius:0;background:#fbf8f2;box-shadow:0 3px 14px rgba(0,0,0,.3);border-top:3px solid #9b2d1f}",
  ".bm .leaflet-popup-content{margin:12px 14px;font-family:var(--serif,Georgia,serif)}",
  ".bm-pop-k{font:600 .68rem/1 var(--sans,system-ui);letter-spacing:.08em;text-transform:uppercase;margin-bottom:5px}",
  ".bm-pop-ru{font:1.35rem/1.15 var(--display,Georgia,serif);color:#1b1613}",
  ".bm-pop-en{font-style:italic;color:rgba(27,22,19,.6);margin-top:1px}",
  ".bm-pop-date{margin-top:4px;font-weight:600;color:#9b2d1f}",
  ".bm-pop-conf{margin-top:6px;font-size:.8rem;color:rgba(27,22,19,.6)}",
  ".bm-pop-conf.c0{color:#9b2d1f}",
  ".bm-pop-n{margin-top:6px;font-size:.8rem;color:rgba(27,22,19,.6)}",
  ".bm-pop-refs{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;max-height:150px;overflow:auto}",
  ".bm-ref{font:.78rem/1.2 var(--sans,system-ui);padding:3px 6px;border:1px solid rgba(155,45,31,.35);color:#9b2d1f;text-decoration:none;background:#fff}",
  ".bm-ref i{font-style:normal;color:rgba(27,22,19,.55)}",
  ".bm-ref:hover{background:#9b2d1f;color:#fff}",
  ".bm-ref:hover i{color:#fff}",
  ".bm-ref.off{border-color:rgba(27,22,19,.15);color:rgba(27,22,19,.4);background:none}",
  ".bm-src{display:block;margin-top:9px;font:.75rem var(--sans,system-ui);color:rgba(27,22,19,.55)}",
  ".bm-legend{display:flex;flex-wrap:wrap;gap:6px 14px;font:.78rem/1.2 var(--sans,system-ui);color:var(--ink-2,#555)}",
  ".bm-leg{display:inline-flex;align-items:center;gap:6px}",
  ".bm-dot{width:12px;height:12px;border-radius:50%;border:1.5px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.3);display:inline-flex;align-items:center;justify-content:center;font-size:8px}",
  ".bm-dot.conf0{border-style:dashed;opacity:.8}",
  ".bm-dot.battle{background:#d4a62a!important;color:#2a1c04}",
  ".bm-list{list-style:none;margin:4px 0 0;padding:0;display:grid;grid-template-columns:1fr;gap:0}",
  "@media (min-width:640px){.bm-list.all{grid-template-columns:1fr 1fr;column-gap:24px}}",
  ".bm-list li{display:grid;grid-template-columns:28px 1fr auto;grid-template-rows:auto auto;column-gap:10px;align-items:center;padding:8px 2px;border-bottom:1px solid var(--rule-soft,rgba(27,22,19,.11));cursor:pointer}",
  ".bm-list li:hover,.bm-list li.on{background:var(--rubric-soft,rgba(155,45,31,.08))}",
  ".bm-num{grid-row:1/3;width:24px;height:24px;border-radius:50%;color:#fff;display:flex;align-items:center;justify-content:center;font:700 11px/1 var(--sans,system-ui);border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.2)}",
  ".bm-num.battle{background:#d4a62a!important;color:#2a1c04;font-size:13px}",
  ".bm-list.all .bm-num{width:14px;height:14px;margin-left:5px}",
  ".bm-name{font:1.05rem/1.2 var(--display,Georgia,serif);color:var(--ink,#1b1613)}",
  ".bm-en{grid-column:2;font-size:.82rem;font-style:italic;color:var(--ink-3,#888)}",
  ".bm-meta{grid-column:3;grid-row:1/3;font:.75rem var(--sans,system-ui);color:var(--ink-3,#888);text-align:right;max-width:9em}",
  ".bm-credit{font:.72rem/1.45 var(--sans,system-ui);color:var(--ink-3,#888)}",
  ".bm-credit a{color:inherit}",
].join("\n");
