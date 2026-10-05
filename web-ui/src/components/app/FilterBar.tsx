import React, { useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface FilterBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  value,
  onChange,
  placeholder = "filter results...",
  className,
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      onChange("");
      inputRef.current?.blur();
    }
  };

  return (
    <div
      onClick={() => inputRef.current?.focus()}
      className={cn(
        "relative flex h-8 items-center rounded-data border bg-surface-panel px-2.5 font-mono text-xs transition-colors",
        isFocused
          ? "border-signal ring-1 ring-signal shadow-focus"
          : "border-border-hairline hover:border-border-strong",
        className
      )}
    >
      <span className="text-signal font-semibold mr-1.5 select-none">/</span>
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        placeholder={placeholder}
        className="w-full bg-transparent text-text-primary placeholder:text-text-tertiary focus:outline-none"
      />
      {isFocused && (
        <span className="inline-block w-1.5 h-3.5 bg-signal terminal-caret ml-0.5 select-none" />
      )}
      {value && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onChange("");
          }}
          className="text-text-tertiary hover:text-text-primary ml-1 text-[10px]"
          title="Clear filter (Esc)"
        >
          [esc]
        </button>
      )}
    </div>
  );
};
