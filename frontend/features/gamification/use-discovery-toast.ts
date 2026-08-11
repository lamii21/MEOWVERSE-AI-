"use client";

import { useSyncExternalStore } from "react";

import { getSnapshot, subscribe } from "@/lib/discovery-toast-store";

export function useDiscoveryToast() {
  return useSyncExternalStore(subscribe, getSnapshot, () => null);
}
