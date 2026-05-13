import React from "react";
import clsx from "clsx";

interface InsightCardProps {
  icon: React.ReactNode;
  title: string;
  value: string | number;
  subtitle?: string;
  color?: "blue" | "green" | "yellow" | "red";
}

export const InsightCard: React.FC<InsightCardProps> = ({
  icon,
  title,
  value,
  subtitle,
  color = "blue",
}) => {
  const colorClasses = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    yellow: "bg-yellow-50 text-yellow-700",
    red: "bg-red-50 text-red-700",
  };

  const iconColorClasses = {
    blue: "text-blue-600",
    green: "text-green-600",
    yellow: "text-yellow-600",
    red: "text-red-600",
  };

  return (
    <div className={clsx("px-3 py-3 rounded-lg border", colorClasses[color])}>
      <div className="flex items-start gap-2">
        <div className={clsx("shrink-0", iconColorClasses[color])}>{icon}</div>
        <div className="grow">
          <p className="text-xs font-medium opacity-75">{title}</p>
          <p className="text-lg font-bold">{value}</p>
          {subtitle && <p className="text-xs opacity-60">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
};
