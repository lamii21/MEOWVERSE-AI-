"use client";

import { useEffect, useState } from "react";

/** Delays reflecting `value` until it's stopped changing for `delayMs`
 * — used to keep collection search from firing a server request on
 * every keystroke (Phase 10 spec §6). */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
