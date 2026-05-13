import * as React from "react";

import { cn } from "@/lib/utils";

function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-[20px] bg-white p-5 shadow-[rgba(0,39,80,0.03)_0px_56px_72px_-16px,rgba(0,39,80,0.03)_0px_32px_32px_-16px,rgba(0,39,80,0.04)_0px_6px_12px_-3px,rgba(0,39,80,0.04)_0px_0px_0px_1px]",
        className,
      )}
      {...props}
    />
  );
}

function CardHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mb-4 space-y-1", className)} {...props} />;
}

function CardTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn("text-lg font-semibold tracking-[-0.015em] text-[#1b2540]", className)}
      {...props}
    />
  );
}

function CardDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn("text-sm tracking-[-0.01em] text-[#6b7184]", className)}
      {...props}
    />
  );
}

function CardContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn(className)} {...props} />;
}

export { Card, CardContent, CardDescription, CardHeader, CardTitle };
