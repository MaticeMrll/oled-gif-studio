"use strict";

/* ==========================================================================
   OLED GIF Studio — frontend logic (vanilla JS, no dependencies)
   ========================================================================== */

(function () {
  /* ---------------------------------------------------------------- utils */

  function $(id) {
    return document.getElementById(id);
  }

  function debounce(fn, ms) {
    let t = null;
    return function (...args) {
      if (t) clearTimeout(t);
      t = setTimeout(() => fn.apply(null, args), ms);
    };
  }

  /**
   * POST JSON to `url`, returns the parsed body on success.
   * Throws an Error with a human-readable message on network failure
   * or when the backend responds with { ok: false, error }.
   */
  async function postJSON(url, body, signal) {
    let res;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
      });
    } catch (err) {
      if (err && err.name === "AbortError") throw err;
      throw new Error("Impossible de contacter le serveur local (" + (err && err.message ? err.message : "erreur réseau") + ").");
    }
    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      // ignore, handled below
    }
    if (!res.ok || !data || data.ok === false) {
      const msg = (data && data.error) ? data.error : ("Erreur serveur (HTTP " + res.status + ")");
      throw new Error(msg);
    }
    return data;
  }

  async function getJSON(url, signal) {
    let res;
    try {
      res = await fetch(url, { signal });
    } catch (err) {
      if (err && err.name === "AbortError") throw err;
      throw new Error("Impossible de contacter le serveur local (" + (err && err.message ? err.message : "erreur réseau") + ").");
    }
    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      // ignore
    }
    if (!res.ok || !data || data.ok === false) {
      const msg = (data && data.error) ? data.error : ("Erreur serveur (HTTP " + res.status + ")");
      throw new Error(msg);
    }
    return data;
  }

  function downloadDataURL(dataURL, filename) {
    const a = document.createElement("a");
    a.href = dataURL;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  function downloadText(content, filename, mime) {
    const blob = new Blob([content], { type: mime || "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  /* ---------------------------------------------------------------- state */

  const state = {
    meta: null,
    effectsByName: {},
    contentMode: "text", // "text" | "describe"
    imageDataURL: null,
    imageName: "",
    lastGif: null, // { gif, effect, w, h, frames, duration }
    genToken: 0,
    genAbort: null,
    pushPolling: null,
  };

  /* ---------------------------------------------------------------- DOM refs */

  const els = {
    tabText: $("tab-text"),
    tabDescribe: $("tab-describe"),
    panelText: $("panel-text"),
    panelDescribe: $("panel-describe"),
    text: $("text"),
    describe: $("describe"),

    dropzone: $("dropzone"),
    dropzoneEmpty: $("dropzone-empty"),
    dropzoneFilled: $("dropzone-filled"),
    imageFile: $("image-file"),
    imageThumb: $("image-thumb"),
    imageFilename: $("image-filename"),
    btnBrowse: $("btn-browse"),
    btnRemoveImage: $("btn-remove-image"),
    imageOptions: $("image-options"),
    style: $("style"),
    fit: $("fit"),
    denoise: $("denoise"),

    preset: $("preset"),
    customSizeToggle: $("custom-size-toggle"),
    customSizeFields: $("custom-size-fields"),
    sizeW: $("size-w"),
    sizeH: $("size-h"),
    invert: $("invert"),

    effect: $("effect"),
    effectDesc: $("effect-desc"),
    fps: $("fps"),
    fpsVal: $("fps-val"),
    seconds: $("seconds"),
    secondsVal: $("seconds-val"),
    speed: $("speed"),
    seed: $("seed"),
    fontSize: $("font-size"),
    charset: $("charset"),
    scale: $("scale"),
    scaleVal: $("scale-val"),

    btnGenerate: $("btn-generate"),
    autoPreview: $("auto-preview"),
    btnDownload: $("btn-download"),
    btnExportC: $("btn-export-c"),
    btnExportXbm: $("btn-export-xbm"),

    loops: $("loops"),
    btnPush: $("btn-push"),
    btnPushStop: $("btn-push-stop"),
    pushStatus: $("push-status"),
    pushStatusDot: $("push-status-dot"),
    pushStatusText: $("push-status-text"),

    screenWrap: $("screen-wrap"),
    screenImg: $("screen-img"),
    screenEmpty: $("screen-empty"),
    screenLoading: $("screen-loading"),
    infoLine: $("info-line"),
    generateError: $("generate-error"),
  };

  /* ---------------------------------------------------------------- content tabs */

  function setContentMode(mode) {
    state.contentMode = mode;
    const isText = mode === "text";
    els.tabText.classList.toggle("is-active", isText);
    els.tabDescribe.classList.toggle("is-active", !isText);
    els.tabText.setAttribute("aria-selected", String(isText));
    els.tabDescribe.setAttribute("aria-selected", String(!isText));
    els.panelText.classList.toggle("is-hidden", !isText);
    els.panelDescribe.classList.toggle("is-hidden", isText);
    scheduleAutoPreview();
  }

  els.tabText.addEventListener("click", () => setContentMode("text"));
  els.tabDescribe.addEventListener("click", () => setContentMode("describe"));

  /* ---------------------------------------------------------------- image upload */

  function readFileAsDataURL(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("Lecture du fichier impossible."));
      reader.readAsDataURL(file);
    });
  }

  async function handleImageFile(file) {
    if (!file || !file.type.startsWith("image/")) return;
    try {
      const dataURL = await readFileAsDataURL(file);
      state.imageDataURL = dataURL;
      state.imageName = file.name || "image";
      els.imageThumb.src = dataURL;
      els.imageFilename.textContent = state.imageName;
      els.dropzoneEmpty.classList.add("is-hidden");
      els.dropzoneFilled.classList.remove("is-hidden");
      els.imageOptions.classList.remove("is-hidden");
      scheduleAutoPreview();
    } catch (err) {
      showGenerateError(err.message || String(err));
    }
  }

  function clearImage() {
    state.imageDataURL = null;
    state.imageName = "";
    els.imageThumb.src = "";
    els.imageFile.value = "";
    els.dropzoneEmpty.classList.remove("is-hidden");
    els.dropzoneFilled.classList.add("is-hidden");
    els.imageOptions.classList.add("is-hidden");
    scheduleAutoPreview();
  }

  els.btnBrowse.addEventListener("click", () => els.imageFile.click());
  els.dropzone.addEventListener("click", (e) => {
    if (e.target === els.btnBrowse || e.target === els.btnRemoveImage) return;
    if (els.dropzoneFilled.classList.contains("is-hidden")) els.imageFile.click();
  });
  els.dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      els.imageFile.click();
    }
  });
  els.imageFile.addEventListener("change", () => {
    if (els.imageFile.files && els.imageFile.files[0]) handleImageFile(els.imageFile.files[0]);
  });
  els.btnRemoveImage.addEventListener("click", (e) => {
    e.stopPropagation();
    clearImage();
  });

  ["dragenter", "dragover"].forEach((evt) => {
    els.dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      e.stopPropagation();
      els.dropzone.classList.add("is-dragover");
    });
  });
  ["dragleave", "drop"].forEach((evt) => {
    els.dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      e.stopPropagation();
      els.dropzone.classList.remove("is-dragover");
    });
  });
  els.dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) handleImageFile(file);
  });

  /* ---------------------------------------------------------------- custom size */

  els.customSizeToggle.addEventListener("change", () => {
    els.customSizeFields.classList.toggle("is-hidden", !els.customSizeToggle.checked);
    els.preset.disabled = els.customSizeToggle.checked;
    scheduleAutoPreview();
  });

  /* ---------------------------------------------------------------- sliders */

  els.fps.addEventListener("input", () => {
    els.fpsVal.textContent = els.fps.value;
  });
  els.seconds.addEventListener("input", () => {
    els.secondsVal.textContent = els.seconds.value + " s";
  });
  els.scale.addEventListener("input", () => {
    els.scaleVal.textContent = els.scale.value + "×";
    applyScaleToScreen();
  });

  /* ---------------------------------------------------------------- meta loading */

  async function loadMeta() {
    let meta;
    try {
      meta = await getJSON("/api/meta");
    } catch (err) {
      showGenerateError("Impossible de charger la configuration (" + err.message + ").");
      return;
    }
    state.meta = meta;

    // presets
    els.preset.innerHTML = "";
    (meta.presets || []).forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = p.name + " — " + p.w + "x" + p.h + " — " + p.desc;
      els.preset.appendChild(opt);
    });
    if (meta.default_preset) els.preset.value = meta.default_preset;

    // effects (auto + optgroups texte / motifs)
    els.effect.innerHTML = "";
    const optAuto = document.createElement("option");
    optAuto.value = "auto";
    optAuto.textContent = "auto";
    els.effect.appendChild(optAuto);
    state.effectsByName = {};

    const grpText = document.createElement("optgroup");
    grpText.label = "Texte";
    const grpPattern = document.createElement("optgroup");
    grpPattern.label = "Motifs";

    (meta.effects || []).forEach((fx) => {
      state.effectsByName[fx.name] = fx;
      const opt = document.createElement("option");
      opt.value = fx.name;
      opt.textContent = fx.name;
      opt.dataset.textless = String(!!fx.textless);
      (fx.textless ? grpPattern : grpText).appendChild(opt);
    });
    if (grpText.children.length) els.effect.appendChild(grpText);
    if (grpPattern.children.length) els.effect.appendChild(grpPattern);
    updateEffectDesc();

    // charsets
    els.charset.innerHTML = "";
    (meta.charsets || []).forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      els.charset.appendChild(opt);
    });

    // styles / fits
    els.style.innerHTML = "";
    (meta.styles || []).forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      els.style.appendChild(opt);
    });
    els.fit.innerHTML = "";
    (meta.fits || []).forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f;
      els.fit.appendChild(opt);
    });
  }

  function updateEffectDesc() {
    const fx = state.effectsByName[els.effect.value];
    els.effectDesc.textContent = fx ? fx.desc : "";
  }

  els.effect.addEventListener("change", () => {
    updateEffectDesc();
    scheduleAutoPreview();
  });

  /* ---------------------------------------------------------------- payload / generate */

  function buildPayload() {
    const useCustomSize = els.customSizeToggle.checked;
    const w = parseInt(els.sizeW.value, 10);
    const h = parseInt(els.sizeH.value, 10);

    return {
      text: state.contentMode === "text" ? (els.text.value || "") : "",
      describe: state.contentMode === "describe" ? (els.describe.value || null) : null,
      effect: els.effect.value || "auto",
      preset: useCustomSize ? null : (els.preset.value || null),
      size: useCustomSize && w > 0 && h > 0 ? (w + "x" + h) : null,
      fps: Number(els.fps.value),
      seconds: Number(els.seconds.value),
      speed: els.speed.value !== "" ? Number(els.speed.value) : null,
      font_size: els.fontSize.value !== "" ? Number(els.fontSize.value) : null,
      charset: els.charset.value || null,
      invert: !!els.invert.checked,
      scale: Number(els.scale.value) || 4,
      seed: els.seed.value !== "" ? Number(els.seed.value) : null,
      image: state.imageDataURL || null,
      style: state.imageDataURL ? els.style.value : null,
      fit: state.imageDataURL ? els.fit.value : null,
      denoise: !!els.denoise.checked,
    };
  }

  function showGenerateError(msg) {
    els.generateError.textContent = msg || "";
  }

  function setLoading(isLoading) {
    els.screenWrap.classList.toggle("is-loading", isLoading);
    els.screenLoading.classList.toggle("is-hidden", !isLoading);
  }

  function applyScaleToScreen() {
    if (!state.lastGif) return;
    const scale = Number(els.scale.value) || 4;
    els.screenImg.style.width = (state.lastGif.w * scale) + "px";
    els.screenImg.style.height = (state.lastGif.h * scale) + "px";
  }

  function renderResult(data) {
    state.lastGif = data;
    els.screenImg.src = data.gif;
    els.screenImg.classList.remove("is-hidden");
    els.screenEmpty.classList.add("is-hidden");
    applyScaleToScreen();
    els.infoLine.textContent = data.w + "x" + data.h + " · " + data.effect + " · " + data.frames + " frames · " + data.duration + " ms";
    els.btnDownload.disabled = false;
    els.btnExportC.disabled = false;
    els.btnExportXbm.disabled = false;
    showGenerateError("");
  }

  async function generate() {
    const myToken = ++state.genToken;
    if (state.genAbort) {
      try { state.genAbort.abort(); } catch (_) { /* noop */ }
    }
    const controller = new AbortController();
    state.genAbort = controller;

    setLoading(true);
    try {
      const payload = buildPayload();
      const data = await postJSON("/api/generate", payload, controller.signal);
      if (myToken !== state.genToken) return; // superseded by a newer request
      renderResult(data);
    } catch (err) {
      if (err && err.name === "AbortError") return;
      if (myToken !== state.genToken) return;
      showGenerateError(err.message || String(err));
    } finally {
      if (myToken === state.genToken) setLoading(false);
    }
  }

  const scheduleAutoPreview = debounce(() => {
    if (els.autoPreview.checked) generate();
  }, 450);

  els.btnGenerate.addEventListener("click", generate);

  // wire every relevant control to the debounced auto-preview
  [
    els.text, els.describe, els.preset, els.sizeW, els.sizeH, els.invert,
    els.fps, els.seconds, els.speed, els.seed, els.fontSize, els.charset, els.scale,
    els.style, els.fit, els.denoise,
  ].forEach((el) => {
    el.addEventListener("input", scheduleAutoPreview);
    el.addEventListener("change", scheduleAutoPreview);
  });

  /* ---------------------------------------------------------------- download / export */

  els.btnDownload.addEventListener("click", () => {
    if (!state.lastGif) return;
    downloadDataURL(state.lastGif.gif, "oled_" + state.lastGif.effect + ".gif");
  });

  async function exportAs(format) {
    try {
      const payload = buildPayload();
      payload.format = format;
      const data = await postJSON("/api/export", payload);
      downloadText(data.content, data.filename, data.mime);
    } catch (err) {
      showGenerateError(err.message || String(err));
    }
  }

  els.btnExportC.addEventListener("click", () => exportAs("c-array"));
  els.btnExportXbm.addEventListener("click", () => exportAs("xbm"));

  /* ---------------------------------------------------------------- push */

  function setPushUI(running, text, isError) {
    els.btnPush.disabled = !!running;
    els.btnPushStop.disabled = !running;
    els.pushStatus.classList.toggle("is-running", !!running);
    els.pushStatus.classList.toggle("is-error", !!isError);
    if (text) els.pushStatusText.textContent = text;
  }

  function stopPushPolling() {
    if (state.pushPolling) {
      clearInterval(state.pushPolling);
      state.pushPolling = null;
    }
  }

  async function pollPushStatus() {
    try {
      const data = await getJSON("/api/push/status");
      if (data.error) {
        setPushUI(false, "Erreur : " + data.error, true);
        stopPushPolling();
        return;
      }
      if (data.running) {
        setPushUI(true, "En cours vers " + (data.address || "?") + " · " + (data.sent || 0) + " frames envoyées", false);
      } else {
        setPushUI(false, "Arrêté · " + (data.sent || 0) + " frames envoyées vers " + (data.address || "?"), false);
        stopPushPolling();
      }
    } catch (err) {
      setPushUI(false, "Erreur de statut : " + err.message, true);
      stopPushPolling();
    }
  }

  els.btnPush.addEventListener("click", async () => {
    try {
      setPushUI(true, "Connexion à SteelSeries GG…", false);
      const payload = buildPayload();
      payload.loops = els.loops.value !== "" ? Number(els.loops.value) : 0;
      const data = await postJSON("/api/push", payload);
      setPushUI(true, "En cours vers " + (data.address || "?") + "…", false);
      stopPushPolling();
      state.pushPolling = setInterval(pollPushStatus, 1000);
    } catch (err) {
      setPushUI(false, "Erreur : " + err.message, true);
    }
  });

  els.btnPushStop.addEventListener("click", async () => {
    try {
      await postJSON("/api/push/stop", {});
      setPushUI(false, "Arrêté.", false);
    } catch (err) {
      setPushUI(false, "Erreur : " + err.message, true);
    } finally {
      stopPushPolling();
    }
  });

  /* ---------------------------------------------------------------- init */

  async function init() {
    await loadMeta();
    if (!els.text.value) els.text.value = "GG";
    await generate();
  }

  init();
})();
