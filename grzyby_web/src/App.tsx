import { Anchor, Container, Group, Stack, Text, Title } from "@mantine/core";

import { ServerStatus } from "./health/ServerStatus";
import { InstallGuide } from "./install/InstallGuide";

/** Puts the page together from features: what this is, then how to add it to a chatbot. */
export function App() {
    return (
        <Container size="sm" py="xl">
            <Stack gap="lg">
                <Stack gap="xs">
                    <Title order={1}>Gdzie na grzyby</Title>
                    <Text>
                        Podpowiadacz dla grzybiarzy w Twoim chatbocie. Pytasz „gdzie na podgrzybki koło Suwałk?”, a dostajesz mapę lasów
                        pokolorowaną według szans, ponumerowane najlepsze miejsca z uzasadnieniem i trasę w Google Maps. Cała Polska, za
                        darmo, bez konta.
                    </Text>
                </Stack>
                <Stack gap="xs">
                    <Title order={2}>Jak podłączyć</Title>
                    <InstallGuide />
                </Stack>
                <Text size="sm" c="dimmed">
                    Dane: Bank Danych o Lasach, GDOŚ, Open-Meteo, © autorzy OpenStreetMap, © CARTO. Kod i zdjęcia:{" "}
                    <Anchor href="https://github.com/Manomenu/grzyby-mcp" target="_blank" rel="noreferrer">
                        github.com/Manomenu/grzyby-mcp
                    </Anchor>
                    .
                </Text>
                <Group>
                    <ServerStatus />
                </Group>
            </Stack>
        </Container>
    );
}
