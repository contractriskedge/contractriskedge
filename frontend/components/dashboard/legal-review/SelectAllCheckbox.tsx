"use client";

import React from "react";

interface SelectAllCheckboxProps {
  checked: boolean;
  indeterminate?: boolean;
  onChange: (checked: boolean) => void;
  total: number;
  selected: number;
  className?: string;
}

export function SelectAllCheckbox({
  checked,
  indeterminate = false,
  onChange,
  total,
  selected,
  className = "",
}: SelectAllCheckboxProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (inputRef.current) {
      inputRef.current.indeterminate = indeterminate && !checked;
    }
  }, [indeterminate, checked]);

  return (
    <label
      className={`flex items-center gap-2 px-4 py-2 border-b border-gray-100 bg-gray-50/50 select-none ${className}`}
    >
      <input
        ref={inputRef}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-4 h-4 rounded border-gray-300 text-navy-700 focus:ring-navy-400 focus:ring-offset-1 cursor-pointer"
        aria-label={checked ? "Deselect all clauses" : "Select all clauses"}
      />
      <span className="text-xs font-medium text-gray-600">
        {selected > 0 ? `${selected} of ${total} selected` : `${total} clauses`}
      </span>
    </label>
  );
}
