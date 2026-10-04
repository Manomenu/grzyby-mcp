/// <reference types="vite/client" />

interface ImportMetaEnv {
    /** Where the API lives. Unset in every real setup — the vite proxy and nginx both serve it at /api. */
    readonly VITE_API_BASE?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
