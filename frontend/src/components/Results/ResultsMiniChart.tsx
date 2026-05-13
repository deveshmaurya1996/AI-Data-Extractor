"use client";

import React, { useMemo } from "react";

type Point = { label: string; value: number };

function pickNumericSeries(
  rows: Record<string, unknown>[],
): { labelKey: string; valueKey: string; points: Point[] } | null {
  if (rows.length < 2) return null;
  const keys = Object.keys(rows[0]).filter((k) => !k.startsWith("__"));
  let valueKey: string | null = null;
  for (const k of keys) {
    const nums = rows.slice(0, 50).map((r) => {
      const v = r[k];
      if (typeof v === "number" && !Number.isNaN(v)) return v;
      if (typeof v === "string" && v.trim() !== "" && !Number.isNaN(Number(v)))
        return Number(v);
      return NaN;
    });
    if (nums.every((n) => !Number.isNaN(n))) {
      valueKey = k;
      break;
    }
  }
  if (!valueKey) return null;
  const labelKey =
    keys.find((k) => k !== valueKey && k !== "__source_file") ?? valueKey;
  const points: Point[] = rows.slice(0, 12).map((r) => ({
    label: String(r[labelKey] ?? "").slice(0, 18),
    value:
      typeof r[valueKey!] === "number"
        ? (r[valueKey!] as number)
        : Number(r[valueKey!]),
  }));
  return { labelKey, valueKey, points };
}

interface ResultsMiniChartProps {
  data: Record<string, unknown>[];
}

export const ResultsMiniChart: React.FC<ResultsMiniChartProps> = ({
  data,
}) => {
  const spec = useMemo(() => pickNumericSeries(data), [data]);
  if (!spec) return null;

  const max = Math.max(...spec.points.map((p) => p.value), 1e-9);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3">
      <p className="text-xs font-semibold text-gray-600 mb-2">
        Quick chart ({spec.valueKey} by {spec.labelKey})
      </p>
      <div className="flex flex-col gap-1.5">
        {spec.points.map((p, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span
              className="w-24 shrink-0 truncate text-gray-600"
              title={p.label}
            >
              {p.label || "—"}
            </span>
            <div className="grow h-5 bg-gray-100 rounded overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded transition-all"
                style={{ width: `${Math.min(100, (p.value / max) * 100)}%` }}
              />
            </div>
            <span className="w-14 text-right tabular-nums text-gray-800">
              {Number.isInteger(p.value) ? p.value : p.value.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
