import React from "react";
import { ConfidenceBadgeProps } from "@/types/ui";
import clsx from "clsx";

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  level,
  showLabel = true,
}) => {
  const colors = {
    high: "bg-green-100 text-green-800",
    medium: "bg-yellow-100 text-yellow-800",
    low: "bg-red-100 text-red-800",
  };

  const icons = {
    high: "🟢",
    medium: "🟡",
    low: "🔴",
  };

  const labels = {
    high: "High",
    medium: "Medium",
    low: "Low",
  };

  return (
    <div
      className={clsx(
        "px-3 py-1 rounded-full text-sm font-medium",
        colors[level],
      )}
    >
      <span className="mr-2">{icons[level]}</span>
      {showLabel && labels[level]}
    </div>
  );
};
