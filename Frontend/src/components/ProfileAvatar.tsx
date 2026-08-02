"use client";

import { useEffect, useState } from "react";
import type { User } from "@/lib/api/types";
import * as authApi from "@/lib/api/auth";
import { cn } from "@/lib/utils/format";

export function ProfileAvatar({ user, className }: { user: User; className?: string }) {
  const [loadedImage, setLoadedImage] = useState<{ version: string; url: string } | null>(null);
  const version = user.profile_picture_version ?? null;
  const imageUrl = loadedImage?.version === version ? loadedImage.url : null;

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;

    if (version) {
      authApi.profilePicture(version)
        .then((blob) => {
          if (!active) return;
          objectUrl = URL.createObjectURL(blob);
          setLoadedImage({ version, url: objectUrl });
        })
        .catch(() => undefined);
    }

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [version]);

  return (
    <span
      className={cn(
        "inline-flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e6efe9] text-sm font-black text-[#17453a] ring-1 ring-[#17453a]/10",
        className,
      )}
    >
      {imageUrl ? (
        // This is an authenticated object URL, so Next image optimization is not applicable.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imageUrl} alt={`${user.name}'s profile picture`} className="h-full w-full object-cover" />
      ) : (
        <span aria-hidden="true">{user.name.slice(0, 1).toUpperCase()}</span>
      )}
    </span>
  );
}
