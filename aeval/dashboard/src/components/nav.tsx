"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/runs", label: "Runs" },
  { href: "/models", label: "Models" },
  { href: "/compare", label: "Compare" },
  { href: "/scorecard", label: "Scorecard" },
  { href: "/taxonomy", label: "Taxonomy" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <aside className="w-48 bg-surface border-r border-border p-4 flex flex-col gap-1">
      <h1 className="text-lg font-bold mb-4 text-text-primary">aeval</h1>
      {links.map((link) => {
        const active =
          link.href === "/"
            ? pathname === "/"
            : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`block px-3 py-2 rounded text-sm no-underline ${
              active
                ? "bg-accent/20 text-accent font-medium"
                : "text-text-secondary hover:text-text-primary hover:bg-border/50"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </aside>
  );
}
