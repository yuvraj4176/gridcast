import React from "react";
import { Icon } from "./Icon";

interface SummaryCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  note: string;
  trend?: string;
  amber?: boolean;
}

export function SummaryCard({
  icon,
  label,
  value,
  note,
  trend,
  amber,
}: SummaryCardProps) {
  return (
    <article className="metric-card">
      <div className="flex items-start justify-between">
        <Icon>{icon}</Icon>
        {trend && (
          <span className={amber ? "trend amber" : "trend"}>{trend}</span>
        )}
      </div>
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
      <p className="metric-note">{note}</p>
    </article>
  );
}
