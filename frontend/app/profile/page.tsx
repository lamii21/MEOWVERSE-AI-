"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen, Cat, Crown, Gem, Heart, Palette, Sparkles } from "lucide-react";
import Link from "next/link";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RequireAuth } from "@/features/auth/components/RequireAuth";
import { ProgressCard } from "@/features/gamification/components/ProgressCard";
import { useAuth } from "@/hooks/use-auth";
import { resolveMediaUrl } from "@/lib/media";
import { fetchAchievements, fetchCollection, fetchProgress, fetchStats } from "@/services/collection";
import { cn } from "@/lib/utils";

function initialsOf(name: string): string {
  return name.trim().slice(0, 1).toUpperCase() || "?";
}

function formatJoinedDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function StatTile({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Cat;
  label: string;
  value: string | number;
}) {
  return (
    <div className="glass rounded-2xl p-4 text-center">
      <Icon className="mx-auto size-5 text-magic-500" aria-hidden="true" />
      <p className="mt-2 font-heading text-xl font-bold">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function ProfileContent() {
  const { user } = useAuth();
  const statsQuery = useQuery({ queryKey: ["stats"], queryFn: fetchStats });
  const achievementsQuery = useQuery({ queryKey: ["achievements"], queryFn: fetchAchievements });
  const progressQuery = useQuery({ queryKey: ["progress"], queryFn: fetchProgress });
  const favoriteCatQuery = useQuery({
    queryKey: ["favorite-cat-preview"],
    queryFn: () => fetchCollection({ favoritesOnly: true, sort: "newest", page: 1, pageSize: 1 }),
  });
  const favoriteCat = favoriteCatQuery.data?.items[0] ?? null;

  if (!user) return null;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-12">
      <div className="glass flex flex-col items-center gap-3 rounded-3xl p-8 text-center">
        <Avatar size="lg">
          {user.avatar_url && <AvatarImage src={user.avatar_url} alt="" />}
          <AvatarFallback className="text-lg">{initialsOf(user.display_name)}</AvatarFallback>
        </Avatar>
        <h1 className="font-heading text-2xl font-bold">{user.display_name}</h1>
        <p className="text-sm text-muted-foreground">
          Cat explorer since {formatJoinedDate(user.created_at)}
        </p>
      </div>

      {progressQuery.data && <ProgressCard progress={progressQuery.data} />}

      {statsQuery.data && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile icon={Cat} label="Cats discovered" value={statsQuery.data.total_cats} />
          <StatTile icon={Heart} label="Favorites" value={statsQuery.data.favorites_count} />
          <StatTile icon={Gem} label="Rare+" value={statsQuery.data.rare_count} />
          <StatTile icon={Crown} label="Legendary+" value={statsQuery.data.legendary_count} />
          <StatTile icon={BookOpen} label="Stories" value={statsQuery.data.stories_created} />
          <StatTile
            icon={Sparkles}
            label="MeowVerse explored"
            value={`${statsQuery.data.completion_percentage}%`}
          />
          <StatTile
            icon={Cat}
            label="Breeds found"
            value={`${statsQuery.data.unique_breeds_discovered}/${statsQuery.data.total_supported_breeds}`}
          />
          <StatTile icon={Palette} label="Colors found" value={statsQuery.data.unique_colors_discovered} />
        </div>
      )}

      {statsQuery.data && (statsQuery.data.favorite_breed || statsQuery.data.most_common_color) && (
        <div className="glass flex flex-wrap items-center justify-center gap-4 rounded-2xl p-4 text-sm text-muted-foreground">
          {statsQuery.data.favorite_breed && (
            <span className="flex items-center gap-1.5">
              <Cat className="size-4" aria-hidden="true" />
              Favorite breed: <strong className="text-foreground">{statsQuery.data.favorite_breed}</strong>
            </span>
          )}
          {statsQuery.data.most_common_color && (
            <span className="flex items-center gap-1.5">
              <Palette className="size-4" aria-hidden="true" />
              Most common color:{" "}
              <strong className="text-foreground">{statsQuery.data.most_common_color}</strong>
            </span>
          )}
        </div>
      )}

      {favoriteCat && (
        <Link
          href={`/collection/${favoriteCat.id}`}
          className="glass flex items-center gap-4 rounded-2xl p-4 transition-transform hover:-translate-y-0.5"
        >
          <div className="flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-magic-200 to-peach-200 text-2xl dark:from-magic-900/60 dark:to-peach-900/40">
            {favoriteCat.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={resolveMediaUrl(favoriteCat.image_url) ?? undefined}
                alt=""
                className="size-full object-cover"
              />
            ) : (
              <span aria-hidden="true">🐱</span>
            )}
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Your favorite cat</p>
            <p className="font-heading text-sm font-semibold">{favoriteCat.profile.name}</p>
            <p className="text-xs text-muted-foreground">{favoriteCat.profile.rarity}</p>
          </div>
        </Link>
      )}

      <Separator />

      <div id="achievements">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-lg font-semibold">Achievements</h2>
          <Link href="/achievements" className="text-xs font-medium text-magic-600 hover:underline dark:text-magic-300">
            View all
          </Link>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {achievementsQuery.data?.map((achievement) => (
            <div
              key={achievement.key}
              className={cn(
                "flex items-center gap-3 rounded-2xl border p-3",
                achievement.unlocked
                  ? "border-magic-300 bg-magic-50 dark:bg-magic-900/20"
                  : "border-border opacity-60",
              )}
            >
              <span className="text-2xl" aria-hidden="true">
                {achievement.emoji}
              </span>
              <div>
                <p className="text-sm font-medium">{achievement.label}</p>
                <p className="text-xs text-muted-foreground">{achievement.description}</p>
              </div>
              {achievement.unlocked && (
                <Badge variant="secondary" className="ml-auto shrink-0">
                  Unlocked
                </Badge>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <RequireAuth>
      <ProfileContent />
    </RequireAuth>
  );
}
