import { statusColor } from "@/lib/utils";

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(status)}`}
    >
      {status}
    </span>
  );
}
