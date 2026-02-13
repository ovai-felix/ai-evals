export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-48 bg-surface rounded border border-border">
      <p className="text-text-secondary text-sm">{message}</p>
    </div>
  );
}
