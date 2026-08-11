/** Backend-persisted image URLs (Phase 9's ImageStorageProvider) come
 * back as relative paths (`/media/<key>.jpg`) — resolve them against
 * the API origin so they load regardless of which frontend origin is
 * currently serving the page. */
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("blob:")) {
    return url;
  }
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return `${apiUrl}${url}`;
}
