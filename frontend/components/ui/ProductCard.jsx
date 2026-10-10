"use client";

import Link from "next/link";
import { useLanguage } from "@/lib/LanguageContext";
import { formatRupees } from "@/lib/utils";

/**
 * ProductCard — one product row with edit/delete actions.
 * Photo/नाम पर टैप = photo album page (10-10 user माँग)।
 */
export default function ProductCard({ product, onDelete }) {
  const { t } = useLanguage();

  return (
    <div className="card flex items-center gap-4">
      <Link
        href={`/products/album?id=${product.id}`}
        className="flex min-w-0 flex-1 items-center gap-4"
      >
        {product.photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.photo}
            alt={product.name}
            className="h-16 w-16 rounded-xl object-cover"
          />
        ) : (
          <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-brand-100 text-3xl">
            📦
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{product.name}</p>
          <p className="font-bold text-brand-600">
            {formatRupees(product.price)}
          </p>
        </div>
      </Link>
      <div className="flex flex-col gap-2">
        <button className="rounded-lg border-2 border-gray-200 px-3 py-1 text-sm font-semibold text-gray-600">
          {t("edit")}
        </button>
        <button
          onClick={onDelete}
          className="rounded-lg border-2 border-red-200 px-3 py-1 text-sm font-semibold text-hindi-danger"
        >
          {t("delete")}
        </button>
      </div>
    </div>
  );
}
