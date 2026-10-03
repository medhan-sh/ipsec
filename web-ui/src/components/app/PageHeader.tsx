import React from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  actions,
  className,
}) => {
  return (
    <div className={cn("flex items-start justify-between pb-4 border-b border-border-hairline mb-6 font-mono", className)}>
      <div>
        <h1 className="text-lg font-semibold tracking-tight text-text-primary lowercase">
          {title}
        </h1>
        {description && (
          <p className="text-xs text-text-secondary mt-1 font-sans max-w-2xl">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
};
