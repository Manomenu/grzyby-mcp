import "@mantine/core/styles.css";
// Self-hosted, so no request to a font service: Fraunces for headings, Source Sans 3 for text —
// both OFL, both with every Polish letter.
import "@fontsource-variable/fraunces";
import "@fontsource-variable/source-sans-3";

import { type CSSVariablesResolver, MantineProvider, createTheme } from "@mantine/core";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";

const theme = createTheme({
    // Moss green, darkest last; the shade at index 7 is the one buttons and tabs use.
    colors: {
        moss: ["#f1f6ec", "#e2ecd8", "#c4d9b0", "#a4c585", "#88b361", "#76a84b", "#6aa13f", "#4f7d2f", "#446e28", "#365c1d"],
    },
    primaryColor: "moss",
    primaryShade: 7,
    defaultRadius: "md",
    fontFamily: "'Source Sans 3 Variable', system-ui, sans-serif",
    headings: { fontFamily: "'Fraunces Variable', Georgia, serif", fontWeight: "600" },
});

// The page itself is the forest at dusk; the text sits on panels of warm paper, not screen white.
const resolver: CSSVariablesResolver = () => ({
    variables: { "--grzyby-paper": "#f8f3e6", "--grzyby-ink": "#2a2a22" },
    light: { "--mantine-color-body": "#18211a" },
    dark: {},
});

const root = document.getElementById("root");
if (!root) throw new Error("index.html has no #root element");

createRoot(root).render(
    <StrictMode>
        <MantineProvider theme={theme} cssVariablesResolver={resolver} forceColorScheme="light">
            <App />
        </MantineProvider>
    </StrictMode>,
);
