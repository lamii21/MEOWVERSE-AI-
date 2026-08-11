import { notFound } from "next/navigation";

import { PublicStoryView } from "@/features/story/components/PublicStoryView";
import { StoryApiError, fetchPublicStory } from "@/services/stories";

export default async function PublicStoryPage({ params }: PageProps<"/story/[id]">) {
  const { id } = await params;

  let story;
  try {
    story = await fetchPublicStory(id);
  } catch (err) {
    if (err instanceof StoryApiError && err.kind === "not_found") {
      notFound();
    }
    throw err;
  }

  return (
    <div className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center justify-center px-4 py-16">
      <PublicStoryView story={story} />
    </div>
  );
}
