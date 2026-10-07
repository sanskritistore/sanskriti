"use client";

import { useRef } from "react";

/**
 * PhotoPicker — camera or gallery, mobile-first.
 * Uses a plain file input with capture support; compresses to a
 * data URL preview. Placeholder for a proper upload pipeline.
 */
export default function PhotoPicker({ value, onChange, hint }) {
  const inputRef = useRef(null);

  function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onChange?.(reader.result); // data URL preview
    reader.readAsDataURL(file);
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
