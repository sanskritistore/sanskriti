// 📸 फ़ोटो स्टूडियो — सब कुछ user के phone/browser में होता है!
// Server पर कोई बोझ नहीं — तेज़, free, और backend कभी गिरता नहीं।
// Background हटाने वाला AI (isnet_quint8) पहली बार download होता है (~40MB),
// फिर browser cache में रहता है — अगली बार तुरंत चलता है।

// Library bundle में नहीं — runtime पर CDN से (webpackIgnore = build छुटकारा)
const CDN_URL = "https://esm.sh/@imgly/background-removal@1.7.0";
let _libPromise = null;
function loadLib() {
  if (!_libPromise) _libPromise = import(/* webpackIgnore: true */ CDN_URL);
  return _libPromise;
}

function blobToImage(blob) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("image load failed")); };
    img.src = url;
  });
}

// पारदर्शी (alpha) हिस्से की असली सीमा निकालो — फालतू खाली जगह हटाने के लिए
function alphaBounds(img) {
  const c = document.createElement("canvas");
  c.width = img.width; c.height = img.height;
  const ctx = c.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(img, 0, 0);
  const { data } = ctx.getImageData(0, 0, c.width, c.height);
  let minX = c.width, minY = c.height, maxX = -1, maxY = -1;
  for (let y = 0; y < c.height; y += 2) {
    for (let x = 0; x < c.width; x += 2) {
      if (data[(y * c.width + x) * 4 + 3] > 10) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  if (maxX < 0) return { x: 0, y: 0, w: img.width, h: img.height };
  return { x: minX, y: minY, w: maxX - minX + 2, h: maxY - minY + 2 };
}

/**
 * Photo को सुंदर बनाओ: background हटाओ → सफ़ेद canvas → नीचे लिखावट (optional)
 * @param {string} dataUri - "data:image/..." photo
 * @param {string} text - नीचे लिखना है (खाली हो तो सिर्फ white bg)
 * @param {(msg:string)=>void} onProgress - progress message दिखाने के लिए
 * @returns {Promise<string>} नई photo का data URI (webp)
 */
export async function enhancePhoto(dataUri, text, onProgress = () => {}) {
  onProgress("AI तैयार हो रहा है… (पहली बार थोड़ा time)");
  const { removeBackground } = await loadLib();

  const srcBlob = await (await fetch(dataUri)).blob();

  const fgBlob = await removeBackground(srcBlob, {
    model: "isnet_quint8",
    output: { format: "image/png", quality: 1 },
    progress: (key, current, total) => {
      if (key && String(key).startsWith("fetch")) {
        onProgress("AI model download हो रहा है…");
      } else {
        onProgress("Background हट रहा है…");
      }
    },
  });

  onProgress("सफ़ेद background लग रहा है…");
  const fg = await blobToImage(fgBlob);
  const b = alphaBounds(fg);

  // सफ़ेद चौकोर canvas, product के इर्द-गिर्द 10% margin
  const side = Math.ceil(Math.max(b.w, b.h) * 1.2);
  const canvas = document.createElement("canvas");
  canvas.width = side; canvas.height = side;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, side, side);
  const dx = Math.round((side - b.w) / 2);
  const dy = Math.round((side - b.h) / 2);
  ctx.drawImage(fg, b.x, b.y, b.w, b.h, dx, dy, b.w, b.h);

  // ✍️ नीचे लिखावट की पट्टी (Hindi fonts browser खुद संभालता है!)
  const cleanText = (text || "").trim();
  if (cleanText) {
    const bandH = Math.round(side * 0.14);
    const y0 = side - bandH;
    ctx.fillStyle = "#0d1b2a"; // navy
    ctx.fillRect(0, y0, side, bandH);
    let fontSize = Math.round(bandH * 0.45);
    const setFont = () => { ctx.font = `bold ${fontSize}px "Noto Sans Devanagari", system-ui, sans-serif`; };
    setFont();
    while (fontSize > 12 && ctx.measureText(cleanText).width > side * 0.9) { fontSize -= 2; setFont(); }
    ctx.fillStyle = "#ffc400"; // yellow
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(cleanText, side / 2, y0 + bandH / 2 + 1);
  }

  onProgress("तैयार!");
  // बहुत बड़ी photo को 1200px तक सीमित (DB में हल्की रहे)
  let out = canvas;
  if (side > 1200) {
    const c2 = document.createElement("canvas");
    c2.width = c2.height = 1200;
    c2.getContext("2d").drawImage(canvas, 0, 0, 1200, 1200);
    out = c2;
  }
  try {
    return out.toDataURL("image/webp", 0.88);
  } catch {
    return out.toDataURL("image/jpeg", 0.9);
  }
}
