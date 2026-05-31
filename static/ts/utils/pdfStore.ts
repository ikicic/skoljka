/** IndexedDB PDF store for the import wizard. */

const DB_NAME = "pdfImport";
const STORE = "pdfs";
const DB_VERSION = 1;

interface PdfEntry {
  data: ArrayBuffer;
  savedAt: number;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function request<T>(
  mode: IDBTransactionMode,
  run: (store: IDBObjectStore) => IDBRequest,
): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const store = tx.objectStore(STORE);
        const req = run(store);
        req.onsuccess = () => resolve(req.result as T);
        req.onerror = () => reject(req.error);
      }),
  );
}

export async function savePdf(
  jobId: string,
  data: ArrayBuffer,
): Promise<void> {
  const entry: PdfEntry = { data, savedAt: Date.now() };
  await request<IDBValidKey>("readwrite", (s) => s.put(entry, jobId));
}

export async function loadPdf(jobId: string): Promise<ArrayBuffer | null> {
  try {
    const entry = await request<PdfEntry | undefined>("readonly", (s) =>
      s.get(jobId),
    );
    return entry?.data ?? null;
  } catch {
    return null;
  }
}

export async function deletePdf(jobId: string): Promise<void> {
  try {
    await request<undefined>("readwrite", (s) => s.delete(jobId));
  } catch {
    // best-effort
  }
}

export async function purgePdfs(olderThanMs: number): Promise<void> {
  const cutoff = Date.now() - olderThanMs;
  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      const store = tx.objectStore(STORE);
      const cursorReq = store.openCursor();
      cursorReq.onsuccess = () => {
        const cursor = cursorReq.result;
        if (!cursor) {
          resolve();
          return;
        }
        const entry = cursor.value as PdfEntry | undefined;
        if (!entry || typeof entry.savedAt !== "number" || entry.savedAt < cutoff) {
          cursor.delete();
        }
        cursor.continue();
      };
      cursorReq.onerror = () => reject(cursorReq.error);
    });
  } catch {
    // ignore
  }
}
