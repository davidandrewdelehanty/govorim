// Annotations on the reader's text: highlights, notes and pen ink.
//
// THE MODEL is the W3C Web Annotation one that Recogito and Apache Annotator
// are built on. A highlight is anchored twice: by POSITION — start and end in
// the chapter's own character offsets, which are exactly the coordinates the
// reader's word spans already carry as data-rw-start/-end — and by QUOTE, the
// words themselves, which is what would find the passage again if a book's
// text were ever corrected and the offsets moved. Those libraries paint
// highlights by wrapping DOM text nodes; this reader's text is React-rendered
// word spans that also answer taps for definitions, and wrapping them from
// outside React would fight both. So the model is borrowed and the painting is
// done here: a highlight is a data attribute on the spans it covers.
//
// INK is drawn with perfect-freehand (MIT, vendored in src/vendor). A stroke
// belongs to the paragraph it was drawn on, with its points stored as
// fractions of that paragraph's box, so when the page reflows — a phone, a
// wider window, a bigger font — the stroke stays with its paragraph and
// stretches with it. It cannot stay on the exact word: line breaks move words
// and ink has no idea which word it was over. That is the price of a pen on
// reflowing text, and the reason highlights are the precise tool and ink the
// loose one.

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { getStroke } from "./vendor/perfect-freehand.js";

export var HL_COLORS = [
  { id: "yellow", label: "Yellow" },
  { id: "green",  label: "Green" },
  { id: "blue",   label: "Blue" },
  { id: "pink",   label: "Rose" },
];
export var INK_COLORS = [
  { id: "ink",  label: "Ink" },
  { id: "pink", label: "Red" },
  { id: "blue", label: "Blue" },
];
var INK_FILL = { ink: "#1b1613", pink: "#9b2d1f", blue: "#2f5c8a", green: "#3d6b37", yellow: "#a07d12" };

export function annotId() {
  var a = "abcdefghijklmnopqrstuvwxyz0123456789", s = "a";
  for (var i = 0; i < 13; i++) s += a[Math.floor(Math.random() * a.length)];
  return s;
}

// A stroke outline (from getStroke) as an SVG path, the way perfect-freehand's
// own README draws it: quadratic curves through the midpoints.
function strokePath(pts) {
  if (!pts || !pts.length) return "";
  var d = ["M", pts[0][0].toFixed(1), pts[0][1].toFixed(1), "Q"];
  for (var i = 0; i < pts.length; i++) {
    var p = pts[i], q = pts[(i + 1) % pts.length];
    d.push(p[0].toFixed(1), p[1].toFixed(1), ((p[0] + q[0]) / 2).toFixed(1), ((p[1] + q[1]) / 2).toFixed(1));
  }
  d.push("Z");
  return d.join(" ");
}

function spanRange(el) {
  var s = +el.getAttribute("data-rw-start");
  var e = +el.getAttribute("data-rw-end");
  if (!(e > s)) e = s + (el.textContent || "").length;
  return [s, e];
}

// The paragraph a point or an element belongs to, identified by the offset of
// its first Russian word — stable for a chapter, and the same on every device.
function paraOf(el, root) {
  var p = el && el.closest ? el.closest("p") : null;
  if (!p || !root.contains(p)) return null;
  var first = p.querySelector("[data-rw-start]");
  return first ? { p: p, start: +first.getAttribute("data-rw-start") } : null;
}

// ── The selection: which words, as chapter offsets, and what they say ──
export function readSelection(root) {
  var sel = window.getSelection && window.getSelection();
  if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
  var range = sel.getRangeAt(0);
  if (!root.contains(range.commonAncestorContainer)) return null;
  var spans = root.querySelectorAll("[data-rw-start]");
  var start = Infinity, end = -1, lastRect = null;
  for (var i = 0; i < spans.length; i++) {
    if (!range.intersectsNode(spans[i])) continue;
    var r = spanRange(spans[i]);
    if (r[0] < start) start = r[0];
    if (r[1] > end) { end = r[1]; lastRect = spans[i].getBoundingClientRect(); }
  }
  if (!(end > start)) return null;
  var box = range.getBoundingClientRect();
  return {
    start: start, end: end,
    quote: sel.toString().replace(/\s+/g, " ").trim().slice(0, 600),
    x: box.left + box.width / 2, y: box.top, bottom: box.bottom,
    lastRect: lastRect,
  };
}

// ── The layer: paints highlights onto the words, draws ink, holds the pen ──
//
// props:
//   rootRef   the .ltxt element holding the chapter's word spans
//   items     annotations for this chapter: { id, kind, layer, color, ... }
//   tool      "" | "pen" | "erase"
//   inkColor  pen colour id
//   onInk(stroke)          a finished stroke: { paraStart, points, color, size }
//   onErase(item)          an ink item clicked with the eraser
//   onMarker(item, rect)   a highlight's marker clicked
//   onSelect(sel|null)     the reader's text selection settled or cleared
export function AnnotLayer(props) {
  var rootRef = props.rootRef;
  var items = props.items || [];
  var tool = props.tool || "";
  var [tick, setTick] = useState(0);
  var [geo, setGeo] = useState({ w: 0, h: 0, marks: [], paras: {} });
  var [live, setLive] = useState(null);
  var liveRef = useRef(null);
  var onSelectRef = useRef(props.onSelect);
  onSelectRef.current = props.onSelect;

  // Re-measure when the text box changes size or its words are re-rendered.
  useEffect(function() {
    var root = rootRef.current;
    if (!root) return;
    var raf = 0;
    var bump = function() {
      if (raf) return;
      raf = requestAnimationFrame(function() { raf = 0; setTick(function(t){ return t + 1; }); });
    };
    var ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(bump) : null;
    if (ro) ro.observe(root);
    var mo = new MutationObserver(function(list) {
      // Our own attribute writes are not childList changes, so this only
      // fires when React has actually replaced words.
      for (var i = 0; i < list.length; i++) if (list[i].type === "childList") { bump(); return; }
    });
    mo.observe(root, { childList: true, subtree: true });
    window.addEventListener("resize", bump);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(bump);
    return function() {
      if (ro) ro.disconnect();
      mo.disconnect();
      window.removeEventListener("resize", bump);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [rootRef]);

  // A drag that ends on a word would also be a click on that word, and a click
  // on a word opens its definition. While text is selected, the click belongs
  // to the selection.
  useEffect(function() {
    var root = rootRef.current;
    if (!root) return;
    var swallow = function(e) {
      var s = window.getSelection && window.getSelection();
      if (s && !s.isCollapsed && s.toString().trim()) { e.stopPropagation(); }
    };
    root.addEventListener("click", swallow, true);
    var t = 0;
    var onSel = function() {
      clearTimeout(t);
      t = setTimeout(function() {
        var r = rootRef.current ? readSelection(rootRef.current) : null;
        if (onSelectRef.current) onSelectRef.current(r);
      }, 260);
    };
    document.addEventListener("selectionchange", onSel);
    return function() {
      root.removeEventListener("click", swallow, true);
      document.removeEventListener("selectionchange", onSel);
      clearTimeout(t);
    };
  }, [rootRef]);

  // Paint and measure. Attributes, not classes: React owns className on these
  // spans and would overwrite a class the next time a word's saved state or
  // the audio cursor changed; it never touches an attribute it did not set.
  var sig = items.map(function(it){ return it.id + ":" + (it.updatedAt || 0) + ":" + it.color + ":" + (it.note ? 1 : 0); }).join("|");
  useLayoutEffect(function() {
    var root = rootRef.current;
    if (!root) return;
    var hls = items.filter(function(it){ return it.kind === "hl"; })
      .sort(function(a, b){ return (a.createdAt || 0) - (b.createdAt || 0); });
    var spans = root.querySelectorAll("[data-rw-start]");
    var rootBox = root.getBoundingClientRect();
    var lastSpan = {};
    for (var i = 0; i < spans.length; i++) {
      var el = spans[i], r = spanRange(el), hit = null, n = 0;
      for (var j = 0; j < hls.length; j++) {
        var h = hls[j];
        if (h.start < r[1] && h.end > r[0]) { hit = h; n++; lastSpan[h.id] = el; }
      }
      if (hit) {
        // The newest mark gives the colour; how many readers have marked the
        // word is written beside it, so a word three people chose reads
        // differently from a word one person did.
        var nn = n > 2 ? "3" : String(n);
        if (el.getAttribute("data-hl") !== hit.color) el.setAttribute("data-hl", hit.color);
        if (el.getAttribute("data-hl-layer") !== hit.layer) el.setAttribute("data-hl-layer", hit.layer);
        if (el.getAttribute("data-hl-n") !== nn) el.setAttribute("data-hl-n", nn);
      } else if (el.hasAttribute("data-hl")) {
        el.removeAttribute("data-hl"); el.removeAttribute("data-hl-layer"); el.removeAttribute("data-hl-n");
      }
    }
    // One marker per place. Two readers who highlight the same words end on
    // the same word, and two markers on one spot are one marker you can
    // click and one you cannot; so they merge, and the merged one says how
    // many it stands for. The popover it opens lists them all.
    var marks = [], at = {};
    hls.forEach(function(h) {
      var el = lastSpan[h.id];
      if (!el) return;
      var b = el.getBoundingClientRect();
      var x = b.right - rootBox.left, y = b.top - rootBox.top;
      var key = Math.round(x) + ":" + Math.round(y);
      if (at[key]) {
        var m0 = at[key];
        m0.ids.push(h.id); m0.n++;
        m0.note = m0.note || !!h.note;
        m0.id = h.id; m0.color = h.color; m0.layer = h.layer;   // newest on top
        return;
      }
      var m = { id: h.id, ids: [h.id], n: 1, x: x, y: y, note: !!h.note, color: h.color, layer: h.layer };
      at[key] = m;
      marks.push(m);
    });
    var paras = {};
    items.forEach(function(it) {
      if (it.kind !== "ink" || paras[it.paraStart]) return;
      var first = root.querySelector('[data-rw-start="' + it.paraStart + '"]');
      var p = first && first.closest("p");
      if (!p) return;
      var pb = p.getBoundingClientRect();
      paras[it.paraStart] = { x: pb.left - rootBox.left, y: pb.top - rootBox.top, w: pb.width, h: pb.height };
    });
    var next = { w: root.scrollWidth, h: root.scrollHeight, marks: marks, paras: paras };
    setGeo(function(cur) { return JSON.stringify(cur) === JSON.stringify(next) ? cur : next; });
  }, [sig, tick, rootRef]);

  // ── the pen ──
  var toLocal = function(e) {
    var b = rootRef.current.getBoundingClientRect();
    return [e.clientX - b.left, e.clientY - b.top, e.pressure || 0.5];
  };
  var down = function(e) {
    if (tool !== "pen" || !rootRef.current) return;
    e.preventDefault();
    e.currentTarget.setPointerCapture && e.currentTarget.setPointerCapture(e.pointerId);
    // Which paragraph: look under the overlay for the words.
    var layer = e.currentTarget;
    layer.style.pointerEvents = "none";
    var under = document.elementFromPoint(e.clientX, e.clientY);
    layer.style.pointerEvents = "";
    var hit = paraOf(under, rootRef.current);
    if (!hit) {
      // In a margin or between paragraphs: the nearest paragraph by height.
      var ps = rootRef.current.querySelectorAll("p"), best = null, bestD = Infinity;
      for (var i = 0; i < ps.length; i++) {
        var f = ps[i].querySelector("[data-rw-start]");
        if (!f) continue;
        var pb = ps[i].getBoundingClientRect();
        var d = e.clientY < pb.top ? pb.top - e.clientY : e.clientY > pb.bottom ? e.clientY - pb.bottom : 0;
        if (d < bestD) { bestD = d; best = { p: ps[i], start: +f.getAttribute("data-rw-start") }; }
      }
      hit = best;
    }
    if (!hit) return;
    liveRef.current = { para: hit, pts: [toLocal(e)] };
    setLive({ pts: liveRef.current.pts.slice() });
  };
  var move = function(e) {
    if (!liveRef.current) return;
    liveRef.current.pts.push(toLocal(e));
    setLive({ pts: liveRef.current.pts.slice() });
  };
  var up = function() {
    var L = liveRef.current;
    liveRef.current = null;
    setLive(null);
    if (!L || L.pts.length < 2 || !rootRef.current) return;
    var rb = rootRef.current.getBoundingClientRect();
    var pb = L.para.p.getBoundingClientRect();
    var ox = pb.left - rb.left, oy = pb.top - rb.top;
    var pts = L.pts.map(function(q) {
      return [(q[0] - ox) / (pb.width || 1), (q[1] - oy) / (pb.height || 1)];
    });
    if (props.onInk) props.onInk({ paraStart: L.para.start, points: pts, color: props.inkColor || "ink", size: 3 });
  };

  var inkPaths = items.filter(function(it){ return it.kind === "ink" && geo.paras[it.paraStart]; }).map(function(it) {
    var g = geo.paras[it.paraStart];
    var pts = (it.points || []).map(function(q){ return [g.x + q[0] * g.w, g.y + q[1] * g.h]; });
    return { it: it, pts: pts, d: strokePath(getStroke(pts, { size: it.size || 3, thinning: 0.55, smoothing: 0.6, streamline: 0.5 })) };
  });
  var liveD = live ? strokePath(getStroke(live.pts, { size: 3, thinning: 0.55, smoothing: 0.6, streamline: 0.5 })) : "";

  return (
    <div className={"annot-layer" + (tool ? " tool-" + tool : "")} aria-hidden={tool ? undefined : "true"}>
      <svg className="annot-ink" width={geo.w} height={geo.h}>
        {inkPaths.map(function(p) {
          return (
            <path key={p.it.id} d={p.d} fill={INK_FILL[p.it.color] || INK_FILL.ink}
              className={"ink-stroke" + (p.it.layer === "group" ? " grp" : "")}
              onClick={tool === "erase" ? function(e){ e.stopPropagation(); if (props.onErase) props.onErase(p.it); } : undefined}>
              {p.it.by && p.it.by.name ? <title>{p.it.by.name}</title> : null}
            </path>
          );
        })}
        {/* A three-pixel line is a hard thing to hit with a finger. With the
            eraser in hand each stroke gets a wide invisible twin along its
            centre line, and that is what the tap lands on. */}
        {tool === "erase" && inkPaths.map(function(p) {
          return (
            <polyline key={"hit" + p.it.id} className="ink-hit"
              points={p.pts.map(function(q){ return q[0].toFixed(1) + "," + q[1].toFixed(1); }).join(" ")}
              fill="none" stroke="transparent" strokeWidth="18" strokeLinecap="round" strokeLinejoin="round"
              onClick={function(e){ e.stopPropagation(); if (props.onErase) props.onErase(p.it); }} />
          );
        })}
        {liveD && <path d={liveD} fill={INK_FILL[props.inkColor] || INK_FILL.ink} />}
      </svg>
      {tool === "pen" && (
        <div className="annot-pen" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} />
      )}
      {!tool && geo.marks.map(function(m) {
        return (
          <button key={m.ids[0]} type="button" className={"hl-mark c-" + m.color + (m.note ? " has-note" : "") + (m.layer === "group" ? " grp" : "") + (m.n > 1 ? " multi" : "")}
            style={{ left: m.x + "px", top: m.y + "px" }}
            title={m.n > 1 ? m.n + " marks here — see them all" : (m.note ? "Read the note" : "Highlight — add a note or remove it")}
            onClick={function(e){
              e.stopPropagation();
              var it = null;
              for (var i = 0; i < items.length; i++) if (items[i].id === m.id) { it = items[i]; break; }
              if (it && props.onMarker) props.onMarker(it, e.currentTarget.getBoundingClientRect());
            }}>
            {m.n > 1 ? <span className="hl-mark-n">{m.n}</span> : m.note ? (
              <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true">
                <path d="M2 2.5h8v5.5H5.5L3 10V8H2z" fill="currentColor" />
              </svg>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
