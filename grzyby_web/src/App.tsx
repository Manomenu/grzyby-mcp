import { Center, Stack, Title } from "@mantine/core";

import { ServerStatus } from "./health/ServerStatus";

/** Puts the page together from features. Replace the content with the first real screen. */
export function App() {
    return (
        <Center h="100vh">
            <Stack align="center">
                <Title order={2}>grzyby</Title>
                <ServerStatus />
            </Stack>
        </Center>
    );
}
