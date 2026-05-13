import * as React from "react";

import { cn } from "@/lib/utils";

function Badge({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-2xl px-3 py-1 text-xs font-medium tracking-[-0.01em] text-[#1b2540] shadow-[rgba(0,39,80,0.08)_0px_6px_16px_-3px,rgba(0,39,80,0.04)_0px_0px_0px_1px]",
        className,
      )}
      {...props}
    />
  );
}

export { Badge };
