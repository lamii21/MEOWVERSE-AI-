import { notFound } from "next/navigation";

import { PublicCatView } from "@/features/results/components/PublicCatView";
import { AnalysisApiError, fetchPublicAnalysis } from "@/services/analyses";

export default async function PublicCatPage({ params }: PageProps<"/cat/[id]">) {
  const { id } = await params;

  let result;
  try {
    result = await fetchPublicAnalysis(id);
  } catch (err) {
    if (err instanceof AnalysisApiError && err.kind === "not_found") {
      notFound();
    }
    throw err;
  }

  return (
    <div className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center justify-center px-4 py-16">
      <PublicCatView result={result} />
    </div>
  );
}
