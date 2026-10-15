// Settle the videos check_embeds.py could not (YouTube answered with a bot
// check): load each in a real embedded player, the same way the reader does.
//
// 1. Open https://www.samovar.live in Chrome, open DevTools → Console.
// 2. Paste this whole file, press Enter.
// 3. Paste the contents of tools/embed-unknown.json as:   checkEmbeds([ ...ids... ])
//    Progress prints every 25 videos (~25 a minute). Keep the tab in front.
// 4. When it finishes, embed-browser.json downloads. Move it to tools/ and run
//    python3 tools/check_embeds.py --from-browser tools/embed-browser.json
//
// Verdicts: "ok" = the player started; "okr" = loaded with no error; "err150"/"err101" = owner forbids
// embedding (or age-restricted); "err100" = removed/private; "timeout" = no
// answer in 15 s (left unknown — run those again).
(function () {
  function api() {
    if (window.YT && YT.Player) return Promise.resolve();
    return new Promise(function (res) {
      var prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = function () { if (prev) prev(); res(); };
      var s = document.createElement("script");
      s.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(s);
    });
  }
  var box = document.createElement("div");
  box.style.cssText = "position:fixed;left:0;bottom:0;width:220px;height:140px;overflow:hidden;opacity:.01;pointer-events:none;z-index:-1";
  document.body.appendChild(box);
  function one(id, ms) {
    return new Promise(function (resolve) {
      var el = document.createElement("div"); box.appendChild(el);
      var done = false, p;
      function fin(v) { if (done) return; done = true; try { p.destroy(); } catch (e) {} el.remove(); resolve(v); }
      p = new YT.Player(el, { width: 200, height: 120, videoId: id,
        playerVars: { mute: 1, autoplay: 1, playsinline: 1 },
        events: {
          onReady: function (e) { try { e.target.mute(); e.target.playVideo(); } catch (x) {}
            // a video that can't be embedded errors at load; 4 s of silence is a pass
            setTimeout(function () { fin("okr"); }, 4000); },
          onStateChange: function (e) { if (e.data === 1) fin("ok"); },
          onError: function (e) { fin("err" + e.data); } } });
      setTimeout(function () { fin("timeout"); }, ms);
    });
  }
  window.checkEmbeds = async function (ids, workers) {
    await api();
    var res = {}, q = ids.slice(), n = 0;
    async function pump() {
      while (q.length) {
        var id = q.shift();
        res[id] = await one(id, 20000);
        if (++n % 25 === 0) console.log("embeds: " + n + "/" + ids.length);
      }
    }
    var ps = []; for (var i = 0; i < (workers || 4); i++) ps.push(pump());
    await Promise.all(ps);
    var tally = {}; Object.values(res).forEach(function (v) { tally[v] = (tally[v] || 0) + 1; });
    console.log("embeds done", tally);
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(res, null, 1)], { type: "application/json" }));
    a.download = "embed-browser.json"; document.body.appendChild(a); a.click(); a.remove();
    return tally;
  };
  console.log("ready — now run: checkEmbeds([...ids from tools/embed-unknown.json...])");
})();
