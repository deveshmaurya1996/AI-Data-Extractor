import React, { useState } from "react";
import { ChatMetadata } from "@/types/api";
import { ConfidenceBadge } from "../Common/ConfidenceBadge";
import { CopyButton } from "../Common/CopyButton";
import { ChevronDown, ChevronUp, Code, Info } from "lucide-react";

interface ResultMetadataProps {
  metadata: ChatMetadata;
}

export const ResultMetadata: React.FC<ResultMetadataProps> = ({ metadata }) => {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const confidenceLevel = metadata.confidence_label ?? "medium";
  const strategyLabel = (metadata.strategy ?? "unknown").replace("_", " ");
  const rowCount = metadata.row_count ?? 0;
  const explanation = metadata.explanation ?? "No explanation available.";
  const sql = metadata.sql ?? "";
  const previewData = metadata.data_preview ?? [];

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-100 px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Info size={18} className="text-gray-600" />
            <span className="font-semibold text-gray-900">Query Details</span>
          </div>
          <ConfidenceBadge level={confidenceLevel} showLabel={true} />
        </div>
      </div>

      <div className="divide-y divide-gray-200">
        {(metadata.execution_time_ms !== undefined ||
          metadata.cache_hit !== undefined ||
          (metadata.data_sources && metadata.data_sources.length > 0)) && (
          <div className="px-4 py-3 bg-white text-sm text-gray-700 space-y-1">
            <span className="font-medium text-gray-900">Performance</span>
            {metadata.execution_time_ms !== undefined && (
              <p className="text-xs text-gray-600">
                Server execution: {metadata.execution_time_ms} ms
                {metadata.cache_hit ? " (cached)" : ""}
              </p>
            )}
            {metadata.data_sources && metadata.data_sources.length > 0 && (
              <p className="text-xs text-gray-600">
                Sources: {metadata.data_sources.join(", ")}
              </p>
            )}
          </div>
        )}

        <div>
          <button
            onClick={() => toggleSection("strategy")}
            className="w-full px-4 py-3 text-left hover:bg-gray-100 transition flex items-center justify-between"
          >
            <span className="font-medium text-gray-900">Strategy</span>
            {expandedSection === "strategy" ? (
              <ChevronUp size={20} className="text-gray-600" />
            ) : (
              <ChevronDown size={20} className="text-gray-600" />
            )}
          </button>

          {expandedSection === "strategy" && (
            <div className="px-4 py-3 bg-white border-t border-gray-200">
              <div className="space-y-2">
                <div className="flex justify-between items-start">
                  <span className="text-sm text-gray-600">Type:</span>
                  <span className="text-sm font-medium text-gray-900 capitalize">
                    {strategyLabel}
                  </span>
                </div>
                <div className="flex justify-between items-start">
                  <span className="text-sm text-gray-600">Results:</span>
                  <span className="text-sm font-medium text-gray-900">
                    {rowCount} row{rowCount !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div>
          <button
            onClick={() => toggleSection("explanation")}
            className="w-full px-4 py-3 text-left hover:bg-gray-100 transition flex items-center justify-between"
          >
            <span className="font-medium text-gray-900">Why this answer?</span>
            {expandedSection === "explanation" ? (
              <ChevronUp size={20} className="text-gray-600" />
            ) : (
              <ChevronDown size={20} className="text-gray-600" />
            )}
          </button>

          {expandedSection === "explanation" && (
            <div className="px-4 py-3 bg-white border-t border-gray-200">
              <p className="text-sm text-gray-700 leading-relaxed">{explanation}</p>
            </div>
          )}
        </div>

        <div>
          <button
            onClick={() => toggleSection("sql")}
            className="w-full px-4 py-3 text-left hover:bg-gray-100 transition flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <Code size={18} className="text-gray-600" />
              <span className="font-medium text-gray-900">Generated SQL</span>
            </div>
            {expandedSection === "sql" ? (
              <ChevronUp size={20} className="text-gray-600" />
            ) : (
              <ChevronDown size={20} className="text-gray-600" />
            )}
          </button>

          {expandedSection === "sql" && (
            <div className="px-4 py-3 bg-white border-t border-gray-200">
              <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs overflow-x-auto max-h-48 mb-3 border border-gray-700">
                <pre>{sql || "No SQL available"}</pre>
              </div>
              <CopyButton text={sql} label="Copy SQL" />
            </div>
          )}
        </div>

        {previewData.length > 0 && (
          <div>
            <button
              onClick={() => toggleSection("preview")}
              className="w-full px-4 py-3 text-left hover:bg-gray-100 transition flex items-center justify-between"
            >
              <span className="font-medium text-gray-900">Data Preview</span>
              {expandedSection === "preview" ? (
                <ChevronUp size={20} className="text-gray-600" />
              ) : (
                <ChevronDown size={20} className="text-gray-600" />
              )}
            </button>

            {expandedSection === "preview" && (
              <div className="px-4 py-3 bg-white border-t border-gray-200">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-100">
                      <tr>
                        {Object.keys(previewData[0] || {}).map(
                          (key) => (
                            <th
                              key={key}
                              className="px-3 py-2 text-left font-medium text-gray-700"
                            >
                              {key}
                            </th>
                          ),
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData
                        .slice(0, 3)
                        .map((row: Record<string, unknown>, idx: number) => (
                        <tr key={idx} className="border-t border-gray-200">
                          {Object.values(row).map((value, colIdx) => (
                            <td
                              key={colIdx}
                              className="px-3 py-2 text-gray-700 truncate"
                            >
                              {typeof value === "object"
                                ? JSON.stringify(value)
                                : String(value ?? "-")}
                            </td>
                          ))}
                        </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
