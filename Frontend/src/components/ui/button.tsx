import { cn } from "@/lib/utils/format";

export function Button({
  className,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-[#17453a] text-white shadow-[0_8px_18px_rgba(23,69,58,.14)] hover:-translate-y-0.5 hover:bg-[#0f382f]",
    secondary: "border border-[#17453a]/15 bg-white text-[#173e34] hover:border-[#17453a]/30 hover:bg-[#f4f7f4]",
    ghost: "text-[#4c625b] hover:bg-[#e9eee9] hover:text-[#173e34]",
    danger: "bg-[#a94b3c] text-white hover:bg-[#913e32]",
  };
  return (
    <button
      {...props}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-bold transition-all focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#cfe3d7] disabled:cursor-not-allowed disabled:opacity-50",
        styles[variant],
        className,
      )}
    />
  );
}
