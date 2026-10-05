import { Alert, Group, Text } from "@mantine/core";

import { describe, type ServerStatus as Status } from "./status";

/** A quiet line at the foot of the page: a dot and a word. */
export function ServerStatus({ status }: { status: Status }) {
    const colour = status.kind === "up" ? "moss.6" : status.kind === "down" ? "red.7" : "gray.5";
    return (
        <Group gap={6} wrap="nowrap">
            <Text c={colour} size="xs" aria-hidden>
                ●
            </Text>
            <Text size="xs" c="dimmed">
                serwer: {describe(status)}
            </Text>
        </Group>
    );
}

/** When the server is down, the visitor should know before trying to connect: a banner on top. */
export function ServerDownAlert({ status }: { status: Status }) {
    if (status.kind !== "down") return null;
    return (
        <Alert color="red" variant="filled" title="Serwer teraz nie odpowiada" radius="lg">
            Odpowiedzi z mapą mogą chwilowo nie działać — spróbuj za kilka minut. Konektor możesz dodać już teraz.
        </Alert>
    );
}
