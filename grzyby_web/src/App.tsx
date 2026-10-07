import { Anchor, Box, Button, Container, Divider, Paper, Stack, Text, Title } from "@mantine/core";

import { ServerDownAlert, ServerStatus } from "./health/ServerStatus";
import { useServerStatus } from "./health/useServerStatus";
import { InstallGuide } from "./install/InstallGuide";
import { SearchPage } from "./miejsca/SearchPage";

// Photos beside the panel where the screen has room for them (Mantine's lg: 1200 px and up); on a
// phone the panel takes the whole width. Each fades into the page's dark green towards the panel.
const PHOTOS = [
    { side: "left", src: "/img/las.webp", fade: "to right" },
    { side: "right", src: "/img/borowik.webp", fade: "to left" },
] as const;

function SidePhoto({ side, src, fade }: (typeof PHOTOS)[number]) {
    return (
        <Box
            visibleFrom="lg"
            className="side-photo"
            aria-hidden
            pos="fixed"
            top={0}
            bottom={0}
            {...{ [side]: 0 }}
            // The panel is Container size="sm": 45rem.
            w="calc((100vw - 45rem) / 2)"
            style={{
                backgroundImage: `linear-gradient(${fade}, transparent 55%, var(--mantine-color-body)), url(${src})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
            }}
        />
    );
}

function Credits() {
    return (
        <Text size="xs" c="dimmed">
            Dane: Bank Danych o Lasach, GDOŚ, Open-Meteo, © autorzy OpenStreetMap, © CARTO. Zdjęcia z Wikimedia Commons, CC BY-SA 4.0:{" "}
            <Anchor href="https://commons.wikimedia.org/wiki/File:Bruderwald-Herbst-026375.jpg" target="_blank" rel="noreferrer" inherit>
                las — Ermell
            </Anchor>
            ,{" "}
            <Anchor
                href="https://commons.wikimedia.org/wiki/File:Bayerischer_Spessart_Naturpark,_Gemeine_Steinpilz_(Boletus_edulis).jpg"
                target="_blank"
                rel="noreferrer"
                inherit
            >
                borowik — Thomas Fuhrmann
            </Anchor>
            . Kod:{" "}
            <Anchor href="https://github.com/Manomenu/grzyby-mcp" target="_blank" rel="noreferrer" inherit>
                github.com/Manomenu/grzyby-mcp
            </Anchor>
            .
        </Text>
    );
}

// The search without a chatbot has a page of its own: the tool and nothing else.
const SEARCH_PATH = "/szukaj";

/** Picks the page by its address; nginx and Vite serve index.html for both. */
export function App() {
    return window.location.pathname === SEARCH_PATH ? <SearchPage /> : <Home />;
}

/** The front page, put together from features: what this is, the search, how to add it to a chatbot. */
function Home() {
    const status = useServerStatus();
    return (
        <>
            {PHOTOS.map((photo) => (
                <SidePhoto key={photo.side} {...photo} />
            ))}
            <Container size="sm" px="xs" py={{ base: "xs", sm: "xl" }} pos="relative">
                <Stack gap="md">
                    <ServerDownAlert status={status} />
                    <Paper bg="var(--grzyby-paper)" c="var(--grzyby-ink)" radius="lg" shadow="xl" p={{ base: "lg", sm: 40 }}>
                        <Stack gap="xl">
                            <Stack gap="sm">
                                <Text size="sm" fw={600} tt="uppercase" c="moss.8" style={{ letterSpacing: "0.12em" }}>
                                    dla grzybiarzy, w Twoim chatbocie
                                </Text>
                                <Title order={1} fz={{ base: 40, sm: 56 }} lh={1.05} c="moss.9">
                                    Gdzie na grzyby
                                </Title>
                                <Text size="lg" lh={1.6}>
                                    Pytasz „gdzie na podgrzybki koło Suwałk?”, a dostajesz mapę lasów pokolorowaną według szans,
                                    ponumerowane najlepsze miejsca z uzasadnieniem i trasę w Google Maps. Cała Polska, za darmo, bez konta.
                                </Text>
                                <Button component="a" href={SEARCH_PATH} size="lg" radius="xl" mt="xs" style={{ alignSelf: "flex-start" }}>
                                    Szukaj bez chatbota →
                                </Button>
                            </Stack>
                            <Stack gap="sm">
                                <Title order={2} c="moss.9">
                                    Jak podłączyć
                                </Title>
                                <InstallGuide />
                            </Stack>
                            <Divider color="#e2d9c3" />
                            <Stack gap="xs">
                                <Credits />
                                <ServerStatus status={status} />
                            </Stack>
                        </Stack>
                    </Paper>
                </Stack>
            </Container>
        </>
    );
}
