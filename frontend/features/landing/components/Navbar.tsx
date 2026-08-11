import Link from "next/link";

import { Button } from "@/components/ui/button";

const links = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#capabilities", label: "AI capabilities" },
  { href: "#faq", label: "FAQ" },
];

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 w-full">
      <nav className="glass mx-auto mt-4 flex max-w-6xl items-center justify-between rounded-2xl px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-heading text-lg font-semibold">
          <span aria-hidden="true">🐾</span>
          MeowVerse AI
        </Link>

        <ul className="hidden items-center gap-6 text-sm font-medium text-muted-foreground md:flex">
          {links.map((link) => (
            <li key={link.href}>
              <a href={link.href} className="transition-colors hover:text-foreground">
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <Button
          size="sm"
          className="rounded-full"
          nativeButton={false}
          render={<Link href="/discover" />}
        >
          Discover My Cat
        </Button>
      </nav>
    </header>
  );
}
