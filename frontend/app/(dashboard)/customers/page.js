"use client";

import { useEffect, useMemo, useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";
import LanguageToggle from "@/components/ui/LanguageToggle";

/**
 * ग्राहक सूची — Custom Audience (09-10 user का खुद का idea)
 *
 * एक page, तीन काम:
 *   1. मौजूदा audience lists दिखो (नाम + अंदाज़ा-गिनती)
 *   2. नई list बनाओ
 *   3. किसी list में phone numbers जोड़ो (एक line में एक)
 *
 * ERROR RULE (08-10 सीख): कोई silent fail नहीं — हर गड़बड़ी लाल
 * कार्ड में साफ़ लिखी दिखेगी, ताकि user समझे क्या हुआ।
 */
export default function CustomersPage() {
  const { t } = useLanguage();
  const api = useAPI();

  const [lists, setLists] = useState(null); // null = loading
  const [loadError, setLoadError] = useState("");

  const [target, setTarget] = useState("new"); // "new" या audience id
  const [newName, setNewName] = useState("");
  const [rawNumbers, setRawNumbers] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null); // {received, invalid}
  const [error, setError] = useState("");

  // 🗑️ गलती से जुड़ा number हटाने का खाना (user की माँग 09-10 शाम)
  const [rmListId, setRmListId] = useState("");
  const [rmNumbers, setRmNumbers] = useState("");
  const [rmBusy, setRmBusy] = useState(false);
  const [rmResult, setRmResult] = useState(null); // {removed, invalid}
  const [rmError, setRmError] = useState("");

  async function refresh() {
    setLoadError("");
    try {
      const data = await api.audiences.list();
      setLists(data.audiences || []);
    } catch (e) {
      setLists([]);
      setLoadError(e.message || "Error");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // textarea से numbers निकालो (line/comma/space से अलग)
  const parsed = useMemo(() => {
    return rawNumbers
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }, [rawNumbers]);

  async function handleSubmit() {
    setError("");
    setResult(null);
    if (parsed.length === 0) {
      setError(t("customers.errorNoNumbers"));
      return;
    }
    if (target === "new" && newName.trim().length < 2) {
      setError(t("customers.errorNoName"));
      return;
    }
    setBusy(true);
    try {
      let audienceId = target;
      if (target === "new") {
        const created = await api.audiences.create({ name: newName.trim() });
        audienceId = created.id;
      }
      const res = await api.audiences.upload(audienceId, parsed);
      setResult(res);
      setRawNumbers("");
      setNewName("");
      await refresh();
    } catch (e) {
      setError(e.message || "Error");
    } finally {
      setBusy(false);
    }
  }

  // 🗑️ चुनी सूची से numbers हटाओ
  const rmParsed = rmNumbers
    .split(/[\n,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);

  async function handleRemove() {
    setRmError("");
    setRmResult(null);
    if (!rmListId) {
      setRmError(t("customers.removePickList"));
      return;
    }
    if (rmParsed.length === 0) {
      setRmError(t("customers.errorNoNumbers"));
      return;
    }
    setRmBusy(true);
    try {
      const res = await api.audiences.remove(rmListId, rmParsed);
      setRmResult(res);
      setRmNumbers("");
    } catch (e) {
      setRmError(e.message || "Error");
    } finally {
      setRmBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("customers.title")}</h1>
        <LanguageToggle />
      </div>

      <p className="text-gray-600">{t("customers.subtitle")}</p>

      <div className="card bg-amber-50 text-sm text-gray-700">
        {t("customers.hint")}
      </div>

      {/* ── आपकी lists ─────────────────────────────── */}
      <h2 className="text-lg font-semibold">{t("customers.yourLists")}</h2>
      {lists === null ? (
        <p className="py-4 text-center text-gray-400">{t("loading")}</p>
      ) : loadError ? (
        <div className="card border border-red-200 bg-red-50 text-red-700">
          ⚠️ {loadError}
        </div>
      ) : lists.length === 0 ? (
        <div className="card py-6 text-center">
          <div className="text-4xl">👥</div>
          <p className="mt-2 text-gray-500">{t("customers.empty")}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {lists.map((a) => (
            <div key={a.id} className="card flex items-center justify-between">
              <div>
                <p className="font-semibold">{a.name}</p>
                <p className="text-sm text-gray-500">
                  {a.size_low != null
                    ? `${a.size_low}–${a.size_high} ${t("customers.people")}`
                    : t("customers.counting")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setTarget(a.id);
                  setResult(null);
                  setError("");
                }}
                className={`rounded-lg px-3 py-2 text-sm font-medium ${
                  target === a.id
                    ? "bg-brand-600 text-white"
                    : "bg-gray-100 text-gray-700"
                }`}
              >
                {t("customers.addNumbers")}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── Numbers जोड़ने का खाना ───────────────────── */}
      <div className="card space-y-3">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setTarget("new")}
            className={`flex-1 rounded-lg px-3 py-3 font-medium ${
              target === "new"
                ? "bg-brand-600 text-white"
                : "bg-gray-100 text-gray-700"
            }`}
          >
            ➕ {t("customers.newList")}
          </button>
        </div>

        {target === "new" && (
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t("customers.listNameHint")}
            className="w-full rounded-lg border border-gray-300 px-3 py-3"
          />
        )}

        <label className="block text-sm font-medium text-gray-700">
          {t("customers.numbersLabel")}
        </label>
        <textarea
          value={rawNumbers}
          onChange={(e) => setRawNumbers(e.target.value)}
          placeholder={t("customers.numbersHint")}
          rows={6}
          className="w-full rounded-lg border border-gray-300 px-3 py-3 font-mono"
        />
        {parsed.length > 0 && (
          <p className="text-sm text-gray-600">
            {t("customers.parsed", { count: parsed.length })}
          </p>
        )}

        <button
          type="button"
          onClick={handleSubmit}
          disabled={busy}
          className="w-full rounded-lg bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
        >
          {busy ? t("customers.adding") : t("customers.addNumbers")}
        </button>

        {/* गड़बड़ी — हमेशा साफ़ दिखेगी (कोई silent fail नहीं) */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-red-700">
            ⚠️ {error}
          </div>
        )}

        {/* कामयाबी */}
        {result && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-3 py-3 text-green-800">
            <p className="font-semibold">
              {t("customers.success", { count: result.received })}
            </p>
            {result.invalid > 0 && (
              <p className="text-sm">
                {t("customers.invalidSkipped", { count: result.invalid })}
              </p>
            )}
            <p className="mt-1 text-sm">{t("customers.successNote")}</p>
          </div>
        )}
      </div>

      {/* ── 🗑️ गलती से जुड़ा number हटाओ ─────────────── */}
      {lists !== null && lists.length > 0 && (
        <div className="card space-y-3 border border-red-200">
          <h2 className="text-lg font-semibold text-red-700">
            {t("customers.removeTitle")}
          </h2>
          <p className="text-sm text-gray-600">{t("customers.removeHint")}</p>

          <select
            value={rmListId}
            onChange={(e) => setRmListId(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-3"
          >
            <option value="">{t("customers.removePickList")}</option>
            {lists.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>

          <textarea
            value={rmNumbers}
            onChange={(e) => setRmNumbers(e.target.value)}
            placeholder={t("customers.numbersHint")}
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-3 py-3 font-mono"
          />
          {rmParsed.length > 0 && (
            <p className="text-sm text-gray-600">
              {t("customers.parsed", { count: rmParsed.length })}
            </p>
          )}

          <button
            type="button"
            onClick={handleRemove}
            disabled={rmBusy || !rmListId || rmParsed.length === 0}
            className="w-full rounded-lg bg-red-600 py-3 font-semibold text-white disabled:opacity-50"
          >
            {rmBusy ? t("customers.removing") : t("customers.removeBtn")}
          </button>

          {/* गड़बड़ी — हमेशा साफ़ दिखेगी */}
          {rmError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-red-700">
              ⚠️ {rmError}
            </div>
          )}

          {/* कामयाबी */}
          {rmResult && (
            <div className="rounded-lg border border-green-200 bg-green-50 px-3 py-3 text-green-800">
              <p className="font-semibold">
                {t("customers.removed", { count: rmResult.removed })}
              </p>
              <p className="mt-1 text-sm">{t("customers.removedNote")}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
