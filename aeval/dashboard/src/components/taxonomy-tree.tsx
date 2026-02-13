"use client";

import { useState } from "react";
import type { TaxonomyNode } from "@/lib/types";

interface TreeProps {
  taxonomy: TaxonomyNode[];
}

function stateLabel(node: TaxonomyNode): { text: string; className: string } {
  if (node.eval_count === 0)
    return { text: "GAP", className: "text-danger bg-danger/20" };
  if (node.avg_discrimination < 0.08)
    return { text: "Saturated", className: "text-danger bg-danger/10" };
  if (node.avg_discrimination < 0.15)
    return { text: "Watch", className: "text-warning bg-warning/10" };
  return { text: "Active", className: "text-success bg-success/10" };
}

function TreeNode({ node, depth }: { node: TaxonomyNode; depth: number }) {
  const [open, setOpen] = useState(depth === 0);
  const hasChildren = node.children.length > 0;
  const isLeaf = !hasChildren;
  const label = isLeaf ? stateLabel(node) : null;

  return (
    <div>
      <button
        type="button"
        onClick={() => hasChildren && setOpen(!open)}
        className={`flex items-center gap-2 w-full text-left py-1.5 px-2 rounded text-sm hover:bg-border/30 transition-colors ${
          hasChildren ? "cursor-pointer" : "cursor-default"
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren && (
          <span className="text-text-secondary text-xs w-4 text-center">
            {open ? "\u25BE" : "\u25B8"}
          </span>
        )}
        {!hasChildren && <span className="w-4" />}

        <span className={`flex-1 ${depth === 0 ? "font-medium" : ""}`}>
          {node.name}
        </span>

        {isLeaf && (
          <>
            <span className="text-xs text-text-secondary">
              {node.eval_count} eval{node.eval_count !== 1 ? "s" : ""}
            </span>
            {node.eval_count > 0 && (
              <span className="text-xs text-text-secondary">
                disc: {node.avg_discrimination.toFixed(3)}
              </span>
            )}
            {label && (
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${label.className}`}
              >
                {label.text}
              </span>
            )}
          </>
        )}
      </button>

      {open &&
        hasChildren &&
        node.children.map((child) => (
          <TreeNode key={child.id} node={child} depth={depth + 1} />
        ))}
    </div>
  );
}

export function TaxonomyTree({ taxonomy }: TreeProps) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h3 className="text-sm font-medium text-text-secondary mb-2">
        Taxonomy Tree
      </h3>
      <div className="space-y-0.5">
        {taxonomy.map((node) => (
          <TreeNode key={node.id} node={node} depth={0} />
        ))}
      </div>
    </div>
  );
}
