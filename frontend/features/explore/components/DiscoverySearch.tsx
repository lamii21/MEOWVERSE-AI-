import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

export function DiscoverySearch({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="relative w-full sm:max-w-xs">
      <Search
        className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search cats..."
        className="pl-8"
        aria-label="Search public cats"
      />
    </div>
  );
}
