"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { PendingUploadProvider } from "@/hooks/use-pending-upload";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <PendingUploadProvider>{children}</PendingUploadProvider>
    </QueryClientProvider>
  );
}
