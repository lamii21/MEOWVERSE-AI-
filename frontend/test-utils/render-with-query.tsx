import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";

import type { ReactElement } from "react";

/** Shared by every test that renders a component using TanStack Query
 * (auth state, collection/stats/achievements queries, save/favorite
 * mutations) — a fresh QueryClient per render so tests can't leak
 * cached data into one another, with retries off so a mocked rejection
 * surfaces immediately instead of being retried into a timeout. */
export function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}
