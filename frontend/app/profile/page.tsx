"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen, Cat, Crown, Heart, Palette } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RequireAuth } from "@/features/auth/components/RequireAuth";
import { useAuth } from "@/hooks/use-auth";
import { fetchAchievements, fetchStats } from "@/services/collection";
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

      {statsQuery.data && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile icon={Cat} label="Cats discovered" value={statsQuery.data.total_cats} />
          <StatTile icon={Heart} label="Favorites" value={statsQuery.data.favorites_count} />
          <StatTile icon={Crown} label="Legendary+" value={statsQuery.data.legendary_count} />
          <StatTile icon={BookOpen} label="Stories" value={statsQuery.data.stories_created} />
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

      <Separator />

      <div id="achievements">
        <h2 className="font-heading text-lg font-semibold">Achievements</h2>
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
