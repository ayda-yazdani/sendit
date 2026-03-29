import { useEffect } from "react";
import { supabase } from "../supabase";

type PostgresChangeEvent = "INSERT" | "UPDATE" | "DELETE" | "*";

interface UseRealtimeOptions {
  table: string;
  filter?: string;
  event?: PostgresChangeEvent;
  onInsert?: (payload: any) => void;
  onUpdate?: (payload: any) => void;
  onDelete?: (payload: any) => void;
  onChange?: (payload: any) => void;
}

export function useRealtime({
  table,
  filter,
  event = "*",
  onInsert,
  onUpdate,
  onDelete,
  onChange,
}: UseRealtimeOptions) {
  useEffect(() => {
    const channelName = `${table}-${filter || "all"}-${Date.now()}`;

    const channel = supabase
      .channel(channelName)
      .on(
        "postgres_changes" as any,
        {
          event,
          schema: "public",
          table,
          ...(filter ? { filter } : {}),
        },
        (payload: any) => {
          onChange?.(payload);
          if (payload.eventType === "INSERT") onInsert?.(payload);
          if (payload.eventType === "UPDATE") onUpdate?.(payload);
          if (payload.eventType === "DELETE") onDelete?.(payload);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [table, filter, event]);
}
