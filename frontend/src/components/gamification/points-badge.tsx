import { Gem } from "lucide-react";
import { cn } from "@/lib/utils";

interface PointsBadgeProps {
  points: number;
  size?: "sm" | "md" | "lg";
  variant?: "default" | "gradient";
}

const sizeClasses = {
  sm: "px-2 py-0.5 text-xs gap-1 [&>svg]:h-3 [&>svg]:w-3",
  md: "px-3 py-1 text-sm gap-1.5 [&>svg]:h-4 [&>svg]:w-4",
  lg: "px-4 py-1.5 text-base gap-2 [&>svg]:h-5 [&>svg]:w-5",
};

export function PointsBadge({
  points,
  size = "md",
  variant = "default",
}: PointsBadgeProps) {
  if (points <= 0) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-semibold whitespace-nowrap",
        sizeClasses[size],
        variant === "gradient"
          ? "bg-gradient-to-r from-blue-500 to-purple-500 text-white"
          : "bg-blue-100 text-blue-700 border border-blue-200"
      )}
    >
      <Gem className="fill-current" />
      <span>{points}</span>
    </span>
  );
}
