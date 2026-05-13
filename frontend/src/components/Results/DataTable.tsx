import React, { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { DataTableProps } from "@/types/ui";

export const DataTable = <T extends Record<string, unknown>>({
  data,
  columns = [],
  isLoading = false,
  maxRows = 10,
  enableFilter = false,
  enablePagination = false,
  pageSize: pageSizeProp,
}: DataTableProps<T>) => {
  const [filterText, setFilterText] = useState("");
  const [pageIndex, setPageIndex] = useState(0);

  const pageSize = enablePagination
    ? (pageSizeProp ?? maxRows ?? 10)
    : (maxRows ?? 10);

  const filteredData = useMemo(() => {
    if (!enableFilter || !filterText.trim()) return data;
    const q = filterText.trim().toLowerCase();
    return data.filter((row) =>
      Object.values(row).some((cell) =>
        String(cell ?? "")
          .toLowerCase()
          .includes(q),
      ),
    );
  }, [data, filterText, enableFilter]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredData.length / Math.max(pageSize, 1)),
  );

  const displayData = useMemo(() => {
    if (enablePagination) {
      const start = pageIndex * pageSize;
      return filteredData.slice(start, start + pageSize);
    }
    return filteredData.slice(0, maxRows);
  }, [filteredData, pageIndex, pageSize, enablePagination, maxRows]);

  if (isLoading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">No data to display</div>
    );
  }

  const displayColumns =
    columns.length > 0
      ? columns
      : (Object.keys(data[0] || {}) as (keyof T & string)[]);

  return (
    <div className="space-y-2">
      {enableFilter && (
        <input
          type="search"
          value={filterText}
          onChange={(e) => {
            setFilterText(e.target.value);
            setPageIndex(0);
          }}
          placeholder="Filter rows…"
          className="w-full max-w-md text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-400"
          aria-label="Filter table rows"
        />
      )}

      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {displayColumns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2 text-left font-semibold text-gray-700"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayData.map((row, idx) => (
              <tr
                key={idx}
                className="border-b border-gray-200 hover:bg-gray-50 transition"
              >
                {displayColumns.map((col) => (
                  <td key={`${idx}-${col}`} className="px-4 py-2 text-gray-900">
                    {typeof row[col] === "object"
                      ? JSON.stringify(row[col])
                      : String(row[col] ?? "-")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {!enablePagination && filteredData.length > maxRows && (
          <div className="bg-gray-50 px-4 py-2 text-sm text-gray-600 border-t border-gray-200">
            Showing {displayData.length} of {filteredData.length} results
          </div>
        )}
        {enablePagination && filteredData.length > 0 && (
          <div className="flex items-center justify-between bg-gray-50 px-4 py-2 text-sm text-gray-600 border-t border-gray-200">
            <span>
              Page {pageIndex + 1} of {totalPages} ({filteredData.length} rows)
            </span>
            <div className="flex gap-1">
              <button
                type="button"
                disabled={pageIndex <= 0}
                onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
                className="p-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-white"
                aria-label="Previous page"
              >
                <ChevronLeft size={18} />
              </button>
              <button
                type="button"
                disabled={pageIndex >= totalPages - 1}
                onClick={() =>
                  setPageIndex((p) => Math.min(totalPages - 1, p + 1))
                }
                className="p-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-white"
                aria-label="Next page"
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
