import { notFound } from "next/navigation";

import { PublicPortraitView } from "@/features/portrait/components/PublicPortraitView";
import { AnalysisApiError, fetchPublicAnalysis } from "@/services/analyses";
import { PortraitApiError, fetchPortrait } from "@/services/portrait";

export default async function PublicPortraitPage({ params }: PageProps<"/portrait/[id]">) {
  const { id } = await params;

  let portrait;
  try {
    portrait = await fetchPortrait(id);
  } catch (err) {
    if (err instanceof PortraitApiError && err.kind === "not_found") {
      notFound();
    }
    throw err;
  }

  if (portrait.status !== "succeeded" || !portrait.is_public) {
    notFound();
  }

  // The parent cat's own analysis may or may not also be public — a
  // portrait being shared never implies its source analysis is. Only
  // show cat name/breed/archetype context when that analysis is
  // *itself* independently public; otherwise the portrait still
  // renders on its own, with no private data borrowed from it.
  let catContext = null;
  try {
    catContext = await fetchPublicAnalysis(portrait.analysis_id);
  } catch (err) {
    if (!(err instanceof AnalysisApiError && err.kind === "not_found")) {
      throw err;
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center justify-center px-4 py-16">
      <PublicPortraitView portrait={portrait} catContext={catContext} />
    </div>
  );
}
