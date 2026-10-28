import React from "react";
import { formatDate } from "../../utils/formatters";

interface ChartShellProps {
  title: string;
  generatedAt?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}

export function ChartShell({
  title,
  generatedAt,
  children,
  action,
}: ChartShellProps) {
  const dateStr = formatDate(generatedAt);
  return (
    <section className="panel overflow-hidden">
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {dateStr && <p>Forecast generated {dateStr}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
