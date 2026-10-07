"use client";

import { useRef } from "react";

const MAX_DIM = 1600; // px — Meta ad के लिए पर्याप्त (1080-1200px दिखती है)
const JPEG_QUALITY = 0.85; // poster के अक्षर साफ़ रहें, size ~300-700KB

/**
 * PhotoPicker — camera or gallery, mobile-first.
 * फ़ोन की भारी photo (5-10MB) को browser में ही छोटी करता है (~300KB)
 * ताकि धीमे मोबाइल नेट पर भी upload न टूटे (07-10: user को save error
 * आई थी — 9MB photo धीमे नेट पर अटक गई थी)।
 */
export default function PhotoPicker({ value, onChange, hint }) {
  const inputRef = useRef(null);

  function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => compress(reader.result);
    reader.readAsDataURL(file);
  }

  /** Canvas से photo छोटी करें: max 1600px, JPEG 85% (5-10MB → ~300KB) */
  function compress(dataUrl) {
    const img = new Image();
    img.onload = () => {
      let { width, height } = img;
      if (Math.max(width, height) > MAX_DIM) {
        const scale = MAX_DIM / Math.max(width, height);
        width = Math.round(width * scale);
        height = Math.round(height * scale);
      }
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      canvas.getContext("2d").drawImage(img, 0, 0, width, height);
      onChange?.(canvas.toDataURL("image/jpeg", JPEG_QUALITY));
    };
    img.onerror = () => onChange?.(dataUrl); // कुछ गड़बड़ हो तो as-is
    img.src = dataUrl;
  }

  return (
    <div className="space-y-3">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFile}
      />

      {value ? (
        <div className="relative mx-auto">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={value}
            alt="preview"
            className="h-48 w-48 rounded-2xl object-cover ring-2 ring-brand-500"
          />
          <button
            onClick={() => onChange(null)}
            className="absolute -right-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-hindi-danger text-lg font-bold text-white"
            aria-label="Remove photo"
          >
            ×
          </button>
        </div>
      ) : (
        <button
          onClick={() => inputRef.current?.click()}
          className="mx-auto flex h-48 w-48 flex-col items-center justify-center gap-2 rounded-2xl border-4 border-dashed border-brand-300 bg-brand-50 text-brand-600"
        >
          <span className="text-5xl">📷</span>
          <span className="text-sm font-semibold">{hint || "Photo"}</span>
        </button>
      )}
    </div>
  );
}
