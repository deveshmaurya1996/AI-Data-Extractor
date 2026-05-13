import React from "react";
import { ChatMessage } from "@/types/chat";
import { DataTable } from "./DataTable";
import { ResultMetadata } from "./ResultMetadata";
import { ResultsMiniChart } from "./ResultsMiniChart";
import { BarChart3, Braces, Download } from "lucide-react";
import { downloadTextFile, rowsToCsv } from "@/lib/exportResults";

interface ResultsContainerProps {
  message: ChatMessage;
}

export const ResultsContainer: React.FC<ResultsContainerProps> = ({
  message,
}) => {
  const data = message.data;
  const metadata = message.metadata;

  if (!data || data.length === 0 || !metadata) {
    return null;
  }

  const handleExportCsv = () => {
    const csv = rowsToCsv(data as Record<string, unknown>[]);
    downloadTextFile(csv, `results-${Date.now()}.csv`, "text/csv;charset=utf-8");
  };

  const handleExportJson = () => {
    const body = JSON.stringify(data, null, 2);
    downloadTextFile(
      body,
      `results-${Date.now()}.json`,
      "application/json;charset=utf-8",
    );
  };

  const columns = Object.keys(data[0] || {});
  const rowCount = metadata.row_count ?? data.length;

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 bg-linear-to-r from-blue-50 to-indigo-50 px-4 py-3 rounded-lg border border-blue-200">
        <div className="flex items-center gap-2">
          <BarChart3 size={20} className="text-blue-600" />
          <span className="font-semibold text-gray-900">
            Results ({rowCount} rows)
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleExportCsv}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-100 border border-blue-300 rounded transition"
          >
            <Download size={16} />
            Export CSV
          </button>
          <button
            type="button"
            onClick={handleExportJson}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-indigo-600 hover:bg-indigo-100 border border-indigo-300 rounded transition"
          >
            <Braces size={16} />
            Export JSON
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <div className="border border-gray-200 rounded-lg overflow-hidden bg-white min-w-0">
          <DataTable
            key={message.id}
            data={data}
            columns={columns}
            maxRows={15}
            enableFilter
            enablePagination
            pageSize={15}
          />
        </div>
        <div className="min-w-0 space-y-3">
          <ResultsMiniChart data={data as Record<string, unknown>[]} />
        </div>
      </div>

      <ResultMetadata metadata={metadata} />
    </div>
  );
};
