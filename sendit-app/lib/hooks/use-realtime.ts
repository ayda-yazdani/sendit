import { useEffect } from "react";

interface UseRealtimeOptions {
  table: string;
  filter?: string;
  event?: "INSERT" | "UPDATE" | "DELETE" | "*";
  onInsert?: (payload: unknown) => void;
  onUpdate?: (payload: unknown) => void;
  onDelete?: (payload: unknown) => void;
  onChange?: (payload: unknown) => void;
}

export function useRealtime(_options: UseRealtimeOptions) {
  useEffect(() => {
    return () => undefined;
  }, []);
}
