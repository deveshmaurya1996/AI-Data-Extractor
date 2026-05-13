"use client";

import { useEffect, useState } from "react";
import { format, formatDistanceToNow } from "date-fns";
import { enUS } from "date-fns/locale";

type ClientRelativeTimeProps = {
  date: Date;
  className?: string;
};

export function ClientRelativeTime({
  date,
  className,
}: ClientRelativeTimeProps) {
  const timeMs = date.getTime();
  const [label, setLabel] = useState(() =>
    format(date, "MMM d, yyyy · h:mm a", { locale: enUS }),
  );

  useEffect(() => {
    const at = new Date(timeMs);
    const tick = () => setLabel(formatDistanceToNow(at, { addSuffix: true }));

    tick();
    const id = setInterval(tick, 60_000);
    return () => clearInterval(id);
  }, [timeMs]);

  return <span className={className}>{label}</span>;
}
