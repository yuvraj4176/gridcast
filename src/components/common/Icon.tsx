import React from "react";

export function Icon({ children }: { children: React.ReactNode }) {
  return (
    <span className="grid h-8 w-8 place-items-center rounded-lg bg-slate-50 text-base text-blue-900">
      {children}
    </span>
  );
}
