"use client";

import * as React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

const insetShadow = "[box-shadow:rgba(255,255,255,0.2)_0px_0.5px_0px_0px_inset,_rgba(0,0,0,0.2)_0px_0px_0px_0.5px_inset,_rgba(0,0,0,0.05)_0px_1px_2px_0px]";
const focusShadow = "[box-shadow:rgba(0,0,0,0.1)_0px_4px_12px]";

const variants = {
  default: `bg-[#1c1c1c] text-[#fcfbf8] ${insetShadow} active:opacity-80 focus-visible:${focusShadow} outline-none`,
  ghost: `border border-[rgba(28,28,28,0.4)] text-[#1c1c1c] bg-transparent active:opacity-80 focus-visible:${focusShadow} outline-none`,
  cream: `bg-[#f7f4ed] text-[#1c1c1c] active:opacity-80 focus-visible:${focusShadow} outline-none`,
  pill: `bg-[#f7f4ed] text-[#1c1c1c] rounded-full opacity-50 hover:opacity-80 focus-visible:opacity-80 focus-visible:${focusShadow} outline-none ${insetShadow}`,
};

const sizes = {
  default: "px-4 py-2 rounded-md text-sm font-medium",
  sm: "px-3 py-1 rounded-md text-xs font-medium",
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  asChild?: boolean;
}

export default function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: ButtonProps) {
  const base = cn(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap transition-all disabled:pointer-events-none disabled:opacity-50",
    variants[variant],
    sizes[size],
    className
  );

  if (asChild) {
    const child = React.Children.only(props.children) as React.ReactElement<{ className?: string }>;
    return React.cloneElement(child, {
      className: cn(child.props.className, base),
    });
  }

  return <button className={base} {...props} />;
}
