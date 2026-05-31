import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

interface Envelope<T> {
  v: T;
  t: number;
}

function read<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const env = JSON.parse(raw) as Envelope<T>;
    if (!env || typeof env !== "object" || !("v" in env)) return null;
    return env.v;
  } catch {
    return null;
  }
}

function write<T>(key: string, value: T): void {
  try {
    const env: Envelope<T> = { v: value, t: Date.now() };
    localStorage.setItem(key, JSON.stringify(env));
  } catch {
    // quota, disabled storage, etc. — best effort
  }
}

/** useState-like hook that mirrors its value to localStorage. */
export function useLocalStorage<T>(
  key: string | null,
  initial: T,
  options?: { debounceMs?: number },
): [T, Dispatch<SetStateAction<T>>, () => void] {
  const debounceMs = options?.debounceMs ?? 0;

  const [value, setValue] = useState<T>(() => {
    if (!key) return initial;
    const stored = read<T>(key);
    return stored !== null ? stored : initial;
  });

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const keyRef = useRef(key);
  keyRef.current = key;

  useEffect(() => {
    if (!key) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    if (debounceMs > 0) {
      timerRef.current = setTimeout(() => write(key, value), debounceMs);
    } else {
      write(key, value);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [key, value, debounceMs]);

  const clear = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (keyRef.current) {
      try {
        localStorage.removeItem(keyRef.current);
      } catch {
        // ignore
      }
    }
  }, []);

  return [value, setValue, clear];
}

/** Remove stale localStorage entries under `prefix`. */
export function purgeLocalStorage(prefix: string, maxAgeMs: number): void {
  try {
    const now = Date.now();
    const toRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith(prefix)) continue;
      try {
        const raw = localStorage.getItem(key);
        if (!raw) continue;
        const env = JSON.parse(raw) as Envelope<unknown>;
        if (!env || typeof env.t !== "number" || now - env.t > maxAgeMs) {
          toRemove.push(key);
        }
      } catch {
        toRemove.push(key);
      }
    }
    toRemove.forEach((k) => {
      try {
        localStorage.removeItem(k);
      } catch {
        // ignore
      }
    });
  } catch {
    // ignore
  }
}
