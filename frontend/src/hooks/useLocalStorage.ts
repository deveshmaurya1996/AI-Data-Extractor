import { useCallback, useRef, useSyncExternalStore } from "react";

const MUTATION_EVENT = "local-storage-mutation";

type LsSnap = { k: string; p: 0 | 1; v: string | null };

function emitMutation(key: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<{ key: string }>(MUTATION_EVENT, { detail: { key } }),
  );
}

function parseSnap<T>(snap: string, initialValue: T): T {
  try {
    const { p, v } = JSON.parse(snap) as LsSnap;
    if (p === 0 || v === null) return initialValue;
    return JSON.parse(v) as T;
  } catch {
    return initialValue;
  }
}

export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((val: T) => T)) => void] {
  const unreadRef = useRef(true);
  const microtaskGenRef = useRef(0);

  const getServerSnapshot = useCallback(
    () => JSON.stringify({ k: key, p: 0, v: null } satisfies LsSnap),
    [key],
  );

  const getSnapshot = useCallback(() => {
    if (typeof window === "undefined") return getServerSnapshot();
    if (unreadRef.current) return getServerSnapshot();
    try {
      const v = window.localStorage.getItem(key);
      return JSON.stringify({ k: key, p: 1, v } satisfies LsSnap);
    } catch {
      return getServerSnapshot();
    }
  }, [key, getServerSnapshot]);

  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      const gen = ++microtaskGenRef.current;
      queueMicrotask(() => {
        if (gen !== microtaskGenRef.current) return;
        unreadRef.current = false;
        onStoreChange();
      });

      const onStorage = (e: StorageEvent) => {
        if (e.key === null || e.key === key) onStoreChange();
      };
      const onMutate = (e: Event) => {
        const d = (e as CustomEvent<{ key: string }>).detail;
        if (d?.key === key) onStoreChange();
      };

      window.addEventListener("storage", onStorage);
      window.addEventListener(MUTATION_EVENT, onMutate as EventListener);
      return () => {
        microtaskGenRef.current += 1;
        window.removeEventListener("storage", onStorage);
        window.removeEventListener(MUTATION_EVENT, onMutate as EventListener);
        unreadRef.current = true;
      };
    },
    [key],
  );

  const snap = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const storedValue = parseSnap<T>(snap, initialValue);

  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      if (typeof window === "undefined") return;
      try {
        let current: T = initialValue;
        const raw = window.localStorage.getItem(key);
        if (raw) current = JSON.parse(raw) as T;
        const valueToStore =
          value instanceof Function ? value(current) : value;
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
        emitMutation(key);
      } catch (error) {
        console.log(error);
      }
    },
    [key, initialValue],
  );

  return [storedValue, setValue];
}
